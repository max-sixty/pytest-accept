# pytest-accept

This is a quick proof-of-concept for an inine expect-test pytest plugin. 
i.e. a plugin which replaces incorrect values in your test with correct values.

This saves you from copying & pasting results from the command line; instead letting you jump to reviewing the diff in version control.

## What it does

Given a test file like [test_test.py](pytest_accept/tests/test_test.py) containing a failing assertion:

```python
def test_x():

    assert 1 + 1 == 3

    assert 2 == 3
```

After running `pytest` from the `tests` path, a file [test_test.py.new](pytest_accept/tests/test_test.py) is written with the first result corrected:

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

...whether or not it overwrites the original file or creates a new file with a `.new` suffix is controlled by the
`OVERWRITE` constant in `conftest.py`.

## Current shortcomings

### Big ones

- It's limited to the first `assert` in each test, since execution stops after the first failure
  - We could use a specific function, like `expect(result, "abc")`, similar to frameworks like
    [rust's insta](https://github.com/mitsuhiko/insta) or [ocaml's ppx_expect](https://github.com/janestreet/ppx_expect).
  - Those have the disadvantage of coupling the test to the plugin: it's not possible to accept a result
    of a generic equality assertion, and not possible to run the test without the plugin installed.
  - [pytest-check](https://github.com/okken/pytest-check) does something similar for a different purpose
  - I had hoped that given's python dynamic-everything, we could continue
    after a failure. I need to do some more research on whether that's possible.
- It's limited to inline constants, and so doesn't support parameterization nor fixtures

### Not big ones

- It might format the inline value badly. But you can run an autoformatter on the resulting file anyway.
- It currently displays a failure like any other, while quietly rewriting the
  file in the background. But we can add decent command line reporting.
- It's not yet a plugin, and so can't be installed or enabled with a flag. But we can make it one.