from __future__ import annotations

from collections import defaultdict
from doctest import DocTestFailure
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pytest

try:
    __version__ = version("pytest-accept")
except PackageNotFoundError:
    __version__ = "unknown"

# StashKey instances to replace global state
failed_doctests_key = pytest.StashKey[dict[Path, list[DocTestFailure]]]()
file_hashes_key = pytest.StashKey[dict[Path, int]]()
asts_modified_key = pytest.StashKey[dict[str, list[tuple[slice, str]]]]()
recent_failure_key = pytest.StashKey[list[tuple]]()


def get_failed_doctests(session) -> dict[Path, list[DocTestFailure]]:
    """Get or create the failed doctests dict from session stash"""
    return session.stash.setdefault(failed_doctests_key, defaultdict(list))


def get_file_hashes(session) -> dict[Path, int]:
    """Get or create the file hashes dict from session stash"""
    return session.stash.setdefault(file_hashes_key, {})


def get_asts_modified(session) -> dict[str, list[tuple[slice, str]]]:
    """Get or create the asts modified dict from session stash"""
    return session.stash.setdefault(asts_modified_key, defaultdict(list))


def get_recent_failure(session) -> list[tuple]:
    """Get or create the recent failure list from session stash"""
    return session.stash.setdefault(recent_failure_key, [])


from .doctest_plugin import (
    pytest_addoption,
    pytest_collect_file,
    pytest_configure,
    pytest_runtest_makereport,
    pytest_sessionfinish,
)

# Note that plugins need to be listed here in order for pytest to pick them up when
# this package is installed.

__all__ = [
    "__version__",
    "pytest_runtest_makereport",
    "pytest_sessionfinish",
    "pytest_addoption",
    "pytest_configure",
    "pytest_collect_file",
]
