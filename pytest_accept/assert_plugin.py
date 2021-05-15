"""
This isn't ready for general use yet; here was the Readme before shelving it in exchange
for focusing on doctests initially.

# pytest-accept

This is a quick proof-of-concept for an inline expect-test pytest plugin. i.e. a
plugin which replaces incorrect values in your test with correct values.

This saves you from copying & pasting results from the command line; instead
letting you jump to reviewing the diff in version control.

## What it does

Given a test file like [test_test.py](pytest_accept/tests/test_test.py)
containing a failing assertion:

```python
def test_x():

    assert 1 + 1 == 3

    assert 2 == 3
```

After running `pytest` from the `tests` path, a file
[test_test.py.new](pytest_accept/tests/test_test.py) is written with the first
result corrected:

```diff
diff --git a/test_test.py b/test_test.py.new
index c704339..697e266 100644
--- a/test_test.py
+++ b/test_test.py.new
@@ -1,5 +1,5 @@
 def test_x():

-    assert 1 + 1 == 3
+    assert 1 + 1 == 2

     assert 2 == 3
```

...whether or not it overwrites the original file or creates a new file with a
`.new` suffix is controlled by the `OVERWRITE` constant in `conftest.py`.

## Current shortcomings

### Big ones

- It's limited to the first `assert` in each test, since execution stops after
  the first failure
  - We could use a specific function, like `expect(result, "abc")`, similar to
    frameworks like [rust's insta](https://github.com/mitsuhiko/insta) or
    [ocaml's ppx_expect](https://github.com/janestreet/ppx_expect).
  - Those have the disadvantage of coupling the test to the plugin: it's not
    possible to accept a result of a generic equality assertion, and not
    possible to run the test without the plugin installed.
  - [pytest-check](https://github.com/okken/pytest-check) does something similar
    for a different purpose
  - I had hoped that given's python dynamic-everything, we could continue after
    a failure. I need to do some more research on whether that's possible.
- It's limited to inline constants, and so doesn't support parameterization nor
  fixtures

### Not big ones

- It might format the inline value badly. But you can run an autoformatter on
  the resulting file anyway.
- It currently displays a failure like any other, while quietly rewriting the
  file in the background. But we can add decent command line reporting.
- It's not yet a plugin, and so can't be installed or enabled with a flag. But
  we can make it one.
"""


import ast
import copy
import logging
from collections import defaultdict
from typing import Dict, List, Tuple

import astor
import pytest

logger = logging.getLogger(__name__)

# Dict of {path: list of (location, new code)}
asts_modified: Dict[str, List[Tuple[slice, str]]] = defaultdict(list)

OVERWRITE = False


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield

    if not call.excinfo or not isinstance(call.excinfo.value, AssertionError):
        return

    op, left, _ = recent_failure.pop()
    if op != "==":
        logger.debug(f"{item.nodeid} does not assert equality, and won't be replaced")

    tb_entry = call.excinfo.traceback[0]
    # not exactly sure why +1, but in tb_entry.__repr__
    line_number_start = tb_entry.lineno + 1
    line_number_end = line_number_start + len(tb_entry.statement.lines) - 1
    original_location = slice(line_number_start, line_number_end)

    path = tb_entry.path
    tree = ast.parse(path.read())

    for item in ast.walk(tree):
        if isinstance(item, ast.Assert) and original_location.start == item.lineno:
            # we need to _then_ check that the next compare item's
            # ops[0] is Eq and then replace the comparator[0]
            assert item.msg is None
            assert len(item.test.comparators) == 1
            assert len(item.test.ops) == 1
            assert isinstance(item.test.ops[0], ast.Eq)

            new_assert = copy.copy(item)
            new_assert.test.comparators[0] = ast.Constant(value=left)

    asts_modified[path].append((original_location, new_assert))
    return outcome.get_result()


recent_failure: List[Tuple] = []


def pytest_assertrepr_compare(config, op, left, right):

    recent_failure.append((op, left, right))


def pytest_sessionfinish(session, exitstatus):

    for path, new_asserts in asts_modified.items():
        original = list(open(path).readlines())
        # sort by line number
        new_asserts = sorted(new_asserts, key=lambda x: x[0].start)

        file = open(path + (".new" if not OVERWRITE else ""), "w+")

        for i, line in enumerate(original):
            line_no = i + 1
            if not new_asserts:
                file.write(line)
            else:
                location, code = new_asserts[0]
                if not (location.start <= line_no <= location.stop):
                    file.write(line)
                elif line_no == location.start:
                    indent = line[: len(line) - len(line.lstrip())]
                    source = astor.to_source(code).splitlines(keepends=True)
                    for j in source:
                        file.write(indent + j)
                elif line_no == location.stop:
                    new_asserts.pop(0)
