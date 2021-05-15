# pytest-accept

pytest-accept replaces existing python doctest outputs with their results from
running the code. It'll save time and toil — rather than copying & pasting
results from the command line, you can jump to reviewing the diffs between
existing and proposed outputs in version control.

## What it does

Given a file like [**`test_add.py`**](pytest_accept/tests/test_add.py)
containing an incorrect output:

```python
def add(x, y):
    """
    Adds two values.

    >>> add(1, 1)
    3

    >>> add("ab", "c")
    'bac'
    """

    return x + y
```

Running doctests using pytest and passing `--accept` replaces the incorrect
values with correct values:

```sh
pytest --doctest-modules --accept
```

```diff
diff --git a/pytest_accept/tests/test_add.py b/pytest_accept/tests/test_add.py
index 10a71fd..c2c945f 100644
--- a/pytest_accept/tests/test_add.py
+++ b/pytest_accept/tests/test_add.py
@@ -3,10 +3,10 @@ def add(x, y):
     Adds two values.
 
     >>> add(1, 1)
-    3
+    2
 
     >>> add("ab", "c")
-    'bac'
+    'abc'
     """
 
     return x + y
```

## Installation

```sh
pip install pytest-accept
```

## Anything else?

Not really! Some things to watch out for:

- It will overwrite the existing values. These aren't generally useful — they're
  designed to match the results of the code. But if they're somehow important,
  passing `--accept-copy` will cause the plugin to instead create a file named
  `{file}.py.new`.
- It'll replace the file at the end of a test. So — to the extent there are
  useful changes to the file between the start and and the end of a test —
  it'll overwrite them.
  - TODO: Should we disable the plugin on `--pdb` as one way of long-running tests?
- This is early, and there are probably some small bugs. Let me know and I'll
  attempt to fix them.
- It currently doesn't affect the printing of results; the doctests will still
  print as failures.
  - TODO: A future version could print something about them being fixed.

## What about normal tests?

A previous effort in [**`assert_plugin.py`**](pytest_accept/assert_plugin.py)
attempted to do this for normal pytest `assert`s, and the file contains some
notes on the effort. The biggest problem is pytest stops on the first `assert`
failure in each test, which is very limiting. (Whereas pytest can be configured
to continue on doctest failures, which `doctest_plugin.py` does.)

It's [probably possible to change pytest's
behavior](https://mail.python.org/pipermail/pytest-dev/2020-March/004918.html)
here, but a significant project.

Some alternatives:

- Use an existing library like
  [pytest-regtest](https://gitlab.com/uweschmitt/pytest-regtest), which offers
  file snapshot testing (i.e. not inline).
- We could write a specific function / fixture, like `accept(result, "abc")`,
  similar to frameworks like [rust's insta](https://github.com/mitsuhiko/insta)
  or [ocaml's ppx_expect](https://github.com/janestreet/ppx_expect).
  - This would have the disadvantage of coupling the test to the plugin: it's
    not possible to run tests independently of the plugin, or use the plugin on
    general `assert` tests. And one of the great elegances of pytest is its
    deferral to a normal `assert` statement.

## What are these tests

<https://blog.janestreet.com/testing-with-expectations/>
