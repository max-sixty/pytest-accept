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
  - Should we disable the plugin on `--pdb` as one way of long-running tests?
- This is early, and there are probably some small bugs. Let me know and I'll
  attempt to fix them.
- It currently doesn't affect the printing of results; the doctests will still
  print as failures. A future version could print something about them being
  fixed.

## What about normal tests?

A previous effort in [**`assert_plugin.py`**](pytest_accept/assert_plugin.py)
attempted to do this for normal pytest `assert`s, and the files contains some
notes on the effort. The main issue is for `assert`s, pytest will stop on the
first failure in each test, which limits its usefulness. It's [probably possible
to change pytest's
behavior](https://mail.python.org/pipermail/pytest-dev/2020-March/004918.html)
here.
