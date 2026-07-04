"""
Gold Layer Integration Validation Script.

This is the official, permanent regression check for the Gold layer.
It is NOT a pytest unit test, NOT an orchestration script, and NOT a
benchmark. Its sole purpose is to validate that the complete Gold
layer builds correctly via ``build_gold_layer()``.

Exceptions are never caught: loading failures, build-shape mismatches,
and missing source data all fail the script immediately and loudly.

Run directly:
    python tests/test_gold.py
"""

from pathlib import Path
from typing import Final

import pandas as pd

from src.gold.runner import build_gold_layer

SILVER_ORDER_SUMMARY_DIR: Final[Path] = Path("data/silver/order_summary")
SILVER_ORDER_SUMMARY_ITEM_DIR: Final[Path] = Path("data/silver/order_summary_item")
SILVER_KOT_DIR: Final[Path] = Path("data/silver/kot_process_time")

_SECTION_SEPARATOR: Final[str] = "=" * 60

_EXPECTED_DIMENSION_COUNT: Final[int] = 6
_EXPECTED_FACT_COUNT: Final[int] = 3

_DIMENSION_LABELS: Final[dict[str, str]] = {
    "date": "DimDate",
    "restaurant": "DimRestaurant",
    "brand": "DimBrand",
    "platform": "DimPlatform",
    "category": "DimCategory",
    "item": "DimItem",
}

_FACT_LABELS: Final[dict[str, str]] = {
    "orders": "FactOrders",
    "order_items": "FactOrderItems",
    "kitchen": "FactKitchen",
}

_DIMENSION_SURROGATE_KEY_COLUMNS: Final[dict[str, str]] = {
    "date": "date_key",
    "restaurant": "restaurant_key",
    "brand": "brand_key",
    "platform": "platform_key",
    "category": "category_key",
    "item": "item_key",
}

_DIMENSION_BUSINESS_KEY_COLUMNS: Final[dict[str, str]] = {
    "date": "business_date",
    "restaurant": "restaurant_name",
    "brand": "brand",
    "platform": "platform",
    "category": "category_name",
    "item": "item_name",
}

_DIMENSION_EXPECTED_COLUMNS: Final[dict[str, tuple[str, ...]]] = {
    "date": (
        "date_key",
        "business_date",
        "weekday",
        "month",
        "month_name",
        "quarter",
        "year",
    ),
    "restaurant": ("restaurant_key", "restaurant_name"),
    "brand": ("brand_key", "brand"),
    "platform": ("platform_key", "platform"),
    "category": ("category_key", "category_name"),
    "item": ("item_key", "item_name"),
}

_FACT_NULL_KEY_COLUMNS: Final[dict[str, tuple[str, ...]]] = {
    "orders": ("date_key", "restaurant_key", "brand_key", "platform_key"),
    "order_items": (
        "date_key",
        "restaurant_key",
        "brand_key",
        "platform_key",
        "category_key",
        "item_key",
    ),
    "kitchen": ("date_key", "item_key"),
}

_FACT_EXPECTED_COLUMNS: Final[dict[str, tuple[str, ...]]] = {
    "orders": (
        "date_key",
        "restaurant_key",
        "brand_key",
        "platform_key",
        "invoice_no",
        "kot_no",
        "my_amount",
        "total_tax",
        "discount",
        "delivery_charge",
        "container_charge",
        "service_charge",
        "additional_charge",
        "deduction_charge",
        "waived_off",
        "round_off",
        "total",
    ),
    "order_items": (
        "date_key",
        "restaurant_key",
        "brand_key",
        "platform_key",
        "category_key",
        "item_key",
        "invoice_no",
        "item_quantity",
        "item_price",
        "item_total",
    ),
    "kitchen": (
        "date_key",
        "item_key",
        "kot_id",
        "order_type",
        "server_name",
        "item_status",
        "qty",
        "price",
        "preparation_time_taken_mins",
    ),
}


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
        raise FileNotFoundError(
            f"Directory does not exist: {directory}"
        )

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


def _validate_build_shape(
    dimensions: dict[str, pd.DataFrame], facts: dict[str, pd.DataFrame]
) -> None:
    """
    Verify ``build_gold_layer()`` produced the expected number of
    dimensions and facts.

    Args:
        dimensions: Mapping of dimension name to its built Gold
            dimension DataFrame.
        facts: Mapping of fact name to its built Gold fact DataFrame.

    Raises:
        ValueError: If the number of dimensions or facts does not
            match the expected count.
    """
    if len(dimensions) != _EXPECTED_DIMENSION_COUNT:
        raise ValueError(
            f"Expected {_EXPECTED_DIMENSION_COUNT} dimensions, got {len(dimensions)}"
        )

    if len(facts) != _EXPECTED_FACT_COUNT:
        raise ValueError(f"Expected {_EXPECTED_FACT_COUNT} facts, got {len(facts)}")


