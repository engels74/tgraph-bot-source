# DRY Consolidation Plan for Test Suite

## Executive Summary

### Goals
This document outlines a comprehensive plan to eliminate code duplication in the TGraph Bot test suite through systematic consolidation of repeated patterns. The primary objectives are:

- **Standardize test patterns** for configuration, mocking, and async operations
- **Improve maintainability** through centralized test utilities
- **Maintain type safety compliance** with 0 errors/warnings in `uvx basedpyright`

### User Guidelines (IMPORTANT!)

- Use `uv` or `uvx` for all Python commands (e.g., `uv run`, `uv run pytest`, `uv pip install`).
- Adhere to Python 3.13 best practices and leverage new typing features.
- Verify type safety using `uvx basedpyright` before commits.
- Install type stubs for dependencies (e.g., `uv pip install types-requests`) only when `basedpyright` reports missing stubs.
- Prefer `# pyright: ignore[specific-error]` over `# type: ignore` comments, always with specific error codes.
- **MANDATORY: Achieve exactly 0 errors and 0 warnings across ALL code including tests.** No exceptions—this prevents technical debt and ensures real issues aren't masked.
- **Fix type issues properly rather than using ignores.** Ignores are a last resort for unavoidable third-party limitations, not a shortcut for difficult typing.
- **NEVER use global configuration ignores.** Always use targeted per-line ignores (`# pyright: ignore[import-untyped]`) to maintain visibility of suppressed issues.
- Add brief inline comments for ignores only when the reason isn't immediately obvious (e.g., `# pyright: ignore[import-untyped] # third-party lib has no stubs`).
- Do not modify basedpyright rules in `pyproject.toml` to suppress issues—fix the root cause instead.
- Treat test files with the same type safety standards as production code.

## Current State Analysis

### Identified Duplication Patterns

#### High Impact Duplications
1. **TGraphBotConfig Creation** (8+ occurrences)
   - Files: `test_main.py`, `test_manager.py`, `test_config.py`, `test_end_to_end_customization.py`, `test_memory_management.py`, `test_non_blocking_graph_generation.py`
   - Pattern: Repeated creation of test configurations with similar field values

2. **ConfigManager Setup** (6+ occurrences)
   - Files: `test_main.py`, `test_manager.py`, `test_config.py`, `test_non_blocking_graph_generation.py`
   - Pattern: ConfigManager instantiation with mock configuration loading

3. **Temporary File Management** (6+ occurrences)
   - Files: `test_manager.py`, `test_base_graph.py`, `test_memory_management.py`, `test_recovery_and_schedule_integrity.py`
   - Pattern: NamedTemporaryFile and TemporaryDirectory creation with cleanup

#### Medium Impact Duplications
4. **Discord Bot Mocking** (5+ occurrences)
   - Files: `test_main.py`, `test_update_tracker_enhanced.py`, `test_non_blocking_graph_generation.py`
   - Pattern: MagicMock creation with user, guild, and channel attributes

5. **Discord Interaction Mocking** (4+ occurrences)
   - Files: `test_error_handler.py`, `test_config.py`
   - Pattern: Mock interaction objects with user, guild, channel, and command attributes

6. **AsyncMock Patterns** (6+ occurrences)
   - Files: `test_main.py`, `test_update_tracker_enhanced.py`, `test_error_handler.py`
   - Pattern: Async function mocking with patch decorators

#### Lower Impact Duplications
7. **Graph Factory Setup** (3+ occurrences)
   - Files: `test_base_graph.py`, `test_end_to_end_customization.py`, `test_memory_management.py`
   - Pattern: Graph factory creation and configuration

8. **Error Context Creation** (3+ occurrences)
   - Files: `test_error_handler.py`
   - Pattern: ErrorContext instantiation with similar parameters

## Detailed Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

#### Objective
Establish foundational test infrastructure with core fixtures and utilities that address the highest-impact duplications.

#### Subtask 1.1: Create Global Test Configuration
**Files Created**: `tests/conftest.py`

