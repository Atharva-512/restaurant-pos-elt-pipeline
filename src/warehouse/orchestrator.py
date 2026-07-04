"""
Warehouse Pipeline Orchestrator.

Coordinates the complete Warehouse pipeline stage: running the
Warehouse Runner and reporting a summary. This module contains no
SQL, no DataFrame manipulation, and no business logic — it only
delegates to ``runner.py``.
"""

import pandas as pd

from src.warehouse.runner import run_warehouse_layer


def run_warehouse_pipeline_stage(
    gold_layer: dict[str, dict[str, pd.DataFrame]]
) -> dict[str, int]:
    """
    Run the complete Warehouse pipeline stage.

    Steps:
        1. Run the Warehouse Runner via ``run_warehouse_layer()``.
        2. Print a summary of the run.

    Args:
        gold_layer: The dictionary produced by ``build_gold_layer()``,
            containing ``"dimensions"`` and ``"facts"`` keys, each
            mapping a dataset name to its built Gold DataFrame.

    Returns:
        dict[str, int]: A summary of the run, e.g.
        ``{"tables": 9, "views": 9}``.
    """
    summary = run_warehouse_layer(gold_layer)

    _print_summary(summary)

    return summary


def _print_summary(summary: dict[str, int]) -> None:
    """
    Print a final summary report of the Warehouse pipeline run.

    Args:
        summary: The summary returned by ``run_warehouse_layer()``.
    """
    print("=================================================")
    print("Warehouse Pipeline Completed")
    print(f"Tables Loaded : {summary['tables']}")
    print(f"Views Created : {summary['views']}")
    print("=================================================")
