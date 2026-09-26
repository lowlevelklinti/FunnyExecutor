"""Funny Executor entrypoint: launches the pytauri window with the FAPI backend."""

import sys
from pathlib import Path

# Put the executor engine (FAPI) on the import path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from backend.app import main

if __name__ == "__main__":
    sys.exit(main())
