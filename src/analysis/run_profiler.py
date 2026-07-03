"""
Silver Layer Profiler Runner.

A one-time engineering analysis script that discovers every Parquet
file under ``data/silver/``, profiles each dataset using
``profile_dataframe()`` from ``src.analysis.data_profiler``, and prints
a clean, human-readable report to the console.

This script performs no data mutation, no file writes, and no
candidate key detection — it is a read-only analysis tool.
"""

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from src.analysis.data_profiler import profile_dataframe

SILVER_ROOT: Path = Path("data/silver")


def discover_silver_parquet_files(silver_root: Path = SILVER_ROOT) -> List[Path]:
    """
    Recursively discover all Parquet files under the Silver root directory.

    Args:
        silver_root: Root directory to search under. Defaults to
            ``data/silver``.

    Returns:
        List[Path]: Sorted list of Parquet file paths found. Empty list
        if the directory does not exist or contains no Parquet files.
    """
    if not silver_root.exists():
        return []

    return sorted(silver_root.rglob("*.parquet"))


def load_parquet(file_path: Path) -> pd.DataFrame:
    """
    Load a single Parquet file into a DataFrame.

    Args:
        file_path: Path to the Parquet file.

    Returns:
        pd.DataFrame: The loaded data.
    """
    return pd.read_parquet(file_path)


def resolve_dataset_name(file_path: Path, silver_root: Path = SILVER_ROOT) -> str:
    """
    Derive a readable dataset name from a Parquet file's path relative
    to the Silver root.

    Args:
        file_path: Path to the Parquet file.
        silver_root: Root directory the file lives under.

    Returns:
        str: A dataset name such as "order_summary/order_summary_2024_01".
    """
    try:
        relative_path = file_path.relative_to(silver_root)
    except ValueError:
        relative_path = file_path

    return str(relative_path.with_suffix(""))


def print_report(profile: Dict[str, Any]) -> None:
    """
    Print a clean, human-readable profiling report for a single dataset.

    Args:
        profile: The dictionary returned by ``profile_dataframe()``.
    """
    rows = profile["rows"]

    print("=" * 50)
    print(profile["dataset"])
    print("=" * 50)
    print(f"Rows              : {rows}")
    print(f"Columns           : {profile['columns']}")
    print(f"Memory Usage      : {profile['memory_usage_mb']} MB")

    print("-" * 36)
    print("Column Profile")
    print("-" * 36)
    for column_name, stats in profile["column_profile"].items():
        print(f"  {column_name}")
        print(f"    Datatype       : {stats['dtype']}")
        print(f"    Null %         : {stats['null_percent']}%")
        print(f"    Distinct %     : {stats['distinct_percent']}%")

    print("-" * 36)
    print("Duplicate Rows")
    print("-" * 36)

    duplicate_info = profile["duplicate_rows"]

    print(f"  Count           : {duplicate_info['count']}")
    print(f"  Percentage      : {duplicate_info['percentage']}%")

    print("-" * 36)
    print("Numeric Summary")
    print("-" * 36)
    if profile["numeric_summary"]:
        for column_name, stats in profile["numeric_summary"].items():
            print(f"  {column_name}")
            print(f"    Min            : {stats['min']}")
            print(f"    Max            : {stats['max']}")
            print(f"    Mean           : {stats['mean']}")
            print(f"    Median         : {stats['median']}")
            print(f"    Negative Values: {stats['negative_values']}")
            print(f"    Zero Values    : {stats['zero_values']}")
    else:
        print("  No numeric columns.")

    print("-" * 36)
    print("Date Summary")
    print("-" * 36)
    if profile["date_summary"]:
        for column_name, stats in profile["date_summary"].items():
            print(f"  {column_name}")
            print(f"    Min Date       : {stats['min_date']}")
            print(f"    Max Date       : {stats['max_date']}")
    else:
        print("  No date columns.")

    print("=" * 50)
    print()


def print_summary(datasets_profiled: int) -> None:
    """
    Print the final summary once all Silver datasets have been profiled.

    Args:
        datasets_profiled: Total number of datasets that were profiled.
    """
    print("=" * 36)
    print("Profiling Completed")
    print(f"Datasets Profiled : {datasets_profiled}")
    print("=" * 36)


def run_profiler() -> None:
    """
    Discover, load, and profile every Parquet file under ``data/silver/``,
    printing a report for each and a final summary at the end.
    """
    parquet_files = discover_silver_parquet_files()

    datasets_profiled = 0

    for file_path in parquet_files:
        dataframe = load_parquet(file_path)
        dataset_name = resolve_dataset_name(file_path)

        profile = profile_dataframe(dataframe, dataset_name)
        print_report(profile)

        datasets_profiled += 1

    print_summary(datasets_profiled)


if __name__ == "__main__":
    run_profiler()
