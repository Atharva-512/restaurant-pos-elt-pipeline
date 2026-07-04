"""
Gold Lookup Failure Diagnostic Script.

This is NOT a unit test. It is a temporary debugging utility used
during Gold layer development to investigate WHY certain surrogate
key lookups produced nulls in the Gold fact tables.

The script never modifies any data — Silver, Gold, or otherwise. It
only reads Silver data, builds the Gold layer via the existing
``build_gold_layer()`` function, and prints diagnostics.

Run directly:
    python tests/debug_gold_lookup_failures.py
"""

from pathlib import Path
from typing import Final

import pandas as pd

from src.gold.runner import build_gold_layer

SILVER_ORDER_SUMMARY_DIR: Final[Path] = Path("data/silver/order_summary")
SILVER_ORDER_SUMMARY_ITEM_DIR: Final[Path] = Path("data/silver/order_summary_item")
SILVER_KOT_DIR: Final[Path] = Path("data/silver/kot_process_time")

_SECTION_SEPARATOR: Final[str] = "=" * 60
_SAMPLE_ROW_LIMIT: Final[int] = 20
_DISTINCT_VALUE_LIMIT: Final[int] = 20

# Human-readable labels for business columns, used in "Distinct ..."
# headings.
_COLUMN_DISPLAY_LABELS: Final[dict[str, str]] = {
    "business_date": "Business Dates",
    "restaurant_name": "Restaurants",
    "brand": "Brands",
    "platform": "Platforms",
    "invoice_no": "Invoice Numbers",
    "category_name": "Categories",
    "item_name": "Items",
    "punch_time": "Punch Times",
}

_ORDERS_KEY_COLUMNS: Final[tuple[str, ...]] = (
    "date_key",
    "restaurant_key",
    "brand_key",
    "platform_key",
)
_ORDERS_BUSINESS_COLUMNS: Final[tuple[str, ...]] = (
    "business_date",
    "restaurant_name",
    "brand",
    "platform",
    "invoice_no",
)

_ORDER_ITEMS_KEY_COLUMNS: Final[tuple[str, ...]] = (
    "date_key",
    "restaurant_key",
    "brand_key",
    "platform_key",
    "category_key",
    "item_key",
)
_ORDER_ITEMS_BUSINESS_COLUMNS: Final[tuple[str, ...]] = (
    "restaurant_name",
    "invoice_no",
    "business_date",
    "brand",
    "platform",
    "category_name",
    "item_name",
)

_KITCHEN_KEY_COLUMNS: Final[tuple[str, ...]] = ("date_key", "item_key")
_KITCHEN_BUSINESS_COLUMNS: Final[tuple[str, ...]] = (
    "punch_time",
    "business_date",
    "item_name",
)


def _discover_parquet_files(directory: Path) -> list[Path]:
    """
    Recursively discover every Parquet file under a directory.

    Args:
        directory: Root directory to search under.

    Returns:
        list[Path]: Sorted list of Parquet file paths found under
        ``directory``. Empty list if the directory does not exist.
    """
    if not directory.exists():
        return []

    return sorted(directory.rglob("*.parquet"))


def _load_silver_dataset(directory: Path) -> pd.DataFrame:
    """
    Load every Parquet file under a Silver dataset directory into a
    single DataFrame.

    Args:
        directory: Root directory of the Silver dataset.

    Returns:
        pd.DataFrame: The concatenated contents of every Parquet file
        found under ``directory``.

    Raises:
        FileNotFoundError: If no Parquet files are found under
            ``directory``.
    """
    parquet_files = _discover_parquet_files(directory)

    if not parquet_files:
        raise FileNotFoundError(f"No Parquet files found under: {directory}")

    frames = [pd.read_parquet(file_path) for file_path in parquet_files]

    return pd.concat(frames, ignore_index=True)


