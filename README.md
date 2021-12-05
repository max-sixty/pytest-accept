# pytest-accept

[![GitHub Workflow CI Status](https://img.shields.io/github/workflow/status/max-sixty/pytest-accept/Test?logo=github&style=for-the-badge)](https://github.com/max-sixty/pytest-accept/actions?query=workflow:test)
[![PyPI Version](https://img.shields.io/pypi/v/pytest-accept?style=for-the-badge)](https://pypi.python.org/pypi/pytest-accept/)
[![GitHub License](https://img.shields.io/github/license/max-sixty/pytest-accept?style=for-the-badge)](https://github.com/max-sixty/pytest-accept/blob/main/LICENSE)

pytest-accept is a pytest plugin for automatically updating doctest outputs. It
runs doctests, observes the generated outputs, and writes them to the doctests'
documented outputs.

It's designed for a couple of use cases:

- People who work with doctests and don't enjoy manually copying generated
  outputs from the pytest error log and pasting them into their doctests'
  documented outputs. pytest-accept does the copying & pasting for you.
- People who generally find writing tests a bit annoying, and prefer to develop
  by "running the code and seeing whether it works". This library aims to make
  testing a joyful part of that development loop.

pytest-accept is decoupled from the doctests it works with — it can be used with
existing doctests, and the doctests it edits are no different from normal
doctests.

## Jesse, what the?

Here's an example of pytest-accept does: given a file like
[**`add.py`**](examples/add.py) containing an incorrect documented output:

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

...running doctests using pytest and passing `--accept` replaces the existing
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

This style of testing is fairly well-developed in some languages, although still
doesn't receive the attention I think it deserves, and historically hasn't had
good support in python.

Confusingly, it's referred to "snapshot testing" or "regression testing" or
"expect testing" or "literate testing" or "acceptance testing". The best
explanation I've seen on this testing style is from Ron Minsky in a [Jane Street
Blogpost](https://blog.janestreet.com/testing-with-expectations/). @matklad
also has an excellent summary in his blog post [How to
Test](https://matklad.github.io//2021/05/31/how-to-test.html).

## Installation

```sh
pip install pytest-accept
```

## What about normal tests?

A previous effort in [**`assert_plugin.py`**](pytest_accept/assert_plugin.py)
attempted to do this for `assert` statements, and the file contains some notes
on the effort. The biggest problem is pytest stops on the first `assert` failure
in each test, which is very limiting. (Whereas pytest can be configured to
continue on doctest failures, which this library takes advantage of.)

It's [probably possible to change pytest's
behavior](https://mail.python.org/pipermail/pytest-dev/2020-March/004918.html)
here, but it's a significant effort on the pytest codebase.

Some alternatives:

- Use an existing library like
  [pytest-regtest](https://gitlab.com/uweschmitt/pytest-regtest), which offers
  file snapshot testing (i.e. not inline).
- We could write a specific function / fixture, like `accept(result, "abc")`,
  similar to frameworks like rust's excellent
  [insta](https://github.com/mitsuhiko/insta) (which I developed some features
  for), or [ocaml's ppx_expect](https://github.com/janestreet/ppx_expect).
  - But this has the disadvantage of coupling the test to the plugin: it's not
    possible to run tests independently of the plugin, or use the plugin on
    general `assert` tests. And one of the great elegances of pytest is its
    deferral to a normal `assert` statement.
- Some of this testing feels like writing a notebook and testing that.
  [pytest-notebook](https://github.com/chrisjsewell/pytest-notebook) fully
  implements this.

## Anything else?

Nothing ground-breaking! Some notes:

- If a docstring uses escape characters such as `\n`, python will interpret them
  as the escape character rather than the literal. Use a raw string to have it
  interpreted as a literal. e.g. this fails:

    ```python
    def raw_string():
        """
        >>> "\n"
        '\n'
        """
    ```

    but succeeds with:

    ```diff
    def raw_string():
    -    """
    +    r"""
        >>> "\n"
        '\n'
     ```

  Possibly pytest-accept could do more here — e.g. change the format of the
  docstring. But that would not be trivial to implement, and may be too
  invasive.
- The library attempts to confirm the file hasn't changed between the start and
  end of the test and won't overwrite the file where it detects there's been a
  change. This can be helpful for workflows where the tests run repeatedly in
  the background (e.g. using something like
  [watchexec](https://github.com/watchexec/watchexec)) while a person is working
  on the file, or when the tests take a long time, maybe because of `--pdb`. To
  be doubly careful, passing `--accept-copy` will cause the plugin to instead
  create a file named `{file}.py.new` rather than overwriting the file on any
  doctest failure.
  - It will overwrite the existing documented values, though these aren't
    generally useful per se — they're designed to match the generated of the
    code. The only instances they could be useful is where they've been manual
    curated (e.g. removing volatile outputs like hashes), and in those cases
    ideally they can be restored from version control. Or as above, pass
    `--accept-copy` to be conservative.
- This is still fairly early, has mostly been used by me &
  [xarray](https://github.com/pydata/xarray/pull/5950#issuecomment-974687406)
  and there may be some small bugs. Let me know anything at all and I'll attempt
  to fix them.
- It currently doesn't affect the printing of test results; the doctests will
  still print as failures.
  - TODO: A future version could print something about them being fixed.
- Python's doctest library is imperfect:
  - It can't handle indents, and probably other things.
    - We modify the output to match the doctest format; e.g. with blanklines. If
      generated output isn't sufficient for the doctest to pass, and there is
      some form of output that's sufficient, please report as a bug.
  - The syntax for `.*` is an ellipsis `...`, which is also the syntax for
    continuing a code line, so the beginning of a line must always be specified.
  - The syntax for all the directives is arguably less than aesthetically
    pleasing.
  - It doesn't have an option for pretty printing, so the test must pretty print
    itself with `pprint(x)`, which is verbose.
  - It reports line numbers incorrectly in some cases — two docstring lines
    separated with continuation character `\` is counted as one, meaning this
    library will not have access to the correct line number for doctest inputs
    and outputs.
