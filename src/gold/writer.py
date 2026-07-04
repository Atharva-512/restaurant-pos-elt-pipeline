"""
Gold Layer Writer.

Persists the completed Gold layer to Parquet under ``data/gold/``.
This module performs only writing — it does not build, transform, or
orchestrate any DataFrames.
"""

from pathlib import Path
from typing import Final

import pandas as pd

GOLD_ROOT: Final[Path] = Path("data/gold")

_DIMENSION_DIRECTORY_PREFIX: Final[str] = "dim_"
_FACT_DIRECTORY_PREFIX: Final[str] = "fact_"


def write_gold_layer(gold_layer: dict[str, dict[str, pd.DataFrame]]) -> dict[str, int]:
    """
    Write the completed Gold layer to Parquet.

    Every dimension is written under ``data/gold/dim_<name>/`` and
    every fact is written under ``data/gold/fact_<name>/``.

    Args:
        gold_layer: The dictionary returned by ``build_gold_layer()``,
            containing ``"dimensions"`` and ``"facts"`` keys, each
            mapping a dataset name to its built Gold DataFrame.

    Returns:
        dict[str, int]: A concise write summary, e.g.
        ``{"dimensions_written": 6, "facts_written": 3}``.
    """
    dimensions_written = _write_datasets(
        gold_layer["dimensions"], _DIMENSION_DIRECTORY_PREFIX
    )
    facts_written = _write_datasets(gold_layer["facts"], _FACT_DIRECTORY_PREFIX)

    return {
        "dimensions_written": dimensions_written,
        "facts_written": facts_written,
    }


def _write_datasets(datasets: dict[str, pd.DataFrame], directory_prefix: str) -> int:
    """
    Write a group of Gold datasets to their own directories under
    ``data/gold/``.

    Each dataset is written to
    ``data/gold/<directory_prefix><dataset_name>/<directory_prefix><dataset_name>.parquet``,
    overwriting any existing file.

    Args:
        datasets: Mapping of dataset name to its built Gold DataFrame.
        directory_prefix: Prefix identifying the dataset group (e.g.
            ``"dim_"`` or ``"fact_"``).

    Returns:
        int: The number of datasets written.
    """
    for dataset_name, dataframe in datasets.items():
        directory_name = f"{directory_prefix}{dataset_name}"
        dataset_directory = GOLD_ROOT / directory_name
        dataset_directory.mkdir(parents=True, exist_ok=True)

        output_path = dataset_directory / f"{directory_name}.parquet"
        dataframe.to_parquet(output_path, index=False)

    return len(datasets)
