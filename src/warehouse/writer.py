"""
Warehouse Writer.

Persists the completed Gold analytical model into DuckDB. This module
owns only database persistence — it performs no cleaning, parsing,
enrichment, business transformations, dimensional modelling, or
surrogate key generation. Those responsibilities permanently belong
to Gold. This module consumes the in-memory ``gold_layer`` object
directly; it never reads Gold Parquet files from disk.
"""

from pathlib import Path
from typing import Final

import duckdb
import pandas as pd

WAREHOUSE_ROOT: Final[Path] = Path("data") / "warehouse"
DATABASE_NAME: Final[str] = "restaurant_pos.duckdb"
DATABASE_PATH: Final[Path] = WAREHOUSE_ROOT / DATABASE_NAME

_DIMENSION_TABLE_PREFIX: Final[str] = "dim_"
_FACT_TABLE_PREFIX: Final[str] = "fact_"


def write_warehouse(gold_layer: dict[str, dict[str, pd.DataFrame]]) -> dict[str, int]:
    """
    Materialize the completed Gold analytical model into DuckDB.

    Every Gold dimension is materialized as a ``dim_<name>`` table and
    every Gold fact is materialized as a ``fact_<name>`` table inside
    ``data/warehouse/restaurant_pos.duckdb``, using DuckDB's native
    SQL ``CREATE OR REPLACE TABLE`` approach.

    Args:
        gold_layer: The dictionary produced by ``build_gold_layer()``,
            containing ``"dimensions"`` and ``"facts"`` keys, each
            mapping a dataset name to its built Gold DataFrame.

    Returns:
        dict[str, int]: A load summary, e.g.
        ``{"dimensions_loaded": 6, "facts_loaded": 3, "tables_loaded": 9}``.
    """
    connection = _create_connection()

    try:
        connection.begin()

        dimensions_loaded = _materialize_tables(
            connection,
            gold_layer["dimensions"],
            _DIMENSION_TABLE_PREFIX,
        )

        facts_loaded = _materialize_tables(
            connection,
            gold_layer["facts"],
            _FACT_TABLE_PREFIX,
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return {
        "dimensions_loaded": dimensions_loaded,
        "facts_loaded": facts_loaded,
        "tables_loaded": dimensions_loaded + facts_loaded,
    }

def _create_connection() -> duckdb.DuckDBPyConnection:
    """
    Create a DuckDB connection to the warehouse database file.

    Creates the warehouse directory automatically if it does not
    already exist.

    Returns:
        duckdb.DuckDBPyConnection: An open connection to
        ``data/warehouse/restaurant_pos.duckdb``.
    """
    WAREHOUSE_ROOT.mkdir(parents=True, exist_ok=True)

    return duckdb.connect(str(DATABASE_PATH))


def _materialize_tables(
    connection: duckdb.DuckDBPyConnection,
    datasets: dict[str, pd.DataFrame],
    table_prefix: str,
) -> int:
    """
    Materialize a group of Gold DataFrames into DuckDB tables via SQL.

    Each DataFrame is registered with DuckDB and then materialized
    using ``CREATE OR REPLACE TABLE ... AS SELECT * FROM ...``, rather
    than ``DataFrame.to_sql()``.

    Args:
        connection: An open DuckDB connection.
        datasets: Mapping of dataset name to its built Gold DataFrame.
        table_prefix: Prefix identifying the dataset group (e.g.
            ``"dim_"`` or ``"fact_"``).

    Returns:
        int: The number of tables materialized.
    """
    for dataset_name, dataframe in datasets.items():
        table_name = f"{table_prefix}{dataset_name}"
        view_name = f"{table_name}_df"

        connection.register(view_name, dataframe)

        try:
            connection.execute(
                f"""
                CREATE OR REPLACE TABLE {table_name} AS
                SELECT *
                FROM {view_name}
                """
            )
        finally:
            connection.unregister(view_name)

    return len(datasets)
