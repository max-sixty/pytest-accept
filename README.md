# pytest-accept

[![GitHub Workflow CI Status](https://img.shields.io/github/actions/workflow/status/max-sixty/pytest-accept/test.yaml?branch=main&logo=github&style=for-the-badge)](https://github.com/max-sixty/pytest-accept/actions?query=workflow:test)
[![PyPI Version](https://img.shields.io/pypi/v/pytest-accept?style=for-the-badge)](https://pypi.python.org/pypi/pytest-accept/)
[![GitHub License](https://img.shields.io/github/license/max-sixty/pytest-accept?style=for-the-badge)](https://github.com/max-sixty/pytest-accept/blob/main/LICENSE)

pytest-accept is a pytest plugin for automatically updating outputs. It runs
along with pytest, observes the generated outputs, and writes them to the test's
documented outputs.

## Before

```python
def test_calculate_total():
    assert calculate_total([10, 20, 30], 0.1) == 55
    assert calculate_total([5, 5], 0.2) == 10
```

## After `pytest --accept`

```diff
def test_calculate_total():
-    assert calculate_total([10, 20, 30], 0.1) == 55
-    assert calculate_total([5, 5], 0.2) == 10
+    assert calculate_total([10, 20, 30], 0.1) == 66.0
+    assert calculate_total([5, 5], 0.2) == 12.0
```

pytest-accept is decoupled from the tests it works with — it can be used with
existing tests, and the tests it edits are no different from normal tests. It
works with both doctests and normal `assert` statements.

## Installation

```sh
uv tool install -U pytest-accept
```

Or with pip:

```sh
pip install pytest-accept
```

To run, just pass `--accept` to pytest:

```sh
pytest --accept
```

## Why?

- Often it's fairly easy to observe whether something is working by viewing the
  output it produces
- ...but often output is verbose, and copying and pasting the output into the
  test is tedious
- `pytest-accept` does the copying & pasting for you
- Similarly, lots of folks generally find writing any tests a bit annoying, and
  prefer to develop by "running the code and seeing if it works". This library
  aims to make testing a joyful part of that development loop

This style of testing is fairly well-developed in some languages, although still
doesn't receive the attention I think it deserves, and historically hasn't had
good support in python.

The best explanation I've seen on this testing style is from
**[@yminsky](https://github.com/yminsky)** in a
[Jane Street Blogpost](https://blog.janestreet.com/testing-with-expectations/).
**[@matklad](https://github.com/matklad)** also has an excellent summary in his
blog post [How to Test](https://matklad.github.io//2021/05/31/how-to-test.html).

## How it works

`pytest-accept`:

- Intercepts test failures from both doctests and assert statements
- Parses the files to understand where the documented values are
- Updates the documented values to match the generated values
- Writes everything back atomically

Things to know:

- **Simple comparisons only**: Assert rewriting only works with `==` comparisons
  against literals or simple expressions
- **Overwrite by default**: Pass `--accept-copy` to write to `.py.new` files
  instead.

<details>
<summary>Doctest quirks</summary>

Doctests are great for examples, but they have quirks

- Use raw strings for examples with backslashes:

  ```python
  r"""
  >>> print("\n")
  \n
  """
  ```

- We handle blank lines automatically:

  ```python
  """
  >>> print("one\n\ntwo")
  one
  <BLANKLINE>
  two
  """
  ```

- Really long outputs get truncated so they won't break your editor

</details>

## Prior art

This testing style goes by many names: "snapshot testing", "regression testing",
"expect testing", "literate testing", or "acceptance testing". Whatever the
name, the pattern is the same: write tests, see what they produce, accept what's
correct.

[@matklad](https://github.com/matklad) has an excellent overview in
[How to Test](https://matklad.github.io//2021/05/31/how-to-test.html). The
approach is well-established in many languages:

- [cram](https://bitheap.org/cram/) (command-line tests)
- [ppx_expect](https://github.com/janestreet/ppx_expect) (OCaml)
- [insta](https://github.com/mitsuhiko/insta) (Rust)

For more complex test scenarios, consider:

- [pytest-regtest](https://gitlab.com/uweschmitt/pytest-regtest) for file-based
  testing
- [syrupy](https://github.com/tophat/syrupy) for snapshot testing
- [pytest-insta](https://github.com/vberlier/pytest-insta) for insta-style
  review

thanks to [@untiaker](https://github.com/untitaker), who found how to expand the
original doctest solution into an approach that works with standard `assert`
statements.
