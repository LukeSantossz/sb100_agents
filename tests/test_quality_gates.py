"""The quality gates must describe the code, not a weaker version of it (issue #133).

Two drifts this file exists to stop, both of which had happened:

- The coverage floor sat at 23 while measured coverage was near 90, so a
  regression could delete most of the tested behaviour and still pass.
- `pyproject.toml` declared seven packages strict while CI type-checked three, so
  four of them passed strict only on a developer's machine.

Both are configuration agreeing with itself, which no other test looks at.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_CI_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci.yml"

_MINIMUM_FLOOR = 70

# Directories at the repository root that hold Python but are not the product:
# the test suite itself, the offline evaluation harness, and one-shot entry points.
# Everything else with modules in it is domain code and belongs to the gates.
# __pycache__ is named explicitly rather than skipped by its leading underscore,
# because a package legitimately named _something must still be discovered.
_NOT_DOMAIN_CODE = {"tests", "eval", "scripts", "__pycache__"}


def _pyproject() -> dict:
    return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))


def _coverage_floor() -> int:
    addopts = _pyproject()["tool"]["pytest"]["ini_options"]["addopts"]
    for option in addopts:
        match = re.fullmatch(r"--cov-fail-under=(\d+)", option.strip())
        if match:
            return int(match.group(1))
    raise AssertionError("no --cov-fail-under in the pytest addopts")


def _domain_packages(root: Path = _REPO_ROOT) -> set[str]:
    """Top-level directories holding Python modules, read from disk rather than listed.

    Derived so the gates cannot silently stop covering a package somebody adds: a
    hand-written list is what let ``database`` and ``ui`` sit outside coverage.

    Searched recursively, and a leading underscore does not disqualify a name. Both
    matter for a package that does not exist yet: a directory whose modules all sit
    in sub-packages, or one named ``_internal``, would otherwise be skipped by the
    very check written to stop a package being forgotten.

    Args:
        root: Directory to search. A parameter so the discovery rules themselves can
            be tested against a tree built for the purpose.
    """
    return {
        path.name
        for path in root.iterdir()
        if path.is_dir()
        and not path.name.startswith(".")
        and path.name not in _NOT_DOMAIN_CODE
        and any(module for module in path.rglob("*.py") if "__pycache__" not in module.parts)
    }


def _coverage_scope() -> set[str]:
    """Packages the pytest addopts actually measure."""
    addopts = _pyproject()["tool"]["pytest"]["ini_options"]["addopts"]
    return {
        match.group(1)
        for match in (re.fullmatch(r"--cov=(\w+)", option.strip()) for option in addopts)
        if match
    }


def _packages_declared_strict() -> set[str]:
    """Package names from every [[tool.mypy.overrides]] block with strict = true."""
    strict: set[str] = set()
    for override in _pyproject()["tool"]["mypy"].get("overrides", []):
        if not override.get("strict"):
            continue
        modules = override["module"]
        for module in [modules] if isinstance(modules, str) else modules:
            strict.add(module.removesuffix(".*"))
    return strict


def test_the_coverage_floor_is_at_least_seventy() -> None:
    """A floor far under the real number is a gate that cannot fail.

    It was 23 against roughly 90% measured. The exact target is the one the
    README already names.
    """
    assert _coverage_floor() >= _MINIMUM_FLOOR


def test_ci_type_checks_every_package_declared_strict() -> None:
    """Declaring a package strict and never checking it is a claim, not a gate."""
    workflow = _CI_WORKFLOW.read_text(encoding="utf-8")
    mypy_invocation = next(
        (line for line in workflow.splitlines() if line.strip().startswith("mypy ")),
        None,
    )
    assert mypy_invocation is not None, "no mypy invocation found in the CI workflow"

    missing = sorted(
        package for package in _packages_declared_strict() if f"{package}/" not in mypy_invocation
    )
    assert not missing, (
        f"pyproject declares these strict and CI never checks them: {missing}\n"
        f"CI runs: {mypy_invocation.strip()}"
    )


def test_the_typecheck_job_installs_the_project() -> None:
    """mypy without the dependencies checks a different program.

    Every third-party import resolves to Any, and strict mode's Any rules fire on
    different lines, so a green run would not mean green for a contributor.
    """
    workflow = _CI_WORKFLOW.read_text(encoding="utf-8")
    typecheck_job = workflow.split("  typecheck:", 1)[1].split("\n  test:", 1)[0]
    assert "pip install -e ." in typecheck_job, (
        "the typecheck job does not install the project, so mypy sees Any for every "
        "third-party import"
    )


def test_coverage_measures_every_package_holding_domain_code() -> None:
    """A package outside --cov contributes nothing to the number the gate checks.

    ``database`` and ``ui`` were both outside it, so the reported total described the
    other seven packages. ``database/semantic_chunker.py`` is the whole indexing
    pipeline and the only writer to the vector store, and it was invisible.
    """
    missing = sorted(_domain_packages() - _coverage_scope())
    assert not missing, (
        f"these hold domain code and no coverage flag measures them: {missing}\n"
        f"pytest addopts measure: {sorted(_coverage_scope())}"
    )


def test_domain_discovery_finds_a_package_whose_modules_are_all_nested(
    tmp_path: Path,
) -> None:
    """A package with no module directly inside it is still a package.

    ``glob("*.py")`` looked one level down, so a directory laid out as
    ``service/routes/handler.py`` would be reported as holding no Python and quietly
    excused from the gates, by the check written to prevent exactly that.
    """
    nested = tmp_path / "service" / "routes"
    nested.mkdir(parents=True)
    (nested / "handler.py").write_text("x = 1", encoding="utf-8")

    assert _domain_packages(tmp_path) == {"service"}


def test_domain_discovery_finds_a_package_named_with_a_leading_underscore(
    tmp_path: Path,
) -> None:
    """``__pycache__`` is what the underscore rule was aimed at, not ``_internal``."""
    (tmp_path / "_internal").mkdir()
    (tmp_path / "_internal" / "engine.py").write_text("x = 1", encoding="utf-8")
    cache = tmp_path / "_internal" / "__pycache__"
    cache.mkdir()
    (cache / "engine.cpython-312.py").write_text("x = 1", encoding="utf-8")

    assert _domain_packages(tmp_path) == {"_internal"}


def test_domain_discovery_ignores_a_directory_with_no_python(tmp_path: Path) -> None:
    """Compiled artefacts and data directories are not packages to cover."""
    (tmp_path / "archives").mkdir()
    (tmp_path / "archives" / "boletim.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "stale.py").write_text("x = 1", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "site.py").write_text("x = 1", encoding="utf-8")

    assert _domain_packages(tmp_path) == set()


def test_the_two_coverage_scopes_agree() -> None:
    """``[tool.coverage.run] source`` and the addopts are one setting written twice.

    When they disagree the effective scope is their union, which is nobody's stated
    intent and hides which list is stale.
    """
    source = set(_pyproject()["tool"]["coverage"]["run"]["source"])
    assert source == _coverage_scope(), (
        "coverage.run source and the --cov flags name different packages:\n"
        f"  source only: {sorted(source - _coverage_scope())}\n"
        f"  --cov only:  {sorted(_coverage_scope() - source)}"
    )


@pytest.mark.parametrize("package", sorted(_packages_declared_strict()))
def test_every_package_declared_strict_exists(package: str) -> None:
    """A strict override naming a package that is gone checks nothing, silently."""
    assert (_REPO_ROOT / package).is_dir(), (
        f"pyproject declares {package} strict; it does not exist"
    )
