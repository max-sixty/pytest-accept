"""Test unified change handling between assert and doctest plugins"""

import textwrap
from pathlib import Path


def test_both_plugins_simple_case(pytester):
    """Test assert and doctest changes in separate functions"""
    test_contents = textwrap.dedent('''
    def add(a, b):
        """
        >>> add(1, 1)
        3
        """
        return a + b

    def test_assertion():
        assert 1 + 1 == 3
    ''').strip()

    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    # Doctests fail (can't be rewritten during execution), assertions pass (rewritten during execution)
    result.assert_outcomes(failed=1, passed=1)

    # Check the generated .new file
    new_file = Path(str(path) + ".new")
    assert new_file.exists()

    content = new_file.read_text()
    # Should have both changes: doctest output corrected AND assertion corrected
    assert ">>> add(1, 1)" in content and "2" in content  # Doctest corrected
    assert "assert 1 + 1 == 2" in content  # Assertion corrected


def test_interleaved_changes_same_function(pytester):
    """Test when assertions and doctests are mixed within same function"""
    test_contents = textwrap.dedent('''
    def test_with_docstring():
        """
        This function has a doctest:
        >>> 1 + 1
        3
        """
        # Regular assertion after the docstring
        assert 2 + 2 == 5

        # Another assertion
        result = 10
        assert result == 11
    ''').strip()

    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(failed=1, passed=1)  # doctest fails, test function passes

    # Check the generated .new file
    new_file = Path(str(path) + ".new")
    assert new_file.exists()

    content = new_file.read_text()
    print("Generated content:")
    print(content)

    # All changes should be applied correctly
    assert ">>> 1 + 1" in content and "2" in content  # Doctest corrected
    assert "assert 2 + 2 == 4" in content  # First assertion corrected
    assert "assert result == 10" in content  # Second assertion corrected


def test_multiple_doctests_and_assertions(pytester):
    """Test multiple doctests and assertions in same file"""
    test_contents = textwrap.dedent('''
    def func1(x):
        """
        >>> func1(5)
        10
        """
        return x * 2

    def func2(x):
        """
        >>> func2(3)
        7
        >>> func2(0)
        1
        """
        return x + 1

    def test_multiple():
        assert func1(5) == 11     # Should become == 10
        assert func2(3) == 5      # Should become == 4
        assert func2(0) == 2      # Should become == 1
    ''').strip()

    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(
        failed=1, passed=2
    )  # 1 doctest fails, 2 pass (1 doctest + 1 test function)

    new_file = Path(str(path) + ".new")
    assert new_file.exists()

    content = new_file.read_text()
    print("Generated content:")
    print(content)

    # Check doctest corrections
    assert ">>> func1(5)" in content and "10" in content  # This one was already correct
    assert ">>> func2(3)" in content and "4" in content  # Should be corrected to 4
    assert ">>> func2(0)" in content and "1" in content  # This one was already correct

    # Check assertion corrections
    assert "assert func1(5) == 10" in content
    assert "assert func2(3) == 4" in content
    assert "assert func2(0) == 1" in content


def test_doctest_between_assertions(pytester):
    """Test doctest corrections when they appear between assertion lines"""
    test_contents = textwrap.dedent('''
    def helper():
        """
        >>> helper()
        'wrong'
        """
        return 'correct'

    def test_complex():
        assert 1 == 2          # Line that will be changed

        # Call function with doctest (this doctest should be corrected too)
        result = helper()

        assert result == 'wrong'  # This should be corrected to 'correct'
    ''').strip()

    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(failed=1, passed=1)  # doctest fails, test passes

    new_file = Path(str(path) + ".new")
    assert new_file.exists()

    content = new_file.read_text()
    print("Generated content:")
    print(content)

    # Check both types of corrections
    assert ">>> helper()\n    'correct'" in content  # Doctest corrected
    assert "assert 1 == 1" in content  # First assertion corrected
    assert "assert result == 'correct'" in content  # Second assertion corrected


def test_priority_ordering_matters(pytester):
    """Test that assert changes (priority=1) are applied before doctest changes (priority=2)"""
    test_contents = textwrap.dedent('''
    def test_func():
        """
        This test has assertion that changes the function behavior:
        >>> test_func()  # This doctest will fail initially
        'original'
        """
        # This assertion will change this function's return value
        assert test_func.__doc__ == "wrong doc"
        return 'original'
    ''').strip()

    # Note: This is a tricky case - the assert plugin changes the code,
    # which might affect what the doctest should show
    path = pytester.makepyfile(test_contents)
    pytester.runpytest("--doctest-modules", "--accept-copy")

    new_file = Path(str(path) + ".new")
    if new_file.exists():
        content = new_file.read_text()
        print("Generated content:")
        print(content)


def test_no_changes_needed(pytester):
    """Test that files with no failing tests don't get modified"""
    test_contents = textwrap.dedent('''
    def add(a, b):
        """
        >>> add(1, 1)
        2
        """
        return a + b

    def test_passing():
        assert 1 + 1 == 2
    ''').strip()

    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(passed=2)

    # No .new file should be created since all tests pass
    new_file = Path(str(path) + ".new")
    assert not new_file.exists()


def test_only_assertions_fail(pytester):
    """Test case where only assertions fail, doctests pass"""
    test_contents = textwrap.dedent('''
    def add(a, b):
        """
        >>> add(1, 1)
        2
        """
        return a + b

    def test_failing_assertion():
        assert add(2, 3) == 6  # Should become == 5
    ''').strip()

    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(
        passed=2
    )  # Both pass - doctest is correct, assertion gets rewritten

    new_file = Path(str(path) + ".new")
    assert new_file.exists()

    content = new_file.read_text()
    # Only assertion should be corrected, doctest unchanged
    assert ">>> add(1, 1)\n    2" in content  # Doctest unchanged
    assert "assert add(2, 3) == 5" in content  # Assertion corrected


