#!/usr/bin/env python
"""
PDF ingestion script.

This script wraps the semantic_chunker for easier command-line usage.
It provides a simpler interface for indexing documents.

Usage:
    python scripts/ingest.py ./archives/
    python scripts/ingest.py ./archives/document.pdf

The actual indexing logic is in database/semantic_chunker.py.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.semantic_chunker import main as chunker_main


def main() -> None:
    """Entry point for the ingest script."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest.py <path>")
        print("  <path> can be a directory or a PDF file")
        sys.exit(1)

    # Forward to semantic_chunker with 'index' command
    sys.argv = [sys.argv[0], "index"] + sys.argv[1:]
    chunker_main()


if __name__ == "__main__":
    main()
