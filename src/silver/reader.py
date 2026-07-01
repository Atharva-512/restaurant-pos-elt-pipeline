"""
reader.py
=========

Bronze Layer Reader.

Loads every Parquet dataset stored under the Bronze layer and groups
them by report type.

Example return value

{
    "order_summary": [
        {
            "file_name": "Order_Summary_Report_2026-05.parquet",
            "dataframe": DataFrame(...)
        },
        ...
    ]
}

The reader performs no transformations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def load_bronze_data(
    bronze_root: Path,
) -> dict[str, list[dict[str, Any]]]:
    """
    Load all Bronze parquet datasets.

    Parameters
    ----------
    bronze_root : Path
        Root Bronze directory.

    Returns
    -------
    dict
        Dictionary grouped by report folder.

        Example

        {
            "order_summary": [
                {
                    "file_name": "...",
                    "dataframe": df
                }
            ]
        }
    """

    bronze_data: dict[str, list[dict[str, Any]]] = {}

    if not bronze_root.exists():
        raise FileNotFoundError(
            f"Bronze directory does not exist: {bronze_root}"
        )

    for report_folder in sorted(bronze_root.iterdir()):

        if not report_folder.is_dir():
            continue

        report_name = report_folder.name

        bronze_data[report_name] = []

        parquet_files = sorted(report_folder.glob("*.parquet"))

        for parquet_file in parquet_files:

            dataframe = pd.read_parquet(parquet_file)

            bronze_data[report_name].append(
                {
                    "file_name": parquet_file.name,
                    "dataframe": dataframe,
                }
            )

    return bronze_data