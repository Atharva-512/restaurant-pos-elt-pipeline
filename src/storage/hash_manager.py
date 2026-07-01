"""
DE-003 : Bronze Layer -- Hash / Metadata Manager
==================================================

Tracks which raw source files have already been ingested into the Bronze
layer, so that unchanged files are skipped on subsequent pipeline runs.

A file is considered "already processed" only if BOTH the filename and
its SHA256 content hash match a prior run. This means:
    - An unchanged file is skipped.
    - A file with the same name but changed content is reprocessed.
    - A brand-new filename is always processed.

Metadata is persisted as JSON at metadata/processed_files.json:

{
    "Order_Summary_Report_2026-05.csv": {
        "hash": "b94d27b9934d3e08a52e52d7da7dabfa...",
        "processed_time": "2026-07-01T10:15:32.123456+00:00"
    }
}
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

# Default location of the metadata file: <project_root>/metadata/processed_files.json
DEFAULT_METADATA_PATH = Path("data") / "metadata" / "processed_files.json"

# Chunk size used when streaming a file for hashing (1 MB).
_HASH_CHUNK_SIZE = 1024 * 1024


def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate the SHA256 hash of a file's contents.

    The file is read in fixed-size chunks rather than loaded into memory
    all at once, so this is safe and efficient for very large files.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Hex-encoded SHA256 digest string.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory.
        OSError: For other I/O errors while reading the file.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Cannot hash file, path does not exist: {file_path}")
    if file_path.is_dir():
        raise IsADirectoryError(f"Cannot hash a directory: {file_path}")

    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(_HASH_CHUNK_SIZE)
                if not chunk:
                    break
                sha256.update(chunk)
    except OSError as exc:
        logger.error("Failed to read file for hashing: %s (%s)", file_path, exc)
        raise

    digest = sha256.hexdigest()
    logger.debug("Computed SHA256 for %s: %s", file_path.name, digest)
    return digest


def load_processed_metadata(
    metadata_path: Path = DEFAULT_METADATA_PATH,
) -> Dict[str, Dict[str, str]]:
    """
    Load the processed-files metadata JSON from disk.

    Args:
        metadata_path: Path to the metadata JSON file.

    Returns:
        Dict of {filename: {"hash": ..., "processed_time": ...}}.
        Returns an empty dict if the file does not exist or is empty.

    Raises:
        json.JSONDecodeError: If the metadata file exists but contains
                               invalid JSON.
    """
    metadata_path = Path(metadata_path)

    if not metadata_path.exists():
        logger.info("No existing metadata found at %s, starting fresh.", metadata_path)
        return {}

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except json.JSONDecodeError as exc:
        logger.error("Metadata file %s is corrupted: %s", metadata_path, exc)
        raise


def save_processed_metadata(
    metadata: Dict[str, Dict[str, str]],
    metadata_path: Path = DEFAULT_METADATA_PATH,
) -> None:
    """
    Persist the processed-files metadata dict to disk as JSON.

    Creates parent directories if they don't already exist.

    Args:
        metadata: The full metadata dict to write.
        metadata_path: Destination path for the metadata JSON file.

    Raises:
        OSError: If the file cannot be written.
    """
    metadata_path = Path(metadata_path)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, sort_keys=True)
    except OSError as exc:
        logger.error("Failed to write metadata file %s: %s", metadata_path, exc)
        raise

    logger.debug("Saved processed metadata (%d entries) to %s", len(metadata), metadata_path)


def should_process(
    file_path: Path,
    metadata: Dict[str, Dict[str, str]] | None = None,
    metadata_path: Path = DEFAULT_METADATA_PATH,
) -> bool:
    """
    Determine whether a raw source file needs to be (re)processed.

    A file is skipped only if its filename already exists in the metadata
    AND its current SHA256 hash matches the stored hash.

    Args:
        file_path: Path to the raw source file to check.
        metadata: Optional pre-loaded metadata dict. If not provided, it
                  will be loaded from `metadata_path`.
        metadata_path: Location of the metadata JSON (used only if
                       `metadata` is not supplied).

    Returns:
        True if the file is new or has changed and should be processed.
        False if an identical (name + hash) entry already exists.
    """
    file_path = Path(file_path)

    if metadata is None:
        metadata = load_processed_metadata(metadata_path)

    current_hash = calculate_file_hash(file_path)
    existing_entry = metadata.get(file_path.name)

    if existing_entry is not None and existing_entry.get("hash") == current_hash:
        logger.info("Unchanged, skipping: %s", file_path.name)
        return False

    return True


def record_processed_file(
    metadata: Dict[str, Dict[str, str]],
    file_path: Path,
    file_hash: str | None = None,
) -> Dict[str, Dict[str, str]]:
    """
    Add/update a single file's entry in the in-memory metadata dict.

    This does NOT persist to disk -- call save_processed_metadata()
    afterwards to write the updated dict.

    Args:
        metadata: The metadata dict to update (mutated in place).
        file_path: The raw source file that was processed.
        file_hash: Precomputed SHA256 hash. If not provided, it will be
                   calculated from the file.

    Returns:
        The updated metadata dict (same object as passed in).
    """
    file_path = Path(file_path)
    if file_hash is None:
        file_hash = calculate_file_hash(file_path)

    metadata[file_path.name] = {
        "hash": file_hash,
        "processed_time": datetime.now(timezone.utc).isoformat(),
    }
    return metadata
