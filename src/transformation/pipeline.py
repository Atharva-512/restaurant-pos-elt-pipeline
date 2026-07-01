"""
Silver Layer -- Pipeline Orchestrator
========================================

Runs the full Bronze -> Silver transformation sequence against a single
DataFrame:

    1. standardize_columns
    2. handle_nulls
    3. convert_datatypes
    4. validate_business_rules
    5. remove_duplicates

This module contains no I/O (no file reads/writes, no SQL, no logging) --
it operates purely on in-memory DataFrames and is intended to be called
once per Bronze source file/table by an upstream orchestrator.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.transformation.business_validator import validate_business_rules
from src.transformation.column_standardizer import standardize_columns
from src.transformation.datatype_converter import convert_datatypes
from src.transformation.duplicate_handler import remove_duplicates
from src.transformation.null_handler import handle_nulls


def run_silver_pipeline(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Run the full Silver-layer transformation pipeline on `df`.

    Execution order:
        1. standardize_columns  -- normalize column names.
        2. handle_nulls         -- normalize null-like tokens to None.
        3. convert_datatypes    -- infer and cast datetime/int/float/bool.
        4. validate_business_rules -- read-only checks (does not alter data).
        5. remove_duplicates    -- drop exact duplicate rows.

    Args:
        df: Raw (Bronze) input DataFrame. Not mutated.

    Returns:
        A tuple of:
            - clean_dataframe: the fully transformed, de-duplicated
              DataFrame.
            - metadata: dict describing the run, e.g.:
                {
                    "rows_before": 100,
                    "rows_after": 98,
                    "duplicates_removed": 2,
                    "validation_errors": []
                }
    """
    rows_before = len(df)

    standardized_df = standardize_columns(df)
    null_handled_df = handle_nulls(standardized_df)
    typed_df = convert_datatypes(null_handled_df)

    validation_report = validate_business_rules(typed_df)

    clean_dataframe, duplicates_removed = remove_duplicates(typed_df)

    metadata: dict[str, Any] = {
        "rows_before": rows_before,
        "rows_after": len(clean_dataframe),
        "duplicates_removed": duplicates_removed,
        "validation_errors": validation_report["validation_errors"],
    }

    return clean_dataframe, metadata
