"""
Gold Brand Dimension Builder.

Builds the conformed ``DimBrand`` dimension from the enriched Silver
Order Summary dataset. This module performs no file I/O, no database
operations, no logging, and no orchestration — it is a pure
transformation module that models Silver brand names into a Gold
dimension.
"""

from typing import Final

import pandas as pd

# Column required from the Silver Order Summary dataset.
_BRAND_COLUMN: Final[str] = "brand"

_REQUIRED_SILVER_COLUMNS: Final[tuple[str, ...]] = (
    _BRAND_COLUMN,
)

# Surrogate key column for the Gold dimension.
_BRAND_KEY_COLUMN: Final[str] = "brand_key"
_SURROGATE_KEY_START: Final[int] = 1


def build_brand_dimension(silver_orders: pd.DataFrame) -> pd.DataFrame:
    """
    Build the Gold ``DimBrand`` dimension from enriched Silver orders.

    Selects the brand already present in the Silver layer, drops rows
    with a null brand, removes duplicate brands, sorts the remaining
    brands alphabetically, and assigns a sequential surrogate key.

    Brandless platforms (Delivery, Pick Up, Dine In) legitimately
    produce null brands in Silver; those rows are dropped and must
    not appear in ``DimBrand``.

    Args:
        silver_orders: An enriched Silver Order Summary DataFrame
            containing a ``brand`` column.

    Returns:
        pd.DataFrame: The Gold ``DimBrand`` dimension with columns
        ``brand_key`` and ``brand``, sorted by ``brand`` ascending.
    """
    brand_dimension = silver_orders.loc[:, _REQUIRED_SILVER_COLUMNS]
    brand_dimension = brand_dimension.dropna(subset=[_BRAND_COLUMN])
    brand_dimension = brand_dimension.drop_duplicates()
    brand_dimension = brand_dimension.sort_values(by=_BRAND_COLUMN)
    brand_dimension = brand_dimension.reset_index(drop=True)

    brand_dimension = _assign_surrogate_key(brand_dimension)

    return brand_dimension


def _assign_surrogate_key(brand_dimension: pd.DataFrame) -> pd.DataFrame:
    """
    Assign a sequential surrogate key as the first column.

    Args:
        brand_dimension: A deduplicated, sorted, index-reset brand
            dimension DataFrame.

    Returns:
        pd.DataFrame: The brand dimension DataFrame with a
        ``brand_key`` column inserted as the first column, starting
        from 1 and incrementing sequentially.
    """
    brand_dimension = brand_dimension.copy()

    surrogate_keys = range(
        _SURROGATE_KEY_START, _SURROGATE_KEY_START + len(brand_dimension)
    )
    brand_dimension.insert(0, _BRAND_KEY_COLUMN, surrogate_keys)

    return brand_dimension
