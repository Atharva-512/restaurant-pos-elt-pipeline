"""
Gold Date Dimension Builder.

Builds the conformed ``DimDate`` dimension from the enriched Silver
Order Summary dataset. This module performs no file I/O, no database
operations, no logging, and no orchestration — it is a pure
transformation module that models already-derived Silver calendar
attributes into a Gold dimension.
"""

from typing import Final

import pandas as pd

# Columns required from the Silver Order Summary dataset. These
# attributes are already derived by the Silver layer and are not
# recomputed here.
_BUSINESS_DATE_COLUMN: Final[str] = "business_date"
_WEEKDAY_COLUMN: Final[str] = "weekday"
_MONTH_COLUMN: Final[str] = "month"
_MONTH_NAME_COLUMN: Final[str] = "month_name"
_QUARTER_COLUMN: Final[str] = "quarter"
_YEAR_COLUMN: Final[str] = "year"

_REQUIRED_SILVER_COLUMNS: Final[tuple[str, ...]] = (
    _BUSINESS_DATE_COLUMN,
    _WEEKDAY_COLUMN,
    _MONTH_COLUMN,
    _MONTH_NAME_COLUMN,
    _QUARTER_COLUMN,
    _YEAR_COLUMN,
)
# Surrogate key column for the Gold dimension.
_DATE_KEY_COLUMN: Final[str] = "date_key"
_SURROGATE_KEY_START: Final[int] = 1


def build_date_dimension(silver_orders: pd.DataFrame) -> pd.DataFrame:
    """
    Build the Gold ``DimDate`` dimension from enriched Silver orders.

    Selects the calendar attributes already derived by the Silver
    layer, removes duplicate dates, sorts them chronologically, and
    assigns a sequential surrogate key.

    Args:
        silver_orders: An enriched Silver Order Summary DataFrame
            containing ``business_date``, ``weekday``, ``month``,
            ``month_name``, ``quarter``, and ``year`` columns.

    Returns:
        pd.DataFrame: The Gold ``DimDate`` dimension with columns
        ``date_key``, ``business_date``, ``weekday``, ``month``,
        ``month_name``, ``quarter``, and ``year``, sorted by
        ``business_date`` ascending.
    """
    date_dimension = silver_orders.loc[:, _REQUIRED_SILVER_COLUMNS].drop_duplicates()
    date_dimension = date_dimension.sort_values(by=_BUSINESS_DATE_COLUMN)
    date_dimension = date_dimension.reset_index(drop=True)

    date_dimension = _assign_surrogate_key(date_dimension)

    return date_dimension


def _assign_surrogate_key(date_dimension: pd.DataFrame) -> pd.DataFrame:
    """
    Assign a sequential surrogate key as the first column.

    Args:
        date_dimension: A deduplicated, sorted, index-reset Date
            Dimension DataFrame.

    Returns:
        pd.DataFrame: The Date Dimension with a ``date_key`` column
        inserted as the first column, starting from 1 and
        incrementing sequentially.
    """
    date_dimension = date_dimension.copy()

    surrogate_keys = range(
        _SURROGATE_KEY_START,
        _SURROGATE_KEY_START + len(date_dimension),
    )

    date_dimension.insert(
        0,
        _DATE_KEY_COLUMN,
        surrogate_keys,
    )

    return date_dimension