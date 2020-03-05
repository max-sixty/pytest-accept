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

# OVERWRITE = True
OVERWRITE = False


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield

    if not call.excinfo or not isinstance(call.excinfo.value, AssertionError):
        return

    op, left, right = recent_failure.pop()
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
