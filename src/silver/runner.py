"""
runner.py
=========

Coordinates execution of the Silver Transformation Engine.

This module

1. Reads Bronze datasets
2. Runs Silver transformations
3. Prints transformation reports
4. Returns transformed data and metadata

No files are written here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.silver.reader import load_bronze_data
from src.transformation.business.enricher import (
    enrich_business_attributes,
)
from src.transformation.pipeline import run_silver_pipeline


def run_silver_transformations(
    bronze_root: Path,
    written_files: list[Path] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """
    Execute the Silver Transformation Engine
    for every Bronze dataset.

    Parameters
    ----------
    bronze_root : Path
        Bronze directory.

    Returns
    -------
    dict
        Dictionary containing transformed
        DataFrames and metadata.
    """

    bronze_data = load_bronze_data(
    bronze_root=bronze_root,
    parquet_files=written_files,
    )
    silver_results: dict[str, list[dict[str, Any]]] = {}

    print("\n")
    print("=" * 55)
    print("SILVER TRANSFORMATION REPORT")
    print("=" * 55)

    for dataset_name, datasets in bronze_data.items():

        silver_results[dataset_name] = []

        for dataset in datasets:

            file_name = dataset["file_name"]
            dataframe = dataset["dataframe"]

            clean_df, metadata = run_silver_pipeline(dataframe)

            # ---------------------------------------------------------
            # Business Silver enrichment
            # ---------------------------------------------------------
            # Business attributes (brand, platform, calendar, daypart)
            # are currently derived only for the Order Summary dataset,
            # as it contains the required business context
            # (sub_order_type).
            # ---------------------------------------------------------
            if dataset_name == "order_summary":
                clean_df = enrich_business_attributes(
                    clean_df,
                    timestamp_column="date",
                    sub_order_type_column="sub_order_type",
                )

            silver_results[dataset_name].append(
                {
                    "file_name": file_name,
                    "dataframe": clean_df,
                    "metadata": metadata,
                }
            )

            print(f"\nDataset              : {dataset_name}")
            print(f"Source File          : {file_name}")
            print(f"Rows Before          : {metadata['rows_before']}")
            print(f"Rows After           : {metadata['rows_after']}")
            print(
                f"Duplicates Removed   : "
                f"{metadata['duplicates_removed']}"
            )
            print(
                f"Validation Errors    : "
                f"{len(metadata['validation_errors'])}"
            )
            print(metadata["validation_errors"])
            print(f"Columns After        : {len(clean_df.columns)}")
            print("-" * 55)

    return silver_results