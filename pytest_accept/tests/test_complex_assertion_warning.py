def test_complex_assertion_warning(pytester):
    """Test that complex assertions trigger a warning and are skipped"""
    # Create a test with an assertion that exceeds the complexity threshold
    # We simulate what pytest's assertion rewriter would generate
    test_contents = """
def test_complex():
    # This would normally be rewritten by pytest into many AST nodes
    # We'll create an assertion with many comparisons to trigger the threshold
    assert (
        1 == 1 and 2 == 2 and 3 == 3 and 4 == 4 and 5 == 5 and
        6 == 6 and 7 == 7 and 8 == 8 and 9 == 9 and 10 == 10 and
        11 == 11 and 12 == 12 and 13 == 13 and 14 == 14 and 15 == 15 and
        16 == 16 and 17 == 17 and 18 == 18 and 19 == 19 and 20 == 20 and
        21 == 21 and 22 == 22 and 23 == 23 and 24 == 24 and 25 == 25 and
        26 == 26 and 27 == 27 and 28 == 28 and 29 == 29 and 30 == 30 and
        31 == 31 and 32 == 32 and 33 == 33 and 34 == 34 and 35 == 35 and
        36 == 36 and 37 == 37 and 38 == 38 and 39 == 39 and 40 == 40 and
        41 == 41 and 42 == 42 and 43 == 43 and 44 == 44 and 45 == 45 and
        46 == 46 and 47 == 47 and 48 == 48 and 49 == 49 and 50 == 50 and
        51 == 51 and 52 == 52 and 53 == 53 and 54 == 54 and 55 == 55 and
        56 == 56 and 57 == 57 and 58 == 58 and 59 == 59 and 60 == 60 and
        61 == 61 and 62 == 62 and 63 == 63 and 64 == 64 and 65 == 65 and
        66 == 66 and 67 == 67 and 68 == 68 and 69 == 69 and 70 == 70 and
        71 == 71 and 72 == 72 and 73 == 73 and 74 == 74 and 75 == 75
    )
"""
    path = pytester.makepyfile(test_contents)

    # Run with accept mode and capture warnings via log output
    result = pytester.runpytest("--accept-copy", "--log-cli-level=WARNING")

    # The test should pass (all comparisons are true)
    result.assert_outcomes(passed=1)

    # Check that the warning was logged - the warning appears in the captured log
    # Since the warning is logged, we check for it in the output
    assert "Skipping accept mode for a complex assertion" in result.stdout.str()
    assert (
        "This assertion will fail normally and won't be auto-corrected"
        in result.stdout.str()
    )
    assert (
        "To fix: simplify the assertion or manually update the expected value"
        in result.stdout.str()
    )

    # The .new file should not be created since no assertions were rewritten
    assert not (path.parent / (path.name + ".new")).exists()


def test_complex_assertion_fails_normally(pytester):
    """Test that complex assertions that fail are not auto-corrected"""
    # Create a test with a complex assertion that will fail
    test_contents = """
def test_complex_fail():
    # Complex assertion with a failure
    assert (
        1 == 1 and 2 == 2 and 3 == 3 and 4 == 4 and 5 == 5 and
        6 == 6 and 7 == 7 and 8 == 8 and 9 == 9 and 10 == 10 and
        11 == 11 and 12 == 12 and 13 == 13 and 14 == 14 and 15 == 15 and
        16 == 16 and 17 == 17 and 18 == 18 and 19 == 19 and 20 == 20 and
        21 == 21 and 22 == 22 and 23 == 23 and 24 == 24 and 25 == 25 and
        26 == 26 and 27 == 27 and 28 == 28 and 29 == 29 and 30 == 30 and
        31 == 31 and 32 == 32 and 33 == 33 and 34 == 34 and 35 == 35 and
        36 == 36 and 37 == 37 and 38 == 38 and 39 == 39 and 40 == 40 and
        41 == 41 and 42 == 42 and 43 == 43 and 44 == 44 and 45 == 45 and
        46 == 46 and 47 == 47 and 48 == 48 and 49 == 49 and 50 == 50 and
        51 == 51 and 52 == 52 and 53 == 53 and 54 == 54 and 55 == 55 and
        56 == 56 and 57 == 57 and 58 == 58 and 59 == 59 and 60 == 60 and
        61 == 61 and 62 == 62 and 63 == 63 and 64 == 64 and 65 == 65 and
        66 == 66 and 67 == 67 and 68 == 68 and 69 == 69 and 70 == 70 and
        71 == 71 and 72 == 72 and 73 == 73 and 74 == 74 and 75 == 99  # This fails
    )
"""
    path = pytester.makepyfile(test_contents)

    # Run with accept mode and capture warnings via log output
    result = pytester.runpytest("--accept-copy", "--log-cli-level=WARNING")

    # The test should fail because the assertion is not wrapped in try-except
    result.assert_outcomes(failed=1)

    # Check that the warning was logged
    assert "Skipping accept mode for a complex assertion" in result.stdout.str()
    assert (
        "This assertion will fail normally and won't be auto-corrected"
        in result.stdout.str()
    )

    # The .new file should not be created
    assert not (path.parent / (path.name + ".new")).exists()


def test_simple_assertion_still_works(pytester):
    """Test that simple assertions are still rewritten correctly"""
    test_contents = """
def test_simple():
    assert 1 == 2
    assert "hello" == "world"
"""
    path = pytester.makepyfile(test_contents)

    # Run with accept mode
    result = pytester.runpytest("--accept-copy")
    result.assert_outcomes(passed=1)

    # Check that the .new file was created with corrections
    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()
        assert "assert 1 == 1" in content
        # Check for both single and double quotes since Python may use either
        assert (
            "assert 'hello' == 'hello'" in content
            or 'assert "hello" == "hello"' in content
        )
