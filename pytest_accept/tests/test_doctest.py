"""
Unsurprisingly, these tests are in the form of doctests.
"""


def add_example():
    """

    Setup:

    >>> pytester = getfixture("pytester")
    >>> if sys.platform == "win32":
    ...     pytest.skip("Paths differ on windows")
    ...
    >>> pytester.copy_example("add.py")
    PosixPath('.../pytest_accept.tests.test_doctest.add_example0/add.py')

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

    (For some reason we need to delete the pyc file, TODO: work out why upstream
    >>> for f in pytester.path.glob(r"**/*.pyc"):
    ...     f.unlink()
    ...

    >>> result = pytester.runpytest("--doctest-modules", "--accept")
    =...
    add.py ...
    =... passed ...

    """


def no_overwrite_example():
    """

    pytest-accept won't overwrite the file if its contents change between the time of
    running the test and writing the generated values.

    >>> pytester = getfixture("pytester")

    >>> pytest.skip(
    ...     "I can't seem to work out a good way of testing this, since it "
    ...     "requires adjusting files midway through the test. So skipping for now."
    ... )

    >>> if sys.platform == "win32":
    ...     pytest.skip("Paths differ on windows")
    ...
    >>> path = pytester.copy_example("add.py")

    Collect the tests, to simulate starting the tests:
    >>> (item,), rec = pytester.inline_genitems("--doctest-modules", "--accept")
    ===...
    ...
    ===...
    >>> item
    <DoctestItem add.add>

    Now change the file:
    >>> path.open("w+").write(" ")
    1

    # TODO: Is there a way to run the test like this?
    # >>> item.runtest()
    # >>> item.runner.run()
    Now the file should _not_ be overwritten:
    >>> print((pytester.path / "add.py").read_text())

    """


def linebreak():
    """
    Setup:

    >>> pytester = getfixture("pytester")
    >>> pytester.copy_example("linebreak.py")
    PosixPath('.../pytest_accept.tests.test_doctest.linebreak0/linebreak.py')
    >>> result = pytester.runpytest("--doctest-modules", "--accept")
    ========================...
    linebreak.py F
    ...
    010     >>> add(1, 1)
    Expected:
        3
    Got:
        2
    ...
    013     >>> add("ab", "c")
    Expected:
        'cab'
    Got:
        'abc'
    ...
    ========================...
    FAILED linebreak.py::linebreak.add
    ========================...

    >>> pytest.xfail("The next test fails due to doctest's reporting of linebreaks.")

    >>> print((pytester.path / "linebreak.py").read_text())
    def add(x, y):
    ...>>> add(1, 1)
    2
    ...>>> add("ab", "c")
    'abc'
    ...
    """
