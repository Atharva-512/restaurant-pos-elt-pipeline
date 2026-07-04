"""
Gold FactOrderItems Builder.

Builds the Gold ``FactOrderItems`` table from the enriched Silver
Order Summary Item dataset. This module performs only transformation:
it enriches order items with order-header context (business date,
brand, platform), attaches dimension surrogate keys, and selects the
fact's columns. It does not perform file I/O, orchestration,
validation, or any database operations.
"""

from typing import Final

import pandas as pd

from src.gold.lookup import attach_dimension_keys

# Columns used to join Silver Order Summary onto Silver Order Items.
_RESTAURANT_NAME_COLUMN: Final[str] = "restaurant_name"
_INVOICE_NO_COLUMN: Final[str] = "invoice_no"

_ORDER_JOIN_COLUMNS: Final[tuple[str, ...]] = (
    _RESTAURANT_NAME_COLUMN,
    _INVOICE_NO_COLUMN,
)

# Order-header columns brought over from Silver Order Summary.
_BUSINESS_DATE_COLUMN: Final[str] = "business_date"
_BRAND_COLUMN: Final[str] = "brand"
_PLATFORM_COLUMN: Final[str] = "platform"

_ORDER_CONTEXT_COLUMNS: Final[tuple[str, ...]] = (
    _BUSINESS_DATE_COLUMN,
    _BRAND_COLUMN,
    _PLATFORM_COLUMN,
)

# Dimension surrogate keys included in the fact.
_DATE_KEY_COLUMN: Final[str] = "date_key"
_RESTAURANT_KEY_COLUMN: Final[str] = "restaurant_key"
_BRAND_KEY_COLUMN: Final[str] = "brand_key"
_PLATFORM_KEY_COLUMN: Final[str] = "platform_key"
_CATEGORY_KEY_COLUMN: Final[str] = "category_key"
_ITEM_KEY_COLUMN: Final[str] = "item_key"

_DIMENSION_KEY_COLUMNS: Final[tuple[str, ...]] = (
    _DATE_KEY_COLUMN,
    _RESTAURANT_KEY_COLUMN,
    _BRAND_KEY_COLUMN,
    _PLATFORM_KEY_COLUMN,
    _CATEGORY_KEY_COLUMN,
    _ITEM_KEY_COLUMN,
)

# Degenerate dimension carried directly from Silver onto the fact.
_DEGENERATE_DIMENSION_COLUMNS: Final[tuple[str, ...]] = (
    _INVOICE_NO_COLUMN,
)

# Measures carried directly from Silver onto the fact.
_ITEM_QUANTITY_COLUMN: Final[str] = "item_quantity"
_ITEM_PRICE_COLUMN: Final[str] = "item_price"
_ITEM_TOTAL_COLUMN: Final[str] = "item_total"

_MEASURE_COLUMNS: Final[tuple[str, ...]] = (
    _ITEM_QUANTITY_COLUMN,
    _ITEM_PRICE_COLUMN,
    _ITEM_TOTAL_COLUMN,
)

_FACT_COLUMNS: Final[tuple[str, ...]] = (
    _DIMENSION_KEY_COLUMNS + _DEGENERATE_DIMENSION_COLUMNS + _MEASURE_COLUMNS
)


def build_order_items_fact(
    silver_order_items: pd.DataFrame,
    silver_orders: pd.DataFrame,
    dimensions: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Build the Gold ``FactOrderItems`` table from enriched Silver order items.

    Enriches Silver Order Items with order-header context from Silver
    Order Summary, attaches the ``date``, ``restaurant``, ``brand``,
    ``platform``, ``category``, and ``item`` dimension surrogate keys,
    and selects the fact's dimension keys, degenerate dimension, and
    measures.

    Args:
        silver_order_items: An enriched Silver Order Summary Item
            DataFrame.
        silver_orders: An enriched Silver Order Summary DataFrame,
            used to supply order-header context.
        dimensions: Mapping of dimension name to its Gold dimension
            DataFrame, as expected by ``attach_dimension_keys()``.

    Returns:
        pd.DataFrame: The Gold ``FactOrderItems`` table containing
        ``date_key``, ``restaurant_key``, ``brand_key``,
        ``platform_key``, ``category_key``, ``item_key``,
        ``invoice_no``, ``item_quantity``, ``item_price``, and
        ``item_total``.
    """
    order_items_with_context = _enrich_order_context(silver_order_items, silver_orders)
    order_items_with_keys = attach_dimension_keys(order_items_with_context, dimensions)
    order_items_fact = order_items_with_keys.loc[:, _FACT_COLUMNS]

    return order_items_fact


def _enrich_order_context(
    silver_order_items: pd.DataFrame,
    silver_orders: pd.DataFrame,
) -> pd.DataFrame:

    silver_order_items = silver_order_items.copy()
    silver_orders = silver_orders.copy()

    silver_order_items[_INVOICE_NO_COLUMN] = (
        silver_order_items[_INVOICE_NO_COLUMN].astype(str)
    )

    silver_orders[_INVOICE_NO_COLUMN] = (
        silver_orders[_INVOICE_NO_COLUMN].astype(str)
    )

    order_context = silver_orders.loc[
        :, list(_ORDER_JOIN_COLUMNS) + list(_ORDER_CONTEXT_COLUMNS)
    ]

    return silver_order_items.merge(
        order_context,
        on=list(_ORDER_JOIN_COLUMNS),
        how="left",
        copy=False,
    )
