import os


def test_basic(pytester):
    test_contents = "def test_x():\n    assert 1 == 3\n"
    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--accept-copy")
    result.assert_outcomes(passed=1)

    with open(str(path) + ".new") as f:
        assert f.read() == test_contents.replace("1 == 3", "1 == 1")


def test_neq(pytester):
    test_contents = "def test_x():\n    assert 1 != 1\n"
    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--accept-copy")
    result.assert_outcomes(failed=1)
    assert "FAILED test_neq.py::test_x - assert 1 != 1" in result.outlines

    assert not os.path.exists(str(path) + ".new")


def test_exception(pytester):
    test_contents = "def test_x():\n    assert [][1] == 0\n"
    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--accept-copy")
    result.assert_outcomes(failed=1)
    assert (
        "FAILED test_exception.py::test_x - IndexError: list index out of range"
        in result.outlines
    )

    assert not os.path.exists(str(path) + ".new")


def test_too_complex(pytester):
    test_contents = "import random\ndef test_x():\n    assert 10 == random.random()\n"
    path = pytester.makepyfile(test_contents)
    result = pytester.runpytest("--accept-copy")
    result.assert_outcomes(passed=1)

    assert not os.path.exists(str(path) + ".new")


def test_multiple_asserts(pytester):
    test_contents = "def test_x():\n    assert 1 == 3\n    assert 2 == 3\n"
    path = pytester.makepyfile(test_contents)

    result = pytester.runpytest("--accept-copy")
    result.assert_outcomes(passed=1)

    with open(str(path) + ".new") as f:
        assert f.read() == test_contents.replace("1 == 3", "1 == 1").replace(
            "2 == 3", "2 == 2"
        )