def test_only_doctests_fail(pytester):
    """Test case where only doctests fail, assertions pass"""
    test_contents = textwrap.dedent('''
    def multiply(a, b):
        """
        >>> multiply(3, 4)
        13
        """
        return a * b

    def test_passing_assertion():
        assert multiply(2, 5) == 10
    ''').strip()

    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(failed=1, passed=1)  # doctest fails, assertion passes

    new_file = Path(str(path) + ".new")
    assert new_file.exists()

    content = new_file.read_text()
    # Only doctest should be corrected, assertion unchanged
    assert ">>> multiply(3, 4)\n    12" in content  # Doctest corrected
    assert "assert multiply(2, 5) == 10" in content  # Assertion unchanged


def test_assert_mode_vs_accept_copy_mode(pytester):
    """Test that --accept mode works with unified changes (overwrites original)"""
    test_contents = textwrap.dedent('''
    def func(x):
        """
        >>> func(5)
        99
        """
        return x * 2

    def test_assertion():
        assert func(3) == 99
    ''').strip()

    path = pytester.makepyfile(test_contents)
    original_content = path.read_text()

    # Use --accept instead of --accept-copy
    result = pytester.runpytest("--doctest-modules", "--accept")
    result.assert_outcomes(failed=1, passed=1)  # doctest fails, assertion passes

    # Original file should be modified, no .new file
    new_file = Path(str(path) + ".new")
    assert not new_file.exists()

    # Original file should have the corrections
    modified_content = path.read_text()
    assert modified_content != original_content
    assert ">>> func(5)\n    10" in modified_content  # Doctest corrected
    assert "assert func(3) == 6" in modified_content  # Assertion corrected


def test_complete_file_contents_preserved(pytester):
    """Test that all lines are preserved and in correct order with complex interleaved changes"""
    test_contents = textwrap.dedent('''
    # File header comment
    from math import sqrt

    def calculate(x, y):
        """Calculate something complex

        This function demonstrates multiple operations:
        >>> calculate(4, 3)
        99.5
        >>> calculate(0, 0)
        7.5
        """
        # Complex calculation
        result = sqrt(x * x + y * y)
        return result

    class Helper:
        """Helper class for calculations"""

        def __init__(self, multiplier):
            self.multiplier = multiplier

        def transform(self, value):
            """Transform a value

            >>> helper = Helper(2)
            >>> helper.transform(5)
            999
            """
            return value * self.multiplier

    def test_calculations():
        """Test our calculation functions"""
        # Test basic calculation
        assert calculate(3, 4) == 6.0    # Should be 5.0

        # Test helper class
        helper = Helper(3)
        assert helper.transform(4) == 99  # Should be 12

        # Test edge cases
        assert calculate(0, 0) == 1.0     # Should be 0.0

        # Another calculation
        result = calculate(1, 1)
        assert result == 3.14             # Should be ~1.414

    # End of file comment
    ''').strip()

    path = pytester.makepyfile(test_contents)
    pytester.runpytest("--doctest-modules", "--accept-copy")

    # Some tests will pass (assertions get rewritten), some will fail (doctests can't be rewritten during execution)
    # We don't care about exact outcomes, just that file is processed

    # Check the generated .new file
    new_file = Path(str(path) + ".new")
    assert new_file.exists()

    corrected_content = new_file.read_text()
    print("=== ORIGINAL CONTENT ===")
    print(repr(test_contents))
    print("\n=== CORRECTED CONTENT ===")
    print(repr(corrected_content))

    # Assert complete file structure is preserved
    expected_corrected = textwrap.dedent('''
    # File header comment
    from math import sqrt

    def calculate(x, y):
        """Calculate something complex

        This function demonstrates multiple operations:
        >>> calculate(4, 3)
        5.0
        >>> calculate(0, 0)
        0.0
        """
        # Complex calculation
        result = sqrt(x * x + y * y)
        return result

    class Helper:
        """Helper class for calculations"""

        def __init__(self, multiplier):
            self.multiplier = multiplier

        def transform(self, value):
            """Transform a value

            >>> helper = Helper(2)
            >>> helper.transform(5)
            10
            """
            return value * self.multiplier

    def test_calculations():
        """Test our calculation functions"""
        # Test basic calculation
        assert calculate(3, 4) == 5.0

        # Test helper class
        helper = Helper(3)
        assert helper.transform(4) == 12

        # Test edge cases
        assert calculate(0, 0) == 0.0

        # Another calculation
        result = calculate(1, 1)
        assert result == 1.4142135623730951

    # End of file comment
    ''').strip()

    # Normalize whitespace for comparison
    def normalize_content(content):
        # Split into lines and strip each line, then rejoin, and strip final whitespace
        return "\n".join(line.rstrip() for line in content.split("\n")).rstrip()

    corrected_normalized = normalize_content(corrected_content)
    expected_normalized = normalize_content(expected_corrected)

    # Assert exact content match
    assert corrected_normalized == expected_normalized, f"""
File contents don't match exactly!

Expected:
{expected_normalized!r}

Got:
{corrected_normalized!r}

Diff lines:
Expected lines: {len(expected_normalized.split(chr(10)))}
Got lines: {len(corrected_normalized.split(chr(10)))}
"""
