"""Guard that every standards reference in repo docs resolves on disk.

The development standards live in the `.standards` git submodule. When a framework
update relocates a standards file, a doc that still points at the old path rots
silently. This test fails fast on such a dangling reference.

It self-skips when the submodule is not checked out (e.g. CI running
`actions/checkout` without `submodules: recursive`), so it never false-fails where
`.standards/` is intentionally absent.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DOCS_WITH_REFERENCES = ("CLAUDE.md", "CONTRIBUTING.md")
_REFERENCE_PATTERN = re.compile(r"\.standards/[^\s`,)]+")


def _submodule_checked_out() -> bool:
    standards_dir = _REPO_ROOT / ".standards"
    return standards_dir.is_dir() and any(standards_dir.iterdir())


def _iter_references() -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    for doc_name in _DOCS_WITH_REFERENCES:
        doc_text = (_REPO_ROOT / doc_name).read_text(encoding="utf-8")
        for match in _REFERENCE_PATTERN.findall(doc_text):
            references.append((doc_name, match.rstrip(".,)")))
    return references


@pytest.mark.skipif(
    not _submodule_checked_out(),
    reason="`.standards` submodule is not checked out; nothing to resolve",
)
@pytest.mark.parametrize(("doc_name", "reference"), _iter_references())
def test_standards_reference_resolves(doc_name: str, reference: str) -> None:
    target = _REPO_ROOT / reference
    assert target.exists(), f"{doc_name} references a missing path: {reference}"
