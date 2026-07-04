"""
Gold FactOrders Builder.

Builds the Gold ``FactOrders`` table from the enriched Silver Order
Summary dataset. This module performs only transformation — it
attaches dimension surrogate keys and selects the fact's columns. It
does not perform file I/O, orchestration, validation, or any database
operations.
"""

from typing import Final

import pandas as pd

from src.gold.lookup import attach_dimension_keys

# Dimension surrogate keys included in the fact.
_DATE_KEY_COLUMN: Final[str] = "date_key"
_RESTAURANT_KEY_COLUMN: Final[str] = "restaurant_key"
_BRAND_KEY_COLUMN: Final[str] = "brand_key"
_PLATFORM_KEY_COLUMN: Final[str] = "platform_key"

_DIMENSION_KEY_COLUMNS: Final[tuple[str, ...]] = (
    _DATE_KEY_COLUMN,
    _RESTAURANT_KEY_COLUMN,
    _BRAND_KEY_COLUMN,
    _PLATFORM_KEY_COLUMN,
)

# Degenerate dimensions carried directly from Silver onto the fact.
_INVOICE_NO_COLUMN: Final[str] = "invoice_no"
_KOT_NO_COLUMN: Final[str] = "kot_no"

_DEGENERATE_DIMENSION_COLUMNS: Final[tuple[str, ...]] = (
    _INVOICE_NO_COLUMN,
    _KOT_NO_COLUMN,
)

# Measures carried directly from Silver onto the fact.
_MY_AMOUNT_COLUMN: Final[str] = "my_amount"
_TOTAL_TAX_COLUMN: Final[str] = "total_tax"
_DISCOUNT_COLUMN: Final[str] = "discount"
_DELIVERY_CHARGE_COLUMN: Final[str] = "delivery_charge"
_CONTAINER_CHARGE_COLUMN: Final[str] = "container_charge"
_SERVICE_CHARGE_COLUMN: Final[str] = "service_charge"
_ADDITIONAL_CHARGE_COLUMN: Final[str] = "additional_charge"
_DEDUCTION_CHARGE_COLUMN: Final[str] = "deduction_charge"
_WAIVED_OFF_COLUMN: Final[str] = "waived_off"
_ROUND_OFF_COLUMN: Final[str] = "round_off"
_TOTAL_COLUMN: Final[str] = "total"

_MEASURE_COLUMNS: Final[tuple[str, ...]] = (
    _MY_AMOUNT_COLUMN,
    _TOTAL_TAX_COLUMN,
    _DISCOUNT_COLUMN,
    _DELIVERY_CHARGE_COLUMN,
    _CONTAINER_CHARGE_COLUMN,
    _SERVICE_CHARGE_COLUMN,
    _ADDITIONAL_CHARGE_COLUMN,
    _DEDUCTION_CHARGE_COLUMN,
    _WAIVED_OFF_COLUMN,
    _ROUND_OFF_COLUMN,
    _TOTAL_COLUMN,
)

_FACT_COLUMNS: Final[tuple[str, ...]] = (
    _DIMENSION_KEY_COLUMNS + _DEGENERATE_DIMENSION_COLUMNS + _MEASURE_COLUMNS
)


def build_orders_fact(
    silver_orders: pd.DataFrame,
    dimensions: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Build the Gold ``FactOrders`` table from enriched Silver orders.

    Attaches the ``date``, ``restaurant``, ``brand``, and ``platform``
    dimension surrogate keys onto the Silver Order Summary DataFrame,
    then selects the fact's dimension keys, degenerate dimensions, and
    measures.

    Args:
        silver_orders: An enriched Silver Order Summary DataFrame.
        dimensions: Mapping of dimension name to its Gold dimension
            DataFrame, as expected by ``attach_dimension_keys()``.

    Returns:
        pd.DataFrame: The Gold ``FactOrders`` table containing
        ``date_key``, ``restaurant_key``, ``brand_key``,
        ``platform_key``, ``invoice_no``, ``kot_no``, ``my_amount``,
        ``total_tax``, ``discount``, ``delivery_charge``,
        ``container_charge``, ``service_charge``,
        ``additional_charge``, ``deduction_charge``, ``waived_off``,
        ``round_off``, and ``total``.
    """
    orders_with_keys = attach_dimension_keys(silver_orders, dimensions)
    orders_fact = orders_with_keys.loc[:, _FACT_COLUMNS]

    return orders_fact
