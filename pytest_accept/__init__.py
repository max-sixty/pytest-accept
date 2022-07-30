import pytest

from .doctest_plugin import (
    pytest_collect_file,
    pytest_configure,
)

from .assert_plugin import pytest_assertrepr_compare

# Note that plugins need to be listed here in order for pytest to pick them up when
# this package is installed.


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield

    from .doctest_plugin import pytest_runtest_makereport
    pytest_runtest_makereport(item, call, outcome)

    from .assert_plugin import pytest_runtest_makereport
    pytest_runtest_makereport(item, call, outcome)
    # returning this is required by pytest
    return outcome.get_result()

def pytest_sessionfinish(session, exitstatus):
    from .doctest_plugin import pytest_sessionfinish
    pytest_sessionfinish(session, exitstatus)

    from .assert_plugin import pytest_sessionfinish
    pytest_sessionfinish(session, exitstatus)

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

__all__ = [
    pytest_collect_file,
    pytest_configure,
    pytest_assertrepr_compare,
    pytest_runtest_makereport,
    pytest_sessionfinish,
]

