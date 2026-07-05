"""
Reporting Layer Publisher.

Reads curated datasets (Analytics Views and Dimensions) from the
DuckDB Warehouse and publishes them as CSV files. This module owns
ONLY publishing — it knows nothing about pipeline orchestration,
Power BI, or ``main.py``. All CSV writing is delegated to
``export_dataframe_to_csv()`` in ``exporter.py``.
"""

import logging
from pathlib import Path

import duckdb
import pandas as pd

from src.reporting.reporting_config import (
    REPORTING_DIMENSIONS,
    REPORTING_DIMENSIONS_FOLDER,
    REPORTING_VIEWS,
    REPORTING_VIEWS_FOLDER,
    WAREHOUSE_DB_PATH,
)
from src.reporting.exporter import export_dataframe_to_csv

logger = logging.getLogger(__name__)


def get_connection() -> duckdb.DuckDBPyConnection:
    """
    Open a DuckDB connection to the Warehouse database.

    Returns:
        duckdb.DuckDBPyConnection: An active connection to
        ``WAREHOUSE_DB_PATH``.

    Raises:
        duckdb.Error: If the connection cannot be established.
    """
    try:
        return duckdb.connect(str(WAREHOUSE_DB_PATH))

    except duckdb.Error:
        logger.exception("Failed to connect to Warehouse database: %s", WAREHOUSE_DB_PATH)
        raise


def fetch_dataset(
    connection: duckdb.DuckDBPyConnection,
    dataset_name: str,
) -> pd.DataFrame:
    """
    Fetch a Warehouse dataset (view or dimension) as a DataFrame.

    Args:
        connection: An open DuckDB connection.
        dataset_name: The name of the view or table to read.

    Returns:
        pd.DataFrame: The full contents of the dataset.

    Raises:
        duckdb.Error: If the query fails.
    """
    try:
        query = f"SELECT * FROM {dataset_name}"
        return connection.execute(query).fetchdf()

    except duckdb.Error:
        logger.exception("Failed to fetch dataset: %s", dataset_name)
        raise


def publish_dataset(
    connection: duckdb.DuckDBPyConnection,
    dataset_name: str,
    output_directory: Path,
) -> int:
    """
    Publish a single Warehouse dataset as a CSV file.

    Args:
        connection: An open DuckDB connection.
        dataset_name: The name of the view or table to publish.
        output_directory: The folder the CSV file is written into.

    Returns:
        int: The number of rows exported.
    """
    dataframe = fetch_dataset(connection, dataset_name)
    output_path = output_directory / f"{dataset_name}.csv"

    export_dataframe_to_csv(dataframe, output_path)

    logger.info("✓ %s.csv", dataset_name)

    return len(dataframe)


def publish_views() -> tuple[int, int]:
    """
    Publish every Analytics View defined in ``REPORTING_VIEWS``.

    Returns:
        tuple[int, int]: The number of views published and the total
        number of rows exported.
    """
    logger.info("Publishing Reporting Views...")

    datasets_published = 0
    total_rows_exported = 0

    with get_connection() as connection:
        for view_name in REPORTING_VIEWS:
            total_rows_exported += publish_dataset(connection, view_name, REPORTING_VIEWS_FOLDER)
            datasets_published += 1

    return datasets_published, total_rows_exported


def publish_dimensions() -> tuple[int, int]:
    """
    Publish every Dimension defined in ``REPORTING_DIMENSIONS``.

    Returns:
        tuple[int, int]: The number of dimensions published and the
        total number of rows exported.
    """
    logger.info("Publishing Reporting Dimensions...")

    datasets_published = 0
    total_rows_exported = 0

    with get_connection() as connection:
        for dimension_name in REPORTING_DIMENSIONS:
            total_rows_exported += publish_dataset(
                connection,
                dimension_name,
                REPORTING_DIMENSIONS_FOLDER,
            )
            datasets_published += 1

    return datasets_published, total_rows_exported
