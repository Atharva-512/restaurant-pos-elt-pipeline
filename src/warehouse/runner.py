"""
Warehouse Runner.

Owns Warehouse execution: persisting the Gold model into DuckDB and
creating the analytical SQL views on top of it. This module contains
no SQL and no business logic — it only delegates to ``writer.py`` and
``views.py``.
"""

import pandas as pd

from src.warehouse.views import create_views
from src.warehouse.writer import write_warehouse


def run_warehouse_layer(gold_layer: dict[str, dict[str, pd.DataFrame]]) -> dict[str, int]:
    """
    Materialize the Gold model into DuckDB and create analytical views.

    Steps:
        1. Persist every Gold dimension and fact via
           ``write_warehouse()``.
        2. Create every analytical SQL view via ``create_views()``.

    Args:
        gold_layer: The dictionary produced by ``build_gold_layer()``,
            containing ``"dimensions"`` and ``"facts"`` keys, each
            mapping a dataset name to its built Gold DataFrame.

    Returns:
        dict[str, int]: A summary of the run, e.g.
        ``{"tables": 9, "views": 9}``.
    """
    write_summary = write_warehouse(gold_layer)
    views_created = create_views()

    return {
        "tables": write_summary["tables_loaded"],
        "views": views_created,
    }
