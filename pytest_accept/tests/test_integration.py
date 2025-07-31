"""Integration tests for assert and doctest plugins working together"""


def test_both_plugins_same_file(pytester):
    """Test that both assert and doctest plugins can update the same file"""
    test_contents = '''def add(a, b):
    """Add two numbers

    >>> add(2, 2)
    5
    >>> add(3, 3)
    7
    """
    return a + b


def test_add():
    assert add(1, 1) == 3
    assert add(2, 2) == 5
'''

    path = pytester.makepyfile(test_contents)

    # Run with both --accept-copy and --doctest-modules
    result = pytester.runpytest("--accept-copy", "--doctest-modules")
    result.assert_outcomes(passed=1, failed=1)  # assertions pass, doctests fail

    # Check the .new file has both updates
    with open(str(path) + ".new") as f:
        content = f.read()
        # Check doctest updates
        assert ">>> add(2, 2)\n    4" in content
        assert ">>> add(3, 3)\n    6" in content
        # Check assertion updates
        assert "assert add(1, 1) == 2" in content
        assert "assert add(2, 2) == 4" in content


def test_both_plugins_overwrite(pytester):
    """Test that both plugins can overwrite the original file"""
    test_contents = '''def multiply(a, b):
    """Multiply two numbers

    >>> multiply(2, 3)
    5
    """
    return a * b


def test_multiply():
    assert multiply(2, 2) == 5
'''

    path = pytester.makepyfile(test_contents)

    # Run with --accept to overwrite
    result = pytester.runpytest("--accept", "--doctest-modules")
    result.assert_outcomes(passed=1, failed=1)

    # Check the original file was updated
    with open(str(path)) as f:
        content = f.read()
        # Check doctest updates
        assert ">>> multiply(2, 3)\n    6" in content
        # Check assertion updates
        assert "assert multiply(2, 2) == 4" in content
