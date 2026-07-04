"""
Gold Platform Dimension Builder.

Builds the conformed ``DimPlatform`` dimension from the enriched
Silver Order Summary dataset. This module performs no file I/O, no
database operations, no logging, and no orchestration — it is a pure
transformation module that models Silver platform names into a Gold
dimension.
"""

from typing import Final

import pandas as pd

# Column required from the Silver Order Summary dataset.
_PLATFORM_COLUMN: Final[str] = "platform"

_REQUIRED_SILVER_COLUMNS: Final[tuple[str, ...]] = (
    _PLATFORM_COLUMN,
)

# Surrogate key column for the Gold dimension.
_PLATFORM_KEY_COLUMN: Final[str] = "platform_key"
_SURROGATE_KEY_START: Final[int] = 1


def build_platform_dimension(silver_orders: pd.DataFrame) -> pd.DataFrame:
    """
    Build the Gold ``DimPlatform`` dimension from enriched Silver orders.

    Selects the platform already present in the Silver layer, drops
    rows with a null platform, removes duplicate platforms, sorts the
    remaining platforms alphabetically, and assigns a sequential
    surrogate key.

    Args:
        silver_orders: An enriched Silver Order Summary DataFrame
            containing a ``platform`` column.

    Returns:
        pd.DataFrame: The Gold ``DimPlatform`` dimension with columns
        ``platform_key`` and ``platform``, sorted by ``platform``
        ascending.
    """
    platform_dimension = silver_orders.loc[:, _REQUIRED_SILVER_COLUMNS]
    platform_dimension = platform_dimension.dropna(subset=[_PLATFORM_COLUMN])
    platform_dimension = platform_dimension.drop_duplicates()
    platform_dimension = platform_dimension.sort_values(by=_PLATFORM_COLUMN)
    platform_dimension = platform_dimension.reset_index(drop=True)

    platform_dimension = _assign_surrogate_key(platform_dimension)

    return platform_dimension


def _assign_surrogate_key(platform_dimension: pd.DataFrame) -> pd.DataFrame:
    """
    Assign a sequential surrogate key as the first column.

    Args:
        platform_dimension: A deduplicated, sorted, index-reset
            platform dimension DataFrame.

    Returns:
        pd.DataFrame: The platform dimension DataFrame with a
        ``platform_key`` column inserted as the first column,
        starting from 1 and incrementing sequentially.
    """
    platform_dimension = platform_dimension.copy()

    surrogate_keys = range(
        _SURROGATE_KEY_START, _SURROGATE_KEY_START + len(platform_dimension)
    )
    platform_dimension.insert(0, _PLATFORM_KEY_COLUMN, surrogate_keys)

    return platform_dimension
