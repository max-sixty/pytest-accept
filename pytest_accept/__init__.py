from __future__ import annotations

import logging
import re
import textwrap
from abc import ABC, abstractmethod
from dataclasses import dataclass
from doctest import DocTestFailure
from importlib.metadata import PackageNotFoundError, version
from itertools import zip_longest
from pathlib import Path
from typing import Any

import astor
import pytest

# Package version
try:
    __version__ = version("pytest-accept")
except PackageNotFoundError:
    __version__ = "unknown"

# Logger
logger = logging.getLogger(__name__)

# ===== StashKey instances =====
# Using Any type for forward reference - actual type is dict[Path, list[Change]]
file_changes_key = pytest.StashKey[Any]()
file_hashes_key = pytest.StashKey[dict[Path, int]]()

# StashKeys for assertion tracking
recent_failure_key = pytest.StashKey[list[tuple]]()

# StashKey to store session reference in config for access during assertion handling
session_ref_key = pytest.StashKey[Any]()  # Actually pytest.Session


# ===== Change Classes =====
@dataclass
class Change(ABC):
    """Base class for file changes"""

    priority: int  # Execution order: assert=1, doctest=2

    @property
    @abstractmethod
    def kind(self) -> str:
        """Return the kind of change (e.g., 'assert', 'doctest')"""
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        """Convert to a serializable dictionary for xdist"""
        pass

    @classmethod
    def from_dict(cls, d: dict) -> Change:
        """Create appropriate Change subclass from a dictionary"""
        kind = d["kind"]
        if kind == "assert":
            return AssertChange.from_dict(d)
        elif kind == "doctest":
            return DoctestChange.from_dict(d)
        else:
            raise ValueError(f"Unknown change kind: {kind}")


