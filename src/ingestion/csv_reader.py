"""
csv_reader.py
=============

CSV Reader for the Restaurant POS ELT Pipeline.

Responsible for reading a single CSV report file into a pandas DataFrame.
This module performs reading only — no validation, transformation, or
loading into any downstream store.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class CSVReadError(Exception):
    """Raised when a CSV file cannot be read into a DataFrame."""


def read_csv_file(path: Path) -> pd.DataFrame:
    """
    Read a single CSV file into a pandas DataFrame.

    The file is expected to be UTF-8 encoded. If strict UTF-8 decoding
    fails (e.g. due to a BOM written by tools like Excel), a fallback
    attempt is made using the ``utf-8-sig`` encoding before giving up.

    Args:
        path: Path to the CSV file to read.

    Returns:
        A pandas DataFrame containing the file's tabular data. The
        originating file name is attached to ``DataFrame.attrs`` under
        the keys ``source_file`` and ``source_path`` for downstream
        traceability.

    Raises:
        FileNotFoundError: If the file does not exist.
        CSVReadError: If the file exists but cannot be parsed into a
            valid DataFrame (empty file, malformed CSV, encoding
            failure, or any other I/O error).
    """
    path = Path(path)

    if not path.exists():
        message = f"CSV file does not exist: {path}"
        logger.error(message)
        raise FileNotFoundError(message)

    logger.debug("Reading CSV file: %s", path)

    try:
        dataframe = pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning(
            "UTF-8 decoding failed for %s, retrying with utf-8-sig encoding", path
        )
        try:
            dataframe = pd.read_csv(path, encoding="utf-8-sig")
        except Exception as exc:  # noqa: BLE001 - surfaced as CSVReadError
            message = f"Failed to decode CSV file '{path}' as UTF-8: {exc}"
            logger.error(message)
            raise CSVReadError(message) from exc
    except pd.errors.EmptyDataError as exc:
        message = f"CSV file is empty or has no columns: {path}"
        logger.error(message)
        raise CSVReadError(message) from exc
    except pd.errors.ParserError as exc:
        message = f"Failed to parse CSV file due to malformed content: {path}"
        logger.error(message)
        raise CSVReadError(message) from exc
    except OSError as exc:
        message = f"OS error while reading CSV file '{path}': {exc}"
        logger.error(message)
        raise CSVReadError(message) from exc
    except Exception as exc:  # noqa: BLE001 - final safety net
        message = f"Unexpected error while reading CSV file '{path}': {exc}"
        logger.error(message)
        raise CSVReadError(message) from exc

    if dataframe.empty:
        logger.warning("CSV file was read successfully but contains zero rows: %s", path)

    dataframe.attrs["source_file"] = path.name
    dataframe.attrs["source_path"] = str(path)

    logger.info(
        "Successfully read CSV file '%s' -> rows=%d, columns=%d",
        path.name,
        dataframe.shape[0],
        dataframe.shape[1],
    )

    return dataframe
