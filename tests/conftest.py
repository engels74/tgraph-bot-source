"""
Global test configuration fixtures for TGraph Bot tests.

This module provides reusable pytest fixtures for creating TGraphBotConfig
instances with different levels of configuration for testing purposes.
All fixtures return properly typed and validated configuration objects.

Additionally provides async fixtures for event loop management and common
async testing patterns.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from collections.abc import AsyncGenerator, Coroutine, Generator
from datetime import datetime, timedelta
from pathlib import Path
from typing import TypedDict

import pytest

from src.tgraph_bot.config.schema import TGraphBotConfig


class AsyncTestContext(TypedDict):
    """Type definition for async test context dictionary."""
    background_tasks: set[asyncio.Task[object]]
    cleanup_tasks: list[Coroutine[object, object, object]]
    start_time: float


# == SPECIALIZED TEST FIXTURES ==


# Complex Configuration Scenarios
@pytest.fixture
def invalid_config_dict() -> dict[str, object]:
    """
    Create an invalid configuration dictionary for testing error scenarios.
    
    This fixture provides a configuration with various validation issues
    to test error handling and validation logic.
    
    Returns:
        dict[str, object]: Configuration dictionary with validation issues
    """
    return {
        # Missing required fields (TAUTULLI_API_KEY, DISCORD_TOKEN)
        "TAUTULLI_URL": "invalid-url-format",  # Invalid URL
        "CHANNEL_ID": "not-a-number",  # Invalid type
        "UPDATE_DAYS": -1,  # Negative value
        "FIXED_UPDATE_TIME": "25:99",  # Invalid time format
        "TV_COLOR": "not-a-color",  # Invalid color format
        "CONFIG_COOLDOWN_MINUTES": -5,  # Negative cooldown
    }


@pytest.fixture
def edge_case_config() -> TGraphBotConfig:
    """
    Create a configuration with edge case values for boundary testing.
    
    This fixture provides a configuration with values at the boundaries
    of valid ranges to test edge case handling.
    
    Returns:
        TGraphBotConfig: Configuration with edge case values
    """
    return TGraphBotConfig(
        # Required fields
        TAUTULLI_API_KEY="a",  # Minimal length
        TAUTULLI_URL="http://localhost",  # Minimal URL
        DISCORD_TOKEN="x" * 50,  # Minimal Discord token length
        CHANNEL_ID=1,  # Minimum valid Discord ID
        
        # Edge case values
        UPDATE_DAYS=1,  # Minimum
        KEEP_DAYS=1,  # Minimum
        TIME_RANGE_DAYS=1,  # Minimum
        FIXED_UPDATE_TIME="00:00",  # Midnight
        
        # All graphs disabled
        ENABLE_DAILY_PLAY_COUNT=False,
        ENABLE_PLAY_COUNT_BY_DAYOFWEEK=False,
        ENABLE_PLAY_COUNT_BY_HOUROFDAY=False,
        ENABLE_TOP_10_PLATFORMS=False,
        ENABLE_TOP_10_USERS=False,
        ENABLE_PLAY_COUNT_BY_MONTH=False,
        
        # Maximum cooldowns
        CONFIG_COOLDOWN_MINUTES=60,
        CONFIG_GLOBAL_COOLDOWN_SECONDS=300,
        UPDATE_GRAPHS_COOLDOWN_MINUTES=60,
        UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS=300,
        MY_STATS_COOLDOWN_MINUTES=60,
        MY_STATS_GLOBAL_COOLDOWN_SECONDS=300,
    )


@pytest.fixture
def maximum_config() -> TGraphBotConfig:
    """
    Create a configuration with maximum/extreme values for stress testing.
    
    This fixture provides a configuration with values at the high end
    of valid ranges to test system behavior under maximum load.
    
    Returns:
        TGraphBotConfig: Configuration with maximum values
    """
    return TGraphBotConfig(
        # Required fields with long values
        TAUTULLI_API_KEY="x" * 100,  # Long API key
        TAUTULLI_URL="https://very-long-domain-name.example.com:8181/api/v2",
        DISCORD_TOKEN="x" * 100,  # Long Discord token
        CHANNEL_ID=999999999999999999,  # Large Discord ID
        
        # Maximum reasonable values
        UPDATE_DAYS=30,  # Monthly updates
        KEEP_DAYS=365,  # Keep for a year
        TIME_RANGE_DAYS=365,  # Full year range
        
        # All graphs enabled with annotations
        ENABLE_DAILY_PLAY_COUNT=True,
        ENABLE_PLAY_COUNT_BY_DAYOFWEEK=True,
        ENABLE_PLAY_COUNT_BY_HOUROFDAY=True,
        ENABLE_TOP_10_PLATFORMS=True,
        ENABLE_TOP_10_USERS=True,
        ENABLE_PLAY_COUNT_BY_MONTH=True,
        
        ANNOTATE_DAILY_PLAY_COUNT=True,
        ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK=True,
        ANNOTATE_PLAY_COUNT_BY_HOUROFDAY=True,
        ANNOTATE_TOP_10_PLATFORMS=True,
        ANNOTATE_TOP_10_USERS=True,
        ANNOTATE_PLAY_COUNT_BY_MONTH=True,
        
        # Maximum cooldowns
        CONFIG_COOLDOWN_MINUTES=60,
        CONFIG_GLOBAL_COOLDOWN_SECONDS=300,
        UPDATE_GRAPHS_COOLDOWN_MINUTES=60,
        UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS=300,
        MY_STATS_COOLDOWN_MINUTES=60,
        MY_STATS_GLOBAL_COOLDOWN_SECONDS=300,
    )


# Error Testing Scenarios
@pytest.fixture
def mock_network_error() -> Exception:
    """
    Create a mock network error for testing error handling.
    
    Returns:
        Exception: A network-related exception for testing
    """
    return TimeoutError("Connection timeout after 30 seconds")


@pytest.fixture
def mock_api_error() -> Exception:
    """
    Create a mock API error for testing error handling.
    
    Returns:
        Exception: An API-related exception for testing
    """
    return Exception("API rate limit exceeded. Please try again in 60 seconds.")


@pytest.fixture
def mock_validation_error() -> Exception:
    """
    Create a mock validation error for testing error handling.
    
    Returns:
        Exception: A validation-related exception for testing
    """
    return ValueError("Invalid configuration value: CHANNEL_ID must be a positive integer")


@pytest.fixture
def error_test_scenarios() -> list[tuple[str, Exception, str]]:
    """
    Provide a list of error scenarios for parameterized testing.
    
    Returns:
        list[tuple[str, Exception, str]]: List of (name, exception, expected_pattern) tuples
    """
    return [
        ("timeout", TimeoutError("Request timeout"), "timeout"),
        ("api_limit", Exception("API rate limit exceeded"), "rate limit"),
        ("validation", ValueError("Invalid input"), "Invalid"),
        ("permission", PermissionError("Access denied"), "denied"),
        ("not_found", FileNotFoundError("File not found"), "not found"),
        ("connection", ConnectionError("Connection failed"), "Connection"),
    ]


# Schedule State Testing
@pytest.fixture
def basic_schedule_state_data() -> dict[str, object]:
    """
    Create basic schedule state data for testing.
    
    Returns:
        dict[str, object]: Basic schedule state data
    """
    now = datetime.now()
    return {
        "last_update": now.isoformat(),
        "next_update": (now + timedelta(days=7)).isoformat(),
        "consecutive_failures": 0,
        "last_failure": None,
        "is_running": False,
        "update_count": 5,
    }


@pytest.fixture
def corrupted_schedule_state_data() -> str:
    """
    Create corrupted schedule state data for testing error recovery.
    
    Returns:
        str: Corrupted JSON string
    """
    return '{ "last_update": "invalid-date", "next_update": incomplete'


@pytest.fixture
def schedule_state_with_failures() -> dict[str, object]:
    """
    Create schedule state data with failure scenarios for testing.
    
    Returns:
        dict[str, object]: Schedule state data with failures
    """
    now = datetime.now()
    return {
        "last_update": (now - timedelta(days=14)).isoformat(),
        "next_update": (now - timedelta(hours=2)).isoformat(),  # Missed update
        "consecutive_failures": 3,
        "last_failure": (now - timedelta(hours=1)).isoformat(),
        "is_running": False,
        "update_count": 2,
    }


@pytest.fixture
def schedule_config_data() -> dict[str, object]:
    """
    Create schedule configuration data for testing.
    
    Returns:
        dict[str, object]: Schedule configuration data
    """
    return {
        "update_days": 7,
        "fixed_update_time": "XX:XX",
        "max_consecutive_failures": 5,
        "failure_backoff_multiplier": 2.0,
    }


# File System Testing Scenarios
@pytest.fixture
def temp_config_file() -> Generator[Path, None, None]:
    """
    Create a temporary configuration file for testing.
    
    Yields:
        Path: Path to the temporary configuration file
    """
    with tempfile.NamedTemporaryFile(
        mode='w', 
        suffix='.yml', 
        delete=False
    ) as f:
        config_content = """
