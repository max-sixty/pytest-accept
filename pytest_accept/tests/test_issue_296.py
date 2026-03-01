"""Reproduce issue #296: indentation depends on blank line whitespace content"""


def test_indentation_with_empty_blank_line(pytester):
    """When the blank line after >>> has no whitespace, output should still be indented."""
    # The blank line between >>> and the closing """ has NO trailing spaces
    test_contents = (
        "def func():\n"
        '    """\n'
        "    >>> func()\n"
        "\n"  # truly empty line - no indentation
        '    """\n'
        "    return 2\n"
    )
    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--doctest-modules", "--accept")
    result.assert_outcomes(failed=1)

    content = path.read_text()
    # The output '2' must be indented to match the docstring level
    assert "    2\n" in content, f"Expected indented output but got:\n{content}"


def test_indentation_two_examples_mixed_blank_lines(pytester):
    """Exact scenario from issue #296: two examples with different blank line content."""
    # Case 1 blank line has 4 spaces; case 2 blank line is truly empty
    test_contents = (
        "def func():\n"
        '    """\n'
        "    Examples\n"
        "    --------\n"
        "    >>> func()\n"
        "    \n"  # blank line WITH indentation spaces
        "    >>> func()\n"
        "\n"  # blank line WITHOUT any spaces
        '    """\n'
        "    return 2\n"
    )
    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--doctest-modules", "--accept")
    result.assert_outcomes(failed=1)

    content = path.read_text()
    lines = content.splitlines()
    # Find the output lines (lines containing just "2" with indentation)
    output_lines = [line for line in lines if line.strip() == "2"]
    assert len(output_lines) == 2, f"Expected 2 output lines but got:\n{content}"
    # Both must be indented identically
    assert output_lines[0] == "    2", f"First output wrong indent:\n{content}"
    assert output_lines[1] == "    2", f"Second output wrong indent:\n{content}"
