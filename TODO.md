# Code Simplification TODOs

## High Priority

### 1. Replace Global Session with StashKey (Option 1C)
**Goal:** Eliminate `global _current_session` by accessing session through pytest's internal state

**Approach:** Since `item.session` exists, we need to find a way to access the current pytest item from within the assertion handler context.

**Options to investigate:**
- Walk the call stack with `sys._getframe()` to find pytest execution frame
- Check if pytest stores current item in thread-local storage
- Use `_pytest.reports` or `_pytest.runner` internals
- Consider if we can pass item context through the AST rewriter

**Files to change:**
- `pytest_accept/assert_plugin.py`: Remove `_current_session` global and `global` statements

### 2. ✅ COMPLETED: Collapse Wrapper Functions 
**Goal:** Remove thin wrapper functions in `__init__.py` that just delegate to plugin functions
**Status:** Successfully replaced wrapper functions with direct exports (`pytest_sessionstart = assert_sessionstart`)

### 3. ✅ COMPLETED: Eliminate Over-Abstraction 
**Goal:** Inline thin utility functions in `common.py`
**Status:** Successfully removed `get_accept_mode()` and `should_process_accepts()` wrapper functions, inlined option checking logic directly in plugin files

## Medium Priority

### 4. Simplify File Coordination
**Goal:** Reduce complexity of inter-plugin file change tracking

**Current complexity:**
- `files_modified_by_plugins_key` StashKey
- Complex `has_file_changed()` logic that considers plugin modifications
- Hash tracking across plugin boundaries

**Simpler approaches to evaluate:**
- Use file timestamps instead of content hashes
- Let each plugin write to separate temp files, merge at end
- Remove inter-plugin coordination entirely (each plugin checks original file only)

**Files to change:**
- `pytest_accept/common.py`: Simplify or remove `files_modified_by_plugins` tracking
- `pytest_accept/doctest_plugin.py`: Remove complex file coordination
- `pytest_accept/assert_plugin.py`: Remove complex file coordination

### 5. Eliminate Complex AST Manipulation Context
**Goal:** Stop threading session context through every function

**Current complexity:**
- `atomic_write(target_path, writer, session=None)` - session parameter everywhere
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

- Keep the multiple assertions per test functionality (don't simplify to first-assertion-only)
- Prioritize readability and maintainability over micro-optimizations
- Each simplification should include before/after line counts for impact measurement