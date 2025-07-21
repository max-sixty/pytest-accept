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

# Direct exports for simple pass-through hooks
pytest_sessionstart = assert_sessionstart
pytest_collection_modifyitems = assert_collection_modifyitems
pytest_assertrepr_compare = assert_assertrepr_compare


def pytest_sessionfinish(session, exitstatus):
    """Coordinate both plugins: assert first, then doctest"""
    # Only run when --accept or --accept-copy is used
    if session.config.getoption("--accept") or session.config.getoption(
        "--accept-copy"
    ):
        # Run assert plugin first (it modifies the actual test files)
        assert_sessionfinish(session, exitstatus)
        # Run doctest plugin after (it can then update the doctests in the same files)
        doctest_sessionfinish(session, exitstatus)


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
