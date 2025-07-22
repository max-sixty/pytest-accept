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

### 5. ✅ COMPLETED: Simplify session parameter threading

**Goal:** Stop threading session context through every function

**Status:** Partially completed - removed `session` parameter from
`atomic_write`

**What was done:**

- Removed `session` parameter from `atomic_write` function
- Removed `files_modified_by_plugins_key` usage and tracking
- Simplified the atomic write logic

**Remaining:**

- `track_file_hash(path, session)` and `has_file_changed(path, session)` still
  use session parameter
- These are harder to eliminate as they need access to the session stash for
  file hash tracking

## Low Priority

### 6. ✅ COMPLETED: Remove Legacy StashKeys

**Goal:** Remove unused StashKeys

**Status:** Completed - removed 3 legacy StashKeys

**What was done:**

- Removed `failed_doctests_key` (unused after unified change handling)
- Removed `files_modified_by_plugins_key` (no longer needed)
- Removed `asts_modified_key` (unused)

**Remaining StashKeys (all necessary):**

- `file_changes_key` - Stores all file changes from both plugins
- `file_hashes_key` - Tracks file hashes to detect changes
- `recent_failure_key` - Tracks assertion comparison data temporarily
- `intercept_assertions_key` - Boolean flag for whether to intercept assertions

**Assessment:** The remaining 4 StashKeys serve distinct purposes and
consolidating them would reduce code clarity.

### 7. Hook Count Assessment (NOT VIABLE)

**Goal:** Reduce plugin hook count by combining hooks

**Assessment:** NOT VIABLE - Each hook serves a specific purpose at a different
phase of pytest's lifecycle:

- `pytest_assertrepr_compare` - Called during assertion evaluation
- `pytest_sessionstart` - Sets up global session and patches AST rewriter
- `pytest_collection_modifyitems` - Tracks file hashes during collection
- `pytest_sessionfinish` - Writes all file changes at end

Combining these would break functionality as they need to run at specific times
in pytest's lifecycle.

## Notes

- Keep the multiple assertions per test functionality (don't simplify to
  first-assertion-only)
- Prioritize readability and maintainability over micro-optimizations
- Each simplification should include before/after line counts for impact
  measurement
