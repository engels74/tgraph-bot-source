"""
Test utilities package for TGraph Bot tests.

This package provides comprehensive utilities and helper functions for testing
TGraph Bot functionality. It includes utilities for configuration management,
temporary file handling, async testing, graph testing, and common test patterns.

The utilities are designed to eliminate code duplication across test files
while maintaining type safety and proper resource management.

## Available Modules

### test_helpers.py
Core test utilities for configuration and file management:
- `create_config_manager_with_config()`: Create ConfigManager with pre-set configuration
- `create_temp_config_file()`: Context manager for temporary YAML config files
- `create_temp_directory()`: Context manager for temporary directories
- `create_mock_discord_bot()`: Create standardized mock Discord bot instances
- `create_mock_user()`: Create mock Discord user objects
- `create_mock_guild()`: Create mock Discord guild objects
- `create_mock_interaction()`: Create mock Discord interaction objects

### async_helpers.py
Async testing utilities and patterns:
- `AsyncTestBase`: Base class for async test patterns with setup/teardown
- `async_mock_context()`: Context manager for async mocking with AsyncMock
- `async_discord_bot_context()`: Context manager for Discord bot mocking
- `assert_raises_async()`: Assert that async operations raise expected exceptions
- `wait_for_condition()`: Wait for conditions to become true with timeout
- Event loop management and async timeout helpers

### graph_helpers.py
Graph-specific testing utilities and matplotlib management:
- `create_test_config_minimal()`: Minimal config for graph testing
- `create_memory_test_graph()`: Graph instances for memory testing
- `create_graph_factory_with_config()`: Factory setup with test config
- `matplotlib_cleanup()`: Context manager for matplotlib resource cleanup
- `assert_graph_cleanup()`: Assertions for graph resource cleanup
- `create_mock_graph_data()`: Mock data for graph generation

## Usage Examples

### Basic Configuration Testing
```python
from tests.utils import create_config_manager_with_config
from tests.conftest import base_config

config = base_config()
manager = create_config_manager_with_config(config)
```

### Temporary File Testing
```python
from tests.utils.test_helpers import create_temp_config_file

with create_temp_config_file({"DISCORD_TOKEN": "test"}) as config_path:
    # Use config_path for testing
    pass
```

### Async Testing
```python
from tests.utils.async_helpers import async_mock_context

async with async_mock_context('module.async_function') as mock_func:
    # Test async functionality
    pass
```

### Graph Testing
```python
from tests.utils.graph_helpers import matplotlib_cleanup, create_memory_test_graph

with matplotlib_cleanup():
    test_graph = create_memory_test_graph()
    # Test graph functionality
```

## Design Principles

1. **Type Safety**: All utilities include comprehensive type annotations
2. **Resource Management**: Proper cleanup with context managers
3. **Error Handling**: Robust error handling with informative messages
4. **Consistency**: Standardized patterns across all utilities
5. **Documentation**: Clear docstrings and usage examples
6. **Testability**: Utilities are themselves tested for reliability

## Testing the Utilities

The test utilities themselves are tested in:
- `tests/unit/utils/test_test_helpers.py`
- `tests/unit/utils/test_async_helpers.py`
- `tests/unit/utils/test_graph_helpers.py`

This ensures the utilities are reliable and behave correctly.
"""

from __future__ import annotations

# Core test utilities
from .test_helpers import (
    create_config_manager_with_config,
    create_temp_config_file,
    create_temp_directory,
    create_mock_discord_bot,
    create_mock_user,
    create_mock_guild,
    create_mock_interaction,
)

# Async testing utilities
from .async_helpers import (
    AsyncTestBase,
    async_mock_context,
    async_discord_bot_context,
    assert_raises_async,
    wait_for_condition,
)

# Graph testing utilities
from .graph_helpers import (
    create_test_config_minimal,
    create_memory_test_graph,
    create_graph_factory_with_config,
    matplotlib_cleanup,
    assert_graph_cleanup,
    create_mock_graph_data,
)

__all__ = [
    # Core utilities
    "create_config_manager_with_config",
    "create_temp_config_file",
    "create_temp_directory",
    "create_mock_discord_bot",
    "create_mock_user",
    "create_mock_guild",
    "create_mock_interaction",
    # Async utilities
    "AsyncTestBase",
    "async_mock_context",
    "async_discord_bot_context",
    "assert_raises_async",
    "wait_for_condition",
    # Graph utilities
    "create_test_config_minimal",
    "create_memory_test_graph",
    "create_graph_factory_with_config",
    "matplotlib_cleanup",
    "assert_graph_cleanup",
    "create_mock_graph_data",
]
