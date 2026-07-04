"""
Gold Category Dimension Builder.

Builds the conformed ``DimCategory`` dimension from the enriched
Silver Order Summary Item dataset. This module performs no file I/O,
no database operations, no logging, and no orchestration — it is a
pure transformation module that models Silver category names into a
Gold dimension.
"""

from typing import Final

import pandas as pd

# Column required from the Silver Order Summary Item dataset.
_CATEGORY_NAME_COLUMN: Final[str] = "category_name"

_REQUIRED_SILVER_COLUMNS: Final[tuple[str, ...]] = (
    _CATEGORY_NAME_COLUMN,
)

# Surrogate key column for the Gold dimension.
_CATEGORY_KEY_COLUMN: Final[str] = "category_key"
_SURROGATE_KEY_START: Final[int] = 1


def build_category_dimension(silver_order_items: pd.DataFrame) -> pd.DataFrame:
    """
    Build the Gold ``DimCategory`` dimension from enriched Silver order items.

    Selects the category name already present in the Silver layer,
    drops rows with a null category, removes duplicate categories,
    sorts the remaining categories alphabetically, and assigns a
    sequential surrogate key.

    Args:
        silver_order_items: An enriched Silver Order Summary Item
            DataFrame containing a ``category_name`` column.

    Returns:
        pd.DataFrame: The Gold ``DimCategory`` dimension with columns
        ``category_key`` and ``category_name``, sorted by
        ``category_name`` ascending.
    """
    category_dimension = silver_order_items.loc[:, _REQUIRED_SILVER_COLUMNS]
    category_dimension = category_dimension.dropna(subset=[_CATEGORY_NAME_COLUMN])
    category_dimension = category_dimension.drop_duplicates()
    category_dimension = category_dimension.sort_values(by=_CATEGORY_NAME_COLUMN)
    category_dimension = category_dimension.reset_index(drop=True)

    category_dimension = _assign_surrogate_key(category_dimension)

    return category_dimension


def _assign_surrogate_key(category_dimension: pd.DataFrame) -> pd.DataFrame:
    """
    Assign a sequential surrogate key as the first column.

    Args:
        category_dimension: A deduplicated, sorted, index-reset
            category dimension DataFrame.

    Returns:
        pd.DataFrame: The category dimension DataFrame with a
        ``category_key`` column inserted as the first column,
        starting from 1 and incrementing sequentially.
    """
    category_dimension = category_dimension.copy()

    surrogate_keys = range(
        _SURROGATE_KEY_START, _SURROGATE_KEY_START + len(category_dimension)
    )
    category_dimension.insert(0, _CATEGORY_KEY_COLUMN, surrogate_keys)

    return category_dimension