**Implementation Steps**:
- [x] Create `tests/conftest.py` file
- [x] Implement `base_config` fixture returning TGraphBotConfig with standard test values
- [x] Implement `minimal_config` fixture for tests requiring minimal configuration
- [x] Implement `comprehensive_config` fixture for tests requiring all configuration options
- [x] Add type annotations and docstrings for all fixtures

**Validation**:
- [x] Run `uvx basedpyright tests/conftest.py` to verify type safety
- [x] Import fixtures in existing test file to verify functionality

#### Subtask 1.2: Create Test Utilities Module
**Files Created**: `tests/utils/__init__.py`, `tests/utils/test_helpers.py`

**Implementation Steps**:
- [x] Create `tests/utils/` directory structure
- [x] Implement `create_config_manager_with_config` function
- [x] Implement `create_temp_config_file` context manager
- [x] Implement `create_temp_directory` context manager
- [x] Add comprehensive type annotations and error handling

**Validation**:
- [x] Run type safety verification on new utilities
- [x] Create simple test to verify utility functions work correctly

#### Subtask 1.3: Update Configuration-Heavy Test Files
**Files Modified**:
- `tests/unit/config/test_manager.py`
- `tests/unit/test_main.py`
- `tests/unit/bot/commands/test_config.py`

**Implementation Steps**:
- [x] Replace inline TGraphBotConfig creation with fixture usage in `test_manager.py`
- [x] Remove duplicate `temp_config_file` fixtures, use global version
- [x] Update `test_main.py` to use centralized configuration fixtures
- [x] Modify `test_config.py` to use standardized config manager setup
- [x] Remove redundant fixture definitions from individual files

**Validation**:
- [x] Run affected test files individually to ensure no regressions
- [x] Verify all tests pass with new fixture usage
- [x] Confirm type safety compliance for modified files

#### Subtask 1.4: Create Mock Object Utilities
**Files Modified**: `tests/utils/test_helpers.py`

**Implementation Steps**:
- [x] Add `create_mock_discord_bot` function with configurable attributes
- [x] Add `create_mock_interaction` function with optional parameters
- [x] Add `create_mock_user` and `create_mock_guild` helper functions
- [x] Implement parameter validation and default value handling

**Validation**:
- [x] Test mock creation functions with various parameter combinations
- [x] Verify mock objects have expected attributes and behaviors

### Phase 2: Async and Mock Consolidation (Week 2)

#### Objective
Consolidate async testing patterns and standardize mock object creation across all test files.

#### Subtask 2.1: Create Async Test Utilities
**Files Created**: `tests/utils/async_helpers.py`
**Files Modified**: `tests/conftest.py`

**Implementation Steps**:
- [x] Create async test base class with common setup methods
- [x] Implement async mock context managers for common patterns
- [x] Add async fixture for event loop management
- [x] Create utilities for async exception testing
- [x] Add async timeout helpers for long-running test operations

**Validation**:
- [x] Run async tests with new utilities to verify functionality
- [x] Test timeout and exception handling scenarios  
- [x] Verify async fixtures work correctly with pytest-asyncio
- [x] Achieve exactly 0 errors and 0 warnings with `uvx basedpyright`
- [x] All 22 tests pass with `uv run pytest`

#### Subtask 2.2: Update Async-Heavy Test Files
**Files Modified**:
- `tests/unit/test_main.py`
- `tests/unit/bot/test_update_tracker_enhanced.py`
- `tests/unit/utils/test_error_handler.py`
- `tests/integration/test_non_blocking_graph_generation.py`

**Implementation Steps**:
- [x] Replace inline AsyncMock patterns with utility functions in `test_main.py`
- [x] Consolidate async test setup in `test_update_tracker_enhanced.py`
- [x] Update error handler tests to use standardized async patterns
- [x] Modify integration tests to use centralized async utilities
- [x] Remove duplicate async setup code from individual files

**Validation**:
- [x] Run all async tests to ensure no timing issues or regressions
- [x] Verify async mock behavior matches original implementations
- [x] Test error handling in async scenarios

