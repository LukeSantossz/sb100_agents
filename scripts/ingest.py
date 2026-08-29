#!/usr/bin/env python
"""
PDF ingestion script.

This script wraps the semantic_chunker for easier command-line usage.
It provides a simpler interface for indexing documents.

Usage:
    python scripts/ingest.py ./archives/
    python scripts/ingest.py ./archives/smart_boletim.pdf

The argument is a directory, searched recursively, or a single PDF file. A path that
denotes no PDF ends the run with a non-zero exit code rather than indexing nothing
and reporting success.

The actual indexing logic is in database/semantic_chunker.py.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.semantic_chunker import main as chunker_main


def main() -> None:
    """Entry point for the ingest script.

    Exits with whatever the chunker returned. Swallowing it would restore the
    defect this wrapper is documented against: a run that indexed nothing
    reporting success (#100).
    """
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest.py <path>")
        print("  <path> can be a directory or a PDF file")
        sys.exit(1)

    sys.exit(chunker_main(["index"] + sys.argv[1:]))


if __name__ == "__main__":
    main()