def _print_section_header(title: str) -> None:
    """
    Print a section header with readable separators.

    Args:
        title: The section title to print.
    """
    print(_SECTION_SEPARATOR)
    print(title)
    print(_SECTION_SEPARATOR)


def _print_dimension_summary(dimensions: dict[str, pd.DataFrame]) -> None:
    """
    Print row and column counts for every Gold dimension.

    Args:
        dimensions: Mapping of dimension name to its built Gold
            dimension DataFrame.
    """
    _print_section_header("DIMENSIONS")

    for dimension_name, dimension_df in dimensions.items():
        print(_DIMENSION_LABELS[dimension_name])
        print(f"  Rows    : {dimension_df.shape[0]}")
        print(f"  Columns : {dimension_df.shape[1]}")
        print()


def _print_fact_summary(facts: dict[str, pd.DataFrame]) -> None:
    """
    Print row and column counts for every Gold fact.

    Args:
        facts: Mapping of fact name to its built Gold fact DataFrame.
    """
    _print_section_header("FACTS")

    for fact_name, fact_df in facts.items():
        print(_FACT_LABELS[fact_name])
        print(f"  Rows    : {fact_df.shape[0]}")
        print(f"  Columns : {fact_df.shape[1]}")
        print()


def _validate_row_counts(
    facts: dict[str, pd.DataFrame],
    silver_orders: pd.DataFrame,
    silver_order_items: pd.DataFrame,
    silver_kot: pd.DataFrame,
) -> bool:
    """
    Verify each fact's row count matches its source Silver dataset.

    Row counts are cached in local variables before comparison.

    Args:
        facts: Mapping of fact name to its built Gold fact DataFrame.
        silver_orders: The Silver Order Summary DataFrame.
        silver_order_items: The Silver Order Summary Item DataFrame.
        silver_kot: The Silver KOT DataFrame.

    Returns:
        bool: ``True`` if every fact's row count matches its source
        Silver dataset, ``False`` otherwise.
    """
    _print_section_header("ROW COUNT VALIDATION")

    row_count_pairs = (
        ("orders", facts["orders"], silver_orders),
        ("order_items", facts["order_items"], silver_order_items),
        ("kitchen", facts["kitchen"], silver_kot),
    )

    all_passed = True

    for fact_name, fact_df, silver_df in row_count_pairs:
        fact_row_count = len(fact_df)
        silver_row_count = len(silver_df)
        passed = fact_row_count == silver_row_count
        all_passed = all_passed and passed

        status = "PASS" if passed else "FAIL"
        label = _FACT_LABELS[fact_name]
        print(f"{label} ({fact_row_count}) == Silver ({silver_row_count}) : {status}")

    return all_passed


def _validate_surrogate_key_duplicates(dimensions: dict[str, pd.DataFrame]) -> bool:
    """
    Verify every dimension's surrogate key has zero duplicates.

    Args:
        dimensions: Mapping of dimension name to its built Gold
            dimension DataFrame.

    Returns:
        bool: ``True`` if every dimension's surrogate key is unique,
        ``False`` otherwise.
    """
    _print_section_header("SURROGATE KEY DUPLICATE CHECK")

    all_passed = True

    for dimension_name, key_column in _DIMENSION_SURROGATE_KEY_COLUMNS.items():
        dimension_df = dimensions[dimension_name]
        duplicate_count = int(dimension_df[key_column].duplicated(keep=False).sum())
        passed = duplicate_count == 0
        all_passed = all_passed and passed

        print(f"{_DIMENSION_LABELS[dimension_name]} : duplicate {key_column} = {duplicate_count}")

    return all_passed


def _validate_business_key_duplicates(dimensions: dict[str, pd.DataFrame]) -> bool:
    """
    Verify every dimension's business key has zero duplicates.

    Args:
        dimensions: Mapping of dimension name to its built Gold
            dimension DataFrame.

    Returns:
        bool: ``True`` if every dimension's business key is unique,
        ``False`` otherwise.
    """
    _print_section_header("BUSINESS KEY DUPLICATE CHECK")

    all_passed = True

    for dimension_name, business_column in _DIMENSION_BUSINESS_KEY_COLUMNS.items():
        dimension_df = dimensions[dimension_name]
        duplicate_count = int(dimension_df[business_column].duplicated(keep=False).sum())
        passed = duplicate_count == 0
        all_passed = all_passed and passed

        print(
            f"{_DIMENSION_LABELS[dimension_name]} : duplicate {business_column} = {duplicate_count}"
        )

    return all_passed


