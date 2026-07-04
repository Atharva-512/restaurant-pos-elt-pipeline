"""
Gold Restaurant Dimension Builder.

Builds the conformed ``DimRestaurant`` dimension from the enriched
Silver Order Summary dataset. This module performs no file I/O, no
database operations, no logging, and no orchestration — it is a pure
transformation module that models Silver restaurant names into a
Gold dimension.
"""

from typing import Final

import pandas as pd

# Column required from the Silver Order Summary dataset.
_RESTAURANT_NAME_COLUMN: Final[str] = "restaurant_name"

_REQUIRED_SILVER_COLUMNS: Final[tuple[str, ...]] = (
    _RESTAURANT_NAME_COLUMN,
)

# Surrogate key column for the Gold dimension.
_RESTAURANT_KEY_COLUMN: Final[str] = "restaurant_key"
_SURROGATE_KEY_START: Final[int] = 1


def build_restaurant_dimension(silver_orders: pd.DataFrame) -> pd.DataFrame:
    """
    Build the Gold ``DimRestaurant`` dimension from enriched Silver orders.

    Selects the restaurant name already present in the Silver layer,
    drops rows with a null restaurant name, removes duplicate names,
    sorts them alphabetically, and assigns a sequential surrogate key.

    Args:
        silver_orders: An enriched Silver Order Summary DataFrame
            containing a ``restaurant_name`` column.

    Returns:
        pd.DataFrame: The Gold ``DimRestaurant`` dimension with
        columns ``restaurant_key`` and ``restaurant_name``, sorted by
        ``restaurant_name`` ascending.
    """
    restaurant_dimension = silver_orders.loc[:, _REQUIRED_SILVER_COLUMNS]
    restaurant_dimension = restaurant_dimension.dropna(
        subset=[_RESTAURANT_NAME_COLUMN]
    )
    restaurant_dimension = restaurant_dimension.drop_duplicates()
    restaurant_dimension = restaurant_dimension.sort_values(
        by=_RESTAURANT_NAME_COLUMN
    )
    restaurant_dimension = restaurant_dimension.reset_index(drop=True)

    restaurant_dimension = _assign_surrogate_key(restaurant_dimension)

    return restaurant_dimension


def _assign_surrogate_key(restaurant_dimension: pd.DataFrame) -> pd.DataFrame:
    """
    Assign a sequential surrogate key as the first column.

    Args:
        restaurant_dimension: A deduplicated, sorted, index-reset
            restaurant dimension DataFrame.

    Returns:
        pd.DataFrame: The restaurant dimension DataFrame with a
        ``restaurant_key`` column inserted as the first column,
        starting from 1 and incrementing sequentially.
    """
    restaurant_dimension = restaurant_dimension.copy()

    surrogate_keys = range(
        _SURROGATE_KEY_START, _SURROGATE_KEY_START + len(restaurant_dimension)
    )
    restaurant_dimension.insert(0, _RESTAURANT_KEY_COLUMN, surrogate_keys)

    return restaurant_dimension
