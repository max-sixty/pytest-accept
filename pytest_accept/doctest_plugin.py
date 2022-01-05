import logging
import re
import textwrap
import warnings
from collections import defaultdict
from doctest import DocTestFailure
from itertools import zip_longest
from pathlib import Path
from typing import Dict, List

import pytest
from _pytest.doctest import DoctestItem, MultipleDoctestFailures

logger = logging.getLogger(__name__)

# TODO: is there a way of tracking failed tests without this static global? I can't find
# a pytest hook which gives all failures at the end of the test suite. And IIUC we need
# all the results at a single point after knowing all failures, since mutating the
# existing file during the test suite will cause a mismatch between the line numbers
# that pytest reports and the line numbers of the mutated file in subsequent tests. An
# alternative is a static with the updated file, but that seems even heavier.

# Dict of {path: list of (location, new code)}
failed_doctests: Dict[Path, List[DocTestFailure]] = defaultdict(list)

# Dict of filename to hashes, so we don't overwrite a changed file
file_hashes: Dict[Path, int] = {}


def pytest_collect_file(path, parent):
    """
    Store the hash of the file so we can check if it changed later
    """
    path = Path(path)
    file_hashes[path] = hash(path.read_bytes())


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    # Returning this is required by pytest.
    outcome = yield

    if not isinstance(item, DoctestItem) or not call.excinfo:
        return

    if isinstance(call.excinfo.value, DocTestFailure):
        failed_doctests[Path(call.excinfo.value.test.filename)].append(
            call.excinfo.value
        )

    elif isinstance(call.excinfo.value, MultipleDoctestFailures):
        for failure in call.excinfo.value.failures:
            # Don't include tests that fail because of an error setting the test.
            if isinstance(failure, DocTestFailure):
                failed_doctests[Path(failure.test.filename)].append(failure)

    return outcome.get_result()


def _snapshot_start_line(failure):
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

    This passes the doctest because it has `<BLANKLINE>`s in the correct place.
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

    We can also use a test to confirm this is what the function creates (but we have to
    add a prefix, or it'll treat it as an actual blank line! Maybe this is pushing
    doctests too far!):
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


def pytest_sessionfinish(session, exitstatus):
    """
    Write generated doctest results to their appropriate files
    """

    assert session.config.option.doctest_continue_on_failure

    passed_accept = session.config.getoption("--accept")
    passed_accept_copy = session.config.getoption("--accept-copy")
    if not (passed_accept or passed_accept_copy):
        return

    for path, failures in failed_doctests.items():

        # Check if the file has changed since the start of the test.
        current_hash = hash(path.read_bytes())
        if path not in file_hashes:
            warnings.warn(
                f"{path} not found by pytest-accept as having collected tests "
                "at the start of the session. Proceeding to overwrite. Please "
                "report an issue if this occurs unexpectedly. Full path list is "
                f"{file_hashes}"
            )
        elif not passed_accept_copy and current_hash != file_hashes[path]:
            logger.warning(
                f"File changed since start of test, not writing results: {path}"
            )
            continue

        # sort by line number
        failures = sorted(failures, key=lambda x: x.test.lineno or 0)

        original = list(path.read_text(encoding="utf-8").splitlines())
        path = path.with_suffix(".py.new") if passed_accept_copy else path
        with path.open("w+", encoding="utf-8") as file:

            # TODO: is there cleaner way of doing this interleaving?

            first_failure = failures[0]
            start_line = _snapshot_start_line(first_failure)
            for line in original[:start_line]:
                print(line, file=file)

            for current, next in zip_longest(failures, failures[1:]):

                snapshot_result = _to_doctest_format(current.got)
                indented = textwrap.indent(
                    snapshot_result, prefix=" " * current.example.indent
                )
                for line in indented.splitlines():
                    print(line, file=file)

                current_finish_line = _snapshot_start_line(current) + len(
                    current.example.want.splitlines()
                )
                next_start_line = _snapshot_start_line(next) if next else len(original)

                for line in original[current_finish_line:next_start_line]:
                    print(line, file=file)
