"""
Reporting Layer Configuration.

Central configuration for the Reporting Layer. Defines filesystem
paths and the curated sets of Warehouse views and dimensions that are
published as CSV reporting datasets whenever the pipeline runs.

This module contains ONLY configuration — no functions, no business
logic.
"""

from pathlib import Path
from typing import Final

WAREHOUSE_DB_PATH: Final[Path] = Path("data") / "warehouse" / "restaurant_pos.duckdb"

REPORTING_ROOT: Final[Path] = Path("data") / "reporting"
REPORTING_VIEWS_FOLDER: Final[Path] = REPORTING_ROOT / "views"
REPORTING_DIMENSIONS_FOLDER: Final[Path] = REPORTING_ROOT / "dimensions"

REPORTING_VIEWS: Final[tuple[str, ...]] = (
    "vw_aov_analysis",
    "vw_brand_performance",
    "vw_brand_sales",
    "vw_category_performance",
    "vw_category_sales",
    "vw_charge_analysis",
    "vw_daily_sales",
    "vw_daypart_sales",
    "vw_discount_analysis",
    "vw_item_performance",
    "vw_item_sales",
    "vw_kitchen_performance",
    "vw_order_status_analysis",
    "vw_order_type_performance",
    "vw_platform_performance",
    "vw_platform_sales",
)

REPORTING_DIMENSIONS: Final[tuple[str, ...]] = (
    "dim_brand",
    "dim_category",
    "dim_date",
    "dim_item",
    "dim_platform",
    "dim_restaurant",
)