TAUTULLI_API_KEY: test_api_key
TAUTULLI_URL: http://localhost:8181/api/v2
DISCORD_TOKEN: test_discord_token
CHANNEL_ID: 123456789012345678
UPDATE_DAYS: 7
LANGUAGE: en
"""
        _ = f.write(config_content)
        f.flush()
        temp_path = Path(f.name)
    
    try:
        yield temp_path
    finally:
        if temp_path.exists():
            temp_path.unlink()


@pytest.fixture
def temp_data_directory() -> Generator[Path, None, None]:
    """
    Create a temporary data directory for testing.
    
    Yields:
        Path: Path to the temporary data directory
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        data_path = Path(temp_dir) / "data"
        _ = data_path.mkdir(exist_ok=True)
        yield data_path


@pytest.fixture
def temp_graph_output_directory() -> Generator[Path, None, None]:
    """
    Create a temporary directory for graph output testing.
    
    Yields:
        Path: Path to the temporary graph output directory
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "graphs" / "output"
        _ = output_path.mkdir(parents=True, exist_ok=True)
        yield output_path


@pytest.fixture
def mock_state_file(temp_data_directory: Path) -> Path:
    """
    Create a mock state file in the temporary data directory.
    
    Args:
        temp_data_directory: Temporary data directory fixture
        
    Returns:
        Path: Path to the mock state file
    """
    state_file = temp_data_directory / "scheduler_state.json"
    
    # Create a basic state file
    state_data = {
        "last_update": datetime.now().isoformat(),
        "next_update": (datetime.now() + timedelta(days=7)).isoformat(),
        "consecutive_failures": 0,
        "is_running": False,
    }
    
    with state_file.open('w') as f:
        _ = json.dump(state_data, f, indent=2)
    
    return state_file


@pytest.fixture
def file_permission_scenarios() -> list[tuple[str, int]]:
    """
    Provide file permission scenarios for testing.
    
    Returns:
        list[tuple[str, int]]: List of (scenario_name, permission_mode) tuples
    """
    return [
        ("read_only", 0o444),
        ("write_only", 0o222), 
        ("no_permissions", 0o000),
        ("execute_only", 0o111),
        ("full_permissions", 0o777),
    ]


# == EXISTING FIXTURES (Basic Configuration) ==

@pytest.fixture
def base_config() -> TGraphBotConfig:
    """
    Create a standard test configuration with commonly used values.
    
    This fixture provides a balanced configuration suitable for most tests
    that need a realistic but controlled configuration environment.
    
    Returns:
        TGraphBotConfig: A standard test configuration with typical values
    """
    return TGraphBotConfig(
        # Essential Settings (required)
        TAUTULLI_API_KEY="test_api_key_standard",
        TAUTULLI_URL="http://localhost:8181/api/v2",
        DISCORD_TOKEN="test_discord_token_1234567890",
        CHANNEL_ID=123456789012345678,
        
        # Timing and Retention (common test values)
        UPDATE_DAYS=7,
        FIXED_UPDATE_TIME="XX:XX",
        KEEP_DAYS=7,
        TIME_RANGE_DAYS=30,
        LANGUAGE="en",
        
        # Graph Options (balanced mix for testing)
        CENSOR_USERNAMES=True,
        ENABLE_GRAPH_GRID=False,
        ENABLE_DAILY_PLAY_COUNT=True,
        ENABLE_PLAY_COUNT_BY_DAYOFWEEK=True,
        ENABLE_PLAY_COUNT_BY_HOUROFDAY=True,
        ENABLE_TOP_10_PLATFORMS=True,
        ENABLE_TOP_10_USERS=True,
        ENABLE_PLAY_COUNT_BY_MONTH=True,
        
        # Graph Colors (default values)
        TV_COLOR="#1f77b4",
        MOVIE_COLOR="#ff7f0e",
        GRAPH_BACKGROUND_COLOR="#ffffff",
        ANNOTATION_COLOR="#ff0000",
        ANNOTATION_OUTLINE_COLOR="#000000",
        ENABLE_ANNOTATION_OUTLINE=True,
        
        # Annotation Options (enabled for testing)
        ANNOTATE_DAILY_PLAY_COUNT=True,
        ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK=True,
        ANNOTATE_PLAY_COUNT_BY_HOUROFDAY=True,
        ANNOTATE_TOP_10_PLATFORMS=True,
        ANNOTATE_TOP_10_USERS=True,
        ANNOTATE_PLAY_COUNT_BY_MONTH=True,
        
        # Command Cooldown Options (minimal for testing)
        CONFIG_COOLDOWN_MINUTES=0,
        CONFIG_GLOBAL_COOLDOWN_SECONDS=0,
        UPDATE_GRAPHS_COOLDOWN_MINUTES=0,
        UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS=0,
        MY_STATS_COOLDOWN_MINUTES=0,
        MY_STATS_GLOBAL_COOLDOWN_SECONDS=0,
    )


@pytest.fixture
def minimal_config() -> TGraphBotConfig:
    """
    Create a minimal test configuration with only required fields.
    
    This fixture provides the absolute minimum configuration needed
    for TGraphBotConfig validation. All optional fields use their
    default values. Ideal for testing core functionality without
    configuration complexity.
    
    Returns:
        TGraphBotConfig: A minimal configuration with only required fields set
    """
    return TGraphBotConfig(
        # Only the essential required settings
        TAUTULLI_API_KEY="test_api_key_minimal",
        TAUTULLI_URL="http://localhost:8181/api/v2",
        DISCORD_TOKEN="test_discord_token_minimal",
        CHANNEL_ID=123456789,
        # All other fields will use their default values from the schema
    )


@pytest.fixture
def comprehensive_config() -> TGraphBotConfig:
    """
    Create a comprehensive test configuration with all options explicitly set.
    
    This fixture provides a complete configuration with all available
    options set to non-default values where appropriate. Useful for
    testing edge cases, full feature integration, and configuration
    validation scenarios.
    
    Returns:
        TGraphBotConfig: A comprehensive configuration with all options set
    """
    return TGraphBotConfig(
        # Essential Settings
        TAUTULLI_API_KEY="test_api_key_comprehensive_full_featured",
        TAUTULLI_URL="https://tautulli.example.com:8181/api/v2",
        DISCORD_TOKEN="test_discord_token_comprehensive_1234567890abcdef",
        CHANNEL_ID=987654321098765432,
        
        # Timing and Retention (non-default values)
        UPDATE_DAYS=14,
        FIXED_UPDATE_TIME="02:30",
        KEEP_DAYS=30,
        TIME_RANGE_DAYS=90,
        LANGUAGE="es",
        
        # Graph Options (mixed settings for comprehensive testing)
        CENSOR_USERNAMES=False,
        ENABLE_GRAPH_GRID=True,
        ENABLE_DAILY_PLAY_COUNT=True,
        ENABLE_PLAY_COUNT_BY_DAYOFWEEK=False,
        ENABLE_PLAY_COUNT_BY_HOUROFDAY=True,
        ENABLE_TOP_10_PLATFORMS=False,
        ENABLE_TOP_10_USERS=True,
        ENABLE_PLAY_COUNT_BY_MONTH=False,
        
        # Graph Colors (custom colors for testing)
        TV_COLOR="#ff4444",
        MOVIE_COLOR="#44ff44",
        GRAPH_BACKGROUND_COLOR="#f8f8f8",
        ANNOTATION_COLOR="#4444ff",
        ANNOTATION_OUTLINE_COLOR="#222222",
        ENABLE_ANNOTATION_OUTLINE=False,
        
        # Annotation Options (mixed settings)
        ANNOTATE_DAILY_PLAY_COUNT=False,
        ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK=True,
        ANNOTATE_PLAY_COUNT_BY_HOUROFDAY=False,
        ANNOTATE_TOP_10_PLATFORMS=True,
        ANNOTATE_TOP_10_USERS=False,
        ANNOTATE_PLAY_COUNT_BY_MONTH=True,
        
        # Command Cooldown Options (realistic values for testing)
        CONFIG_COOLDOWN_MINUTES=10,
        CONFIG_GLOBAL_COOLDOWN_SECONDS=30,
        UPDATE_GRAPHS_COOLDOWN_MINUTES=15,
        UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS=60,
        MY_STATS_COOLDOWN_MINUTES=5,
        MY_STATS_GLOBAL_COOLDOWN_SECONDS=120,
    )


# Async Testing Fixtures

@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for async tests.
    
    This fixture ensures that each test gets a fresh event loop,
    preventing test interference and providing clean async test isolation.
    
    Yields:
        asyncio.AbstractEventLoop: A new event loop for the test
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        # Clean up any remaining tasks
        pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
        if pending_tasks:
            for task in pending_tasks:
                _ = task.cancel()
            # Give tasks a chance to clean up
            _ = loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
        
        # Close the loop
        loop.close()


@pytest.fixture
async def async_test_context() -> AsyncGenerator[AsyncTestContext, None]:
    """
    Provide async test context with common utilities.
    
    This fixture provides a context dictionary with utilities commonly
    needed in async tests, including task tracking and cleanup helpers.
    
    Yields:
        AsyncTestContext: Context dictionary with async test utilities
    """
    context: AsyncTestContext = {
        "background_tasks": set(),
        "cleanup_tasks": [],
        "start_time": asyncio.get_event_loop().time(),
    }
    
    try:
        yield context
    finally:
        # Clean up any background tasks
        if context["background_tasks"]:
            for task in context["background_tasks"]:
                if not task.done():
                    _ = task.cancel()
            
            # Wait for cancellation to complete
            _ = await asyncio.gather(*context["background_tasks"], return_exceptions=True)
        
        # Run any cleanup tasks
        if context["cleanup_tasks"]:
            _ = await asyncio.gather(*context["cleanup_tasks"], return_exceptions=True)


@pytest.fixture
def async_timeout() -> float:
    """
    Provide default timeout for async test operations.
    
    This fixture provides a consistent timeout value for async operations
    in tests, helping to prevent hanging tests while allowing sufficient
    time for operations to complete.
    
    Returns:
        float: Default timeout in seconds (10.0)
    """
    return 10.0


# == FIXTURE DOCUMENTATION ==

"""
Fixture Usage Patterns and Dependencies:

