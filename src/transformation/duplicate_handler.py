"""
Silver Layer -- Duplicate Handler
====================================

Removes fully duplicate rows from a DataFrame and reports how many were
removed.
"""

from __future__ import annotations

import pandas as pd


def remove_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Remove exact duplicate rows from `df`, keeping the first occurrence.

    Args:
        df: Input DataFrame (not mutated).

    Returns:
        A tuple of:
            - clean_dataframe: a new DataFrame with duplicate rows removed
              and the index reset.
            - duplicates_removed: the number of rows that were removed.
    """
    rows_before = len(df)

    clean_dataframe = df.drop_duplicates(keep="first").reset_index(drop=True)
    duplicates_removed = rows_before - len(clean_dataframe)

    return clean_dataframe, duplicates_removed
