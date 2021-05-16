import logging
import textwrap
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
    lines = output.splitlines()
    blankline_sentinel = "<BLANKLINE>"
    transformed_lines = [line if line else blankline_sentinel for line in lines]
    return "\n".join(transformed_lines)


def pytest_sessionfinish(session, exitstatus):

    assert session.config.option.doctest_continue_on_failure

    passed_accept = session.config.getoption("--accept")
    passed_accept_copy = session.config.getoption("--accept-copy")
    if not (passed_accept or passed_accept_copy):
        return

    for path, failures in failed_doctests.items():

        # sort by line number
        failures = sorted(failures, key=lambda x: x.test.lineno or 0)

        original = list(path.read_text().splitlines())
        path = path.with_suffix(".py.new") if passed_accept_copy else path
        with path.open("w+") as file:

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
