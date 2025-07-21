from __future__ import annotations

import logging
import re
import textwrap
from dataclasses import dataclass
from doctest import DocTestFailure
from importlib.metadata import PackageNotFoundError, version
from itertools import zip_longest
from pathlib import Path
from typing import Any

import astor
import pytest

try:
    __version__ = version("pytest-accept")
except PackageNotFoundError:
    __version__ = "unknown"


@dataclass
class Change:
    """Represents a file change from either assert or doctest plugin"""

    plugin: str  # "assert" or "doctest"
    data: Any  # AST changes or doctest failures
    priority: int  # assert=1, doctest=2 (assert runs first)


logger = logging.getLogger(__name__)


def _snapshot_start_line(failure: DocTestFailure) -> int:
    """Calculate the line where doctest snapshot should start"""
    assert failure.test.lineno is not None
    return (
        failure.test.lineno
        + failure.example.lineno
        + len(failure.example.source.splitlines())
    )


def _to_doctest_format(output: str) -> str:
    """Convert a string into a doctest format with <BLANKLINE> markers"""
    lines = output.splitlines()
    blankline_sentinel = "<BLANKLINE>"
    transformed_lines = [line if line else blankline_sentinel for line in lines]
    # In some pathological cases, really long lines can crash an editor.
    shortened_lines = [
        line if len(line) < 1000 else f"{line[:50]}...{line[-50:]}"
        for line in transformed_lines
    ]
    # Again, only for the pathological cases.
    if len(shortened_lines) > 1000:
        shortened_lines = shortened_lines[:50] + ["..."] + shortened_lines[-50:]
    output = "\n".join(shortened_lines)
    return _redact_volatile(output)


def _redact_volatile(output: str) -> str:
    """Replace some volatile values, like temp paths & memory locations"""
    mem_locations = re.sub(r" 0x[0-9a-fA-F]+", " 0x...", output)
    temp_paths = re.sub(r"/tmp/[0-9a-fA-F]+", "/tmp/...", mem_locations)
    return temp_paths


# StashKey instances to replace global state
# Unified change collection - replaces separate plugin stashes
file_changes_key = pytest.StashKey[dict[Path, list[Change]]]()
file_hashes_key = pytest.StashKey[dict[Path, int]]()

# Legacy StashKeys - will be removed during transition
failed_doctests_key = pytest.StashKey[dict[Path, list[DocTestFailure]]]()
files_modified_by_plugins_key = pytest.StashKey[set[Path]]()
asts_modified_key = pytest.StashKey[dict[str, list[tuple[slice, str]]]]()
recent_failure_key = pytest.StashKey[list[tuple]]()
intercept_assertions_key = pytest.StashKey[bool]()

# Import hooks from both plugins
from .assert_plugin import (
    pytest_assertrepr_compare as assert_assertrepr_compare,
)
from .assert_plugin import (
    pytest_collection_modifyitems as assert_collection_modifyitems,
)
from .assert_plugin import (
    pytest_sessionstart as assert_sessionstart,
)
from .common import atomic_write, get_target_path, has_file_changed
from .doctest_plugin import (
    pytest_addoption as doctest_addoption,
)
from .doctest_plugin import (
    pytest_collect_file,
    pytest_configure,
    pytest_runtest_makereport,
)


def _apply_assert_changes(
    original: list[str], assert_changes: list[Change]
) -> list[str]:
    """Apply assert plugin changes to file content"""
    result = original.copy()

    # Extract assert data and sort by line number
    assert_data = [
        (c.data[0], c.data[1]) for c in assert_changes
    ]  # (location, new_assert)
    assert_data = sorted(assert_data, key=lambda x: x[0].start)

    # Apply changes from end to beginning to avoid line number shifts
    for location, code in reversed(assert_data):
        # Replace lines in the location range
        indent = result[location.start - 1][
            : len(result[location.start - 1]) - len(result[location.start - 1].lstrip())
        ]
        source = astor.to_source(code).splitlines()
        indented_source = [indent + line for line in source]

        # Replace the range of lines
        result[location.start - 1 : location.stop] = indented_source

    return result


def _apply_doctest_changes(
    original: list[str], doctest_changes: list[Change]
) -> list[str]:
    """Apply doctest plugin changes to file content"""
    # Extract failures and sort by line number
    failures = [c.data for c in doctest_changes]
    failures = sorted(failures, key=lambda x: x.test.lineno or 0)

    if not failures:
        return original

    result = []

    # Interleave original content with updated doctest outputs
    first_failure = failures[0]
    next_start_line = _snapshot_start_line(first_failure)
    result.extend(original[:next_start_line])

    for current, next_failure in zip_longest(failures, failures[1:]):
        # Get the existing indentation from the source line
        match = re.match(r"\s*", original[next_start_line])
        existing_indent = match.group() if match else ""
        snapshot_result = _to_doctest_format(current.got)
        indented = textwrap.indent(snapshot_result, prefix=existing_indent)
        result.extend(indented.splitlines())

        current_finish_line = _snapshot_start_line(current) + len(
            current.example.want.splitlines()
        )
        next_start_line = (
            _snapshot_start_line(next_failure) if next_failure else len(original)
        )

        result.extend(original[current_finish_line:next_start_line])

    return result


# Direct exports for simple pass-through hooks
pytest_sessionstart = assert_sessionstart
pytest_collection_modifyitems = assert_collection_modifyitems
pytest_assertrepr_compare = assert_assertrepr_compare


def pytest_sessionfinish(session, exitstatus):
    """Unified file writer - handles both assert and doctest changes"""
    # Only run when --accept or --accept-copy is used
    accept = session.config.getoption("--accept")
    accept_copy = session.config.getoption("--accept-copy")
    if not (accept or accept_copy):
        return

    # Get all collected changes
    file_changes = session.stash.get(file_changes_key, {})
    if not file_changes:
        return

    for path, changes in file_changes.items():
        # Check if the file has changed since the start of the test
        if not accept_copy and has_file_changed(path, session):
            logger.warning(
                f"File changed since start of test, not writing results: {path}"
            )
            continue

        # Sort changes by priority (assert=1, doctest=2)
        changes = sorted(changes, key=lambda x: x.priority)

        # Group changes by plugin type for processing
        assert_changes = [c for c in changes if c.plugin == "assert"]
        doctest_changes = [c for c in changes if c.plugin == "doctest"]

        # Determine target path
        target_path = get_target_path(path, accept_copy)

        # Apply all changes in one atomic write
        def write_unified_content(file):
            # Start with original file content
            if accept_copy and target_path.exists():
                # In --accept-copy mode, use existing .new file if it exists
                source_path = target_path
            else:
                source_path = path

            original = list(source_path.read_text(encoding="utf-8").splitlines())

            # Apply assert changes first
            if assert_changes:
                original = _apply_assert_changes(original, assert_changes)

            # Apply doctest changes second
            if doctest_changes:
                original = _apply_doctest_changes(original, doctest_changes)

            # Write final result
            for line in original:
                print(line, file=file)

        atomic_write(target_path, write_unified_content)


# Direct export for options
pytest_addoption = doctest_addoption


# Export all hooks for pytest to discover
__all__ = [
    "__version__",
    "pytest_runtest_makereport",
    "pytest_sessionfinish",
    "pytest_sessionstart",
    "pytest_addoption",
    "pytest_configure",
    "pytest_collect_file",
    "pytest_assertrepr_compare",
    "pytest_collection_modifyitems",
]
