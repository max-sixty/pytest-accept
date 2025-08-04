"""Test doctest output formatting features"""


def test_long_line_truncation(pytester):
    """Test that very long lines get truncated"""
    # Create a doctest that will produce a long line
    long_output = "x" * 1100
    test_contents = f'''
def long_output():
    """
    >>> print("{long_output}")
    wrong
    """
    pass
'''
    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(failed=1)

    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()

    # Should have truncated the long line in the doctest output
    assert "x" * 50 + "..." + "x" * 50 in content
    # The original string is still in the function, but the doctest output is truncated
    doctest_section = content.split('"""')[1]  # Get just the docstring
    assert "x" * 50 + "..." + "x" * 50 in doctest_section


def test_many_lines_truncation(pytester):
    """Test that outputs with many lines get truncated"""
    test_contents = '''
def many_lines():
    """
    >>> for i in range(1200):
    ...     print(f"line {i}")
    ...
    wrong
    """
    pass
'''
    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(failed=1)

    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()

    # Should have first 50 and last 50 lines with ... in between
    assert "line 0" in content
    assert "line 49" in content
    assert "    ...\n" in content
    assert "line 1150" in content
    assert "line 1199" in content
    # Middle lines should be omitted
    assert "line 600" not in content


def test_blank_line_handling(pytester):
    """Test that blank lines become <BLANKLINE>"""
    test_contents = '''
def blank_lines():
    """
    >>> print("first\\\\n\\\\nsecond\\\\n\\\\n\\\\nthird")
    wrong
    """
    pass
'''
    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(failed=1)

    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()

    # Should have <BLANKLINE> markers
    assert "<BLANKLINE>" in content
    assert "first" in content
    assert "second" in content
    assert "third" in content


def test_memory_address_redaction(pytester):
    """Test that memory addresses are redacted"""
    test_contents = '''
def show_object():
    """
    >>> object()
    wrong
    """
    pass
'''
    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(failed=1)

    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()

    # Should have redacted memory address
    assert "<object object at 0x...>" in content


def test_temp_path_redaction(pytester):
    """Test that temp paths are redacted"""
    test_contents = '''
def show_temp_path():
    """
    >>> print("/tmp/abc123def456/file.txt")
    wrong
    """
    pass
'''
    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--doctest-modules", "--accept-copy")
    result.assert_outcomes(failed=1)

    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()

    # Should have redacted temp path
    assert "/tmp/.../file.txt" in content
