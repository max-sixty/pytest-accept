"""Test parametrized test support"""


def test_parametrized_tests_work(pytester):
    """Test that parametrized tests can have their assertions rewritten"""
    test_contents = """
import pytest

@pytest.mark.parametrize("a,b", [(1, 2), (3, 4), (5, 6)])
def test_parametrized_addition(a, b):
    # These assertions have literal values on the right side
    assert a + b == 10  # Wrong literal value

@pytest.mark.parametrize("name", ["alice", "bob", "charlie"])
def test_parametrized_string(name):
    assert len(name) == 10  # Wrong literal value
"""
    path = pytester.makepyfile(test_contents)

    result = pytester.runpytest("--accept-copy", "-v")
    # All tests should pass after rewriting
    result.assert_outcomes(passed=6)  # 3 + 3 parametrized tests

    # Check the generated .new file
    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()
        # Check that assertions were rewritten for each parametrized case
        assert "assert a + b == 3" in content  # 1 + 2
        assert "assert len(name) == 5" in content  # len("alice")


def test_parametrized_with_fixtures(pytester):
    """Test parametrized tests that also use fixtures"""
    test_contents = """
import pytest

@pytest.fixture
def multiplier():
    return 2

@pytest.mark.parametrize("value", [5, 10, 15])
def test_with_fixture_and_param(value, multiplier):
    # This has a literal on the right side, should work
    assert value * multiplier == 100  # Wrong literal
"""
    path = pytester.makepyfile(test_contents)

    result = pytester.runpytest("--accept-copy", "-v")
    result.assert_outcomes(passed=3)

    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()
        assert "assert value * multiplier == 10" in content  # 5 * 2
