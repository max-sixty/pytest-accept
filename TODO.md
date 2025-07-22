# pytest-accept TODO

## Known Issues

### pytest-xdist Compatibility

When running with pytest-xdist (`-n` option), not all assertions are being
corrected properly. Some assertions may be skipped due to race conditions when
multiple workers try to modify the same file. The plugin works correctly in
single-process mode but has issues with concurrent execution.

Example of the issue:
- Running `pytest --accept-copy -n 2` may result in only some assertions being corrected
- The test_concurrent_execution.py tests demonstrate this limitation
