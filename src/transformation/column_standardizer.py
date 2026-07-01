"""
Silver Layer -- Column Standardizer
=====================================

Normalizes DataFrame column names into a consistent, predictable format
so downstream transformation/validation steps can rely on stable naming.
"""

from __future__ import annotations

import re

import pandas as pd

# Matches two or more consecutive underscores, for collapsing.
_MULTI_UNDERSCORE_RE = re.compile(r"_{2,}")

# Characters/substrings stripped outright from column names.
_CHARS_TO_REMOVE = ("%", "(", ")", "/")


def _standardize_name(column_name: object) -> str:
    """
    Apply the column-name standardization rules to a single column name.

    Rules applied (in order):
        1. Strip leading/trailing whitespace.
        2. Lowercase.
        3. Replace spaces with "_".
        4. Remove "%".
        5. Remove "(" and ")".
        6. Remove "/".
        7. Collapse multiple consecutive underscores into one.
        8. Strip leading/trailing whitespace again (defensive, in case
           removals introduced trailing spaces) and trim stray edge
           underscores left behind by the removals above.

    Args:
        column_name: The original column name (any type; coerced to str).

    Returns:
        The standardized column name as a string.
    """
    name = str(column_name).strip()
    name = name.lower()
    name = name.replace(" ", "_")

    for char in _CHARS_TO_REMOVE:
        name = name.replace(char, "")

    name = _MULTI_UNDERSCORE_RE.sub("_", name)
    name = name.strip()
    name = name.strip("_")

    return name


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of `df` with standardized column names.

    Standardization rules:
        - lowercase
        - spaces replaced with "_"
        - "%" removed
        - "(" and ")" removed
        - "/" removed
        - multiple consecutive underscores collapsed into one
        - surrounding whitespace stripped

    Args:
        df: Input DataFrame (not mutated).

    Returns:
        A new DataFrame with the same data and standardized column names.
    """
    result = df.copy()
    result.columns = [_standardize_name(col) for col in result.columns]
    return result
