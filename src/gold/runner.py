"""
Gold Layer Runner.

Builds the complete Gold layer in memory by composing the existing
Gold dimension and fact builders. This module performs no file I/O,
no logging, and no validation — it only builds DataFrames.
"""

import pandas as pd

from src.gold.dimensions.brand import build_brand_dimension
from src.gold.dimensions.category import build_category_dimension
from src.gold.dimensions.date import build_date_dimension
from src.gold.dimensions.item import build_item_dimension
from src.gold.dimensions.platform import build_platform_dimension
from src.gold.dimensions.restaurant import build_restaurant_dimension
from src.gold.facts.kitchen import build_kitchen_fact
from src.gold.facts.order_items import build_order_items_fact
from src.gold.facts.orders import build_orders_fact


def build_gold_layer(
    silver_orders: pd.DataFrame,
    silver_order_items: pd.DataFrame,
    silver_kot: pd.DataFrame,
) -> dict[str, dict[str, pd.DataFrame]]:
    """
    Build the complete Gold layer from enriched Silver DataFrames.

    Builds every Gold dimension first, then builds every Gold fact
    using those dimensions. Dimensions are built exactly once and
    reused across all facts.

    Args:
        silver_orders: An enriched Silver Order Summary DataFrame.
        silver_order_items: An enriched Silver Order Summary Item
            DataFrame.
        silver_kot: An enriched Silver KOT DataFrame.

    Returns:
        dict[str, dict[str, pd.DataFrame]]: A dictionary with two
        keys, ``"dimensions"`` and ``"facts"``, each mapping a Gold
        dataset name to its built DataFrame.
    """
    dimensions = _build_dimensions(silver_orders, silver_order_items)
    facts = _build_facts(silver_orders, silver_order_items, silver_kot, dimensions)

    return {
        "dimensions": dimensions,
        "facts": facts,
    }


def _build_dimensions(
    silver_orders: pd.DataFrame,
    silver_order_items: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """
    Build every Gold dimension.

    Execution order: Date, Restaurant, Brand, Platform, Category,
    Item.

    Args:
        silver_orders: An enriched Silver Order Summary DataFrame,
            used to build the date, restaurant, brand, and platform
            dimensions.
        silver_order_items: An enriched Silver Order Summary Item
            DataFrame, used to build the category and item
            dimensions.

    Returns:
        dict[str, pd.DataFrame]: Mapping of dimension name to its
        built Gold dimension DataFrame.
    """
    return {
        "date": build_date_dimension(silver_orders),
        "restaurant": build_restaurant_dimension(silver_orders),
        "brand": build_brand_dimension(silver_orders),
        "platform": build_platform_dimension(silver_orders),
        "category": build_category_dimension(silver_order_items),
        "item": build_item_dimension(silver_order_items),
    }


def _build_facts(
    silver_orders: pd.DataFrame,
    silver_order_items: pd.DataFrame,
    silver_kot: pd.DataFrame,
    dimensions: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """
    Build every Gold fact using the already-built dimensions.

    Execution order: Orders, Order Items, Kitchen.

    Args:
        silver_orders: An enriched Silver Order Summary DataFrame.
        silver_order_items: An enriched Silver Order Summary Item
            DataFrame.
        silver_kot: An enriched Silver KOT DataFrame.
        dimensions: Mapping of dimension name to its built Gold
            dimension DataFrame, as returned by
            ``_build_dimensions()``.

    Returns:
        dict[str, pd.DataFrame]: Mapping of fact name to its built
        Gold fact DataFrame.
    """
    return {
        "orders": build_orders_fact(silver_orders, dimensions),
        "order_items": build_order_items_fact(
            silver_order_items, silver_orders, dimensions
        ),
        "kitchen": build_kitchen_fact(silver_kot, dimensions),
    }
