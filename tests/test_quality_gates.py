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
_NOT_DOMAIN_CODE = {"tests", "eval", "scripts"}


def _pyproject() -> dict:
    return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))


def _coverage_floor() -> int:
    addopts = _pyproject()["tool"]["pytest"]["ini_options"]["addopts"]
    for option in addopts:
        match = re.fullmatch(r"--cov-fail-under=(\d+)", option.strip())
        if match:
            return int(match.group(1))
    raise AssertionError("no --cov-fail-under in the pytest addopts")


def _domain_packages() -> set[str]:
    """Top-level directories holding Python modules, read from disk rather than listed.

    Derived so the gates cannot silently stop covering a package somebody adds: a
    hand-written list is what let ``database`` and ``ui`` sit outside coverage.
    """
    return {
        path.name
        for path in _REPO_ROOT.iterdir()
        if path.is_dir()
        and not path.name.startswith((".", "_"))
        and path.name not in _NOT_DOMAIN_CODE
        and any(path.glob("*.py"))
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
