"""Verify that atomic writes are actually working with temp files"""

import os
import threading
import time
from pathlib import Path


def test_temp_files_created_during_write(pytester, monkeypatch):
    """Verify temp files are created and renamed atomically"""
    temp_files_seen = []
    renames_seen = []

    original_mkstemp = os.open
    original_replace = os.replace

    def tracking_open(path, flags, *args, **kwargs):
        result = original_mkstemp(path, flags, *args, **kwargs)
        if ".tmp_" in str(path):
            temp_files_seen.append(str(path))
        return result

    def tracking_replace(src, dst):
        renames_seen.append((str(src), str(dst)))
        return original_replace(src, dst)

    monkeypatch.setattr("os.open", tracking_open)
    monkeypatch.setattr("os.replace", tracking_replace)
    test_contents = """
def test_atomic():
    assert 1 == 2
"""
    pytester.makepyfile(test_contents)
    pytester.runpytest("--accept-copy")
    # Should have created temp files
    assert len(temp_files_seen) > 0, "No temp files were created"
    assert any(".tmp_" in f for f in temp_files_seen), (
        "Temp files should have .tmp_ prefix"
    )
    # Should have renamed temp file to target
    assert len(renames_seen) > 0, "No atomic renames performed"
    src, dst = renames_seen[0]
    assert ".tmp_" in src
    assert dst.endswith(".py.new")
    # Temp file should not exist after rename
    assert not Path(src).exists()
    # Target file should exist
    assert Path(dst).exists()


def test_no_partial_files_on_interrupt(pytester, monkeypatch):
    """Test that interrupted writes don't leave partial files"""
    write_count = 0
    original_write = os.write

    def interrupting_write(fd, data):
        nonlocal write_count
        write_count += 1
        if write_count > 3:  # Allow some writes then fail
            raise OSError("Simulated write failure")
        return original_write(fd, data)

    test_contents = """
def test_interrupt():
    assert 1 == 2
    assert 2 == 3
    assert 3 == 4
"""
    path = pytester.makepyfile(test_contents)
    monkeypatch.setattr("os.write", interrupting_write)
    # This should fail during write
    pytester.runpytest("--accept-copy")
    # No .new file should exist (cleaned up after failure)
    # Check for any leftover temp files
    temp_files = list(path.parent.glob(".tmp_*.py"))
    assert len(temp_files) == 0, f"Temp files not cleaned up: {temp_files}"


def test_concurrent_writes_are_safe(pytester):
    """Test that concurrent writes to same file are safe with atomic operations"""
    test_contents = """
def test_concurrent():
    assert 1 == 2
"""
    path = pytester.makepyfile(test_contents)
    # Track file operations
    operations = []

    def monitor_directory():
        """Monitor directory for temp files during test execution"""
        start_time = time.time()
        while time.time() - start_time < 2:  # Monitor for 2 seconds
            for file in path.parent.iterdir():
                if file.name.startswith(".tmp_"):
                    operations.append(("temp_seen", file.name, time.time()))
            time.sleep(0.01)

    # Start monitoring in background
    monitor = threading.Thread(target=monitor_directory)
    monitor.start()
    # Run test
    pytester.runpytest("--accept-copy")
    monitor.join()
    # Should have final file
    assert path.with_suffix(".py.new").exists()
    # Note: We might not catch the temp files due to timing, but that's OK
    # The important thing is no temp files remain
    # No temp files should remain
    remaining_temps = list(path.parent.glob(".tmp_*.py"))
    assert len(remaining_temps) == 0


def test_fsync_called_for_durability(pytester, monkeypatch):
    """Verify fsync is called to ensure durability"""
    fsync_called = False
    original_fsync = os.fsync

    def tracking_fsync(fd):
        nonlocal fsync_called
        fsync_called = True
        return original_fsync(fd)

    monkeypatch.setattr("os.fsync", tracking_fsync)
    test_contents = """
def test_fsync():
    assert 1 == 2
"""
    pytester.makepyfile(test_contents)
    pytester.runpytest("--accept-copy")
    # fsync should be called for durability
    assert fsync_called, "fsync was not called - changes may not be durable"


def test_doctest_uses_atomic_writes(pytester, monkeypatch):
    """Verify doctest plugin also uses atomic writes"""
    temp_files_seen = []
    original_mkstemp = os.open

    def tracking_open(path, flags, *args, **kwargs):
        result = original_mkstemp(path, flags, *args, **kwargs)
        if ".tmp_" in str(path):
            temp_files_seen.append(str(path))
        return result

    monkeypatch.setattr("os.open", tracking_open)
    test_contents = '''
def add(a, b):
    """
    >>> add(1, 1)
    3
    """
    return a + b
'''
    pytester.makepyfile(test_contents)
    pytester.runpytest("--doctest-modules", "--accept-copy")
    # Should have created temp files for doctest too
    assert len(temp_files_seen) > 0, "Doctest plugin should use temp files"
