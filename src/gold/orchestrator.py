"""
Gold Pipeline Orchestrator.

Coordinates the complete Gold pipeline stage: building the Gold layer
in memory and writing it to Parquet. This module contains no business
logic, transformations, validation, or manual DataFrame manipulation
— it only delegates to ``runner.py`` and ``writer.py``.
"""

import pandas as pd

from src.gold.runner import build_gold_layer
from src.gold.writer import write_gold_layer


def run_gold_pipeline_stage(
    silver_orders: pd.DataFrame,
    silver_order_items: pd.DataFrame,
    silver_kot: pd.DataFrame,
) -> dict[str, int]:
    """
    Run the complete Gold pipeline stage.

    Steps:
        1. Build the complete Gold layer via ``build_gold_layer()``.
        2. Write the Gold layer to Parquet via ``write_gold_layer()``.
        3. Summarize the run.

    Args:
        silver_orders: An enriched Silver Order Summary DataFrame.
        silver_order_items: An enriched Silver Order Summary Item
            DataFrame.
        silver_kot: An enriched Silver KOT DataFrame.

    Returns:
        dict[str, int]: A final pipeline summary, e.g.
        ``{"dimensions": 6, "facts": 3, "written": 9}``.
    """
    gold_layer = build_gold_layer(silver_orders, silver_order_items, silver_kot)
    write_summary = write_gold_layer(gold_layer)
    dimensions_count = len(gold_layer["dimensions"])
    facts_count = len(gold_layer["facts"])
    written_count = write_summary["dimensions_written"] + write_summary["facts_written"]

    return {
        "gold_layer": gold_layer,
        "summary": {
            "dimensions": dimensions_count,
            "facts": facts_count,
            "written": written_count,
        },
    }
