# Code Simplification TODOs

## High Priority

### 1. Replace Global Session with StashKey (Option 1C)

**Goal:** Eliminate `global _current_session` by accessing session through
pytest's internal state

**Approach:** Since `item.session` exists, we need to find a way to access the
current pytest item from within the assertion handler context.

**Options to investigate:**

- Walk the call stack with `sys._getframe()` to find pytest execution frame
- Check if pytest stores current item in thread-local storage
- Use `_pytest.reports` or `_pytest.runner` internals
- Consider if we can pass item context through the AST rewriter

**Files to change:**

- `pytest_accept/assert_plugin.py`: Remove `_current_session` global and
  `global` statements

### 2. ✅ COMPLETED: Collapse Wrapper Functions

**Goal:** Remove thin wrapper functions in `__init__.py` that just delegate to
plugin functions **Status:** Successfully replaced wrapper functions with direct
exports (`pytest_sessionstart = assert_sessionstart`)

### 3. ✅ COMPLETED: Eliminate Over-Abstraction

**Goal:** Inline thin utility functions in `common.py` **Status:** Successfully
removed `get_accept_mode()` and `should_process_accepts()` wrapper functions,
inlined option checking logic directly in plugin files

## Medium Priority

### 4. ✅ COMPLETED: Simplify File Coordination

**Goal:** Reduce complexity of inter-plugin file change tracking

**Status:** Successfully implemented unified change handling system that
eliminates inter-plugin coordination complexity

**What was done:**

- Created unified `Change` dataclass and `file_changes_key` StashKey
- Both plugins now submit changes to single collection instead of separate
  stashes
- Single unified writer in `__init__.py` handles both assert and doctest changes
- Eliminated `files_modified_by_plugins_key` complexity and coordination logic
- Natural priority ordering ensures assert changes (priority=1) run before
  doctest changes (priority=2)

**Unified Change Handling Approach (✅ IMPLEMENTED):**

Instead of each plugin writing files independently, both plugins submit changes
to a unified change collector:

```python
# Single StashKey for all file changes
file_changes_key = pytest.StashKey[dict[Path, list[Change]]]()


@dataclass
class Change:
    plugin: str  # "assert" or "doctest"
    data: Any  # AST changes or doctest failures
    priority: int  # assert=1, doctest=2 (assert runs first)
```

**Benefits:**

- Eliminates `files_modified_by_plugins_key` complexity
- Removes duplicate file change detection logic
- Single unified writer handles all file operations
- Natural ordering: assert changes applied before doctest changes
- Simpler testing: one place to verify file write logic

**Implementation:**

- Assert plugin:
  `session.stash.setdefault(file_changes_key, {}).setdefault(path, []).append(Change("assert", ast_change, 1))`
- Doctest plugin:
  `session.stash.setdefault(file_changes_key, {}).setdefault(path, []).append(Change("doctest", failure, 2))`
- Unified writer: Sort changes by priority, apply all changes to each file in
  one atomic write

**Files to change:**

- `pytest_accept/common.py`: Simplify or remove `files_modified_by_plugins`
  tracking
- `pytest_accept/doctest_plugin.py`: Remove complex file coordination
- `pytest_accept/assert_plugin.py`: Remove complex file coordination

### 5. Eliminate Complex AST Manipulation Context

**Goal:** Stop threading session context through every function

**Current complexity:**

- `atomic_write(target_path, writer, session=None)` - session parameter
  everywhere
- `track_file_hash(path, session)` - session parameter everywhere
- `has_file_changed(path, session)` - session parameter everywhere

**Simpler approach:**

- Each pytest hook already receives the session/item/config it needs
- Stop trying to pass session context to utility functions
- Inline more logic directly in the hooks where session is naturally available

**Files to change:**

- `pytest_accept/common.py`: Remove session parameters from utilities
- `pytest_accept/assert_plugin.py`: Handle more logic directly in hooks
- `pytest_accept/doctest_plugin.py`: Handle more logic directly in hooks

## Low Priority

### 6. Consolidate StashKey Definitions

**Goal:** Group related StashKeys and reduce total number

**Current keys:**

- `failed_doctests_key`
- `file_hashes_key`
- `files_modified_by_plugins_key`
- `asts_modified_key`
- `recent_failure_key`
- `intercept_assertions_key`

**Potential consolidation:**

- Combine file-related keys into single `file_state_key`
- Combine assertion-related keys into single `assertion_state_key`

### 7. Reduce Plugin Hook Count

**Goal:** Combine hooks where possible

**Current hooks per plugin:**

- Assert plugin: 4 hooks
- Doctest plugin: 5 hooks
- Init wrapper: 3 additional hooks

**Consider:**

- Can collection and session hooks be combined?
- Do we need separate `pytest_sessionstart` and `pytest_sessionfinish`?

## Notes

- Keep the multiple assertions per test functionality (don't simplify to
  first-assertion-only)
- Prioritize readability and maintainability over micro-optimizations
- Each simplification should include before/after line counts for impact
  measurement
