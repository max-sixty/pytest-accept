import pytest

pytest_plugins = ["pytester"]


@pytest.fixture(autouse=True)
def add_standard_imports(doctest_namespace):
    doctest_namespace["pytest"] = pytest
    import sys

    doctest_namespace["sys"] = sys
