"""
main.py
=======

Entry point for the Restaurant POS ELT Pipeline.

Currently wires up the File Discovery Engine only. Loading, Bronze-layer
ingestion, and PostgreSQL persistence are implemented in later stages.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from src.ingestion.discovery import (
    NoSupportedFilesFoundError,
    RawDirectoryNotFoundError,
    discover_reports,
)

RAW_DATA_DIRECTORY = Path("data/raw")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("restaurant_pos_elt_pipeline")

# Keep console output clean; detailed logs still go through the logger above.
logging.getLogger("src.ingestion.discovery").setLevel(logging.WARNING)


def print_banner() -> None:
    """Print the pipeline header banner."""
    print("=================================")
    print("Restaurant POS ELT Pipeline")
    print("=================================")


def main() -> int:
    """
    Run the discovery stage of the pipeline.

    Returns:
        Process exit code: 0 on success, 1 on failure.
    """
    print_banner()
    print("Scanning raw directory...")

    try:
        discovered = discover_reports(RAW_DATA_DIRECTORY)
    except RawDirectoryNotFoundError as exc:
        logger.error("Raw directory error: %s", exc)
        print(f"✗ Raw directory not found: {RAW_DATA_DIRECTORY}")
        return 1
    except NoSupportedFilesFoundError as exc:
        logger.error("No supported files found: %s", exc)
        print("✗ No supported .csv or .xlsx files were found.")
        return 1

    for report_name in sorted(discovered):
        file_count = len(discovered[report_name])
        print(f"✓ {report_name} : {file_count} files")

    print("Discovery completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
