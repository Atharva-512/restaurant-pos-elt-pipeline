"""
DE-003 : Bronze Layer -- Parquet Writer
=========================================

Writes DataFrames loaded from raw source files into the Bronze layer as
Parquet files, using pyarrow with snappy compression.

Layout convention:

    data/bronze/<report_name>/<source_file_stem>.parquet

Example:
    data/bronze/order_summary/Order_Summary_Report_2026-05.parquet
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

DEFAULT_BRONZE_ROOT = Path("data") / "bronze"


class ParquetWriteError(Exception):
    """Raised when a DataFrame cannot be written to Parquet in the Bronze layer."""


def write_parquet(
    report_name: str,
    source_file: Path,
    dataframe: pd.DataFrame,
    overwrite: bool = False,
    bronze_root: Path = DEFAULT_BRONZE_ROOT,
) -> Path:
    """
    Write a DataFrame to the Bronze layer as a Parquet file.

    The destination folder `data/bronze/<report_name>/` is created
    automatically if it does not already exist. The output filename
    reuses the source file's stem, e.g. "Order_Summary_Report_2026-05.csv"
    -> "Order_Summary_Report_2026-05.parquet".

    Args:
        report_name: Logical report/table name; used as the Bronze
                     sub-folder (e.g. "order_summary").
        source_file: Path to the original raw source file (used only to
                     derive the output filename).
        dataframe: The DataFrame to persist. Column names/order are
                   preserved exactly as given.
        overwrite: If False (default) and the destination file already
                   exists, a FileExistsError is raised. If True, the
                   existing file is replaced.
        bronze_root: Root directory of the Bronze layer.

    Returns:
        Path to the written Parquet file.

    Raises:
        ValueError: If `dataframe` is None or not a pandas DataFrame,
                    or if `report_name` is empty.
        FileExistsError: If the destination already exists and
                          `overwrite` is False.
        ParquetWriteError: If writing the Parquet file fails for any
                            other reason (wraps the underlying exception).
    """
    if not report_name or not report_name.strip():
        raise ValueError("report_name must be a non-empty string.")
    if not isinstance(dataframe, pd.DataFrame):
        raise ValueError(f"Expected a pandas DataFrame, got: {type(dataframe)}")

    source_file = Path(source_file)
    destination_dir = Path(bronze_root) / report_name
    destination_file = destination_dir / f"{source_file.stem}.parquet"

    if destination_file.exists() and not overwrite:
        raise FileExistsError(
            f"Bronze file already exists (use overwrite=True to replace): "
            f"{destination_file}"
        )

    try:
        destination_dir.mkdir(parents=True, exist_ok=True)

        table = pa.Table.from_pandas(dataframe, preserve_index=False)
        pq.write_table(table, destination_file, compression="snappy")

        logger.info(
            "Wrote Bronze parquet: %s (%d rows, %d cols)",
            destination_file,
            len(dataframe),
            len(dataframe.columns),
        )
        return destination_file

    except (OSError, pa.ArrowException) as exc:
        logger.error("Failed to write Parquet file %s: %s", destination_file, exc)
        raise ParquetWriteError(
            f"Failed to write Bronze parquet for '{source_file.name}' "
            f"(report='{report_name}'): {exc}"
        ) from exc
