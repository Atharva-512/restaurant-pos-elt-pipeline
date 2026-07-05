"""
Warehouse Analytics Layer.

Owns creation of analytical SQL views on top of the Warehouse DuckDB
database. This module contains no ingestion, cleaning, enrichment, or
dimensional modelling logic — it only defines and executes read-only
SQL views for consumption by Power BI.

Architecturally, the Warehouse tables (``dim_*`` and ``fact_*``)
represent the physical dimensional model, while the SQL Views defined
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
            d.month AS month,
            d.month_name AS month_name,
            d.year AS year,
            r.restaurant_name AS restaurant_name,
            COUNT(DISTINCT f.invoice_no) AS orders,
            SUM(f.my_amount) AS gross_sales,
            SUM(f.discount) AS discount,
            SUM(f.delivery_charge) AS delivery_charge,
            SUM(f.container_charge) AS container_charge,
            SUM(f.total_tax) AS tax,
            SUM(f.total) AS net_sales,
            ROUND(
                SUM(f.total) / NULLIF(COUNT(DISTINCT f.invoice_no), 0),
                2
            ) AS average_order_value
        FROM fact_orders AS f
        INNER JOIN dim_date AS d
            ON f.date_key = d.date_key
        INNER JOIN dim_restaurant AS r
            ON f.restaurant_key = r.restaurant_key
        GROUP BY
            d.business_date,
            d.weekday,
            d.month,
            d.month_name,
            d.year,
            r.restaurant_name
        ORDER BY
            d.business_date,
            r.restaurant_name
    """,
    "vw_platform_performance": """
        CREATE OR REPLACE VIEW vw_platform_performance AS
        SELECT
            p.platform AS platform,
            COUNT(DISTINCT f.invoice_no) AS orders,
            SUM(f.my_amount) AS gross_sales,
            SUM(f.discount) AS discount,
            SUM(f.total_tax) AS tax,
            SUM(f.total) AS net_sales,
            ROUND(
                SUM(f.total) / NULLIF(COUNT(DISTINCT f.invoice_no), 0),
                2
            ) AS average_order_value,
            ROUND(AVG(f.discount), 2) AS average_discount
        FROM fact_orders AS f
        INNER JOIN dim_platform AS p
            ON f.platform_key = p.platform_key
        GROUP BY
            p.platform
        ORDER BY
            net_sales DESC
    """,
    "vw_brand_performance": """
        CREATE OR REPLACE VIEW vw_brand_performance AS
        SELECT
            b.brand AS brand,
            COUNT(DISTINCT f.invoice_no) AS orders,
            SUM(f.my_amount) AS gross_sales,
            SUM(f.discount) AS discount,
            SUM(f.total_tax) AS tax,
            SUM(f.total) AS net_sales,
            ROUND(
                SUM(f.total) / NULLIF(COUNT(DISTINCT f.invoice_no), 0),
                2
            ) AS average_order_value,
            ROUND(AVG(f.discount), 2) AS average_discount
        FROM fact_orders AS f
        INNER JOIN dim_brand AS b
            ON f.brand_key = b.brand_key
        GROUP BY
            b.brand
        ORDER BY
            net_sales DESC
    """,
    "vw_category_performance": """
        CREATE OR REPLACE VIEW vw_category_performance AS
        SELECT
            c.category_name AS category,
            SUM(f.item_quantity) AS items_sold,
            SUM(f.item_price * f.item_quantity) AS gross_sales,
            SUM(f.item_total) AS net_sales,
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
            net_sales DESC
    """,
    "vw_item_performance": """
        CREATE OR REPLACE VIEW vw_item_performance AS
        SELECT
            i.item_name AS item,
            c.category_name AS category,
            SUM(f.item_quantity) AS quantity,
            SUM(f.item_price * f.item_quantity) AS gross_sales,
            ROUND(AVG(f.item_price), 2) AS average_item_price
        FROM fact_order_items AS f
        INNER JOIN dim_item AS i
            ON f.item_key = i.item_key
        INNER JOIN dim_category AS c
            ON f.category_key = c.category_key
        GROUP BY
            i.item_name,
            c.category_name
        ORDER BY
            gross_sales DESC
    """,
    "vw_kitchen_performance": """
        CREATE OR REPLACE VIEW vw_kitchen_performance AS
        SELECT
            f.order_type AS order_type,
            f.server_name AS server_name,
            f.item_status AS item_status,
            COUNT(DISTINCT f.kot_id) AS kitchen_tickets,
            ROUND(AVG(f.preparation_time_taken_mins), 2) AS average_preparation_time,
            MIN(f.preparation_time_taken_mins) AS minimum_preparation_time,
            MAX(f.preparation_time_taken_mins) AS maximum_preparation_time,
            CASE
                WHEN AVG(f.preparation_time_taken_mins) < 10 THEN 'Excellent'
                WHEN AVG(f.preparation_time_taken_mins) < 15 THEN 'Good'
                ELSE 'Needs Attention'
            END AS performance_status
        FROM fact_kitchen AS f
        GROUP BY
            f.order_type,
            f.server_name,
            f.item_status
        ORDER BY
            average_preparation_time DESC
    """,
    "vw_daypart_sales": """
        CREATE OR REPLACE VIEW vw_daypart_sales AS
        SELECT
            COALESCE(f.daypart, 'Unknown') AS daypart,
            COUNT(DISTINCT f.invoice_no) AS orders,
            SUM(f.my_amount) AS gross_sales,
            SUM(f.discount) AS discount,
            SUM(f.total_tax) AS tax,
            SUM(f.total) AS net_sales,
            ROUND(
                SUM(f.total) / NULLIF(COUNT(DISTINCT f.invoice_no), 0),
                2
            ) AS average_order_value,
            ROUND(AVG(f.discount), 2) AS average_discount
        FROM fact_orders AS f
        GROUP BY
            COALESCE(f.daypart, 'Unknown')
        ORDER BY
            net_sales DESC
    """,
    "vw_order_type_performance": """
        CREATE OR REPLACE VIEW vw_order_type_performance AS
        SELECT
            f.order_type AS order_type,
            COUNT(DISTINCT f.invoice_no) AS orders,
            SUM(f.my_amount) AS gross_sales,
            SUM(f.discount) AS discount,
            SUM(f.total_tax) AS tax,
            SUM(f.total) AS net_sales,
            ROUND(
                SUM(f.total) / NULLIF(COUNT(DISTINCT f.invoice_no), 0),
                2
            ) AS average_order_value,
            ROUND(AVG(f.discount), 2) AS average_discount
        FROM fact_orders AS f
        GROUP BY
            f.order_type
        ORDER BY
            net_sales DESC
    """,
    "vw_order_status_analysis": """
        CREATE OR REPLACE VIEW vw_order_status_analysis AS
        SELECT
            f.status AS status,
            CASE
                WHEN f.status = 'Success'
                    THEN 'Not Cancelled'
                WHEN f.order_cancel_reason IS NULL
                    THEN 'Unknown'
                ELSE f.order_cancel_reason
            END AS order_cancel_reason,
            COUNT(DISTINCT f.invoice_no) AS orders,
            SUM(f.my_amount) AS gross_sales,
            SUM(f.total) AS net_sales,
            ROUND(
                SUM(f.total) / NULLIF(COUNT(DISTINCT f.invoice_no), 0),
                2
            ) AS average_order_value,
            ROUND(
                100.0 * COUNT(DISTINCT f.invoice_no)
                /
                SUM(COUNT(DISTINCT f.invoice_no)) OVER (),
                2
            ) AS order_percentage
        FROM fact_orders AS f
        GROUP BY
            f.status,
            CASE
                WHEN f.status = 'Success'
                    THEN 'Not Cancelled'
                WHEN f.order_cancel_reason IS NULL
                    THEN 'Unknown'
                ELSE f.order_cancel_reason
            END
        ORDER BY
            orders DESC
    """,
}


def _open_connection() -> duckdb.DuckDBPyConnection:
    """
    Open a DuckDB connection to the Warehouse database.

    Returns:
        duckdb.DuckDBPyConnection: An open connection.
    """
    return duckdb.connect(str(DATABASE_PATH))


def _execute_views(connection: duckdb.DuckDBPyConnection) -> int:
    """
    Execute every SQL statement in ``_VIEW_DEFINITIONS``.

    Args:
        connection: An open DuckDB connection.

    Returns:
        int: Number of views created.
    """
    for _, view_sql in _VIEW_DEFINITIONS.items():
        connection.execute(view_sql)

    return len(_VIEW_DEFINITIONS)


def create_views() -> int:
    """
    Create every analytical SQL view in the Warehouse database.

    Opens a connection, executes all view definitions, commits, and
    closes the connection.

    Returns:
        int: Number of views created.
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
