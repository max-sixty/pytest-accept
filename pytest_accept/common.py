"""Common functionality shared between pytest-accept plugins."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Callable

# Track file hashes to detect changes during test run
file_hashes: dict[Path, int] = {}

# Track files that have been modified by pytest-accept plugins in this session
files_modified_by_plugins: set[Path] = set()


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

        # Mark this file as modified by plugins
        files_modified_by_plugins.add(target_path)

    except Exception:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def get_accept_mode(session) -> tuple[bool, bool]:
    """Return (accept, accept_copy) flags from session config."""
    accept = session.config.getoption("--accept", False)
    accept_copy = session.config.getoption("--accept-copy", False)
    return accept, accept_copy


def should_process_accepts(session) -> bool:
    """Check if either accept mode is enabled."""
    accept, accept_copy = get_accept_mode(session)
    return accept or accept_copy


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


def track_file_hash(path: Path) -> None:
    """Store the hash of a file to detect later changes."""
    file_hashes[path] = hash(path.read_bytes())


def has_file_changed(path: Path) -> bool:
    """Check if a file has changed since it was tracked."""
    if path not in file_hashes:
        return True  # Unknown file, assume changed for safety

    # If this file was modified by our plugins, don't consider it "changed"
    if path in files_modified_by_plugins:
        return False

    current_hash = hash(path.read_bytes())
    return current_hash != file_hashes[path]
