"""
Silver Layer -- Datatype Converter
=====================================

Infers and casts each column's "true" datatype (datetime, integer, float,
or boolean) purely from its values -- no column names are hardcoded or
inspected. Columns that don't cleanly match any of these types are left
as-is (text).
"""

from __future__ import annotations

import warnings

import pandas as pd

# Tokens (case-insensitive, whitespace-trimmed) recognized as booleans.
_BOOL_TRUE_TOKENS = frozenset({"true", "yes", "y"})
_BOOL_FALSE_TOKENS = frozenset({"false", "no", "n"})


def _try_convert_boolean(series: pd.Series, non_null_mask: pd.Series) -> pd.Series | None:
    """
    Attempt to interpret `series` as boolean based on its string values.

    Returns the converted Series (pandas nullable "boolean" dtype) if every
    non-null value matches a recognized true/false token, otherwise None.
    """
    str_values = series[non_null_mask].astype(str).str.strip().str.lower()
    unique_values = set(str_values.unique())

    if not unique_values or not unique_values.issubset(_BOOL_TRUE_TOKENS | _BOOL_FALSE_TOKENS):
        return None

    mapping = {token: True for token in _BOOL_TRUE_TOKENS}
    mapping.update({token: False for token in _BOOL_FALSE_TOKENS})

    normalized = series.astype(str).str.strip().str.lower().map(mapping)
    normalized[~non_null_mask] = None
    return normalized.astype("boolean")


def _try_convert_numeric(series: pd.Series, non_null_mask: pd.Series) -> pd.Series | None:
    """
    Attempt to interpret `series` as numeric (integer or float).

    Returns the converted Series (pandas nullable "Int64" or "Float64"
    dtype) if every non-null value parses cleanly as a number, otherwise
    None.
    """
    numeric = pd.to_numeric(series, errors="coerce")

    if numeric.notna().sum() != int(non_null_mask.sum()):
        return None

    non_null_numeric = numeric[non_null_mask]
    is_whole_number = (non_null_numeric % 1 == 0).all()

    if is_whole_number:
        return numeric.astype("Int64")
    return numeric.astype("Float64")


def _try_convert_datetime(series: pd.Series, non_null_mask: pd.Series) -> pd.Series | None:
    """
    Attempt to interpret `series` as datetime.

    Returns the converted Series (datetime64[ns]) if every non-null value
    parses cleanly as a date/timestamp, otherwise None.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(series, errors="coerce")

    if parsed.notna().sum() != int(non_null_mask.sum()):
        return None

    return parsed


def _convert_column(series: pd.Series) -> pd.Series:
    """
    Infer and apply the best-fit dtype for a single column.

    Detection order: datetime -> integer/float -> boolean -> leave as-is.
    Datetime is checked first because restaurant POS exports are rich in
    date/timestamp columns (order dates, KOT times, bill dates, etc.)
    that must not be misclassified as numeric or boolean. Columns that
    are already a concrete typed dtype (numeric, bool, datetime) are
    returned unchanged; this check is dtype-agnostic so it correctly
    treats both legacy "object" text columns and pandas's dedicated
    "str" dtype (default since pandas 3.0) as text to convert.

    Args:
        series: The column to convert.

    Returns:
        The converted (or original) Series.
    """
    already_typed = (
        pd.api.types.is_numeric_dtype(series)
        or pd.api.types.is_bool_dtype(series)
        or pd.api.types.is_datetime64_any_dtype(series)
    )
    if already_typed:
        return series

    non_null_mask = series.notna()
    if not non_null_mask.any():
        return series

    for converter in (_try_convert_datetime, _try_convert_numeric, _try_convert_boolean):
        converted = converter(series, non_null_mask)
        if converted is not None:
            return converted

    return series


def convert_datatypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of `df` with each column cast to its inferred datatype.

    Detects, per column and without any hardcoded column-name logic, in
    priority order:
        1. datetime
        2. integer / float
        3. boolean

    Datetime is prioritized first to correctly capture the many date and
    timestamp columns typical of restaurant POS exports before numeric or
    boolean inference gets a chance to misclassify them. Columns that
    don't unambiguously match one of these types (e.g. free text) are
    left unchanged.

    Args:
        df: Input DataFrame (not mutated).

    Returns:
        A new DataFrame with inferred datatypes applied.
    """
    result = df.copy()

    for column in result.columns:
        result[column] = _convert_column(result[column])

    return result
