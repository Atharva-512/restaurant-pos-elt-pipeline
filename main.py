"""
main.py
=======

Entry point for the Restaurant POS ELT Pipeline.

Currently wires up the File Discovery Engine and the Reader Framework
(CSV / Excel readers + loader). Validation, transformations, Bronze-layer
persistence, and PostgreSQL loading are implemented in later stages.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

from src.ingestion.discovery import (
    NoSupportedFilesFoundError,
    RawDirectoryNotFoundError,
    discover_reports,
)
from src.ingestion.loader import load_reports

RAW_DATA_DIRECTORY = Path("data/raw")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("restaurant_pos_elt_pipeline")

# Keep console output clean; detailed logs still go through the logger above.
logging.getLogger("src.ingestion.discovery").setLevel(logging.WARNING)
logging.getLogger("src.ingestion.csv_reader").setLevel(logging.WARNING)
logging.getLogger("src.ingestion.excel_reader").setLevel(logging.WARNING)
logging.getLogger("src.ingestion.loader").setLevel(logging.WARNING)


def print_banner() -> None:
    """Print the pipeline header banner."""
    print("=================================")
    print("Restaurant POS ELT Pipeline")
    print("=================================")


def print_discovery_summary(discovered: dict[str, list[Path]]) -> None:
    """Print a one-line summary per report showing how many files were found."""
    for report_name in sorted(discovered):
        file_count = len(discovered[report_name])
        print(f"✓ {report_name} : {file_count} files")


def print_load_summary(loaded_reports: dict[str, list[pd.DataFrame]]) -> None:
    """
    Print a per-file load summary grouped by report name.

    For every successfully loaded file, prints the report name, file
    name, row count, and column count.
    """
    print("\n---------------------------------")
    print("Load Summary")
    print("---------------------------------")

    for report_name in sorted(loaded_reports):
        dataframes = loaded_reports[report_name]
        print(f"\nReport: {report_name}")

        if not dataframes:
            print("   (no files successfully loaded)")
            continue

        for dataframe in dataframes:
            file_name = dataframe.attrs.get("source_file", "unknown")
            rows, columns = dataframe.shape
            print(f"   File: {file_name:<30} Rows: {rows:<8} Columns: {columns}")


def main() -> int:
    """
    Run the discovery and loading stages of the pipeline.

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

    print_discovery_summary(discovered)
    print("Discovery completed successfully.")

    print("\nLoading files...")
    loaded_reports = load_reports(discovered)
    print_load_summary(loaded_reports)

    print("\nLoad completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
