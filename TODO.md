# pytest-accept Testing Gaps

## Critical Gaps (High Priority)

### 1. Error Handling in Assertion Rewriting

- Test assertions with messages (`assert x == y, "msg"`)
- Test assertions with non-literal values
- Test assertions that can't be rewritten
- Verify appropriate logging/warnings are generated

### 2. File Change Detection During Test Run

- Test that files modified after collection are not overwritten
- Prevents data loss if user edits file while tests run

### 3. Non-Equality Operators

- Test assertions using `!=`, `<`, `>`, `<=`, `>=`, `is`, `in`
- Verify they fail normally without rewriting
- Consider adding user-friendly message about why not supported

### 4. Complex Assertion Messages

- Test assertions with custom failure messages
- Common pattern that currently skips rewriting silently

## Important Gaps (Medium Priority)

### 5. Concurrent Test Execution

- Test with pytest-xdist (`-n auto`)
- Verify no race conditions with global state
- Check StashKey isolation between workers

### 6. Edge Cases in Doctest Output Formatting

- Test very long lines (>1000 chars) get truncated
- Test very long outputs (>1000 lines) get shortened
- Prevents editor crashes

### 7. Multiple Doctest Failures in Same Example

- Test `MultipleDoctestFailures` handling
- Verify all failures in multi-failure doctest are corrected

### 8. AST Walking Edge Cases

- Test multiple assertions on same line
- Test when line numbers don't match exactly
- Ensure correct assertion is replaced

## Lower Priority Gaps

### 9. Invalid Python in Doctest Output

- Test doctest outputs that aren't valid Python
- Handle error tracebacks appropriately

### 10. File Encoding Issues

- Test non-UTF-8 files
- Test files with encoding declarations

### 11. Symlinks and Special Files

- Test behavior with symlinked test files
- Verify symlinks are preserved

### 12. Assertion Rewriter Patch Conflicts

- Test interaction with other pytest plugins
- Document any known incompatibilities
