"""Test handling of multiple doctest failures in same example"""


def test_multiple_failures_in_one_example(pytester):
    """Test that all failures in a multi-failure doctest are corrected"""
    test_contents = '''
def multi_output():
    """Function with multiple outputs

    >>> multi_output()
    'first'
    'second'
    'third'
    """
    return ['first_actual', 'second_actual', 'third_actual']
'''

    path = pytester.makepyfile(test_contents)

    # Run doctests with accept mode
    result = pytester.runpytest("--doctest-modules", "--accept-copy", "-v")
    result.assert_outcomes(failed=1)

    # Check the .new file
    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()

    # All outputs should be corrected
    assert "['first_actual', 'second_actual', 'third_actual']" in content
    assert "'first'" not in content
    assert "'second'" not in content
    assert "'third'" not in content


def test_multiple_statements_with_failures(pytester):
    """Test multiple statements each with their own failure"""
    test_contents = '''
def calculate():
    """Multiple calculations

    >>> 1 + 1
    3
    >>> 2 * 2
    5
    >>> 10 / 2
    6
    """
    pass
'''

    path = pytester.makepyfile(test_contents)

    # Run doctests with accept mode
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(failed=1)

    # Check the .new file
    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()

    # All calculations should be corrected
    assert ">>> 1 + 1\n    2" in content
    assert ">>> 2 * 2\n    4" in content
    assert ">>> 10 / 2\n    5.0" in content


def test_mixed_pass_fail_statements(pytester):
    """Test mix of passing and failing statements"""
    test_contents = '''
def mixed_results():
    """Some pass, some fail

    >>> 1 + 1
    2
    >>> 2 + 2
    5
    >>> 3 + 3
    6
    >>> 4 + 4
    7
    """
    pass
'''

    path = pytester.makepyfile(test_contents)

    # Run doctests with accept mode
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(failed=1)

    # Check the .new file
    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()

    # Correct ones should stay the same
    assert ">>> 1 + 1\n    2" in content
    # Wrong ones should be fixed
    assert ">>> 2 + 2\n    4" in content
    assert ">>> 3 + 3\n    6" in content
    assert ">>> 4 + 4\n    8" in content


def test_exception_in_doctest(pytester):
    """Test doctest with exceptions"""
    test_contents = '''
def raise_error():
    """Function that raises

    >>> raise_error()
    Traceback (most recent call last):
        ...
    ValueError: wrong message
    """
    raise ValueError("actual message")
'''

    path = pytester.makepyfile(test_contents)

    # Run doctests with accept mode
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(failed=1)

    # Check the .new file
    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()

    # Exception should be updated
    assert "ValueError: actual message" in content
    assert "ValueError: wrong message" not in content


def test_multiline_statement_failure(pytester):
    """Test multiline statements with failures"""
    test_contents = '''
def process_data():
    """Process multiline data

    >>> data = {"a": 1, "b": 2}
    >>> data
    {'a': 10, 'b': 20}
    """
    pass
'''

    path = pytester.makepyfile(test_contents)

    # Run doctests with accept mode
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(failed=1)

    # Check the .new file
    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()

    # Should have the correct dict output
    assert "{'a': 1, 'b': 2}" in content
    assert "{'a': 10, 'b': 20}" not in content