def _load_silver_datasets() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load the enriched Silver Order Summary, Order Summary Item, and
    KOT datasets.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: The Silver
        Order Summary, Order Summary Item, and KOT DataFrames.
    """
    silver_orders = _load_silver_dataset(SILVER_ORDER_SUMMARY_DIR)
    silver_order_items = _load_silver_dataset(SILVER_ORDER_SUMMARY_ITEM_DIR)
    silver_kot = _load_silver_dataset(SILVER_KOT_DIR)

    return silver_orders, silver_order_items, silver_kot


def _build_orders_diagnostic_frame(
    fact_orders: pd.DataFrame, silver_orders: pd.DataFrame
) -> pd.DataFrame:
    """
    Build a diagnostic frame combining FactOrders keys with the
    Silver Order Summary business columns responsible for them.

    Row alignment relies on the Gold build never dropping or
    reordering rows, so the Nth row of ``fact_orders`` corresponds to
    the Nth row of ``silver_orders``.

    Args:
        fact_orders: The built Gold ``FactOrders`` DataFrame.
        silver_orders: The Silver Order Summary DataFrame.

    Returns:
        pd.DataFrame: A read-only diagnostic frame with the FactOrders
        surrogate key columns and the Silver business columns.
    """
    key_columns = fact_orders.loc[:, list(_ORDERS_KEY_COLUMNS)].reset_index(drop=True)
    business_columns = silver_orders.loc[:, list(_ORDERS_BUSINESS_COLUMNS)].reset_index(
        drop=True
    )

    return pd.concat([key_columns, business_columns], axis=1)


def _build_order_items_diagnostic_frame(
    fact_order_items: pd.DataFrame,
    silver_order_items: pd.DataFrame,
    silver_orders: pd.DataFrame,
) -> pd.DataFrame:
    silver_order_items = silver_order_items.copy()
    silver_orders = silver_orders.copy()

    silver_order_items["invoice_no"] = (
        silver_order_items["invoice_no"].astype(str)
    )

    silver_orders["invoice_no"] = (
        silver_orders["invoice_no"].astype(str)
    )
    """
    Build a diagnostic frame combining FactOrderItems keys with the
    Silver business columns responsible for them.

    ``business_date``, ``brand``, and ``platform`` are not present on
    Silver Order Summary Item directly, so they are recovered by
    joining Silver Order Summary Item to Silver Order Summary on
    ``restaurant_name`` and ``invoice_no`` — the same join used when
    the fact was originally built. Row alignment relies on the Gold
    build never dropping or reordering rows.

    Args:
        fact_order_items: The built Gold ``FactOrderItems`` DataFrame.
        silver_order_items: The Silver Order Summary Item DataFrame.
        silver_orders: The Silver Order Summary DataFrame.

    Returns:
        pd.DataFrame: A read-only diagnostic frame with the
        FactOrderItems surrogate key columns and the Silver business
        columns.
    """
    order_context = silver_orders.loc[
        :, ["restaurant_name", "invoice_no", "business_date", "brand", "platform"]
    ]
    order_items_context = silver_order_items.merge(
        order_context, on=["restaurant_name", "invoice_no"], how="left"
    )

    key_columns = fact_order_items.loc[:, list(_ORDER_ITEMS_KEY_COLUMNS)].reset_index(
        drop=True
    )
    business_columns = order_items_context.loc[
        :, list(_ORDER_ITEMS_BUSINESS_COLUMNS)
    ].reset_index(drop=True)

    return pd.concat([key_columns, business_columns], axis=1)


def _build_kitchen_diagnostic_frame(
    fact_kitchen: pd.DataFrame, silver_kot: pd.DataFrame
) -> pd.DataFrame:
    """
    Build a diagnostic frame combining FactKitchen keys with the
    Silver business columns responsible for them.

    ``business_date`` is not present on Silver KOT directly, so it is
    derived here from ``punch_time`` purely for diagnostic display
    (mirroring the derivation Gold performs, without modifying any
    production code). Row alignment relies on the Gold build never
    dropping or reordering rows.

    Args:
        fact_kitchen: The built Gold ``FactKitchen`` DataFrame.
        silver_kot: The Silver KOT DataFrame.

    Returns:
        pd.DataFrame: A read-only diagnostic frame with the
        FactKitchen surrogate key columns and the Silver business
        columns.
    """
    kitchen_context = silver_kot.loc[:, ["punch_time", "item_name"]].copy()
    kitchen_context["business_date"] = kitchen_context["punch_time"].dt.date

    key_columns = fact_kitchen.loc[:, list(_KITCHEN_KEY_COLUMNS)].reset_index(drop=True)
    business_columns = kitchen_context.loc[:, list(_KITCHEN_BUSINESS_COLUMNS)].reset_index(
        drop=True
    )

    return pd.concat([key_columns, business_columns], axis=1)


def _print_section_header(title: str) -> None:
    """
    Print a section header with readable separators.

    Args:
        title: The section title to print.
    """
    print(_SECTION_SEPARATOR)
    print(title)
    print(_SECTION_SEPARATOR)


def _diagnose_key_column(
    diagnostic_frame: pd.DataFrame,
    key_column: str,
    business_columns: tuple[str, ...],
) -> None:
    """
    Print diagnostics for a single surrogate key column.

    If the key column has zero nulls, prints ``PASS``. Otherwise
    prints the null count, percentage, a distinct-value breakdown for
    every business column among the null rows, and a sample of the
    first null rows.

    Args:
        diagnostic_frame: A frame containing the key column and the
            business columns responsible for it.
        key_column: Name of the surrogate key column to diagnose.
        business_columns: Business columns to inspect for the null
            rows.
    """
    print(key_column)

    null_mask = diagnostic_frame[key_column].isna()
    null_count = int(null_mask.sum())

    if null_count == 0:
        print("  PASS")
        print()
        return

    total_rows = len(diagnostic_frame)
    null_percentage = round((null_count / total_rows) * 100, 2)

    print(f"  Null rows  : {null_count}")
    print(f"  Percentage : {null_percentage}%")

    null_rows = diagnostic_frame.loc[null_mask]

    for business_column in business_columns:
        display_label = _COLUMN_DISPLAY_LABELS.get(business_column, business_column)
        print(f"  Distinct {display_label}")
        value_counts = null_rows[business_column].value_counts(dropna=False)
        print(value_counts.head(_DISTINCT_VALUE_LIMIT).to_string())
        print()

    print("  Sample Rows")
    sample_columns = [key_column, *business_columns]
    sample_rows = null_rows.loc[:, sample_columns].head(_SAMPLE_ROW_LIMIT)
    print(sample_rows.to_string(index=False))
    print()


def _diagnose_fact(
    fact_label: str,
    diagnostic_frame: pd.DataFrame,
    key_columns: tuple[str, ...],
    business_columns: tuple[str, ...],
) -> None:
    """
    Print diagnostics for every surrogate key column of a fact table.

    Args:
        fact_label: Human-readable name of the fact being diagnosed.
        diagnostic_frame: A frame containing the fact's key columns
            and the business columns responsible for them.
        key_columns: Surrogate key columns to diagnose.
        business_columns: Business columns to inspect for null rows.
    """
    _print_section_header(fact_label)

    for key_column in key_columns:
        _diagnose_key_column(diagnostic_frame, key_column, business_columns)


def main() -> None:
    """
    Load Silver data, build the Gold layer, and print lookup-failure
    diagnostics for every fact table.
    """
    silver_orders, silver_order_items, silver_kot = _load_silver_datasets()

    result = build_gold_layer(silver_orders, silver_order_items, silver_kot)
    facts = result["facts"]

    orders_diagnostic_frame = _build_orders_diagnostic_frame(
        facts["orders"], silver_orders
    )
    _diagnose_fact(
        "FACT ORDERS",
        orders_diagnostic_frame,
        _ORDERS_KEY_COLUMNS,
        _ORDERS_BUSINESS_COLUMNS,
    )

    order_items_diagnostic_frame = _build_order_items_diagnostic_frame(
        facts["order_items"], silver_order_items, silver_orders
    )
    _diagnose_fact(
        "FACT ORDER ITEMS",
        order_items_diagnostic_frame,
        _ORDER_ITEMS_KEY_COLUMNS,
        _ORDER_ITEMS_BUSINESS_COLUMNS,
    )

    kitchen_diagnostic_frame = _build_kitchen_diagnostic_frame(
        facts["kitchen"], silver_kot
    )
    _diagnose_fact(
        "FACT KITCHEN",
        kitchen_diagnostic_frame,
        _KITCHEN_KEY_COLUMNS,
        _KITCHEN_BUSINESS_COLUMNS,
    )


if __name__ == "__main__":
    main()