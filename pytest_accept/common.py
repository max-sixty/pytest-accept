"""Common functionality shared between pytest-accept plugins."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Callable

from . import file_hashes_key


def atomic_write(
    target_path: str | Path,
    writer: Callable[[Any], None],
    encoding: str = "utf-8",
    suffix: str | None = None,
) -> None:
    """
    Atomically write to a file using a temporary file and rename.

    Args:
        target_path: The final destination path
        writer: A function that takes a file object and writes content
        encoding: Text encoding (default: utf-8)
        suffix: Suffix for temp file (default: uses target file suffix)
    """
    target_path = Path(target_path)
    if suffix is None:
        suffix = target_path.suffix

    temp_fd, temp_path = tempfile.mkstemp(
        dir=target_path.parent, prefix=".tmp_", suffix=suffix
    )
    try:
        with os.fdopen(temp_fd, "w", encoding=encoding) as file:
            writer(file)
            # Ensure file is written to disk before rename
            file.flush()
            os.fsync(file.fileno())

        # Atomic rename
        os.replace(temp_path, target_path)

    except Exception:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def get_target_path(
    source_path: str | Path, accept_copy: bool, suffix: str = ".new"
) -> Path:
    """
    Get the target path based on accept mode.

    Args:
        source_path: Original file path
        accept_copy: Whether to create a copy
        suffix: Suffix to add for copies (default: ".new")
    """
    source_path = Path(source_path)
    if accept_copy:
        # For .py files, insert before extension: file.py -> file.py.new
        # For other files, just append: file.txt -> file.txt.new
        if source_path.suffix == ".py":
            return source_path.with_suffix(f".py{suffix}")
        else:
            return Path(str(source_path) + suffix)
    return source_path


def track_file_hash(path: Path, session) -> None:
    """Store the hash of a file to detect later changes."""
    file_hashes = session.stash.setdefault(file_hashes_key, {})
    file_hashes[path] = hash(path.read_bytes())


def has_file_changed(path: Path, session) -> bool:
    """Check if a file has changed since it was tracked."""
    file_hashes = session.stash.setdefault(file_hashes_key, {})

    if path not in file_hashes:
        return True  # Unknown file, assume changed for safety

    current_hash = hash(path.read_bytes())
    return current_hash != file_hashes[path]


def is_accept_mode(config) -> bool:
    """Check if running in accept mode (--accept or --accept-copy)."""
    return bool(config.getoption("--accept") or config.getoption("--accept-copy"))
