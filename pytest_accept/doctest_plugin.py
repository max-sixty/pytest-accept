from __future__ import annotations

import logging
import re
from doctest import DocTestFailure
from pathlib import Path

import pytest
from _pytest.doctest import DoctestItem, MultipleDoctestFailures

from . import DoctestChange, file_changes_key
from .common import (
    track_file_hash,
)

logger = logging.getLogger(__name__)

# StashKey-based state tracking replaces global dictionaries
# This provides proper isolation between test sessions and better testability


def pytest_collect_file(file_path, parent):
    """
    Store the hash of the file so we can check if it changed later
    """
    track_file_hash(file_path, parent.session)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    # Returning this is required by pytest.
    outcome = yield

    if not isinstance(item, DoctestItem) or not call.excinfo:
        return

    # Submit failures to unified change collection
    file_changes = item.session.stash.setdefault(file_changes_key, {})

    if isinstance(call.excinfo.value, DocTestFailure):
        failure = call.excinfo.value
        path = Path(failure.test.filename)
        if path not in file_changes:
            file_changes[path] = []
        file_changes[path].append(
            DoctestChange(
                priority=2,  # Doctest changes run after assert changes
                failure=failure,
            )
        )

    elif isinstance(call.excinfo.value, MultipleDoctestFailures):
        for failure in call.excinfo.value.failures:
            # Don't include tests that fail because of an error setting the test.
            if isinstance(failure, DocTestFailure):
                path = Path(failure.test.filename)
                if path not in file_changes:
                    file_changes[path] = []
                file_changes[path].append(
                    DoctestChange(
                        priority=2,  # Doctest changes run after assert changes
                        failure=failure,
                    )
                )

    return outcome.get_result()


def _snapshot_start_line(failure: DocTestFailure) -> int:
    assert failure.test.lineno is not None
    return (
        failure.test.lineno
        + failure.example.lineno
        + len(failure.example.source.splitlines())
    )


def pytest_addoption(parser):
    """Add pytest-accept options to pytest"""
    group = parser.getgroup("accept", "accept test plugin")
    group.addoption(
        "--accept",
        action="store_true",
        default=False,
        help="Accept the output of doctests, overwriting python files with generated results.",
    )
    group.addoption(
        "--accept-copy",
        action="store_true",
        default=False,
        help="Write a copy of python file named `.py.new` with the generated results of doctests.",
    )


def pytest_configure(config):
    """Sets doctests to continue after first failure"""
    config.option.doctest_continue_on_failure = True


def _to_doctest_format(output: str) -> str:
    """
    Convert a string into a doctest format.

    For example, this requires `<BLANKLINE>`s:
    >>> print(
    ...     '''
    ... hello
    ...
    ... world
    ... '''
    ... )
    <BLANKLINE>
    hello
    <BLANKLINE>
    world

    Here, we have a doctest confirming this behavior (but we have to add a prefix, or
    it'll treat it as an actual blank line! Maybe this is pushing doctests too far!):
    >>> for line in _to_doctest_format(
    ...     '''
    ... hello
    ...
    ... world
    ... '''
    ... ).splitlines():
    ...     print(f"# {line}")
    # <BLANKLINE>
    # hello
    # <BLANKLINE>
    # world

    """

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
    """
    Replace some volatile values, like temp paths & memory locations.

    >>> _redact_volatile("<__main__.A at 0x10b80ce50>")
    '<__main__.A at 0x...>'

    >>> _redact_volatile("/tmp/abcd234/pytest-accept-test-temp-file-0.py")
    '/tmp/.../pytest-accept-test-temp-file-0.py'

    """
    mem_locations = re.sub(r" 0x[0-9a-fA-F]+", " 0x...", output)
    temp_paths = re.sub(r"/tmp/[0-9a-fA-F]+", "/tmp/...", mem_locations)
    return temp_paths


# pytest_sessionfinish removed - unified writer handles all file operations
