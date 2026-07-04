"""
Gold Dimension Key Lookup.

Attaches surrogate keys from already-built Gold dimensions onto an
already-transformed Silver DataFrame. This module performs only
lookups (LEFT joins) — it does not aggregate, validate, calculate
measures, orchestrate, or perform any file or database I/O.
"""

from typing import Final

import pandas as pd

# Keys used to look up each dimension inside the ``dimensions`` dict
# passed to ``attach_dimension_keys()``.
_DATE_DIMENSION_KEY: Final[str] = "date"
_RESTAURANT_DIMENSION_KEY: Final[str] = "restaurant"
_BRAND_DIMENSION_KEY: Final[str] = "brand"
_PLATFORM_DIMENSION_KEY: Final[str] = "platform"
_CATEGORY_DIMENSION_KEY: Final[str] = "category"
_ITEM_DIMENSION_KEY: Final[str] = "item"

# Business columns used to merge each dimension onto the Silver
# DataFrame.
_BUSINESS_DATE_COLUMN: Final[str] = "business_date"
_RESTAURANT_NAME_COLUMN: Final[str] = "restaurant_name"
_BRAND_COLUMN: Final[str] = "brand"
_PLATFORM_COLUMN: Final[str] = "platform"
_CATEGORY_NAME_COLUMN: Final[str] = "category_name"
_ITEM_NAME_COLUMN: Final[str] = "item_name"

# Surrogate key columns contributed by each dimension.
_DATE_KEY_COLUMN: Final[str] = "date_key"
_RESTAURANT_KEY_COLUMN: Final[str] = "restaurant_key"
_BRAND_KEY_COLUMN: Final[str] = "brand_key"
_PLATFORM_KEY_COLUMN: Final[str] = "platform_key"
_CATEGORY_KEY_COLUMN: Final[str] = "category_key"
_ITEM_KEY_COLUMN: Final[str] = "item_key"


