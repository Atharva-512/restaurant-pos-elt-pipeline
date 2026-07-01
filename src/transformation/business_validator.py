"""
Silver Layer -- Business Validator
=====================================

Runs read-only business-rule checks against a DataFrame and reports any
violations. This module never mutates or returns a modified DataFrame --
it only produces a validation report.
"""

from __future__ import annotations

import pandas as pd

# Columns whose name ends with one of these suffixes (case-insensitive)
# are treated as identifier / primary-key candidates, e.g. "order_id",
# "kot_id", "invoice_no", "bill_no", "order_no".
_ID_SUFFIXES = ("_id", "_no")

# Columns whose full name (case-insensitive) matches one of these are
# also treated as identifier / primary-key candidates. Covers restaurant
# POS-specific identifiers that don't follow the generic suffix patterns
# above (e.g. "customer_phone"), plus the bare "id" column itself.
_ID_EXACT_NAMES = frozenset(
    {
        "id",
        "invoice_no",
        "bill_no",
        "kot_no",
        "order_no",
        "customer_phone",
    }
)

# Datetime sanity bounds used to flag "impossible" dates.
_MIN_VALID_DATE = pd.Timestamp("1900-01-01")


def _identify_id_columns(df: pd.DataFrame) -> list[str]:
    """
    Identify columns that look like identifier / primary-key candidates.

    A column qualifies if its name (case-insensitive, whitespace-trimmed)
    either:
        - exactly matches a known restaurant POS identifier name (e.g.
          "id", "invoice_no", "bill_no", "kot_no", "order_no",
          "customer_phone"), or
        - ends with a generic identifier suffix ("_id" or "_no"), which
          also naturally covers "invoice_no"/"bill_no"/"kot_no"/
          "order_no" and any similarly-named future columns.

    Args:
        df: The DataFrame whose columns to inspect.

    Returns:
        List of column names considered identifier candidates.
    """
    id_columns = []
    for column in df.columns:
        normalized = str(column).strip().lower()
        is_exact_match = normalized in _ID_EXACT_NAMES
        is_suffix_match = any(normalized.endswith(suffix) for suffix in _ID_SUFFIXES)
        if is_exact_match or is_suffix_match:
            id_columns.append(column)
    return id_columns


def _check_negative_numeric_values(df: pd.DataFrame) -> list[str]:
    """Flag numeric columns that contain negative values."""
    errors: list[str] = []

    for column in df.columns:
        series = df[column]
        if not pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
            continue

        negative_count = int((series.dropna() < 0).sum())
        if negative_count > 0:
            errors.append(
                f"Column '{column}' contains {negative_count} negative value(s)."
            )

    return errors


def _check_duplicate_identifiers(df: pd.DataFrame, id_columns: list[str]) -> list[str]:
    """Flag identifier columns that contain duplicate (non-null) values."""
    errors: list[str] = []

    for column in id_columns:
        non_null = df[column].dropna()
        duplicate_count = int(non_null.duplicated(keep=False).sum())
        if duplicate_count > 0:
            errors.append(
                f"Column '{column}' has {duplicate_count} duplicate primary-key "
                f"candidate value(s)."
            )

    return errors


def _check_null_identifiers(df: pd.DataFrame, id_columns: list[str]) -> list[str]:
    """Flag identifier columns that contain null values."""
    errors: list[str] = []

    for column in id_columns:
        null_count = int(df[column].isna().sum())
        if null_count > 0:
            errors.append(
                f"Column '{column}' has {null_count} null identifier value(s)."
            )

    return errors


def _check_impossible_dates(df: pd.DataFrame) -> list[str]:
    """
    Flag datetime columns containing impossible dates: before 1900-01-01,
    or in the future relative to now.
    """
    errors: list[str] = []
    now = pd.Timestamp.now()

    for column in df.columns:
        series = df[column]
        if not pd.api.types.is_datetime64_any_dtype(series):
            continue

        non_null = series.dropna()
        invalid_count = int(((non_null < _MIN_VALID_DATE) | (non_null > now)).sum())
        if invalid_count > 0:
            errors.append(
                f"Column '{column}' contains {invalid_count} impossible date "
                f"value(s) (before {_MIN_VALID_DATE.date()} or in the future)."
            )

    return errors


def validate_business_rules(df: pd.DataFrame) -> dict[str, list[str]]:
    """
    Run business-rule validations against `df` without modifying it.

    Checks performed:
        - Negative values in numeric columns.
        - Duplicate values in identifier / primary-key candidate columns
          (e.g. "*_id", "*_no", "invoice_no", "bill_no", "kot_no",
          "order_no", "customer_phone").
        - Null values in those same identifier / primary-key candidate
          columns.
        - Impossible dates (before 1900-01-01, or in the future) in
          datetime columns.

    Args:
        df: Input DataFrame. Never mutated or returned.

    Returns:
        A dict of the form: {"validation_errors": [<message>, ...]}.
        The list is empty when no violations are found.
    """
    id_columns = _identify_id_columns(df)

    validation_errors: list[str] = []
    validation_errors.extend(_check_negative_numeric_values(df))
    validation_errors.extend(_check_duplicate_identifiers(df, id_columns))
    validation_errors.extend(_check_null_identifiers(df, id_columns))
    validation_errors.extend(_check_impossible_dates(df))

    result: dict[str, list[str]] = {"validation_errors": validation_errors}
    return result
