"""
discovery.py
============

File Discovery Engine for the Restaurant POS ELT Pipeline.

This module is responsible for recursively scanning a raw data directory,
identifying supported source files (.csv, .xlsx), and grouping them by
their parent folder name (i.e. report/table name).

This module performs discovery only. It does not read, parse, validate,
or load any file contents. Loading and Bronze-layer ingestion are handled
by downstream modules.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

# File extensions considered valid source reports for ingestion.
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".csv", ".xlsx"})

# Folder names that should be skipped entirely during the scan.
IGNORED_DIRECTORIES: frozenset[str] = frozenset({"__MACOSX"})


class RawDirectoryNotFoundError(FileNotFoundError):
    """Raised when the provided raw data directory does not exist."""


class NoSupportedFilesFoundError(FileNotFoundError):
    """Raised when the raw directory contains no supported report files."""


def _is_hidden(path: Path) -> bool:
    """
    Determine whether a path (file or directory) is hidden.

    A path is considered hidden if any component of its name starts with
    a dot, e.g. ``.DS_Store``, ``.gitkeep``, ``.ipynb_checkpoints``.

    Args:
        path: The path to inspect.

    Returns:
        True if the path should be treated as hidden, False otherwise.
    """
    return path.name.startswith(".")


def _is_ignored_directory(path: Path) -> bool:
    """
    Determine whether a directory should be excluded from scanning.

    Args:
        path: The directory path to inspect.

    Returns:
        True if the directory is hidden or explicitly ignored (e.g.
        macOS metadata folders such as ``__MACOSX``), False otherwise.
    """
    return _is_hidden(path) or path.name in IGNORED_DIRECTORIES


def _is_supported_file(path: Path) -> bool:
    """
    Determine whether a file is a supported, non-hidden report file.

    Args:
        path: The file path to inspect.

    Returns:
        True if the file has a supported extension and is not hidden or
        otherwise a system artifact, False otherwise.
    """
    if _is_hidden(path):
        return False
    if not path.is_file():
        return False
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def discover_reports(raw_directory: Path) -> Dict[str, List[Path]]:
    """
    Recursively discover supported report files under a raw data directory.

    Files are grouped by the name of their immediate parent folder, which
    corresponds to the report/table name in the POS data model (e.g.
    ``order_summary``, ``order_summary_item``, ``kot_process_time``).

    Hidden files (dotfiles such as ``.DS_Store``) and macOS metadata
    folders (``__MACOSX``) are ignored. Only files with a ``.csv`` or
    ``.xlsx`` extension are considered supported.

    Args:
        raw_directory: Path to the root raw data directory to scan
            (e.g. ``data/raw``).

    Returns:
        A dictionary mapping parent folder name to an alphabetically
        sorted list of discovered file paths, e.g.::

            {
                "order_summary": [Path(...), Path(...)],
                "order_summary_item": [...],
                "kot_process_time": [...],
            }

    Raises:
        RawDirectoryNotFoundError: If ``raw_directory`` does not exist or
            is not a directory.
        NoSupportedFilesFoundError: If the scan completes but no supported
            ``.csv`` or ``.xlsx`` files are found anywhere under
            ``raw_directory``.
    """
    raw_directory = Path(raw_directory)

    if not raw_directory.exists() or not raw_directory.is_dir():
        message = f"Raw directory does not exist or is not a directory: {raw_directory}"
        logger.error(message)
        raise RawDirectoryNotFoundError(message)

    logger.info("Starting recursive scan of raw directory: %s", raw_directory)

    discovered: Dict[str, List[Path]] = {}

    for path in raw_directory.rglob("*"):
        if path.is_dir():
            continue

        # Skip anything located inside a hidden or ignored directory.
        if any(_is_ignored_directory(parent) for parent in path.parents):
            logger.debug("Skipping file inside ignored directory: %s", path)
            continue

        if not _is_supported_file(path):
            logger.debug("Skipping unsupported or hidden file: %s", path)
            continue

        report_name = path.parent.name
        discovered.setdefault(report_name, []).append(path)
        logger.debug("Discovered file '%s' for report '%s'", path.name, report_name)

    if not discovered:
        message = f"No supported .csv or .xlsx files found under: {raw_directory}"
        logger.error(message)
        raise NoSupportedFilesFoundError(message)

    for report_name in discovered:
        discovered[report_name].sort()

    logger.info(
        "Discovery complete. Found %d report group(s): %s",
        len(discovered),
        {name: len(files) for name, files in discovered.items()},
    )

    return discovered
