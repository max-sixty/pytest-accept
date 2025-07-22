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
import sys
from pathlib import Path

import pytest
from _pytest._code.code import ExceptionInfo

from . import (
    AssertChange,
    file_changes_key,
    intercept_assertions_key,
    recent_failure_key,
)
from .common import (
    track_file_hash,
)

logger = logging.getLogger(__name__)

# StashKey to store session reference in config for access during assertion handling
session_ref_key = pytest.StashKey["pytest.Session"]()

# StashKey-based state tracking replaces global dictionaries

_ASSERTION_HANDLER = ast.parse(
    """
__import__("pytest_accept").assert_plugin.__handle_failed_assertion()
"""
).body


def _patch_assertion_rewriter():
    # I'm so sorry.
    # This monkey-patches pytest's private assertion rewriter to wrap all assertions in try-except blocks.

    from _pytest.assertion.rewrite import AssertionRewriter

    old_visit_assert = AssertionRewriter.visit_Assert

    def new_visit_assert(self, assert_):
        rv = old_visit_assert(self, assert_)

        # Add simple safety check - if there are too many AST nodes, skip wrapping
        # This prevents "too many statically nested blocks" errors in edge cases
        total_nodes = sum(1 for _ in ast.walk(ast.Module(body=rv)))
        if total_nodes > 200:  # Higher threshold - only skip for very complex cases
            # module_path is an internal pytest attribute that may not exist in all versions
            if hasattr(self, "module_path"):
                logger.warning(
                    f"Skipping accept mode for a complex assertion in {self.module_path}. "
                    f"This assertion will fail normally and won't be auto-corrected. "
                    f"To fix: simplify the assertion or manually update the expected value."
                )
            # Return original without wrapping to avoid "too many nested blocks"
            return rv

        try_except = ast.Try(
            body=rv,
            handlers=[
                ast.ExceptHandler(
                    expr=AssertionError,
                    identifier="__pytest_accept_e",
                    body=_ASSERTION_HANDLER,
                )
            ],
            orelse=[],
            finalbody=[],
        )

        ast.copy_location(try_except, assert_)
        for node in ast.iter_child_nodes(try_except):
            ast.copy_location(node, assert_)

        return [try_except]

    AssertionRewriter.visit_Assert = new_visit_assert


def __handle_failed_assertion():
    raw_excinfo = sys.exc_info()
    if raw_excinfo is None:
        return

    # Try to get the current test item from the call stack
    import inspect

    for frame_info in inspect.stack():
        frame_locals = frame_info.frame.f_locals
        # Walking up stack frames is inherently uncertain - check if item has session
        if "item" in frame_locals and hasattr(frame_locals["item"], "session"):
            session = frame_locals["item"].session
            __handle_failed_assertion_impl(raw_excinfo, session)
            if session.stash.get(intercept_assertions_key, False):
                return
            break

    # If we couldn't intercept, re-raise
    raise


def __handle_failed_assertion_impl(raw_excinfo, session):
    excinfo = ExceptionInfo.from_exc_info(raw_excinfo)

    recent_failure = session.config.stash.setdefault(recent_failure_key, [])
    if not recent_failure:
        return

    op, left, _ = recent_failure.pop()
    if op != "==":
        logger.debug("does not assert equality, and won't be replaced")
        return

    tb_entry = excinfo.traceback[0]
    # not exactly sure why +1, but in tb_entry.__repr__
    line_number_start = tb_entry.lineno + 1
    line_number_end = line_number_start + len(tb_entry.statement.lines) - 1
    original_location = slice(line_number_start, line_number_end)

    path = tb_entry.path
    with path.open() as f:
        tree = ast.parse(f.read())

    for item in ast.walk(tree):
        if isinstance(item, ast.Assert) and original_location.start == item.lineno:
            # we need to _then_ check that the next compare item's
            # ops[0] is Eq and then replace the comparator[0]
            try:
                assert item.msg is None
                assert len(item.test.comparators) == 1
                assert len(item.test.ops) == 1
                assert isinstance(item.test.ops[0], ast.Eq)

                ast.literal_eval(item.test.comparators[0])
            except Exception:
                continue

            new_assert = copy.copy(item)
            new_assert.test.comparators[0] = ast.Constant(value=left)

            # Submit change to unified change collection
            file_changes = session.stash.setdefault(file_changes_key, {})
            if path not in file_changes:
                file_changes[path] = []
            file_changes[path].append(
                AssertChange(
                    priority=1,  # Assert changes run first
                    location=original_location,
                    ast_node=new_assert,
                )
            )


def pytest_assertrepr_compare(config, op, left, right):
    # Store in config stash since session might not be available yet
    recent_failure = config.stash.setdefault(recent_failure_key, [])
    recent_failure.append((op, left, right))


def pytest_sessionstart(session):
    # Store session reference in config for access during assertion handling
    session.config.stash[session_ref_key] = session

    # Always intercept assertions when using --accept or --accept-copy
    intercept_assertions = bool(
        session.config.getoption("--accept")
        or session.config.getoption("--accept-copy")
    )
    session.stash[intercept_assertions_key] = intercept_assertions

    # Patch the assertion rewriter if needed
    if intercept_assertions:
        _patch_assertion_rewriter()


def pytest_collection_modifyitems(session, config, items):
    """Track file hashes during collection"""
    if session.config.getoption("--accept") or session.config.getoption(
        "--accept-copy"
    ):
        seen_files = set()
        for item in items:
            # Different test types (e.g., doctests) may have different attributes
            if hasattr(item, "fspath") and item.fspath not in seen_files:
                path = Path(item.fspath)
                if path.exists():
                    track_file_hash(path, session)
                    seen_files.add(item.fspath)


# pytest_sessionfinish removed - unified writer handles all file operations
