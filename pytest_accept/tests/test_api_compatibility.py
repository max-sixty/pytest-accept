"""Test API compatibility checks"""


def test_missing_api_disables_accept_mode(pytester, monkeypatch):
    """Test that missing APIs trigger warning and disable accept mode"""
    # Create a plugin that simulates missing APIs
    plugin_code = """
import logging
import sys
from unittest.mock import Mock

logger = logging.getLogger("pytest_accept_test")

def pytest_configure(config):
    # Only run our mock if accept is requested
    if config.getoption("--accept") or config.getoption("--accept-copy"):
        # Save original module
        original_module = sys.modules.get('_pytest.assertion.rewrite')

        # Mock the module with missing attribute
        mock_module = Mock()
        mock_module.AssertionRewriter = Mock(spec=[])  # No visit_Assert attribute
        sys.modules['_pytest.assertion.rewrite'] = mock_module

        try:
            # Import and call the real configure
            from pytest_accept import pytest_configure as real_configure

            # Set up logging to capture warnings
            handler = logging.StreamHandler()
            handler.setLevel(logging.WARNING)
            logging.getLogger("pytest_accept").addHandler(handler)
            logging.getLogger("pytest_accept").setLevel(logging.WARNING)

            # This should trigger our API check and disable accept mode
            real_configure(config)

            # Log what happened for the test to verify
            if not config.option.accept and not config.option.accept_copy:
                logger.warning("ACCEPT MODE WAS DISABLED")

        finally:
            # Restore original module
            if original_module:
                sys.modules['_pytest.assertion.rewrite'] = original_module
            else:
                sys.modules.pop('_pytest.assertion.rewrite', None)
"""

    pytester.makepyfile(conftest=plugin_code)

    test_contents = """
def test_simple():
    assert 1 == 2
"""
    pytester.makepyfile(test_contents)

    # Run with --accept
    result = pytester.runpytest("-v", "--accept", "-s", "--tb=short")

    # The warning should be in stderr or stdout
    output = result.stdout.str() + result.stderr.str()
    assert (
        "pytest-accept: Disabling --accept mode due to missing pytest internals"
        in output
    )
    assert "AssertionRewriter.visit_Assert not found" in output

    # Test should fail because accept mode was disabled
    result.assert_outcomes(failed=1)


def test_normal_operation_with_apis_present(pytester):
    """Test that plugin works normally when APIs are present"""
    test_contents = """
def test_simple():
    assert 1 == 2

def test_another():
    assert "hello" == "world"
"""
    pytester.makepyfile(test_normal=test_contents)

    # Run with accept-copy (should work normally)
    result = pytester.runpytest("--accept-copy", "-v")

    # Tests should pass (assertions wrapped and fixed)
    result.assert_outcomes(passed=2)

    # .new file should be created with fixes
    new_file = pytester.path / "test_normal.py.new"
    assert new_file.exists()
    content = new_file.read_text()
    assert "assert 1 == 1" in content
    assert "assert 'hello' == 'hello'" in content  # AST rewriting normalizes quotes


def test_passing_tests_work_without_apis(pytester, caplog):
    """Test that passing tests still pass when APIs are unavailable"""
    # Create a plugin that simulates missing APIs and verifies behavior
    plugin_code = """
import sys
import logging
from unittest.mock import Mock

def pytest_configure(config):
    # Only run our mock if accept is requested
    if config.getoption("--accept") or config.getoption("--accept-copy"):
        # Save original module
        original_module = sys.modules.get('_pytest.assertion.rewrite')

        # Mock the module to simulate it's missing
        sys.modules['_pytest.assertion.rewrite'] = None

        try:
            # Import and call the real configure
            from pytest_accept import pytest_configure as real_configure

            # This should trigger our API check and disable accept mode
            real_configure(config)

            # Verify accept mode was disabled
            assert config.option.accept is False
            assert config.option.accept_copy is False

        finally:
            # Restore original module
            if original_module:
                sys.modules['_pytest.assertion.rewrite'] = original_module
"""

    pytester.makepyfile(conftest=plugin_code)

    test_contents = """
def test_passing():
    assert 1 == 1
    assert True
    assert "hello" == "hello"

def test_also_passing():
    assert 2 + 2 == 4
"""
    pytester.makepyfile(test_contents)

    # Run with --accept (but it will be disabled due to missing APIs)
    result = pytester.runpytest("--accept", "-v")

    # All tests should still pass (not fail due to missing APIs)
    result.assert_outcomes(passed=2)

    # No .new file should be created since accept mode was disabled
    assert not (pytester.path / "test_passing_tests_work_without_apis.py.new").exists()


def test_warning_message_format(pytester, monkeypatch):
    """Test the warning message format by checking the actual code"""
    # We can't easily test the actual import failure without breaking pytest,
    # but we can verify the code structure exists

    import inspect

    from pytest_accept import pytest_configure

    # Get the source code of pytest_configure
    source = inspect.getsource(pytest_configure)

    # Verify it contains our API checking logic
    assert "from _pytest._code.code import ExceptionInfo" in source
    assert "from _pytest.assertion.rewrite import AssertionRewriter" in source
    assert "from _pytest.doctest import DoctestItem, MultipleDoctestFailures" in source
    assert "AssertionRewriter.visit_Assert not found" in source
    assert "ExceptionInfo.from_exc_info not found" in source
    assert "config.option.accept = False" in source
    assert "config.option.accept_copy = False" in source
