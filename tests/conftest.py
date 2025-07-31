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

from src.tgraph_bot.config.schema import (
    TGraphBotConfig,
    ServicesConfig,
    TautulliConfig,
    DiscordConfig,
    AutomationConfig,
    SchedulingConfig,
    DataRetentionConfig,
    DataCollectionConfig,
    TimeRangesConfig,
    PrivacyConfig,
    SystemConfig,
    LocalizationConfig,
    GraphsConfig,
    GraphFeaturesConfig,
    EnabledTypesConfig,
    GraphAppearanceConfig,
    ColorsConfig,
    GridConfig,
    AnnotationsConfig,
    BasicAnnotationsConfig,
    EnabledOnConfig,
    RateLimitingConfig,
    CommandsConfig,
    CommandCooldownConfig,
)


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
        "services": {
            # Missing required api_key
            "tautulli": {
                "url": "invalid-url-format",  # Invalid URL format
            },
            "discord": {
                # Missing required token
                "channel_id": "not-a-number",  # Invalid type
            },
        },
        "automation": {
            "scheduling": {
                "update_days": -1,  # Negative value
                "fixed_update_time": "25:99",  # Invalid time format
            },
        },
        "graphs": {
            "appearance": {
                "colors": {
                    "tv": "not-a-color",  # Invalid color format
                },
            },
        },
        "rate_limiting": {
            "commands": {
                "config": {
                    "user_cooldown_minutes": -5,  # Negative cooldown
                },
            },
        },
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
        services=ServicesConfig(
            tautulli=TautulliConfig(
                api_key="a",  # Minimal length
                url="http://localhost",  # Minimal URL
            ),
            discord=DiscordConfig(
                token="x" * 50,  # Minimal Discord token length
                channel_id=1,  # Minimum valid Discord ID
            ),
        ),
        automation=AutomationConfig(
            scheduling=SchedulingConfig(
                update_days=1,  # Minimum
                fixed_update_time="00:00",  # Midnight
            ),
            data_retention=DataRetentionConfig(
                keep_days=1,  # Minimum
            ),
        ),
        data_collection=DataCollectionConfig(
            time_ranges=TimeRangesConfig(
                days=1,  # Minimum
            ),
        ),
        graphs=GraphsConfig(
            features=GraphFeaturesConfig(
                enabled_types=EnabledTypesConfig(
                    daily_play_count=False,
                    play_count_by_dayofweek=False,
                    play_count_by_hourofday=False,
                    top_10_platforms=False,
                    top_10_users=False,
                    play_count_by_month=False,
                ),
            ),
        ),
        rate_limiting=RateLimitingConfig(
            commands=CommandsConfig(
                config=CommandCooldownConfig(
                    user_cooldown_minutes=60,
                    global_cooldown_seconds=300,
                ),
                update_graphs=CommandCooldownConfig(
                    user_cooldown_minutes=60,
                    global_cooldown_seconds=300,
                ),
                my_stats=CommandCooldownConfig(
                    user_cooldown_minutes=60,
                    global_cooldown_seconds=300,
                ),
            ),
        ),
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
        services=ServicesConfig(
            tautulli=TautulliConfig(
                api_key="x" * 100,  # Long API key
                url="https://very-long-domain-name.example.com:8181/api/v2",
            ),
            discord=DiscordConfig(
                token="x" * 100,  # Long Discord token
                channel_id=999999999999999999,  # Large Discord ID
            ),
        ),
        automation=AutomationConfig(
            scheduling=SchedulingConfig(
                update_days=30,  # Monthly updates
            ),
            data_retention=DataRetentionConfig(
                keep_days=365,  # Keep for a year
            ),
        ),
        data_collection=DataCollectionConfig(
            time_ranges=TimeRangesConfig(
                days=365,  # Full year range
            ),
        ),
        graphs=GraphsConfig(
            features=GraphFeaturesConfig(
                enabled_types=EnabledTypesConfig(
                    daily_play_count=True,
                    play_count_by_dayofweek=True,
                    play_count_by_hourofday=True,
                    top_10_platforms=True,
                    top_10_users=True,
                    play_count_by_month=True,
                ),
            ),
            appearance=GraphAppearanceConfig(
                annotations=AnnotationsConfig(
                    enabled_on=EnabledOnConfig(
                        daily_play_count=True,
                        play_count_by_dayofweek=True,
                        play_count_by_hourofday=True,
                        top_10_platforms=True,
                        top_10_users=True,
                        play_count_by_month=True,
                    ),
                ),
            ),
        ),
        rate_limiting=RateLimitingConfig(
            commands=CommandsConfig(
                config=CommandCooldownConfig(
                    user_cooldown_minutes=60,
                    global_cooldown_seconds=300,
                ),
                update_graphs=CommandCooldownConfig(
                    user_cooldown_minutes=60,
                    global_cooldown_seconds=300,
                ),
                my_stats=CommandCooldownConfig(
                    user_cooldown_minutes=60,
                    global_cooldown_seconds=300,
                ),
            ),
        ),
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
    return ValueError(
        "Invalid configuration value: CHANNEL_ID must be a positive integer"
    )


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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        config_content = """
services:
  tautulli:
    api_key: test_api_key
    url: http://localhost:8181/api/v2
  discord:
    token: test_discord_token
    channel_id: 123456789012345678

automation:
  scheduling:
    update_days: 7

system:
  localization:
    language: en
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

    with state_file.open("w") as f:
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
    return TGraphBotConfig.model_validate({
        "services": {
            "tautulli": {
                "api_key": "test_api_key_standard",
                "url": "http://localhost:8181/api/v2",
            },
            "discord": {
                "token": "test_discord_token_1234567890",
                "channel_id": 123456789012345678,
                "timestamp_format": "R",
                "ephemeral_message_delete_after": 30.0,
            },
        },
        "automation": {
            "scheduling": {
                "update_days": 7,
                "fixed_update_time": "XX:XX",
            },
            "data_retention": {
                "keep_days": 7,
            },
        },
        "data_collection": {
            "time_ranges": {
                "days": 30,
                "months": 12,
            },
            "privacy": {
                "censor_usernames": True,
            },
        },
        "system": {
            "localization": {
                "language": "en",
            },
        },
        "graphs": {
            "features": {
                "enabled_types": {
                    "daily_play_count": True,
                    "play_count_by_dayofweek": True,
                    "play_count_by_hourofday": True,
                    "top_10_platforms": True,
                    "top_10_users": True,
                    "play_count_by_month": True,
                },
                "media_type_separation": True,
                "stacked_bar_charts": True,
            },
            "appearance": {
                "dimensions": {
                    "width": 14,
                    "height": 8,
                    "dpi": 100,
                },
                "colors": {
                    "tv": "#1f77b4",
                    "movie": "#ff7f0e",
                    "background": "#ffffff",
                },
                "grid": {
                    "enabled": False,
                },
                "annotations": {
                    "basic": {
                        "color": "#ff0000",
                        "outline_color": "#000000",
                        "enable_outline": True,
                        "font_size": 10,
                    },
                    "enabled_on": {
                        "daily_play_count": True,
                        "play_count_by_dayofweek": True,
                        "play_count_by_hourofday": True,
                        "top_10_platforms": True,
                        "top_10_users": True,
                        "play_count_by_month": True,
                    },
                    "peaks": {
                        "enabled": True,
                        "color": "#ffcc00",
                        "text_color": "#000000",
                    },
                },
                "palettes": {
                    "play_count_by_hourofday": "",
                    "top_10_users": "",
                    "daily_play_count": "",
                    "play_count_by_dayofweek": "",
                    "top_10_platforms": "",
                    "play_count_by_month": "",
                },
            },
        },
        "rate_limiting": {
            "commands": {
                "config": {
                    "user_cooldown_minutes": 0,
                    "global_cooldown_seconds": 0,
                },
                "update_graphs": {
                    "user_cooldown_minutes": 0,
                    "global_cooldown_seconds": 0,
                },
                "my_stats": {
                    "user_cooldown_minutes": 0,
                    "global_cooldown_seconds": 0,
                },
            },
        },
    })


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
    return TGraphBotConfig.model_validate({
        "services": {
            "tautulli": {
                "api_key": "test_api_key_minimal",
                "url": "http://localhost:8181/api/v2",
            },
            "discord": {
                "token": "test_discord_token_minimal",
                "channel_id": 123456789,
            },
        },
        # All other sections will use their default values from the schema
    })


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
        services=ServicesConfig(
            tautulli=TautulliConfig(
                api_key="test_api_key_comprehensive_full_featured",
                url="https://tautulli.example.com:8181/api/v2",
            ),
            discord=DiscordConfig(
                token="test_discord_token_comprehensive_1234567890abcdef",
                channel_id=987654321098765432,
            ),
        ),
        automation=AutomationConfig(
            scheduling=SchedulingConfig(
                update_days=14,
                fixed_update_time="02:30",
            ),
            data_retention=DataRetentionConfig(
                keep_days=30,
            ),
        ),
        data_collection=DataCollectionConfig(
            time_ranges=TimeRangesConfig(
                days=90,
            ),
            privacy=PrivacyConfig(
                censor_usernames=False,
            ),
        ),
        system=SystemConfig(
            localization=LocalizationConfig(
                language="es",
            ),
        ),
        graphs=GraphsConfig(
            features=GraphFeaturesConfig(
                enabled_types=EnabledTypesConfig(
                    daily_play_count=True,
                    play_count_by_dayofweek=False,
                    play_count_by_hourofday=True,
                    top_10_platforms=False,
                    top_10_users=True,
                    play_count_by_month=False,
                ),
            ),
            appearance=GraphAppearanceConfig(
                colors=ColorsConfig(
                    tv="#ff4444",
                    movie="#44ff44",
                    background="#f8f8f8",
                ),
                grid=GridConfig(
                    enabled=True,
                ),
                annotations=AnnotationsConfig(
                    basic=BasicAnnotationsConfig(
                        color="#4444ff",
                        outline_color="#222222",
                        enable_outline=False,
                    ),
                    enabled_on=EnabledOnConfig(
                        daily_play_count=False,
                        play_count_by_dayofweek=True,
                        play_count_by_hourofday=False,
                        top_10_platforms=True,
                        top_10_users=False,
                        play_count_by_month=True,
                    ),
                ),
            ),
        ),
        rate_limiting=RateLimitingConfig(
            commands=CommandsConfig(
                config=CommandCooldownConfig(
                    user_cooldown_minutes=10,
                    global_cooldown_seconds=30,
                ),
                update_graphs=CommandCooldownConfig(
                    user_cooldown_minutes=15,
                    global_cooldown_seconds=60,
                ),
                my_stats=CommandCooldownConfig(
                    user_cooldown_minutes=5,
                    global_cooldown_seconds=120,
                ),
            ),
        ),
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
            _ = loop.run_until_complete(
                asyncio.gather(*pending_tasks, return_exceptions=True)
            )

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
            _ = await asyncio.gather(
                *context["background_tasks"], return_exceptions=True
            )

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


# == EXPANDED ERROR TESTING FIXTURES (DRY Improvement) ==


@pytest.fixture
def common_error_scenarios() -> list[tuple[str, type[Exception], str]]:
    """
    Common error scenarios for parameterized testing.

    This fixture consolidates common error patterns across the test suite,
    reducing redundancy in error testing setups.

    Returns:
        List of tuples containing (scenario_name, exception_type, error_pattern)
    """
    return [
        ("type_error_bot", TypeError, "Expected TGraphBot instance"),
        ("type_error_config", TypeError, "Expected.*Config.*instance"),
        ("value_error_invalid", ValueError, "Invalid value"),
        ("value_error_range", ValueError, "out of range"),
        ("validation_error_missing", Exception, "Field required"),
        ("validation_error_type", Exception, "Input should be"),
        ("file_not_found", FileNotFoundError, "No such file"),
        ("permission_denied", PermissionError, "Permission denied"),
        ("connection_error", ConnectionError, "Failed to connect"),
        ("timeout_error", TimeoutError, "Timed out"),
    ]


@pytest.fixture
def config_validation_scenarios() -> list[tuple[str, dict[str, object], str]]:
    """
    Configuration validation error scenarios.

    Provides standardized invalid configuration scenarios for testing
    configuration validation across different components.

    Returns:
        List of tuples containing (scenario_name, invalid_config_data, expected_error_pattern)
    """
    return [
        (
            "missing_api_key",
            {"DISCORD_TOKEN": "test", "CHANNEL_ID": 123},
            "TAUTULLI_API_KEY.*required",
        ),
        (
            "missing_token",
            {"TAUTULLI_API_KEY": "test", "CHANNEL_ID": 123},
            "DISCORD_TOKEN.*required",
        ),
        (
            "invalid_url",
            {
                "TAUTULLI_URL": "not-a-url",
                "TAUTULLI_API_KEY": "test",
                "DISCORD_TOKEN": "test",
                "CHANNEL_ID": 123,
            },
            "Invalid URL",
        ),
        (
            "negative_days",
            {
                "UPDATE_DAYS": -1,
                "TAUTULLI_API_KEY": "test",
                "DISCORD_TOKEN": "test",
                "CHANNEL_ID": 123,
            },
            "greater than 0",
        ),
        (
            "invalid_time",
            {
                "FIXED_UPDATE_TIME": "25:99",
                "TAUTULLI_API_KEY": "test",
                "DISCORD_TOKEN": "test",
                "CHANNEL_ID": 123,
            },
            "Invalid time format",
        ),
        (
            "invalid_color",
            {
                "TV_COLOR": "not-a-color",
                "TAUTULLI_API_KEY": "test",
                "DISCORD_TOKEN": "test",
                "CHANNEL_ID": 123,
            },
            "Invalid color",
        ),
        (
            "negative_cooldown",
            {
                "CONFIG_COOLDOWN_MINUTES": -5,
                "TAUTULLI_API_KEY": "test",
                "DISCORD_TOKEN": "test",
                "CHANNEL_ID": 123,
            },
            "greater than or equal to 0",
        ),
    ]


@pytest.fixture
def mock_error_scenarios() -> list[tuple[str, Exception, str]]:
    """
    Mock-related error scenarios for testing error handling.

    Provides standardized mock exception scenarios for testing
    error handling patterns across different components.

    Returns:
        List of tuples containing (scenario_name, exception_instance, expected_log_pattern)
    """
    return [
        (
            "network_timeout",
            ConnectionError("Connection timed out"),
            "Connection.*timed out",
        ),
        ("api_error", RuntimeError("API returned error 500"), "API.*error.*500"),
        ("json_decode", ValueError("Invalid JSON"), "Invalid JSON"),
        (
            "file_permission",
            PermissionError("Permission denied writing file"),
            "Permission denied",
        ),
        ("memory_error", MemoryError("Out of memory"), "Out of memory"),
        ("runtime_error", RuntimeError("User interrupted"), "User interrupted"),
    ]
