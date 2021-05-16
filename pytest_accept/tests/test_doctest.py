def plugin():
    """

    Setup:

    >>> pytester = getfixture("pytester")
    >>> pytester.copy_example("add.py")
    PosixPath(...pytest_accept.tests.test_doctest.plugin0/add.py')

    Running the first time fails:

    >>> result = pytester.runpytest("--doctest-modules", "--accept")
    ========================...
    add.py F
    ...
    005     >>> add(1, 1)
    Expected:
        3
    Got:
        2
    ...
    008     >>> add("ab", "c")
    Expected:
        'cab'
    Got:
        'abc'
    ...
    ========================...
    FAILED add.py::add.add
    ========================...

    But since we ran with `--accept`, the file has now changed to have correct values:

    >>> print((pytester.path / "add.py").read_text())
    def add(x, y):
    ...>>> add(1, 1)
    2
    ...>>> add("ab", "c")
    'abc'
    ...

    And the tests now pass:

    # (For some reason we need to delete the pyc file, TODO: work out why upstream)
    >>> (pytester.path / "__pycache__/add.cpython-38.pyc").unlink()

    >>> result = pytester.runpytest("--doctest-modules", "--accept")
    =...
    add.py .                                                                                                                                                                   [100%]
    =... 1 passed ...

    """
