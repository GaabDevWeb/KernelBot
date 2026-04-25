#!/usr/bin/env python3
"""Ingere Markdown de content/ para MySQL (base e schema ja devem existir)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permite `python scripts/ingest_content.py` com imports relativos a scripts/
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from setup_local import (  # noqa: E402
    _configure_logging,
    _load_dotenv,
    _require_db_env_only,
    ingest_all_markdown,
)


def main() -> None:
    p = argparse.ArgumentParser(description="Ingestao Markdown → knowledge")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()
    _configure_logging(args.verbose)
    _require_db_env_only()
    _load_dotenv()
    ingest_all_markdown(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
