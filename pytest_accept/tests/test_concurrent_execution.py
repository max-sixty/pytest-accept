"""Test concurrent execution with pytest-xdist"""

import pytest

pytest_plugins = ["pytester"]


def test_concurrent_execution_with_xdist(pytester):
    """Test that the plugin works correctly with pytest-xdist"""
    # Check if xdist is available
    try:
        import xdist  # noqa: F401
    except ImportError:
        pytest.skip("pytest-xdist not installed")

    # Create multiple test files that will run in parallel
    test_contents1 = """
def test_file1_test1():
    assert 1 == 2

def test_file1_test2():
    assert 3 == 4
"""

    test_contents2 = """
def test_file2_test1():
    assert 5 == 6

def test_file2_test2():
    assert 7 == 8
"""

    pytester.makepyfile(test_file1=test_contents1, test_file2=test_contents2)

    # Run with xdist in parallel mode
    result = pytester.runpytest("--accept-copy", "-n", "2", "-v")

    # All tests should pass
    result.assert_outcomes(passed=4)

    # Check that .new files were created for both test files
    test_file1_new = pytester.path / "test_file1.py.new"
    test_file2_new = pytester.path / "test_file2.py.new"

    assert test_file1_new.exists()
    assert test_file2_new.exists()

    # Verify the assertions were fixed in both files
    with open(test_file1_new) as f:
        content = f.read()
        assert "assert 1 == 1" in content
        assert "assert 3 == 3" in content

    with open(test_file2_new) as f:
        content = f.read()
        assert "assert 5 == 5" in content
        assert "assert 7 == 7" in content


def test_global_state_isolation(pytester):
    """Test that global state doesn't cause issues with multiple workers"""
    # This tests that our global _current_session doesn't cause problems
    # when multiple workers are running

    try:
        import xdist  # noqa: F401
    except ImportError:
        pytest.skip("pytest-xdist not installed")

    # Create a test that might expose global state issues
    test_contents = """
import time
import random

def test_concurrent_1():
    # Add some randomness to execution order
    time.sleep(random.random() * 0.1)
    assert 1 == 2

def test_concurrent_2():
    time.sleep(random.random() * 0.1)
    assert 3 == 4

def test_concurrent_3():
    time.sleep(random.random() * 0.1)
    assert 5 == 6

def test_concurrent_4():
    time.sleep(random.random() * 0.1)
    assert 7 == 8
"""

    path = pytester.makepyfile(test_contents)

    # Run multiple times to increase chance of catching race conditions
    for i in range(3):
        result = pytester.runpytest("--accept-copy", "-n", "4", "-q")
        result.assert_outcomes(passed=4)

        # Check the file was correctly updated
        new_path = path.parent / (path.name + ".new")
        assert new_path.exists()

        with open(new_path) as f:
            content = f.read()
            assert "assert 1 == 1" in content
            assert "assert 3 == 3" in content
            assert "assert 5 == 5" in content
            assert "assert 7 == 7" in content

        # Clean up for next iteration
        new_path.unlink()


def test_stash_isolation_between_workers(pytester):
    """Test that StashKeys are properly isolated between workers"""
    try:
        import xdist  # noqa: F401
    except ImportError:
        pytest.skip("pytest-xdist not installed")

    # Create tests that might conflict if stashes aren't isolated
    test_contents = """
def test_worker_1():
    assert "worker1" == "wrong1"

def test_worker_2():
    assert "worker2" == "wrong2"

def test_worker_3():
    assert "worker3" == "wrong3"
"""

    path = pytester.makepyfile(test_contents)

    # Run with multiple workers
    result = pytester.runpytest("--accept-copy", "-n", "3")
    result.assert_outcomes(passed=3)

    # Verify all assertions were fixed correctly
    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    with open(new_path) as f:
        content = f.read()
        assert 'assert "worker1" == "worker1"' in content
        assert 'assert "worker2" == "worker2"' in content
        assert 'assert "worker3" == "worker3"' in content


def test_file_locking_with_concurrent_writes(pytester):
    """Test that concurrent writes to the same file don't corrupt it"""
    try:
        import xdist  # noqa: F401
    except ImportError:
        pytest.skip("pytest-xdist not installed")

    # Create a single file with multiple tests that will be distributed
    test_contents = """
def test_a():
    assert 1 == 2

def test_b():
    assert 3 == 4

def test_c():
    assert 5 == 6

def test_d():
    assert 7 == 8

def test_e():
    assert 9 == 10

def test_f():
    assert 11 == 12
"""

    path = pytester.makepyfile(test_contents)

    # Run with multiple workers on the same file
    result = pytester.runpytest("--accept-copy", "-n", "4", "-v")
    result.assert_outcomes(passed=6)

    # Check that the file was created and is not corrupted
    new_path = path.parent / (path.name + ".new")
    assert new_path.exists()

    # Read the file multiple times to ensure it's not corrupted
    for _ in range(3):
        with open(new_path) as f:
            content = f.read()

        # Verify all assertions were fixed
        assert "assert 1 == 1" in content
        assert "assert 3 == 3" in content
        assert "assert 5 == 5" in content
        assert "assert 7 == 7" in content
        assert "assert 9 == 9" in content
        assert "assert 11 == 11" in content

        # Verify structure is maintained
        assert "def test_a():" in content
        assert "def test_f():" in content