def attach_dimension_keys(
    dataframe: pd.DataFrame,
    dimensions: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Attach Gold dimension surrogate keys onto a Silver DataFrame.

    Every supported dimension present in ``dimensions`` is joined onto
    ``dataframe`` via a LEFT join on its business attribute, adding
    the dimension's surrogate key column. Dimensions absent from
    ``dimensions`` are simply skipped — the function never fails
    because a dimension is missing.

    Supported dimension keys and their lookups:
        - "date": merges on ``business_date``, adds ``date_key``.
        - "restaurant": merges on ``restaurant_name``, adds
          ``restaurant_key``.
        - "brand": merges on ``brand``, adds ``brand_key``.
        - "platform": merges on ``platform``, adds ``platform_key``.
        - "category": merges on ``category_name``, adds
          ``category_key``.
        - "item": merges on ``item_name``, adds ``item_key``.

    Args:
        dataframe: The Silver DataFrame to enrich with surrogate keys.
        dimensions: Mapping of dimension name to its Gold dimension
            DataFrame. Any subset of the supported dimension names may
            be supplied.

    Returns:
        pd.DataFrame: A copy of ``dataframe`` with every available
        surrogate key attached. Every input row is preserved.
    """
    enriched_dataframe = dataframe.copy()

    enriched_dataframe = _attach_date_key(enriched_dataframe, dimensions)
    enriched_dataframe = _attach_restaurant_key(enriched_dataframe, dimensions)
    enriched_dataframe = _attach_brand_key(enriched_dataframe, dimensions)
    enriched_dataframe = _attach_platform_key(enriched_dataframe, dimensions)
    enriched_dataframe = _attach_category_key(enriched_dataframe, dimensions)
    enriched_dataframe = _attach_item_key(enriched_dataframe, dimensions)

    return enriched_dataframe


def _attach_date_key(
    dataframe: pd.DataFrame,
    dimensions: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Attach ``date_key`` from the date dimension, if supplied.

    Args:
        dataframe: The DataFrame to enrich.
        dimensions: Mapping of dimension name to Gold dimension
            DataFrame.

    Returns:
        pd.DataFrame: ``dataframe`` with ``date_key`` attached, or
        unchanged if the date dimension is not present.
    """
    date_dimension = dimensions.get(_DATE_DIMENSION_KEY)

    if date_dimension is None:
        return dataframe

    return _merge_surrogate_key(
        dataframe, date_dimension, _BUSINESS_DATE_COLUMN, _DATE_KEY_COLUMN
    )


def _attach_restaurant_key(
    dataframe: pd.DataFrame,
    dimensions: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Attach ``restaurant_key`` from the restaurant dimension, if supplied.

    Args:
        dataframe: The DataFrame to enrich.
        dimensions: Mapping of dimension name to Gold dimension
            DataFrame.

    Returns:
        pd.DataFrame: ``dataframe`` with ``restaurant_key`` attached,
        or unchanged if the restaurant dimension is not present.
    """
    restaurant_dimension = dimensions.get(_RESTAURANT_DIMENSION_KEY)

    if restaurant_dimension is None:
        return dataframe

    return _merge_surrogate_key(
        dataframe, restaurant_dimension, _RESTAURANT_NAME_COLUMN, _RESTAURANT_KEY_COLUMN
    )


def _attach_brand_key(
    dataframe: pd.DataFrame,
    dimensions: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Attach ``brand_key`` from the brand dimension, if supplied.

    Args:
        dataframe: The DataFrame to enrich.
        dimensions: Mapping of dimension name to Gold dimension
            DataFrame.

    Returns:
        pd.DataFrame: ``dataframe`` with ``brand_key`` attached, or
        unchanged if the brand dimension is not present.
    """
    brand_dimension = dimensions.get(_BRAND_DIMENSION_KEY)

    if brand_dimension is None:
        return dataframe

    return _merge_surrogate_key(
        dataframe, brand_dimension, _BRAND_COLUMN, _BRAND_KEY_COLUMN
    )


def _attach_platform_key(
    dataframe: pd.DataFrame,
    dimensions: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Attach ``platform_key`` from the platform dimension, if supplied.

    Args:
        dataframe: The DataFrame to enrich.
        dimensions: Mapping of dimension name to Gold dimension
            DataFrame.

    Returns:
        pd.DataFrame: ``dataframe`` with ``platform_key`` attached, or
        unchanged if the platform dimension is not present.
    """
    platform_dimension = dimensions.get(_PLATFORM_DIMENSION_KEY)

    if platform_dimension is None:
        return dataframe

    return _merge_surrogate_key(
        dataframe, platform_dimension, _PLATFORM_COLUMN, _PLATFORM_KEY_COLUMN
    )


def _attach_category_key(
    dataframe: pd.DataFrame,
    dimensions: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Attach ``category_key`` from the category dimension, if supplied.

    Args:
        dataframe: The DataFrame to enrich.
        dimensions: Mapping of dimension name to Gold dimension
            DataFrame.

    Returns:
        pd.DataFrame: ``dataframe`` with ``category_key`` attached, or
        unchanged if the category dimension is not present.
    """
    category_dimension = dimensions.get(_CATEGORY_DIMENSION_KEY)

    if category_dimension is None:
        return dataframe

    return _merge_surrogate_key(
        dataframe, category_dimension, _CATEGORY_NAME_COLUMN, _CATEGORY_KEY_COLUMN
    )


def _attach_item_key(
    dataframe: pd.DataFrame,
    dimensions: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Attach ``item_key`` from the item dimension, if supplied.

    Args:
        dataframe: The DataFrame to enrich.
        dimensions: Mapping of dimension name to Gold dimension
            DataFrame.

    Returns:
        pd.DataFrame: ``dataframe`` with ``item_key`` attached, or
        unchanged if the item dimension is not present.
    """
    item_dimension = dimensions.get(_ITEM_DIMENSION_KEY)

    if item_dimension is None:
        return dataframe

    return _merge_surrogate_key(
        dataframe, item_dimension, _ITEM_NAME_COLUMN, _ITEM_KEY_COLUMN
    )


def _merge_surrogate_key(
    dataframe: pd.DataFrame,
    dimension: pd.DataFrame,
    business_column: str,
    key_column: str,
) -> pd.DataFrame:
    """
    Merge a single surrogate key column onto a DataFrame via a LEFT join.

    Only the business column and surrogate key column are taken from
    the dimension, so no extraneous dimension columns are duplicated
    onto the result.

    Args:
        dataframe: The DataFrame to enrich.
        dimension: The Gold dimension DataFrame supplying the
            surrogate key.
        business_column: Name of the business attribute column to
            join on.
        key_column: Name of the surrogate key column to attach.

    Returns:
        pd.DataFrame: A copy of ``dataframe`` with ``key_column``
        attached, preserving every input row and its original order.
    """
    dataframe = dataframe.copy()

    if business_column not in dataframe.columns:
        return dataframe
    
    key_lookup = dimension.loc[:, [business_column, key_column]]

    return dataframe.merge(
    key_lookup,
    on=business_column,
    how="left",
    sort=False,
    copy=False,
    )
