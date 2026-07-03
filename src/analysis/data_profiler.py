"""
Data Profiler.

A one-time engineering analysis tool used to profile Silver-layer
datasets prior to designing the Business Silver layer.

This module is intentionally decoupled from the runtime ELT pipeline.
It performs no business validation, no key detection, and no I/O — it
only inspects a DataFrame and returns a structured profile as a
dictionary.
"""

from typing import Any, Dict

import numpy as np
import pandas as pd


def profile_dataframe(df: pd.DataFrame, dataset_name: str) -> dict:
    """
    Generate a structural and statistical profile of a DataFrame.

    The profile covers dataset-level metadata, per-column statistics,
    duplicate row counts, numeric column summaries, and date column
    summaries. The input DataFrame is never modified.

    Args:
        df: The DataFrame to profile (typically a Silver-layer dataset).
        dataset_name: A human-readable name identifying the dataset.

    Returns:
        dict: A structured profile of the DataFrame. See module-level
        docstring / caller documentation for the exact schema.
    """
    # Work defensively: never mutate the caller's DataFrame.
    # No copy of the data is needed since every operation below is
    # read-only, but we still avoid any in-place calls throughout.

    row_count = int(df.shape[0])
    column_count = int(df.shape[1])

    profile: Dict[str, Any] = {
        "dataset": dataset_name,
        "rows": row_count,
        "columns": column_count,
        "memory_usage_mb": _compute_memory_usage_mb(df),
        "column_profile": _build_column_profile(df, row_count),
        "duplicate_rows": _compute_duplicate_rows(df),
        "numeric_summary": _build_numeric_summary(df),
        "date_summary": _build_date_summary(df),
    }

    return profile


def _compute_memory_usage_mb(df: pd.DataFrame) -> float:
    """
    Compute the total memory footprint of the DataFrame in megabytes.

    Uses deep memory introspection so that object/string columns are
    measured accurately rather than just their pointer size.

    Args:
        df: The DataFrame to measure.

    Returns:
        float: Memory usage in megabytes, rounded to 4 decimal places.
    """
    total_bytes = df.memory_usage(deep=True).sum()
    return round(float(total_bytes) / (1024 ** 2), 4)


def _build_column_profile(df: pd.DataFrame, row_count: int) -> Dict[str, Dict[str, Any]]:
    """
    Build a per-column profile containing dtype, null stats, and
    distinct value counts.

    Args:
        df: The DataFrame to profile.
        row_count: Total number of rows in the DataFrame (used to
            compute null percentages safely for empty DataFrames).

    Returns:
        dict: Mapping of column name to its profile.
    """
    column_profile: Dict[str, Dict[str, Any]] = {}

    for column in df.columns:
        series = df[column]
        null_count = int(series.isna().sum())
        null_percent = round((null_count / row_count) * 100, 2) if row_count > 0 else 0.0
        distinct_count = int(series.nunique(dropna=True))

        distinct_percent = (
            round((distinct_count / row_count) * 100, 2)
            if row_count > 0
            else 0.0
        )

        column_profile[column] = {
            "dtype": str(series.dtype),
            "null_count": null_count,
            "null_percent": null_percent,
            "distinct_count": distinct_count,
            "distinct_percent": distinct_percent,
        }

    return column_profile


def _compute_duplicate_rows(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Count duplicate rows and calculate duplicate percentage.

    Args:
        df: The DataFrame to inspect.

    Returns:
        dict: Duplicate row count and duplicate percentage.
    """
    if df.empty:
        return {
            "count": 0,
            "percentage": 0.0,
        }

    duplicate_count = int(df.duplicated().sum())

    duplicate_percentage = round(
        (duplicate_count / len(df)) * 100,
        2,
    )

    return {
        "count": duplicate_count,
        "percentage": duplicate_percentage,
    }


def _build_numeric_summary(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Build summary statistics for numeric columns only.

    Boolean columns are excluded since they are not meaningfully
    numeric for the purposes of this profile.

    Args:
        df: The DataFrame to profile.

    Returns:
        dict: Mapping of numeric column name to its summary stats.
        Columns with no non-null values are skipped.
    """
    numeric_summary: Dict[str, Dict[str, Any]] = {}

    numeric_columns = [
        column
        for column in df.columns
        if pd.api.types.is_numeric_dtype(df[column])
        and not pd.api.types.is_bool_dtype(df[column])
    ]

    for column in numeric_columns:
        series = df[column]
        non_null_series = series.dropna()

        if non_null_series.empty:
            continue

        numeric_summary[column] = {
            "min": _to_native(non_null_series.min()),
            "max": _to_native(non_null_series.max()),
            "mean": round(float(non_null_series.mean()), 4),
            "median": round(float(non_null_series.median()), 4),
            "negative_values": int((non_null_series < 0).sum()),
            "zero_values": int((non_null_series == 0).sum()),
        }

    return numeric_summary


def _build_date_summary(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Build summary statistics for date/datetime columns only.

    Only columns already typed as datetime are considered — no
    inference or conversion of object/string columns is performed,
    since that would constitute business logic outside this tool's
    scope.

    Args:
        df: The DataFrame to profile.

    Returns:
        dict: Mapping of date column name to its min/max date.
        Columns with no non-null values are skipped.
    """
    date_summary: Dict[str, Dict[str, Any]] = {}

    date_columns = [
        column for column in df.columns if pd.api.types.is_datetime64_any_dtype(df[column])
    ]

    for column in date_columns:
        series = df[column]
        non_null_series = series.dropna()

        if non_null_series.empty:
            continue

        date_summary[column] = {
            "min_date": non_null_series.min(),
            "max_date": non_null_series.max(),
        }

    return date_summary


def _to_native(value: Any) -> Any:
    """
    Convert a numpy scalar to a native Python scalar for clean output.

    Args:
        value: A value that may be a numpy scalar (e.g. np.int64).

    Returns:
        Any: The equivalent native Python scalar, or the original
        value if it is not a numpy generic type.
    """
    if isinstance(value, np.generic):
        return value.item()
    return value
