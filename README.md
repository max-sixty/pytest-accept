# pytest-accept

pytest-accept replaces existing doctest outputs with whatever running the input
returns.

Even if you don't change your approach to testing, it'll save you time and toil
when working with doctests — rather than copying & pasting results from the
command line, you can jump to reviewing the diffs between existing and proposed
outputs in version control.

## What it does

Given a file like [**`add.py`**](examples/add.py)
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

Running doctests using pytest and passing `--accept` replaces the existing
incorrect values with correct values:

```sh
pytest --doctest-modules examples/add.py --accept
```

```diff
diff --git a/examples/add.py b/examples/add.py
index 10a71fd..c2c945f 100644
--- a/examples/add.py
+++ b/examples/add.py
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

## Jesse, what the?

This style of testing is fairly well-developed in some languages, although still
doesn't receive the attention I think it deserves, and historically hasn't had
great support in python.

It changes testing from an annoyance, to an automatic way of running the check
you probably do anyway — run the code and see if the output looks reasonable.

Confusingly, it's referred to "Snapshot testing" or "Regression testing" or
"Expect testing". The best explanation I've seen on this testing style is from
Ron Minsky in a [Jane Street
Blogpost](https://blog.janestreet.com/testing-with-expectations/).

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
  similar to frameworks like rust's excellent
  [insta](https://github.com/mitsuhiko/insta) (which I materially contributed
  to). or [ocaml's ppx_expect](https://github.com/janestreet/ppx_expect).
  - But this has the disadvantage of coupling the test to the plugin: it's not
    possible to run tests independently of the plugin, or use the plugin on
    general `assert` tests. And one of the great elegances of pytest is its
    deferral to a normal `assert` statement.

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
