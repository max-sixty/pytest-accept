"""Test that pytest-accept works without pytest-xdist installed.

This test verifies that pytest-accept can function when pytest-xdist
is not installed. The issue being tested: pytest validates all declared
hooks at startup. If we declare xdist-specific hooks (pytest_configure_node,
pytest_testnodedown) but xdist isn't installed, pytest fails with a
PluginValidationError.
"""


def test_plugin_works_without_xdist(pytester):
    """Test that pytest-accept works when xdist is not available.

    This uses pytester.runpytest_subprocess with -p no:xdist to disable xdist,
    simulating an environment where it's not installed.
    """
    # Create a simple test file
    pytester.makepyfile("""
        def test_failing():
            assert 1 == 2

        def test_another():
            assert "hello" == "world"
    """)

    # Run pytest with xdist disabled via -p no:xdist
    # This simulates xdist not being available
    result = pytester.runpytest_subprocess("-p", "no:xdist", "--accept-copy", "-v")

    # The tests should pass with --accept-copy
    result.assert_outcomes(passed=2)

    # Verify the .new file was created with fixed assertions
    new_file = pytester.path / "test_plugin_works_without_xdist.py.new"
    assert new_file.exists(), "The .new file should have been created"

    content = new_file.read_text()
    assert "assert 1 == 1" in content, "First assertion should be fixed"
    assert (
        "assert 'hello' == 'hello'" in content or 'assert "hello" == "hello"' in content
    ), "Second assertion should be fixed"
