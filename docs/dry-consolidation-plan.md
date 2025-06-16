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
1. Create `tests/conftest.py` file
2. Implement `base_config` fixture returning TGraphBotConfig with standard test values
3. Implement `minimal_config` fixture for tests requiring minimal configuration
4. Implement `comprehensive_config` fixture for tests requiring all configuration options
5. Add type annotations and docstrings for all fixtures

**Validation**:
- Run `uvx basedpyright tests/conftest.py` to verify type safety
- Import fixtures in existing test file to verify functionality

#### Subtask 1.2: Create Test Utilities Module
**Files Created**: `tests/utils/__init__.py`, `tests/utils/test_helpers.py`

**Implementation Steps**:
1. Create `tests/utils/` directory structure
2. Implement `create_config_manager_with_config` function
3. Implement `create_temp_config_file` context manager
4. Implement `create_temp_directory` context manager
5. Add comprehensive type annotations and error handling

**Validation**:
- Run type safety verification on new utilities
- Create simple test to verify utility functions work correctly

#### Subtask 1.3: Update Configuration-Heavy Test Files
**Files Modified**: 
- `tests/unit/config/test_manager.py`
- `tests/unit/test_main.py`
- `tests/unit/bot/commands/test_config.py`

**Implementation Steps**:
1. Replace inline TGraphBotConfig creation with fixture usage in `test_manager.py`
2. Remove duplicate `temp_config_file` fixtures, use global version
3. Update `test_main.py` to use centralized configuration fixtures
4. Modify `test_config.py` to use standardized config manager setup
5. Remove redundant fixture definitions from individual files

**Validation**:
- Run affected test files individually to ensure no regressions
- Verify all tests pass with new fixture usage
- Confirm type safety compliance for modified files

#### Subtask 1.4: Create Mock Object Utilities
**Files Modified**: `tests/utils/test_helpers.py`

**Implementation Steps**:
1. Add `create_mock_discord_bot` function with configurable attributes
2. Add `create_mock_interaction` function with optional parameters
3. Add `create_mock_user` and `create_mock_guild` helper functions
4. Implement parameter validation and default value handling

**Validation**:
- Test mock creation functions with various parameter combinations
- Verify mock objects have expected attributes and behaviors

### Phase 2: Async and Mock Consolidation (Week 2)

#### Objective
Consolidate async testing patterns and standardize mock object creation across all test files.

#### Subtask 2.1: Create Async Test Utilities
**Files Created**: `tests/utils/async_helpers.py`
**Files Modified**: `tests/conftest.py`

**Implementation Steps**:
1. Create async test base class with common setup methods
2. Implement async mock context managers for common patterns
3. Add async fixture for event loop management
4. Create utilities for async exception testing
5. Add async timeout helpers for long-running test operations

**Validation**:
- Run async tests with new utilities to verify functionality
- Test timeout and exception handling scenarios
- Verify async fixtures work correctly with pytest-asyncio

#### Subtask 2.2: Update Async-Heavy Test Files
**Files Modified**:
- `tests/unit/test_main.py`
- `tests/unit/bot/test_update_tracker_enhanced.py`
- `tests/unit/utils/test_error_handler.py`
- `tests/integration/test_non_blocking_graph_generation.py`

**Implementation Steps**:
1. Replace inline AsyncMock patterns with utility functions in `test_main.py`
2. Consolidate async test setup in `test_update_tracker_enhanced.py`
3. Update error handler tests to use standardized async patterns
4. Modify integration tests to use centralized async utilities
5. Remove duplicate async setup code from individual files

**Validation**:
- Run all async tests to ensure no timing issues or regressions
- Verify async mock behavior matches original implementations
- Test error handling in async scenarios

#### Subtask 2.3: Standardize Mock Object Usage
**Files Modified**:
- `tests/unit/utils/test_error_handler.py`
- `tests/unit/bot/commands/test_config.py`
- `tests/integration/test_non_blocking_graph_generation.py`

**Implementation Steps**:
1. Replace inline Discord interaction mocking with utility functions
2. Update bot mocking to use centralized mock creation
3. Standardize mock attribute setting across test files
4. Remove duplicate mock setup code
5. Ensure consistent mock behavior across all tests

**Validation**:
- Verify mock objects have consistent attributes across tests
- Test mock interactions behave as expected
- Confirm no test behavior changes due to mock standardization

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
1. Create graph factory setup utilities with configuration options
2. Implement matplotlib cleanup helpers
3. Add graph validation utilities for common assertions
4. Create memory management helpers for graph testing
5. Update graph-related tests to use new utilities

**Validation**:
- Run graph tests to ensure matplotlib resources are properly managed
- Verify graph creation and cleanup work correctly
- Test memory usage patterns with new utilities

#### Subtask 3.2: Create Specialized Test Fixtures
**Files Modified**: `tests/conftest.py`

**Implementation Steps**:
1. Add fixtures for complex configuration scenarios
2. Create fixtures for error testing scenarios
3. Implement fixtures for schedule state testing
4. Add fixtures for file system testing scenarios
5. Document fixture usage patterns and dependencies

**Validation**:
- Test fixture combinations to ensure no conflicts
- Verify fixture cleanup works correctly
- Test fixture parameterization for multiple scenarios

#### Subtask 3.3: Final Consolidation and Cleanup
**Files Modified**: All remaining test files with duplication

**Implementation Steps**:
1. Identify and consolidate remaining duplication patterns
2. Update any missed test files to use centralized utilities
3. Remove unused imports and fixture definitions
4. Standardize test file structure and organization
5. Add comprehensive documentation for test utilities

**Validation**:
- Run complete test suite to ensure no regressions
- Verify type safety compliance across all test files
- Confirm test execution time hasn't significantly increased
- Validate test coverage remains unchanged

## Testing Validation Strategy

### Continuous Validation
After each subtask:
1. **Type Safety Check**: Run `uvx basedpyright tests/` to ensure 0 errors/warnings
2. **Individual Test Execution**: Run modified test files individually
3. **Integration Testing**: Run related test groups to check for interaction issues
4. **Performance Monitoring**: Verify test execution time remains reasonable

### Phase Completion Validation
After each phase:
1. **Full Test Suite**: Run `uvx pytest tests/` to ensure all tests pass
2. **Coverage Analysis**: Verify test coverage hasn't decreased
3. **Memory Usage**: Check for memory leaks in graph-related tests
4. **Documentation Review**: Ensure all new utilities are properly documented

### Final Validation
After complete implementation:
1. **Comprehensive Test Run**: Execute full test suite multiple times
2. **Type Safety Verification**: Final basedpyright check on entire test directory
3. **Performance Comparison**: Compare test execution time before/after changes
4. **Code Review**: Review all changes for consistency and best practices
