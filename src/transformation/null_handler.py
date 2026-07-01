"""
Silver Layer -- Null Handler
===============================

Normalizes textual "null-like" tokens (e.g. "N/A", "-", "NULL") into real
Python/pandas None values, and trims stray whitespace from text fields,
without touching already-numeric columns.
"""

from __future__ import annotations

import pandas as pd

# Case-sensitive set of literal tokens that represent a missing value.
# Values are checked *after* whitespace trimming, so purely-whitespace
# cells (e.g. " ") already collapse to "" and are covered by that entry.
NULL_TOKENS: frozenset[str] = frozenset(
    {
        "",
        " ",
        "-",
        "--",
        "NA",
        "N/A",
        "NULL",
        "null",
        "None",
        "none",
        "NaN",
        "nan",
    }
)


def _clean_value(value: object) -> object:
    """
    Trim whitespace on a single scalar value and convert it to None if it
    matches one of the known null-like tokens.

    Non-string values (and already-missing values) are returned unchanged.

    Args:
        value: A single cell value.

    Returns:
        None if the value is missing or a recognized null-token, the
        trimmed string otherwise, or the original value if it isn't a
        string.
    """
    if pd.isna(value):
        return None

    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed in NULL_TOKENS:
            return None
        return trimmed

    return value


def handle_nulls(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of `df` with null-like text values normalized to None.

    Responsibilities:
        - Trim leading/trailing whitespace on text (object/string) columns.
        - Replace the literal (post-trim) tokens "", " ", "-", "--", "NA",
          "N/A", "NULL", "null", "None", "none", "NaN", "nan" with None.
        - Numeric (int/float) and boolean columns are left untouched, since
          these tokens cannot appear as valid numeric values and coercing
          them would risk corrupting real numeric data.

    Args:
        df: Input DataFrame (not mutated).

    Returns:
        A new DataFrame with null-like values normalized.
    """
    result = df.copy()

    for column in result.columns:
        series = result[column]

        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
            continue
        if pd.api.types.is_datetime64_any_dtype(series):
            continue

        result[column] = series.apply(_clean_value)

    return result