@dataclass
class AssertChange(Change):
    """Represents an assertion change"""

    location: slice  # Line range in the file
    ast_node: Any  # The new AST node

    @property
    def kind(self) -> str:
        return "assert"

    def to_dict(self) -> dict:
        """Convert to a serializable dictionary"""
        import astor

        return {
            "kind": self.kind,
            "priority": self.priority,
            "location": (self.location.start, self.location.stop),
            "source": astor.to_source(self.ast_node).strip(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> AssertChange:
        """Reconstruct from dictionary"""
        import ast

        ast_node = ast.parse(d["source"]).body[0]
        location = slice(d["location"][0], d["location"][1])
        return cls(priority=d["priority"], location=location, ast_node=ast_node)


@dataclass
class DoctestChange(Change):
    """Represents a doctest change"""

    failure: Any  # DocTestFailure object

    @property
    def kind(self) -> str:
        return "doctest"

    def to_dict(self) -> dict:
        """Convert to a serializable dictionary"""
        return {
            "kind": self.kind,
            "priority": self.priority,
            "test": {
                "filename": str(self.failure.test.filename),
                "lineno": self.failure.test.lineno,
            },
            "example": {
                "lineno": self.failure.example.lineno,
                "source": self.failure.example.source,
                "want": self.failure.example.want,
            },
            "got": self.failure.got,
        }

    @classmethod
    def from_dict(cls, d: dict) -> DoctestChange:
        """Reconstruct from dictionary"""
        from types import SimpleNamespace

        failure = SimpleNamespace(
            test=SimpleNamespace(
                filename=d["test"]["filename"], lineno=d["test"]["lineno"]
            ),
            example=SimpleNamespace(
                lineno=d["example"]["lineno"],
                source=d["example"]["source"],
                want=d["example"]["want"],
            ),
            got=d["got"],
        )
        return cls(priority=d["priority"], failure=failure)


# ===== Helper Functions =====
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


def _apply_assert_changes(
    original: list[str], assert_changes: list[AssertChange]
) -> list[str]:
    """Apply assert plugin changes to file content"""
    result = original.copy()

    # Sort by line number
    assert_changes = sorted(assert_changes, key=lambda c: c.location.start)

    # Apply changes from end to beginning to avoid line number shifts
    for change in reversed(assert_changes):
        # Replace lines in the location range
        indent = result[change.location.start - 1][
            : len(result[change.location.start - 1])
            - len(result[change.location.start - 1].lstrip())
        ]
        source = astor.to_source(change.ast_node).splitlines()
        indented_source = [indent + line for line in source]

        # Replace the range of lines
        result[change.location.start - 1 : change.location.stop] = indented_source

    return result


def _apply_doctest_changes(
    original: list[str], doctest_changes: list[DoctestChange]
) -> list[str]:
    """Apply doctest plugin changes to file content"""
    # Extract failures and sort by line number
    failures = [c.failure for c in doctest_changes]
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


# ===== Import hooks from submodules =====
from .assert_plugin import (
    pytest_assertrepr_compare as assert_assertrepr_compare,
)
from .assert_plugin import (
    pytest_collection_modifyitems as assert_collection_modifyitems,
)
from .assert_plugin import (
    pytest_sessionstart as assert_sessionstart,
)
from .common import atomic_write, get_target_path, has_file_changed, is_accept_mode
from .doctest_plugin import (
    pytest_addoption as doctest_addoption,
)
from .doctest_plugin import (
    pytest_collect_file,
    pytest_runtest_makereport,
)

# Direct exports for simple pass-through hooks
pytest_sessionstart = assert_sessionstart
pytest_collection_modifyitems = assert_collection_modifyitems
pytest_assertrepr_compare = assert_assertrepr_compare
pytest_addoption = doctest_addoption


# ===== Plugin Hooks =====
def pytest_configure(config):
    """Initialize plugin configuration"""
    # Call the doctest configure
    from .doctest_plugin import pytest_configure as doctest_configure

    doctest_configure(config)

    # This hook runs on both master and workers, so we need to check
    # if we're a worker by looking for slaveinput (only exists on workers)
    if hasattr(config, "slaveinput") and "file_hashes" in config.slaveinput:
        # Convert string keys back to Path objects
        serialized_hashes = config.slaveinput["file_hashes"]
        file_hashes = {
            Path(path_str): hash_val for path_str, hash_val in serialized_hashes.items()
        }
        config.stash[file_hashes_key] = file_hashes


def pytest_configure_node(node):
    """xdist hook - send configuration to workers"""
    # Send file hashes to workers so they can track changes
    # node.config.stash should always exist in modern pytest
    if file_hashes_key in node.config.stash:
        # Convert Path keys to strings for serialization
        file_hashes = node.config.stash[file_hashes_key]
        serializable_hashes = {
            str(path): hash_val for path, hash_val in file_hashes.items()
        }
        node.slaveinput["file_hashes"] = serializable_hashes


def pytest_testnodedown(node, error):
    """xdist hook - collect file changes from finished workers"""
    # workeroutput may not exist if the worker crashed or didn't report back
    worker_output = getattr(node, "workeroutput", {})
    if "file_changes" in worker_output:
        # node.session is not guaranteed to exist, so use config.stash directly
        master_changes = node.config.stash.setdefault(file_changes_key, {})

        for path_str, serialized_changes in worker_output["file_changes"].items():
            path = Path(path_str)
            # Deserialize and add all changes
            for change_dict in serialized_changes:
                change = Change.from_dict(change_dict)
                master_changes.setdefault(path, []).append(change)


def pytest_sessionfinish(session, exitstatus):
    """Unified file writer - handles both assert and doctest changes"""
    # Only run when in accept mode
    if not is_accept_mode(session.config):
        return

    accept_copy = session.config.getoption("--accept-copy")

    # This hook runs on both master and workers
    # Check if we're a worker by looking for workeroutput (only exists on workers)
    if hasattr(session.config, "workeroutput"):
        # We're a worker - collect all changes and send to master
        file_changes = session.stash.get(file_changes_key, {})
        if file_changes:
            # Convert Path objects to strings and serialize Change objects
            serializable_changes = {}
            for path, changes in file_changes.items():
                serializable_changes[str(path)] = [
                    change.to_dict() for change in changes
                ]
            session.config.workeroutput["file_changes"] = serializable_changes
        return

    # We're the master (or running without xdist) - write all changes
    # Check both stashes - xdist stores in config.stash, non-xdist in session.stash
    file_changes = session.stash.get(file_changes_key, {}) or session.config.stash.get(
        file_changes_key, {}
    )
    if not file_changes:
        return

    for path_key, changes in file_changes.items():
        # Convert back to Path if needed (from xdist serialization)
        path = Path(path_key) if isinstance(path_key, str) else path_key

        # Check if the file has changed since the start of the test
        if not accept_copy and has_file_changed(path, session):
            logger.warning(
                f"File changed since start of test, not writing results: {path}"
            )
            continue

        # Sort changes by priority (assert=1, doctest=2)
        changes = sorted(changes, key=lambda x: x.priority)

        # Group changes by type for processing
        assert_changes = [c for c in changes if isinstance(c, AssertChange)]
        doctest_changes = [c for c in changes if isinstance(c, DoctestChange)]

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


# ===== Exports =====
__all__ = [
    "__version__",
    "Change",
    "AssertChange",
    "DoctestChange",
    "pytest_runtest_makereport",
    "pytest_sessionfinish",
    "pytest_sessionstart",
    "pytest_addoption",
    "pytest_configure",
    "pytest_collect_file",
    "pytest_assertrepr_compare",
    "pytest_collection_modifyitems",
    "pytest_configure_node",
    "pytest_testnodedown",
]
