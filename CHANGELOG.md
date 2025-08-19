# Changelog

## [0.2.2] - 2025-01-19

### Fixed

- Fixed compatibility with Python 3.13+ by using `ExceptHandler.name` instead of
  deprecated `identifier` attribute (#261) - @dlax
- Fixed handling of `!=` operators and exceptions in assert plugin (#262) -
  @dlax
- Fixed compatibility with environments that don't have pytest-xdist installed
  (#259)

## [0.2.1] - 2024-11-17

### Fixed

- Re-release of 0.2.0 to fix PyPI publishing workflow issue
- No functional changes from 0.2.0

## [0.2.0] - 2024-11-17

### Added

- **Major Feature**: pytest-accept now supports standard `assert` tests as well
  as doctests! (#242)
  - The plugin can now automatically update assertion values in regular pytest
    test functions
  - Works alongside the existing doctest functionality
  - Thanks to @untitaker for the inspiration

For earlier changes, please see the git history.
