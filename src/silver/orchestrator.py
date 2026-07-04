"""
Silver Pipeline Orchestrator.

Coordinates the end-to-end Silver stage: loading Bronze data, running the
Silver transformation engine, writing Silver outputs, and reporting a
final summary. This module contains no transformation or I/O logic of
its own; it delegates to the existing Silver runner and the new Silver
writer.
"""

from pathlib import Path
from typing import Any, List

from src.silver.runner import run_silver_transformations
from src.silver.writer import SILVER_ROOT, write_silver_data


def run_silver_pipeline_stage(
    written_files: List[Path] | None = None,
) -> dict[str, Any]:
    """
    Execute the full Silver pipeline stage.

    Steps:
        1. Load Bronze data and run Silver transformations via
           ``run_silver_pipeline()``.
        2. Write the transformed datasets to the Silver layer via
           ``write_silver_data()``.
        3. Print a final summary of the run.

    Returns:
    dict[str, Any]:
        Dictionary containing:

        - ``silver_data``:
          Transformed Silver datasets.

        - ``written_files``:
          Paths of every Parquet file written to the Silver layer.
    """
    bronze_root = Path("data/bronze")

    silver_data = run_silver_transformations(
    bronze_root=bronze_root,
    written_files=written_files,
)

    written_files = write_silver_data(silver_data)
    _print_summary(dataset_count=len(silver_data), written_files=written_files)
    return {
        "silver_data": silver_data,
        "written_files": written_files,
    }

    



def _print_summary(dataset_count: int, written_files: List[Path]) -> None:
    """
    Print a final summary report of the Silver pipeline run.

    Args:
        dataset_count: Number of datasets processed.
        written_files: List of Parquet file paths written to the Silver layer.
    """
    print("=================================================")
    print("Silver Pipeline Completed")
    print(f"Datasets Processed : {dataset_count}")
    print(f"Files Written : {len(written_files)}")
    print(f"Silver Output : {SILVER_ROOT}/")
    print("=================================================")
