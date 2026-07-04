"""
Gold Item Dimension Builder.

Builds the conformed ``DimItem`` dimension from the enriched Silver
Order Summary Item dataset. This module performs no file I/O, no
database operations, no logging, and no orchestration — it is a pure
transformation module that models Silver item names into a Gold
dimension.

``DimItem`` represents item identity only. Category and SAP code are
deliberately excluded: source profiling showed ``sap_code`` is over
99% null and not unique, and item names legitimately appear under
multiple categories, meaning category is transactional context rather
than part of item identity. Category is modeled separately in
``DimCategory`` and associated to items in ``FactOrderItems``.
"""

from typing import Final

import pandas as pd

# Column required from the Silver Order Summary Item dataset.
_ITEM_NAME_COLUMN: Final[str] = "item_name"

_REQUIRED_SILVER_COLUMNS: Final[tuple[str, ...]] = (
    _ITEM_NAME_COLUMN,
)

# Surrogate key column for the Gold dimension.
_ITEM_KEY_COLUMN: Final[str] = "item_key"
_SURROGATE_KEY_START: Final[int] = 1


def build_item_dimension(silver_order_items: pd.DataFrame) -> pd.DataFrame:
    """
    Build the Gold ``DimItem`` dimension from enriched Silver order items.

    Selects the item name already present in the Silver layer, drops
    rows with a null item name, removes duplicate item names, sorts
    the remaining item names alphabetically, and assigns a sequential
    surrogate key.

    Args:
        silver_order_items: An enriched Silver Order Summary Item
            DataFrame containing an ``item_name`` column.

    Returns:
        pd.DataFrame: The Gold ``DimItem`` dimension with columns
        ``item_key`` and ``item_name``, sorted by ``item_name``
        ascending.
    """
    item_dimension = silver_order_items.loc[:, _REQUIRED_SILVER_COLUMNS]
    item_dimension = item_dimension.dropna(subset=[_ITEM_NAME_COLUMN])
    item_dimension = item_dimension.drop_duplicates()
    item_dimension = item_dimension.sort_values(by=_ITEM_NAME_COLUMN)
    item_dimension = item_dimension.reset_index(drop=True)

    item_dimension = _assign_surrogate_key(item_dimension)

    return item_dimension


def _assign_surrogate_key(item_dimension: pd.DataFrame) -> pd.DataFrame:
    """
    Assign a sequential surrogate key as the first column.

    Args:
        item_dimension: A deduplicated, sorted, index-reset item
            dimension DataFrame.

    Returns:
        pd.DataFrame: The item dimension DataFrame with an
        ``item_key`` column inserted as the first column, starting
        from 1 and incrementing sequentially.
    """
    item_dimension = item_dimension.copy()

    surrogate_keys = range(
        _SURROGATE_KEY_START, _SURROGATE_KEY_START + len(item_dimension)
    )
    item_dimension.insert(0, _ITEM_KEY_COLUMN, surrogate_keys)

    return item_dimension