## Basic Configuration Fixtures
- base_config: Standard configuration for most tests
- minimal_config: Minimal configuration for core functionality tests  
- comprehensive_config: Full-featured configuration for integration tests

## Complex Configuration Scenarios
- invalid_config_dict: For testing validation error handling
- edge_case_config: For boundary value testing
- maximum_config: For stress testing with extreme values

## Error Testing Fixtures  
- mock_network_error: Simulates network timeouts and connection issues
- mock_api_error: Simulates API rate limiting and service errors
- mock_validation_error: Simulates input validation failures
- error_test_scenarios: Parameterized list of common error scenarios

## Schedule State Testing
- basic_schedule_state_data: Normal scheduling state for positive tests
- corrupted_schedule_state_data: Malformed data for error recovery tests
- schedule_state_with_failures: State with missed updates for recovery tests
- schedule_config_data: Configuration for schedule management tests

## File System Testing
- temp_config_file: Temporary configuration file with cleanup
- temp_data_directory: Temporary data directory for state files
- temp_graph_output_directory: Temporary directory for graph outputs
- mock_state_file: Pre-populated state file in temp directory
- file_permission_scenarios: Various file permission scenarios

## Dependencies
- temp_config_file depends on nothing
- mock_state_file depends on temp_data_directory
- All fixtures are independent unless explicitly documented
- Async fixtures (async_test_context) work with event_loop fixture

## Usage Examples
```python
def test_config_validation(invalid_config_dict):
    # Test validation error handling
    
def test_edge_cases(edge_case_config):
    # Test boundary conditions
    
@pytest.mark.parametrize("name,error,pattern", 
                        indirect=True, 
                        values=pytest.fixture.request.getfixturevalue('error_test_scenarios'))
def test_error_handling(name, error, pattern):
    # Parameterized error testing

def test_file_operations(temp_config_file, temp_data_directory):
    # Test file system operations with cleanup
```
"""
