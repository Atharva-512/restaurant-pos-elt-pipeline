"""
Warehouse Analytics Layer.

Owns creation of analytical SQL views on top of the Warehouse DuckDB
database. This module contains no ingestion, cleaning, enrichment, or
dimensional modelling logic — it only defines and executes read-only
SQL views for consumption by Power BI.

Architecturally, the Warehouse tables (``dim_*`` and ``fact_*``)
represent the physical analytical model, while the SQL Views defined
here represent the Analytics Layer built on top of that model. Power
BI consumes only these SQL Views — it never queries the Warehouse
tables or Gold directly. This separation is a frozen architectural
decision of the project.
"""

from typing import Final

import duckdb

from src.warehouse.writer import DATABASE_PATH

_VIEW_DEFINITIONS: Final[dict[str, str]] = {
    "vw_daily_sales": """
        CREATE OR REPLACE VIEW vw_daily_sales AS
        SELECT
            d.business_date AS business_date,
            d.weekday AS weekday,
            d.year AS year,
            d.month AS month,
            d.month_name AS month_name,
            COUNT(DISTINCT f.invoice_no) AS total_orders,
            SUM(f.my_amount) AS gross_sales,
            SUM(f.discount) AS discount,
            SUM(f.total_tax) AS tax,
            SUM(f.total) AS net_sales,
            ROUND(
                SUM(f.total) / NULLIF(COUNT(DISTINCT f.invoice_no), 0),
                2
            ) AS average_order_value
        FROM fact_orders AS f
        INNER JOIN dim_date AS d
            ON f.date_key = d.date_key
        GROUP BY
            d.business_date,
            d.weekday,
            d.year,
            d.month,
            d.month_name
        ORDER BY
            d.business_date
    """,
    "vw_platform_sales": """
        CREATE OR REPLACE VIEW vw_platform_sales AS
        SELECT
            p.platform AS platform,
            COUNT(DISTINCT f.invoice_no) AS total_orders,
            SUM(f.my_amount) AS gross_sales,
            SUM(f.discount) AS discount,
            SUM(f.total_tax) AS tax,
            SUM(f.total) AS net_sales,
            ROUND(
                SUM(f.total) / NULLIF(COUNT(DISTINCT f.invoice_no), 0),
                2
            ) AS average_order_value
        FROM fact_orders AS f
        INNER JOIN dim_platform AS p
            ON f.platform_key = p.platform_key
        GROUP BY
            p.platform
        ORDER BY
            gross_sales DESC
    """,
    "vw_brand_sales": """
        CREATE OR REPLACE VIEW vw_brand_sales AS
        SELECT
            b.brand AS brand,
            COUNT(DISTINCT f.invoice_no) AS total_orders,
            SUM(f.my_amount) AS gross_sales,
            SUM(f.discount) AS discount,
            SUM(f.total) AS net_sales,
            ROUND(
                SUM(f.total) / NULLIF(COUNT(DISTINCT f.invoice_no), 0),
                2
            ) AS average_order_value
        FROM fact_orders AS f
        INNER JOIN dim_brand AS b
            ON f.brand_key = b.brand_key
        GROUP BY
            b.brand
        ORDER BY
            gross_sales DESC
    """,
    "vw_category_sales": """
        CREATE OR REPLACE VIEW vw_category_sales AS
        SELECT
            c.category_name AS category_name,
            SUM(f.item_quantity) AS quantity_sold,
            SUM(f.item_total) AS revenue,
            ROUND(
                SUM(f.item_total) / NULLIF(SUM(f.item_quantity), 0),
                2
            ) AS average_item_price
        FROM fact_order_items AS f
        INNER JOIN dim_category AS c
            ON f.category_key = c.category_key
        GROUP BY
            c.category_name
        ORDER BY
            revenue DESC
    """,
    "vw_item_sales": """
        CREATE OR REPLACE VIEW vw_item_sales AS
        SELECT
            i.item_name AS item_name,
            SUM(f.item_quantity) AS quantity_sold,
            SUM(f.item_total) AS revenue,
            ROUND(
                SUM(f.item_total) / NULLIF(SUM(f.item_quantity), 0),
                2
            ) AS average_price,
            COUNT(DISTINCT f.invoice_no) AS number_of_orders
        FROM fact_order_items AS f
        INNER JOIN dim_item AS i
            ON f.item_key = i.item_key
        GROUP BY
            i.item_name
        ORDER BY
            revenue DESC
    """,
    "vw_discount_analysis": """
        CREATE OR REPLACE VIEW vw_discount_analysis AS
        SELECT
            d.business_date AS business_date,
            SUM(f.my_amount) AS gross_sales,
            SUM(f.discount) AS discount,
            ROUND(
                SUM(f.discount) / NULLIF(SUM(f.my_amount), 0) * 100,
                2
            ) AS discount_percentage
        FROM fact_orders AS f
        INNER JOIN dim_date AS d
            ON f.date_key = d.date_key
        GROUP BY
            d.business_date
        ORDER BY
            d.business_date
    """,
    "vw_charge_analysis": """
        CREATE OR REPLACE VIEW vw_charge_analysis AS
        SELECT
            d.business_date AS business_date,
            SUM(f.delivery_charge) AS delivery_charge,
            SUM(f.container_charge) AS container_charge,
            SUM(f.service_charge) AS service_charge,
            SUM(f.additional_charge) AS additional_charge,
            SUM(f.deduction_charge) AS deduction_charge,
            SUM(f.total) AS total_sales
        FROM fact_orders AS f
        INNER JOIN dim_date AS d
            ON f.date_key = d.date_key
        GROUP BY
            d.business_date
        ORDER BY
            d.business_date
    """,
    "vw_kitchen_performance": """
        CREATE OR REPLACE VIEW vw_kitchen_performance AS
        SELECT
            i.item_name AS item_name,
            ROUND(AVG(f.preparation_time_taken_mins), 2) AS average_preparation_time,
            MIN(f.preparation_time_taken_mins) AS minimum_preparation_time,
            MAX(f.preparation_time_taken_mins) AS maximum_preparation_time,
            SUM(f.qty) AS quantity_prepared
        FROM fact_kitchen AS f
        INNER JOIN dim_item AS i
            ON f.item_key = i.item_key
        GROUP BY
            i.item_name
        ORDER BY
            average_preparation_time DESC
    """,
    "vw_aov_analysis": """
        CREATE OR REPLACE VIEW vw_aov_analysis AS
        WITH monthly_orders AS (
            SELECT
                d.year AS year,
                d.month AS month,
                d.month_name AS month_name,
                COUNT(DISTINCT f.invoice_no) AS orders,
                SUM(f.total) AS sales
            FROM fact_orders AS f
            INNER JOIN dim_date AS d
                ON f.date_key = d.date_key
            GROUP BY
                d.year,
                d.month,
                d.month_name
        )
        SELECT
            year,
            month,
            month_name,
            orders,
            sales,
            ROUND(sales / NULLIF(orders, 0), 2) AS average_order_value
        FROM monthly_orders
        ORDER BY
            year,
            month
    """,
}


def _open_connection() -> duckdb.DuckDBPyConnection:
    """
    Open a DuckDB connection to the Warehouse database file.

    Returns:
        duckdb.DuckDBPyConnection: An open connection to
        ``data/warehouse/restaurant_pos.duckdb``.
    """
    return duckdb.connect(str(DATABASE_PATH))


def _execute_views(connection: duckdb.DuckDBPyConnection) -> int:
    """
    Execute every SQL statement defined in ``_VIEW_DEFINITIONS``.

    Args:
        connection: An open DuckDB connection.

    Returns:
        int: The number of views created.
    """
    for _, view_sql in _VIEW_DEFINITIONS.items():
        connection.execute(view_sql)

    return len(_VIEW_DEFINITIONS)


def create_views() -> int:
    """
    Create every analytical SQL view in the Warehouse database.

    Execution flow:
        Open connection
            -> Execute all SQL views
            -> Commit
            -> Close

    Steps:
        1. Open a connection to the Warehouse DuckDB database.
        2. Execute every SQL view definition via ``_execute_views()``.
        3. Commit and close the connection.

    Returns:
        int: The number of views created.
    """
    connection = _open_connection()

    try:
        views_created = _execute_views(connection)
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return views_created
