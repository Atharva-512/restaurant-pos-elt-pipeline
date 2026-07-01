"""
excel_reader.py
================

Excel Reader for the Restaurant POS ELT Pipeline.

Certain POS exports (notably KOT process-time reports) are generated with
a block of metadata rows (report title, date range, filters, etc.) sitting
above the actual data table. These reports are not perfectly consistent in
shape: the metadata block varies in length, and in some files it is even
wider than the real table, so a purely structural signal (e.g. "widest
row") is not reliable.

Instead, this module detects the header row by content: it scans the top
of the sheet for the row that best matches a known set of business column
names used across KOT reports (KOT, Item, Item Name, Process Time,
Quantity, Category, ...). This keeps the reader working even as the
metadata block grows, shrinks, or changes shape, as long as the header row
itself still uses recognizable business terminology.

This module performs reading only — no validation, transformation, or
loading into any downstream store.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Business column names expected to appear in a genuine KOT report header.
# Matching is case-insensitive and substring-based (e.g. a cell containing
# "Item Name" satisfies both the "item" and "item name" keywords), so
# minor variations in real-world exports (extra spacing, trailing colons,
# pluralization, abbreviations) are still recognized. Deliberately covers
# multiple real-world phrasings of the same concept (e.g. "quantity" /
# "qty", "process time" / "prep time" / "avg time") since KOT exports are
# not perfectly consistent in terminology across branches or report
# versions.
BUSINESS_COLUMN_KEYWORDS: tuple[str, ...] = (
    # KOT / order identifiers
    "kot no",
    "kot",
    "bill",
    "invoice",
    # Item / menu identifiers
    "item name",
    "menu item",
    "item",
    "category",
    "subcategory",
    # Quantity
    "quantity",
    "qty",
    # Timing
    "average time",
    "avg time",
    "preparation time",
    "prep time",
    "process time",
    "time",
    # Outlet / brand
    "virtual brand",
    "brand",
    "restaurant",
    "outlet",
)

# Only the first N rows are scanned for a header, since metadata blocks in
# these reports are never expected to run longer than this.
MAX_HEADER_SCAN_ROWS: int = 30


class ExcelReadError(Exception):
    """Raised when an Excel file cannot be read into a DataFrame."""


class HeaderRowNotFoundError(ExcelReadError):
    """Raised when no plausible business header row can be detected in the sheet."""


def _normalize_cell(value: object) -> str:
    """
    Normalize a single cell value for keyword comparison.

    Args:
        value: Raw cell value as read from the sheet.

    Returns:
        The value as a stripped, lowercase string, or an empty string
        for null/blank cells.
    """
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def _score_row(row: pd.Series) -> int:
    """
    Score a row by how many expected business column names it contains.

    Each business keyword contributes at most one point per row,
    regardless of how many cells in that row match it, so a row is
    scored by the *variety* of business terms it contains rather than
    by raw cell count.

    A row with fewer than two populated cells is scored as zero and
    excluded from consideration outright. Genuine tabular headers
    always define multiple columns; a single populated cell is almost
    always a report title or a narrative label (e.g. "Restaurant POS -
    KOT Process Time Report") which can otherwise accidentally contain
    several business keywords in one sentence and be mistaken for a
    real header.

    Args:
        row: A single row of raw (headerless) sheet data.

    Returns:
        The number of distinct business keywords found in the row, or
        zero if the row does not have enough populated cells to be a
        plausible tabular header.
    """
    normalized_cells = {_normalize_cell(value) for value in row.tolist()}
    normalized_cells.discard("")

    if len(normalized_cells) < 2:
        return 0

    score = 0
    for keyword in BUSINESS_COLUMN_KEYWORDS:
        if any(keyword in cell for cell in normalized_cells):
            score += 1

    return score


def _detect_header_row(raw: pd.DataFrame, max_rows_to_scan: int = MAX_HEADER_SCAN_ROWS) -> int:
    """
    Detect the index of the header row using business column name matching.

    Scans the first ``max_rows_to_scan`` rows of the raw sheet and scores
    each one by how many known KOT business column names (KOT, Item,
    Item Name, Process Time, Quantity, Category, etc.) it contains. The
    row with the highest score is selected as the header. This is
    resilient to inconsistent metadata block lengths and shapes, unlike
    a purely structural (row-width) heuristic.

    Args:
        raw: The sheet read with ``header=None``, i.e. every row -
            including metadata and the true header - present as data.
        max_rows_to_scan: Maximum number of leading rows to inspect when
            searching for the header.

    Returns:
        The zero-based row index of the detected header row.

    Raises:
        HeaderRowNotFoundError: If no row within the scanned range
            contains any recognizable business column name.
    """
    rows_to_scan = min(max_rows_to_scan, len(raw))

    best_score = 0
    best_row_index: int | None = None

    for row_index in range(rows_to_scan):
        score = _score_row(raw.iloc[row_index])
        logger.debug("Row %d scored %d business column matches", row_index, score)

        if score > best_score:
            best_score = score
            best_row_index = row_index

    if best_row_index is None:
        raise HeaderRowNotFoundError(
            f"Unable to identify a business header row within the first "
            f"{rows_to_scan} row(s). Expected columns such as: "
            f"{', '.join(BUSINESS_COLUMN_KEYWORDS)}."
        )

    logger.debug(
        "Detected header row at index %d with score %d/%d business keywords matched",
        best_row_index,
        best_score,
        len(BUSINESS_COLUMN_KEYWORDS),
    )
    return best_row_index


def read_excel_file(path: Path, sheet_name: int | str = 0) -> pd.DataFrame:
    """
    Read a single Excel report into a clean pandas DataFrame.

    Automatically detects the true header row by matching known KOT
    business column names (KOT, Item, Item Name, Process Time, Quantity,
    Category, ...) within the first 30 rows of the sheet, rather than
    assuming a fixed row number or relying on row width. This keeps the
    reader working even when the metadata block above the table varies
    in length or shape across reports.

    Args:
        path: Path to the ``.xlsx`` file to read.
        sheet_name: Sheet to read, by index or name. Defaults to the
            first sheet.

    Returns:
        A pandas DataFrame containing the cleaned tabular data, with
        the detected header row used as column names, whitespace
        stripped from column names, and fully empty rows/columns
        removed. The originating file name is attached to
        ``DataFrame.attrs`` under the keys ``source_file`` and
        ``source_path`` for downstream traceability.

    Raises:
        FileNotFoundError: If the file does not exist.
        ExcelReadError: If the file exists but cannot be parsed (corrupt
            workbook, unsupported format, or any other I/O error).
        HeaderRowNotFoundError: If no row in the scanned range contains
            recognizable business column names.
    """
    path = Path(path)

    if not path.exists():
        message = f"Excel file does not exist: {path}"
        logger.error(message)
        raise FileNotFoundError(message)

    logger.debug("Reading Excel file: %s", path)

    try:
        raw = pd.read_excel(path, sheet_name=sheet_name, header=None, engine="openpyxl")
    except ValueError as exc:
        message = f"Failed to read Excel file '{path}': {exc}"
        logger.error(message)
        raise ExcelReadError(message) from exc
    except OSError as exc:
        message = f"OS error while reading Excel file '{path}': {exc}"
        logger.error(message)
        raise ExcelReadError(message) from exc
    except Exception as exc:  # noqa: BLE001 - final safety net
        message = f"Unexpected error while reading Excel file '{path}': {exc}"
        logger.error(message)
        raise ExcelReadError(message) from exc

    if raw.empty:
        message = f"Excel file contains no data: {path}"
        logger.error(message)
        raise ExcelReadError(message)

    try:
        header_row_index = _detect_header_row(raw)
    except HeaderRowNotFoundError as exc:
        message = f"Could not detect a business header row in '{path}': {exc}"
        logger.error(message)
        raise HeaderRowNotFoundError(message) from exc

    header_values = raw.iloc[header_row_index].tolist()
    dataframe = raw.iloc[header_row_index + 1 :].copy()
    dataframe.columns = [str(value).strip() for value in header_values]
    dataframe = dataframe.reset_index(drop=True)

    # Drop rows and columns that are entirely empty (common in metadata
    # blocks that leave a blank separator row before the real table, or
    # in stray unused columns to the side of the table).
    dataframe = dataframe.dropna(axis=0, how="all")
    dataframe = dataframe.dropna(axis=1, how="all")
    dataframe = dataframe.reset_index(drop=True)

    dataframe.attrs["source_file"] = path.name
    dataframe.attrs["source_path"] = str(path)

    logger.info(
        "Successfully read Excel file '%s' -> rows=%d, columns=%d (header row=%d)",
        path.name,
        dataframe.shape[0],
        dataframe.shape[1],
        header_row_index,
    )

    return dataframe