def _validate_null_surrogate_keys(facts: dict[str, pd.DataFrame]) -> bool:
    """
    Verify every fact's dimension surrogate keys contain no nulls.

    Args:
        facts: Mapping of fact name to its built Gold fact DataFrame.

    Returns:
        bool: ``True`` if none of the checked surrogate key columns
        contain a null value, ``False`` otherwise.
    """
    _print_section_header("NULL SURROGATE KEY CHECK")

    all_passed = True

    for fact_name, key_columns in _FACT_NULL_KEY_COLUMNS.items():
        fact_df = facts[fact_name]
        print(_FACT_LABELS[fact_name])

        for key_column in key_columns:
            null_count = int(fact_df[key_column].isna().sum())
            passed = null_count == 0
            all_passed = all_passed and passed

            status = "PASS" if passed else "FAIL"
            print(f"  {key_column} nulls : {null_count} : {status}")

    return all_passed


def _validate_expected_columns(
    label: str, actual_df: pd.DataFrame, expected_columns: tuple[str, ...]
) -> bool:
    """
    Verify a DataFrame contains exactly the expected columns.

    Args:
        label: Human-readable name of the dataset being checked.
        actual_df: The DataFrame to check.
        expected_columns: The columns the DataFrame is expected to
            contain, in any order.

    Returns:
        bool: ``True`` if the DataFrame's columns exactly match
        ``expected_columns``, ``False`` otherwise.
    """
    passed = tuple(actual_df.columns) == expected_columns

    status = "PASS" if passed else "FAIL"
    print(f"{label} : {status}")

    return passed


def _validate_column_shapes(
    dimensions: dict[str, pd.DataFrame], facts: dict[str, pd.DataFrame]
) -> bool:
    """
    Verify every dimension and fact contains exactly its expected
    columns.

    Args:
        dimensions: Mapping of dimension name to its built Gold
            dimension DataFrame.
        facts: Mapping of fact name to its built Gold fact DataFrame.

    Returns:
        bool: ``True`` if every dimension and fact has exactly its
        expected columns, ``False`` otherwise.
    """
    _print_section_header("COLUMN VALIDATION")

    all_passed = True

    for dimension_name, expected_columns in _DIMENSION_EXPECTED_COLUMNS.items():
        passed = _validate_expected_columns(
            _DIMENSION_LABELS[dimension_name], dimensions[dimension_name], expected_columns
        )
        all_passed = all_passed and passed

    for fact_name, expected_columns in _FACT_EXPECTED_COLUMNS.items():
        passed = _validate_expected_columns(
            _FACT_LABELS[fact_name], facts[fact_name], expected_columns
        )
        all_passed = all_passed and passed

    return all_passed


def _print_final_summary(checks: dict[str, bool]) -> None:
    """
    Print the final validation summary.

    Args:
        checks: Mapping of human-readable check label to whether it
            passed.
    """
    _print_section_header("GOLD VALIDATION SUMMARY")

    for check_label, passed in checks.items():
        marker = "\u2713" if passed else "\u2717"
        print(f"{marker} {check_label}")

    if all(checks.values()):
        print("Gold Layer Validation Successful")
    else:
        print("Gold Layer Validation FAILED")


def main() -> None:
    """
    Run the full Gold layer integration validation.
    """
    _print_section_header("GOLD LAYER VALIDATION")

    silver_orders, silver_order_items, silver_kot = _load_silver_datasets()

    result = build_gold_layer(silver_orders, silver_order_items, silver_kot)
    dimensions = result["dimensions"]
    facts = result["facts"]

    _validate_build_shape(dimensions, facts)

    _print_dimension_summary(dimensions)
    _print_fact_summary(facts)

    row_counts_passed = _validate_row_counts(
        facts, silver_orders, silver_order_items, silver_kot
    )
    surrogate_keys_unique = _validate_surrogate_key_duplicates(dimensions)
    business_keys_unique = _validate_business_key_duplicates(dimensions)
    columns_present = _validate_column_shapes(dimensions, facts)
    null_surrogate_keys_passed = _validate_null_surrogate_keys(facts)

    checks = {
        "Row Counts Match": row_counts_passed,
        "Surrogate Keys Unique": surrogate_keys_unique,
        "Business Keys Unique": business_keys_unique,
        "Expected Columns Present": columns_present,
        "Missing Surrogate Keys Check Passed": null_surrogate_keys_passed,
    }

    _print_final_summary(checks)


if __name__ == "__main__":
    main()
