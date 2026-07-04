"""
Gold FactKitchen Builder.

Builds the Gold ``FactKitchen`` table from the enriched Silver KOT
dataset. This module models kitchen operations. It performs only
transformation: it derives ``business_date`` from ``punch_time``,
attaches dimension surrogate keys, and selects the fact's columns. It
does not perform file I/O, orchestration, validation, or any database
operations.
"""

from typing import Final

import pandas as pd

from src.gold.lookup import attach_dimension_keys

# Source timestamp column used to derive the business date.
_PUNCH_TIME_COLUMN: Final[str] = "punch_time"

# Derived column used only to resolve the date dimension.
_BUSINESS_DATE_COLUMN: Final[str] = "business_date"

# Dimension surrogate keys included in the fact. Restaurant, brand,
# platform, and category keys are intentionally excluded because they
# cannot be derived from the available Silver KOT columns without
# making unsupported assumptions.
_DATE_KEY_COLUMN: Final[str] = "date_key"
_ITEM_KEY_COLUMN: Final[str] = "item_key"

_DIMENSION_KEY_COLUMNS: Final[tuple[str, ...]] = (
    _DATE_KEY_COLUMN,
    _ITEM_KEY_COLUMN,
)

# Degenerate dimensions carried directly from Silver onto the fact.
_KOT_ID_COLUMN: Final[str] = "kot_id"
_ORDER_TYPE_COLUMN: Final[str] = "order_type"
_SERVER_NAME_COLUMN: Final[str] = "server_name"
_ITEM_STATUS_COLUMN: Final[str] = "item_status"

_DEGENERATE_DIMENSION_COLUMNS: Final[tuple[str, ...]] = (
    _KOT_ID_COLUMN,
    _ORDER_TYPE_COLUMN,
    _SERVER_NAME_COLUMN,
    _ITEM_STATUS_COLUMN,
)

# Measures carried directly from Silver onto the fact.
_QTY_COLUMN: Final[str] = "qty"
_PRICE_COLUMN: Final[str] = "price"
_PREPARATION_TIME_TAKEN_MINS_COLUMN: Final[str] = "preparation_time_taken_mins"

_MEASURE_COLUMNS: Final[tuple[str, ...]] = (
    _QTY_COLUMN,
    _PRICE_COLUMN,
    _PREPARATION_TIME_TAKEN_MINS_COLUMN,
)

_FACT_COLUMNS: Final[tuple[str, ...]] = (
    _DIMENSION_KEY_COLUMNS + _DEGENERATE_DIMENSION_COLUMNS + _MEASURE_COLUMNS
)


def build_kitchen_fact(
    silver_kot: pd.DataFrame,
    dimensions: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Build the Gold ``FactKitchen`` table from the enriched Silver KOT dataset.

    Derives ``business_date`` from ``punch_time`` so the date
    dimension can be resolved, attaches the ``date`` and ``item``
    dimension surrogate keys, and selects the fact's dimension keys,
    degenerate dimensions, and measures.

    Args:
        silver_kot: An enriched Silver KOT DataFrame containing
            ``kot_id``, ``order_type``, ``server_name``, ``item_name``,
            ``qty``, ``price``, ``item_status``, ``punch_time``,
            ``prepared_time``, and ``preparation_time_taken_mins``.
        dimensions: Mapping of dimension name to its Gold dimension
            DataFrame, as expected by ``attach_dimension_keys()``.

    Returns:
        pd.DataFrame: The Gold ``FactKitchen`` table containing
        ``date_key``, ``item_key``, ``kot_id``, ``order_type``,
        ``server_name``, ``item_status``, ``qty``, ``price``, and
        ``preparation_time_taken_mins``.
    """
    kitchen_with_date = _derive_business_date(silver_kot)
    kitchen_with_keys = attach_dimension_keys(kitchen_with_date, dimensions)
    kitchen_fact = kitchen_with_keys.loc[:, _FACT_COLUMNS]

    return kitchen_fact


def _derive_business_date(silver_kot: pd.DataFrame) -> pd.DataFrame:
    """
    Derive ``business_date`` from ``punch_time``.

    The Silver KOT dataset does not contain a ``business_date``
    column. This helper derives it from the date component of
    ``punch_time`` so that the date dimension can be resolved via
    ``attach_dimension_keys()``.

    Args:
        silver_kot: An enriched Silver KOT DataFrame containing a
            ``punch_time`` column.

    Returns:
        pd.DataFrame: A copy of ``silver_kot`` with a
        ``business_date`` column added.
    """
    silver_kot = silver_kot.copy()
    silver_kot[_BUSINESS_DATE_COLUMN] = silver_kot[_PUNCH_TIME_COLUMN].dt.date

    return silver_kot
