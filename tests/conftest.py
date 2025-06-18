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
from collections.abc import AsyncGenerator, Coroutine, Generator
from typing import TypedDict

import pytest

from config.schema import TGraphBotConfig


class AsyncTestContext(TypedDict):
    """Type definition for async test context dictionary."""
    background_tasks: set[asyncio.Task[object]]
    cleanup_tasks: list[Coroutine[object, object, object]]
    start_time: float


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
