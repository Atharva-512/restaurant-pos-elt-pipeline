"""
Silver Layer Writer.

Responsible for persisting transformed Silver DataFrames to disk as
Parquet files under ``data/silver/``. This module has a single
responsibility: writing already-transformed data. It performs no
transformation logic itself.
"""

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

SILVER_ROOT: Path = Path("data/silver")


def write_silver_data(silver_data: Dict[str, List[Dict[str, Any]]]) -> List[Path]:
    """
    Write transformed Silver datasets to the Silver layer as Parquet files.

    The ``data/silver/`` directory is created automatically if it does not
    already exist, along with a subfolder for each dataset. Original
    filenames are preserved, and any existing files are overwritten.

    Args:
        silver_data: Dictionary returned by ``run_silver_transformations()``.
            Expected shape::

                {
                    "dataset_name": [
                        {
                            "file_name": "...",
                            "dataframe": pd.DataFrame,
                            ...  # additional metadata keys are ignored
                        },
                        ...
                    ],
                    ...
                }

    Returns:
        List[Path]: Paths of every Parquet file written to the Silver layer.
    """
    written_files: List[Path] = []

    SILVER_ROOT.mkdir(parents=True, exist_ok=True)

    for dataset_name, records in silver_data.items():
        dataset_dir = SILVER_ROOT / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)

        for record in records:
            file_name = record["file_name"]
            dataframe = record["dataframe"]

            output_path = dataset_dir / file_name

            if not output_path.suffix:
                output_path = output_path.with_suffix(".parquet")

            _write_dataframe(dataframe, output_path)
            written_files.append(output_path)

    return written_files


def _write_dataframe(dataframe: pd.DataFrame, output_path: Path) -> None:
    """
    Write a single DataFrame to Parquet at the given path, overwriting
    any existing file.

    Args:
        dataframe: The cleaned DataFrame to persist.
        output_path: Destination Parquet file path.
    """
    dataframe.to_parquet(output_path, index=False)
