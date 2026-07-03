"""
Business Silver Enricher.

Orchestrates all Business Silver transformations by composing the
already-implemented pure business modules:
``parser.py``, ``brand.py``, ``platform.py``, ``calendar.py``,
``daypart.py``, and ``quality.py``.

This module is the ONLY entry point ``pipeline.py`` should call for
Business Silver enrichment::

    clean_dataframe = enrich_business_attributes(
        clean_dataframe,
        timestamp_column="order_date",
    )
"""

from typing import Final

import pandas as pd

from src.transformation.business.brand import standardize_brand
from src.transformation.business.calendar import derive_calendar_attributes
from src.transformation.business.daypart import derive_daypart
from src.transformation.business.parser import parse_sub_order_type
from src.transformation.business.platform import standardize_platform
from src.transformation.business.quality import validate_business_attributes

# Columns produced by this enricher.
_BRAND_COLUMN: Final[str] = "brand"
_PLATFORM_COLUMN: Final[str] = "platform"
_DAYPART_COLUMN: Final[str] = "daypart"
_VALIDATION_ERRORS_COLUMN: Final[str] = "business_validation_errors"
_BUSINESS_DATE_COLUMN: Final[str] = "business_date"


def enrich_business_attributes(
    df: pd.DataFrame,
    *,
    timestamp_column: str,
    sub_order_type_column: str | None = None,
) -> pd.DataFrame:
    """
    Enrich a Silver DataFrame with Business Silver attributes.

    Pipeline of operations performed on a copy of ``df``:
        1. Parse ``sub_order_type`` into raw brand/platform values.
        2. Standardize brand and platform into their canonical forms.
        3. Derive calendar attributes (business date, weekday, month,
           month name, quarter, year) from the timestamp column.
        4. Derive the business daypart from the timestamp column.
        5. Validate the resulting business attributes row by row and
           attach the validation messages as a new column.

    Args:
        df: The Silver-layer DataFrame to enrich.
        timestamp_column: Name of the column containing the datetime
            value used to derive calendar attributes and daypart.
        sub_order_type_column: Name of the column containing the raw
            sub order type string. Defaults to ``"sub_order_type"``.

    Returns:
        pd.DataFrame: A new DataFrame containing all original columns
        plus the derived Business Silver columns. The input DataFrame
        is never modified.
    """
    enriched_df = df.copy()

    if sub_order_type_column is not None:
        enriched_df = _extract_and_standardize_brand_platform(
            enriched_df,
            sub_order_type_column=sub_order_type_column,
        )
    enriched_df = _derive_calendar_columns(
        enriched_df, timestamp_column=timestamp_column
    )
    enriched_df = _derive_daypart_column(
        enriched_df, timestamp_column=timestamp_column
    )
    enriched_df = _attach_validation_errors(enriched_df)

    return enriched_df


def _extract_and_standardize_brand_platform(
    df: pd.DataFrame, *, sub_order_type_column: str
) -> pd.DataFrame:
    """
    Extract brand/platform from ``sub_order_type`` and standardize them.

    Args:
        df: DataFrame containing the ``sub_order_type_column`` column.
        sub_order_type_column: Name of the column containing the raw
            sub order type string.

    Returns:
        pd.DataFrame: The DataFrame with ``brand`` and ``platform``
        columns added (standardized to their canonical forms).
    """
    parsed_values = df[sub_order_type_column].map(parse_sub_order_type)
    parsed_df = pd.DataFrame(
        parsed_values.tolist(),
        columns=[_BRAND_COLUMN, _PLATFORM_COLUMN],
        index=df.index,
    )

    df[_BRAND_COLUMN] = (
    parsed_df[_BRAND_COLUMN]
    .where(parsed_df[_BRAND_COLUMN].notna(), None)
    .map(standardize_brand)
    )
    df[_PLATFORM_COLUMN] = (
    parsed_df[_PLATFORM_COLUMN]
    .where(parsed_df[_PLATFORM_COLUMN].notna(), None)
    .map(standardize_platform)
    )

    return df


def _derive_calendar_columns(df: pd.DataFrame, *, timestamp_column: str) -> pd.DataFrame:
    """
    Derive business calendar columns from the timestamp column.

    Args:
        df: DataFrame containing the ``timestamp_column`` column.
        timestamp_column: Name of the column containing the datetime
            value used to derive calendar attributes.

    Returns:
        pd.DataFrame: The DataFrame with calendar attribute columns
        (business_date, weekday, month, month_name, quarter, year)
        added.
    """
    calendar_attributes = df[timestamp_column].map(derive_calendar_attributes)
    calendar_df = pd.DataFrame(calendar_attributes.tolist(), index=df.index)

    for column in calendar_df.columns:
        df[column] = calendar_df[column]

    return df


def _derive_daypart_column(df: pd.DataFrame, *, timestamp_column: str) -> pd.DataFrame:
    """
    Derive the business daypart column from the timestamp column.

    Args:
        df: DataFrame containing the ``timestamp_column`` column.
        timestamp_column: Name of the column containing the datetime
            value used to derive the daypart.

    Returns:
        pd.DataFrame: The DataFrame with a ``daypart`` column added.
    """
    df[_DAYPART_COLUMN] = df[timestamp_column].map(derive_daypart)

    return df


def _attach_validation_errors(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate the derived Business Silver attributes for every row.

    Args:
        df: DataFrame containing ``brand``, ``platform``,
            ``business_date``, and ``daypart`` columns.

    Returns:
        pd.DataFrame: The DataFrame with a ``business_validation_errors``
        column added, containing the list of validation messages for
        each row.
    """
    df[_VALIDATION_ERRORS_COLUMN] = [
        validate_business_attributes(brand, platform, business_date, daypart)
        for brand, platform, business_date, daypart in zip(
            df[_BRAND_COLUMN],
            df[_PLATFORM_COLUMN],
            df[_BUSINESS_DATE_COLUMN],
            df[_DAYPART_COLUMN],
        )
    ]

    return df
