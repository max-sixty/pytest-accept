from __future__ import annotations

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
    pytest_sessionfinish as assert_sessionfinish,
)
from .assert_plugin import (
    pytest_sessionstart as assert_sessionstart,
)
from .doctest_plugin import (
    pytest_addoption as doctest_addoption,
)
from .doctest_plugin import (
    pytest_collect_file,
    pytest_configure,
    pytest_runtest_makereport,
)
from .doctest_plugin import (
    pytest_sessionfinish as doctest_sessionfinish,
)


def pytest_sessionstart(session):
    """Start both assert and doctest session handlers"""
    assert_sessionstart(session)


def pytest_collection_modifyitems(session, config, items):
    """Handle collection modification for both plugins"""
    assert_collection_modifyitems(session, config, items)


def pytest_sessionfinish(session, exitstatus):
    """Finish both assert and doctest session handlers"""
    # Run both plugins when --accept or --accept-copy is used
    passed_accept = session.config.getoption("--accept")
    passed_accept_copy = session.config.getoption("--accept-copy")

    if passed_accept or passed_accept_copy:
        # Run assert plugin first (it modifies the actual test files)
        assert_sessionfinish(session, exitstatus)
        # Run doctest plugin after (it can then update the doctests in the same files)
        doctest_sessionfinish(session, exitstatus)


def pytest_assertrepr_compare(config, op, left, right):
    """Handle assertion comparison for assert plugin"""
    # Just pass through to the assert plugin
    return assert_assertrepr_compare(config, op, left, right)


def pytest_addoption(parser):
    """Add pytest-accept options to pytest"""
    # The doctest plugin already adds --accept and --accept-copy
    return doctest_addoption(parser)


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
