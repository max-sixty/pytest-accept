import pytest

def pytest_sessionstart(session):
    from .assert_plugin import pytest_sessionstart
    pytest_sessionstart(session)

def pytest_sessionfinish(session, exitstatus):
    from .assert_plugin import pytest_sessionfinish
    pytest_sessionfinish(session, exitstatus)

def pytest_assertrepr_compare(config, op, left, right):
    from .assert_plugin import pytest_assertrepr_compare
    pytest_assertrepr_compare(config, op, left, right)

def pytest_addoption(parser):
    """Add pytest-accept options to pytest"""
    group = parser.getgroup("accept", "accept test plugin")
    group.addoption(
        "--accept",
        dest="ACCEPT",
        default="",
        help="Write a .new file with new file contents ('new'), or overwrite the original test file ('overwrite')"
    )
    group.addoption(
        "--accept-continue",
        action="store_true",
        default=False,
        help="Continue after the first test failure"
    )
