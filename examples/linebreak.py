"""
Docstrings with line continuation characters should be handled correctly.
"""


def add(x, y):
    """
    Adds two \
        values.

    >>> add(1, 1)
    3

    >>> add("ab", "c")
    'cab'
    """

    return x + y
