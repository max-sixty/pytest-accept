import pytest

from .assert_plugin import pytest_assertrepr_compare

# Note that plugins need to be listed here in order for pytest to pick them up when
# this package is installed.


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield

    from .assert_plugin import pytest_runtest_makereport
    pytest_runtest_makereport(item, call, outcome)
    # returning this is required by pytest
    return outcome.get_result()

def pytest_sessionfinish(session, exitstatus):
    from .assert_plugin import pytest_sessionfinish
    pytest_sessionfinish(session, exitstatus)

def pytest_addoption(parser):
    """Add pytest-accept options to pytest"""
    group = parser.getgroup("accept", "accept test plugin")
    group.addoption(
        "--accept",
        action="store_true",
        default=False,
        help="Accept the output of asserts, overwriting python files with generated results.",
    )
    group.addoption(
        "--accept-copy",
        action="store_true",
        default=False,
        help="Write a copy of python file named `.py.new` with the generated results of asserts.",
    )

__all__ = [
    pytest_assertrepr_compare,
    pytest_runtest_makereport,
    pytest_sessionfinish,
]