#### Subtask 2.3: Standardize Mock Object Usage
**Files Modified**:
- `tests/unit/utils/test_error_handler.py`
- `tests/unit/bot/commands/test_config.py`
- `tests/integration/test_non_blocking_graph_generation.py`

**Implementation Steps**:
- [x] Replace inline Discord interaction mocking with utility functions
- [x] Update bot mocking to use centralized mock creation
- [x] Standardize mock attribute setting across test files
- [x] Remove duplicate mock setup code
- [x] Ensure consistent mock behavior across all tests

**Validation**:
- [x] Verify mock objects have consistent attributes across tests
- [x] Test mock interactions behave as expected
- [x] Confirm no test behavior changes due to mock standardization

### Phase 3: Specialized Utilities (Week 3)

#### Objective
Address remaining duplication patterns and create specialized utilities for complex testing scenarios.

#### Subtask 3.1: Create Graph Testing Utilities
**Files Created**: `tests/utils/graph_helpers.py`
**Files Modified**:
- `tests/unit/graphs/graph_modules/test_base_graph.py`
- `tests/integration/test_end_to_end_customization.py`
- `tests/integration/test_memory_management.py`

**Implementation Steps**:
- [ ] Create graph factory setup utilities with configuration options
- [ ] Implement matplotlib cleanup helpers
- [ ] Add graph validation utilities for common assertions
- [ ] Create memory management helpers for graph testing
- [ ] Update graph-related tests to use new utilities

**Validation**:
- [ ] Run graph tests to ensure matplotlib resources are properly managed
- [ ] Verify graph creation and cleanup work correctly
- [ ] Test memory usage patterns with new utilities

#### Subtask 3.2: Create Specialized Test Fixtures
**Files Modified**: `tests/conftest.py`

**Implementation Steps**:
- [ ] Add fixtures for complex configuration scenarios
- [ ] Create fixtures for error testing scenarios
- [ ] Implement fixtures for schedule state testing
- [ ] Add fixtures for file system testing scenarios
- [ ] Document fixture usage patterns and dependencies

**Validation**:
- [ ] Test fixture combinations to ensure no conflicts
- [ ] Verify fixture cleanup works correctly
- [ ] Test fixture parameterization for multiple scenarios

#### Subtask 3.3: Final Consolidation and Cleanup
**Files Modified**: All remaining test files with duplication

**Implementation Steps**:
- [ ] Identify and consolidate remaining duplication patterns
- [ ] Update any missed test files to use centralized utilities
- [ ] Remove unused imports and fixture definitions
- [ ] Standardize test file structure and organization
- [ ] Add comprehensive documentation for test utilities

**Validation**:
- [ ] Run complete test suite to ensure no regressions
- [ ] Verify type safety compliance across all test files
- [ ] Confirm test execution time hasn't significantly increased
- [ ] Validate test coverage remains unchanged

## Testing Validation Strategy

### Continuous Validation
After each subtask:
- [ ] **Type Safety Check**: Run `uvx basedpyright tests/` to ensure 0 errors/warnings
- [ ] **Individual Test Execution**: Run modified test files individually
- [ ] **Integration Testing**: Run related test groups to check for interaction issues
- [ ] **Performance Monitoring**: Verify test execution time remains reasonable

### Phase Completion Validation
After each phase:
- [ ] **Full Test Suite**: Run `uvx pytest tests/` to ensure all tests pass
- [ ] **Coverage Analysis**: Verify test coverage hasn't decreased
- [ ] **Memory Usage**: Check for memory leaks in graph-related tests
- [ ] **Documentation Review**: Ensure all new utilities are properly documented

### Final Validation
After complete implementation:
- [ ] **Comprehensive Test Run**: Execute full test suite multiple times
- [ ] **Type Safety Verification**: Final basedpyright check on entire test directory
- [ ] **Performance Comparison**: Compare test execution time before/after changes
- [ ] **Code Review**: Review all changes for consistency and best practices
