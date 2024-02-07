import sys

import pytest


def test_ellipsis(pytester):

    if sys.platform == "win32":
        pytest.skip("Paths differ on windows")

    pytester.copy_example("ellipsis.py")

    result = pytester.runpytest("--doctest-modules", "--accept-copy")

    new_file = (pytester.path / "ellipsis.py.new").read_text()

    assert (
        new_file
        == """def negate(value: bool) -> bool:
    \"\"\"This function negates its input

    >>> negate(True)
    False
    \"\"\"

    return not value
"""
    )
