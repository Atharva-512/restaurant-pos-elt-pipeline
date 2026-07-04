"""
Restaurant POS ELT Pipeline -- Entry Point
=============================================

Pipeline:

    data/raw
        |
        v
    Discovery              (src.ingestion.discovery)
        |
        v
    CSV / Excel Readers     (src.ingestion.loader)
        |
        v
    DataFrames
        |
        v
    Bronze Layer            (src.storage.hash_manager, src.storage.parquet_writer)
        - SHA256 hash check / skip unchanged files
        - write new/changed DataFrames as Parquet
        - update processed_files.json metadata
"""

from __future__ import annotations

import logging
import pandas as pd
from pathlib import Path

from src.ingestion.discovery import discover_reports
from src.ingestion.loader import load_reports
from src.storage.hash_manager import (
    load_processed_metadata,
    record_processed_file,
    save_processed_metadata,
    should_process,
)
from src.silver.orchestrator import run_silver_pipeline_stage
from src.gold.orchestrator import run_gold_pipeline_stage
from src.warehouse.orchestrator import run_warehouse_pipeline_stage
from src.storage.parquet_writer import write_parquet

RAW_DIR = Path("data") / "raw"
BRONZE_ROOT = Path("data") / "bronze"

logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


def run_pipeline() -> None:
    print("=" * 34)
    print("Restaurant POS ELT Pipeline")
    print("=" * 34)

    # ------------------------------------------------------------------
    # 1. Discover reports
    # ------------------------------------------------------------------
    print("Scanning raw directory...")
    discovered = discover_reports(RAW_DIR)
    for report_name, files in discovered.items():
        print(f"\u2713 {report_name} : {len(files)} files")

    # ------------------------------------------------------------------
    # 2. Load reports into DataFrames
    # ------------------------------------------------------------------
    print("Loading...")
    loaded = load_reports(discovered)
    print("\u2713 Loaded")

    # ------------------------------------------------------------------
    # 3. Bronze layer: hash check -> write parquet -> update metadata
    # ------------------------------------------------------------------
    print("Writing Bronze...")
    metadata = load_processed_metadata()

    written_count = 0
    skipped_count = 0
    written_files = []


    for report_name, entries in loaded.items():
        for source_file, dataframe in entries:
            if not should_process(source_file, metadata=metadata):
                print(f"Skipping already processed file: {source_file.name}")
                skipped_count += 1
                continue

            written_path = write_parquet(
                report_name=report_name,
                source_file=source_file,
                dataframe=dataframe,
                overwrite=True,
                bronze_root=BRONZE_ROOT,
            )
            print(f"\u2713 {written_path.name}")

            written_files.append(written_path)

            record_processed_file(metadata, source_file)
            written_count += 1

    # ------------------------------------------------------------------
    # 4. Persist metadata
    # ------------------------------------------------------------------

    save_processed_metadata(metadata)
    print("Metadata Updated")

    # ------------------------------------------------------------------
    # 5. Silver Layer
    # ------------------------------------------------------------------

    if written_files:

        print("\nStarting Silver Layer...")

        silver_result = run_silver_pipeline_stage(
            written_files=written_files,
        )

        silver_data = silver_result["silver_data"]

        silver_orders = pd.concat(
            [entry["dataframe"] for entry in silver_data["order_summary"]],
            ignore_index=True,
        )

        silver_order_items = pd.concat(
            [entry["dataframe"] for entry in silver_data["order_summary_item"]],
            ignore_index=True,
        )

        silver_kot = pd.concat(
            [entry["dataframe"] for entry in silver_data["kot_process_time"]],
            ignore_index=True,
        )

        print("\nStarting Gold Layer...")

        gold_result = run_gold_pipeline_stage(
            silver_orders=silver_orders,
            silver_order_items=silver_order_items,
            silver_kot=silver_kot,
        )

        warehouse_summary = run_warehouse_pipeline_stage(
            gold_layer=gold_result["gold_layer"]
        )

        silver_status = "Completed"

    else:
        print("\nNo new Bronze datasets detected.")
        print("Skipping Silver Layer.")
        print("Skipping Gold Layer.")
        print("Skipping Warehouse Layer.")

        silver_status = "Skipped"
    # ------------------------------------------------------------------
    # 6. Pipeline Summary
    # ------------------------------------------------------------------

    print("\n=================================")
    print("Restaurant POS ELT Pipeline Completed")
    print("=================================")
    print(f"Bronze Files Written : {written_count}")
    print(f"Bronze Files Skipped : {skipped_count}")
    print(f"Silver Layer         : {silver_status}")
    if silver_status == "Completed":
        gold_summary = gold_result["summary"]

        print(
            f"Gold Layer           : {gold_summary['written']} files written "
            f"({gold_summary['dimensions']} dimensions, "
            f"{gold_summary['facts']} facts)"
        )

        print(
            f"Warehouse Layer      : "
            f"{warehouse_summary['tables']} tables, "
            f"{warehouse_summary['views']} views"
        )
    print("=================================")

if __name__ == "__main__":
    run_pipeline()
