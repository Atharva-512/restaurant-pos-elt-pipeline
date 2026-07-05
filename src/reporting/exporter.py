"""
Reporting Layer Exporter.

Generic CSV exporting utilities for the Reporting Layer. This module
knows nothing about DuckDB, the Warehouse, or any project-specific
dataset — it only operates on already-created pandas DataFrames and
filesystem paths.
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def ensure_directory(path: Path) -> None:
    """
    Ensure a directory exists, creating nested folders as needed.

    Args:
        path: The directory path to create.

    Raises:
        OSError: If the directory cannot be created.
    """
    try:
        path.mkdir(parents=True, exist_ok=True)

    except OSError:
        logger.exception("Failed to create directory: %s", path)
        raise


def export_dataframe_to_csv(
    dataframe: pd.DataFrame,
    output_path: Path,
    index: bool = False,
) -> None:
    """
    Export a DataFrame to a CSV file, overwriting any existing file.

    The parent directory of ``output_path`` is created automatically
    if it does not already exist.

    Args:
        dataframe: The DataFrame to export.
        output_path: The destination CSV file path.
        index: Whether to include the DataFrame index in the output.
            Defaults to ``False``.

    Raises:
        OSError: If the destination directory cannot be created or
            the file cannot be written.
        Exception: If the CSV export otherwise fails.
    """
    ensure_directory(output_path.parent)

    try:
        dataframe.to_csv(
            output_path,
            index=index,
            encoding="utf-8",
        )

    except Exception:
        logger.exception("Failed to export CSV: %s", output_path)
        raise

    logger.info(
        "Published reporting dataset '%s' | Rows: %d",
        output_path.name,
        len(dataframe),
    )
