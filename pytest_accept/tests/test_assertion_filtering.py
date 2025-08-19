"""Test that certain assertions are filtered out and not rewritten"""


def test_assertions_with_messages_not_rewritten(pytester):
    """Assertions with custom messages should not be rewritten"""
    test_contents = """
def test_messages():
    assert 1 == 2  # Simple assertion - will be rewritten
    assert 3 == 4, "custom message"  # Has message - won't be rewritten
"""
    path = pytester.makepyfile(test_contents)

    result = pytester.runpytest("--accept-copy")
    result.assert_outcomes(passed=1)

    # File is created because at least one assertion can be rewritten
    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()
        assert "assert 1 == 1" in content  # Fixed
        assert 'assert 3 == 4, "custom message"' in content  # Not rewritten


def test_non_equality_operators_not_rewritten(pytester):
    """Non-equality operators should not be rewritten"""
    test_contents = """
def test_operators():
    assert 1 == 2  # Will be rewritten
    assert 3 != 3  # Won't be rewritten (not equality)
    assert 4 < 5   # Won't be rewritten (not equality)
"""
    path = pytester.makepyfile(test_contents)

    result = pytester.runpytest("--accept-copy")
    result.assert_outcomes(failed=1)

    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()
        assert "assert 1 == 1" in content  # Fixed
        assert "assert 3 != 3" in content  # Unchanged
        assert "assert 4 < 5" in content  # Unchanged


def test_expressions_are_rewritten(pytester):
    """Simple expressions ARE actually rewritten in current implementation"""
    test_contents = """
def test_expressions():
    x = 5
    assert x == 10        # Simple variable - will be rewritten
    assert 1 + 1 == 3     # Expression - WILL be rewritten (current behavior)
    assert len([]) == 1   # Function call - WILL be rewritten (current behavior)
"""
    path = pytester.makepyfile(test_contents)

    result = pytester.runpytest("--accept-copy")
    result.assert_outcomes(passed=1)

    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()
        assert "assert x == 5" in content  # Variable fixed to actual value
        assert "assert 1 + 1 == 2" in content  # Expression FIXED
        assert "assert len([]) == 0" in content  # Function call FIXED


def test_no_rewritable_assertions_no_file(pytester):
    """When no assertions can be rewritten, no .new file is created"""
    test_contents = """
def test_nothing_to_rewrite():
    assert 1 != 2  # Not equality
    assert 3 < 4   # Not equality
    assert 5 == 6, "has message"  # Has message
"""
    path = pytester.makepyfile(test_contents)

    result = pytester.runpytest("--accept-copy")
    result.assert_outcomes(passed=1)

    # No .new file created because nothing was rewritten
    new_path = path.parent / (path.name + ".new")
    assert not new_path.exists()


def test_multiple_comparisons_not_rewritten(pytester):
    """Assertions with multiple comparisons are not rewritten"""
    test_contents = """
def test_multiple():
    assert 1 == 2         # Simple - will be rewritten
    assert 1 < 2 < 3 == 4 # Multiple comparisons - won't be rewritten
    assert 1 == 1 == 2    # Multiple equality - won't be rewritten
"""
    path = pytester.makepyfile(test_contents)

    result = pytester.runpytest("--accept-copy")
    result.assert_outcomes(passed=1)

    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()
        assert "assert 1 == 1" in content  # Simple assertion fixed
        assert "assert 1 < 2 < 3 == 4" in content  # Multiple unchanged
        assert "assert 1 == 1 == 2" in content  # Multiple unchanged


def test_only_first_assertion_on_line_rewritten(pytester):
    """When multiple assertions on same line, only first is processed"""
    test_contents = """
def test_same_line():
    assert 1 == 2; assert 3 == 4
"""
    path = pytester.makepyfile(test_contents)

    result = pytester.runpytest("--accept-copy")
    result.assert_outcomes(passed=1)

    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()
        # Only the first assertion is fixed, second is lost during AST round-trip
        assert "assert 1 == 1" in content
        # The semicolon and second assertion are typically lost in AST processing
        assert ";" not in content or "assert 3 == 4" not in content
