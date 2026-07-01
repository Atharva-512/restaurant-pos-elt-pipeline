"""
loader.py
=========

Loader for the Restaurant POS ELT Pipeline.

Takes the output of the File Discovery Engine (a mapping of report name
to a list of discovered file paths) and loads every file into a pandas
DataFrame, automatically dispatching to the CSV or Excel reader based on
file extension.

This module performs loading only — no validation, transformation, or
persistence into any downstream store (Bronze layer, PostgreSQL, etc.).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Dict, List

import pandas as pd

from src.ingestion.csv_reader import CSVReadError, read_csv_file
from src.ingestion.excel_reader import ExcelReadError, read_excel_file

logger = logging.getLogger(__name__)

# Maps a supported file extension to the reader function responsible for it.
READER_DISPATCH: Dict[str, Callable[[Path], pd.DataFrame]] = {
    ".csv": read_csv_file,
    ".xlsx": read_excel_file,
}


class UnsupportedFileTypeError(Exception):
    """Raised when a file extension has no registered reader."""


def _read_file(path: Path) -> pd.DataFrame:
    """
    Dispatch a single file to the appropriate reader based on extension.

    Args:
        path: Path to the file to read.

    Returns:
        The loaded pandas DataFrame.

    Raises:
        UnsupportedFileTypeError: If the file extension has no
            registered reader.
        FileNotFoundError: If the file does not exist.
        CSVReadError: If a CSV file fails to load.
        ExcelReadError: If an Excel file fails to load.
    """
    extension = path.suffix.lower()
    reader = READER_DISPATCH.get(extension)

    if reader is None:
        message = f"No reader registered for file extension '{extension}': {path}"
        logger.error(message)
        raise UnsupportedFileTypeError(message)

    return reader(path)


def load_reports(discovered_files: Dict[str, List[Path]]) -> Dict[str, List[pd.DataFrame]]:
    """
    Load every discovered report file into a pandas DataFrame.

    Each file is routed to the CSV or Excel reader based on its
    extension. Individual file failures are logged and skipped so that
    a single corrupt or unreadable file does not abort the entire load;
    the pipeline continues with the remaining files.

    Args:
        discovered_files: Mapping of report name to a list of file
            paths, as produced by ``discovery.discover_reports``, e.g.::

                {
                    "order_summary": [Path(...), Path(...)],
                    "kot_process_time": [Path(...), ...],
                }

    Returns:
        A mapping of report name to a list of loaded DataFrames, e.g.::

            {
                "order_summary": [DataFrame, DataFrame],
                "kot_process_time": [DataFrame, ...],
            }

        Files that failed to load are omitted from the corresponding
        list. Report names with zero successfully loaded files will map
        to an empty list.
    """
    loaded_reports: Dict[str, List[pd.DataFrame]] = {}

    for report_name, file_paths in discovered_files.items():
        logger.info("Loading %d file(s) for report '%s'", len(file_paths), report_name)
        dataframes: List[pd.DataFrame] = []

        for path in file_paths:
            try:
                dataframe = _read_file(path)
            except UnsupportedFileTypeError:
                logger.warning("Skipping unsupported file: %s", path)
                continue
            except FileNotFoundError as exc:
                logger.error("Skipping missing file: %s (%s)", path, exc)
                continue
            except (CSVReadError, ExcelReadError) as exc:
                logger.error("Skipping unreadable file '%s': %s", path, exc)
                continue

            dataframes.append(dataframe)

        loaded_reports[report_name] = dataframes

    total_loaded = sum(len(frames) for frames in loaded_reports.values())
    logger.info("Loading complete. %d file(s) successfully loaded.", total_loaded)

    return loaded_reports
