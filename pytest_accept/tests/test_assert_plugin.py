import os
import pytest

def test_basic(pytester):
    test_contents = (
        "def test_x():\n"
        "    assert 1 == 3\n"
    )
    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--accept-copy")
    result.assert_outcomes(failed=1)

    with open(str(path) + ".new") as f:
        assert f.read() == test_contents.replace("1 == 3", "1 == 1")


def test_multiple_asserts(pytester, request):

    test_contents = (
        "def test_x():\n"
        "    assert 1 == 3\n"
        "    assert 2 == 3\n"
    )
    path = pytester.makepyfile(test_contents)

    @request.addfinalizer
    def _():
        try:
            os.remove(str(path) + ".new")
        except Exception:
            pass

    result = pytester.runpytest("--accept-copy")
    result.assert_outcomes(failed=1)

    with open(str(path) + ".new") as f:
        assert f.read() == test_contents.replace("1 == 3", "1 == 1").replace("2 == 3", "2 == 2")
