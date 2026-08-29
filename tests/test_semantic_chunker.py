"""PDF discovery and exit codes for the indexer (issue #100).

The defect: `process_folder` globbed ``**/*.pdf`` beneath its argument, so a path
to a PDF matched nothing. `python scripts/ingest.py ./archives/some.pdf` logged a
warning and exited ``0`` having indexed nothing, and the documentation advertised
that exact form. A mistyped directory behaved identically, which is the worse
half: the operator gets an empty collection, a success, and a ``/chat`` that
answers from no context.

These tests reach neither Ollama nor Qdrant. Discovery is pure, and the exit-code
cases fail during discovery, before anything tries to embed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from database.semantic_chunker import discover_pdfs, main


def _touch(path: Path, content: bytes = b"%PDF-1.4 stub") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_a_pdf_file_path_is_indexed(tmp_path: Path) -> None:
    """The form the documentation used to advertise, and that indexed nothing."""
    pdf = _touch(tmp_path / "boletim.pdf")
    assert discover_pdfs(pdf) == [pdf]


def test_a_directory_is_searched_recursively(tmp_path: Path) -> None:
    """The behaviour that already worked must keep working, nested files included."""
    first = _touch(tmp_path / "a.pdf")
    nested = _touch(tmp_path / "sub" / "b.pdf")
    _touch(tmp_path / "notes.txt", b"not a pdf")

    found = discover_pdfs(tmp_path)

    assert found == sorted([first, nested]), "discovery must be deterministic"


def test_a_non_pdf_file_is_not_indexed(tmp_path: Path) -> None:
    """Pointing at the wrong file must not be treated as a corpus."""
    assert discover_pdfs(_touch(tmp_path / "notes.txt", b"hello")) == []


def test_a_missing_path_yields_nothing(tmp_path: Path) -> None:
    """A typo resolves to nothing rather than raising; main turns it into an exit code."""
    assert discover_pdfs(tmp_path / "no-such-place") == []


def test_a_directory_without_pdfs_yields_nothing(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    assert discover_pdfs(tmp_path / "empty") == []


@pytest.mark.parametrize(
    ("case", "make"),
    [
        ("missing path", lambda tmp: tmp / "no-such-place"),
        ("not a pdf", lambda tmp: _touch(tmp / "notes.txt", b"hello")),
        ("empty directory", lambda tmp: (tmp / "empty").mkdir() or (tmp / "empty")),
    ],
)
def test_an_empty_result_ends_the_run_non_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], case: str, make
) -> None:
    """Exiting 0 on an empty match is the defect; the message must name the path."""
    target = make(tmp_path)

    exit_code = main(["index", str(target)])

    assert exit_code != 0, f"{case}: indexing nothing reported success"
    assert str(target) in capsys.readouterr().err, f"{case}: the message does not name the path"


def test_the_wrapper_propagates_the_exit_code(tmp_path: Path, monkeypatch) -> None:
    """scripts/ingest.py must not swallow the failure it is a wrapper for."""
    import scripts.ingest as ingest

    monkeypatch.setattr(ingest.sys, "argv", ["ingest.py", str(tmp_path / "no-such-place")])
    with pytest.raises(SystemExit) as excinfo:
        ingest.main()
    assert excinfo.value.code != 0


def test_no_argument_still_prints_help_and_fails(capsys: pytest.CaptureFixture[str]) -> None:
    """`main` with no subcommand must not look like a successful run either."""
    assert main([]) != 0
    assert "usage" in capsys.readouterr().out.lower()
