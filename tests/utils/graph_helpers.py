"""
Graph testing utilities for TGraph Bot tests.

This module provides specialized utilities for testing graph-related functionality,
including graph factory setup, matplotlib resource management, memory management
helpers, and graph validation utilities.

All utilities are designed with type safety and proper error handling in mind,
following Python 3.13 best practices and maintaining 0 type errors/warnings.
"""

from __future__ import annotations

import gc
import tempfile
from abc import ABC
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager

from typing import TYPE_CHECKING, Any, override
from unittest.mock import MagicMock, patch

import matplotlib.pyplot as plt
import psutil

if TYPE_CHECKING:
    from graphs.graph_modules.base_graph import BaseGraph
    from graphs.graph_modules.graph_factory import GraphFactory
    from config.schema import TGraphBotConfig


def create_test_config_comprehensive() -> TGraphBotConfig:
    """
    Create a comprehensive test configuration with all customization options.
    
    This function provides a standardized comprehensive configuration for tests
    that need to validate all customization features and options.
    
    Returns:
        TGraphBotConfig: Comprehensive configuration with all options enabled
        
    Example:
        >>> config = create_test_config_comprehensive()
        >>> assert config.ENABLE_DAILY_PLAY_COUNT is True
        >>> assert config.TV_COLOR == "#2e86ab"
    """
    from config.schema import TGraphBotConfig
    
    return TGraphBotConfig(
        TAUTULLI_API_KEY="test_api_key_comprehensive",
        TAUTULLI_URL="http://localhost:8181/api/v2",
        DISCORD_TOKEN="test_discord_token_comprehensive",
        CHANNEL_ID=123456789,
        
        # Timing and retention
        UPDATE_DAYS=14,
        KEEP_DAYS=21,
        TIME_RANGE_DAYS=60,
        
        # Graph feature toggles
        ENABLE_DAILY_PLAY_COUNT=True,
        ENABLE_PLAY_COUNT_BY_DAYOFWEEK=True,
        ENABLE_PLAY_COUNT_BY_HOUROFDAY=True,
        ENABLE_PLAY_COUNT_BY_MONTH=True,
        ENABLE_TOP_10_PLATFORMS=True,
        ENABLE_TOP_10_USERS=True,
        
        # Visual customizations
        TV_COLOR="#2E86AB",
        MOVIE_COLOR="#A23B72",
        GRAPH_BACKGROUND_COLOR="#F8F9FA",
        ANNOTATION_COLOR="#C73E1D",
        ANNOTATION_OUTLINE_COLOR="#FFFFFF",
        
        # Graph options
        ENABLE_GRAPH_GRID=True,
        CENSOR_USERNAMES=True,
        ENABLE_ANNOTATION_OUTLINE=True,
        
        # Annotation controls
        ANNOTATE_DAILY_PLAY_COUNT=True,
        ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK=True,
        ANNOTATE_PLAY_COUNT_BY_HOUROFDAY=True,
        ANNOTATE_TOP_10_PLATFORMS=True,
        ANNOTATE_TOP_10_USERS=True,
        ANNOTATE_PLAY_COUNT_BY_MONTH=True,
    )


def create_test_config_minimal() -> TGraphBotConfig:
    """
    Create a minimal test configuration with only required fields.
    
    This function provides a standardized minimal configuration for tests
    that focus on core functionality without customization features.
    
    Returns:
        TGraphBotConfig: Minimal configuration with defaults
        
    Example:
        >>> config = create_test_config_minimal()
        >>> assert config.TAUTULLI_API_KEY == "test_api_key_minimal"
        >>> assert config.TV_COLOR == "#1f77b4"  # Default value
    """
    from config.schema import TGraphBotConfig
    
    return TGraphBotConfig(
        TAUTULLI_API_KEY="test_api_key_minimal",
        TAUTULLI_URL="http://localhost:8181/api/v2",
        DISCORD_TOKEN="test_discord_token_minimal",
        CHANNEL_ID=123456789,
    )


def create_test_config_selective(
    *,
    enable_daily_play_count: bool = True,
    enable_play_count_by_dayofweek: bool = False,
    enable_play_count_by_hourofday: bool = False,
    enable_play_count_by_month: bool = True,
    enable_top_10_platforms: bool = False,
    enable_top_10_users: bool = True,
) -> TGraphBotConfig:
    """
    Create a test configuration with selective graph enabling.
    
    This function allows fine-grained control over which graph types are enabled,
    useful for testing specific combinations of graphs.
    
    Args:
        enable_daily_play_count: Enable daily play count graph
        enable_play_count_by_dayofweek: Enable day of week graph
        enable_play_count_by_hourofday: Enable hour of day graph
        enable_play_count_by_month: Enable monthly graph
        enable_top_10_platforms: Enable top platforms graph
        enable_top_10_users: Enable top users graph
    
    Returns:
        TGraphBotConfig: Configuration with selective graph enabling
        
    Example:
        >>> config = create_test_config_selective(
        ...     enable_top_10_users=False,
        ...     enable_top_10_platforms=True
        ... )
        >>> assert config.ENABLE_TOP_10_USERS is False
        >>> assert config.ENABLE_TOP_10_PLATFORMS is True
    """
    from config.schema import TGraphBotConfig
    
    return TGraphBotConfig(
        TAUTULLI_API_KEY="test_api_key_selective",
        TAUTULLI_URL="http://localhost:8181/api/v2",
        DISCORD_TOKEN="test_discord_token_selective",
        CHANNEL_ID=123456789,
        
        ENABLE_DAILY_PLAY_COUNT=enable_daily_play_count,
        ENABLE_PLAY_COUNT_BY_DAYOFWEEK=enable_play_count_by_dayofweek,
        ENABLE_PLAY_COUNT_BY_HOUROFDAY=enable_play_count_by_hourofday,
        ENABLE_PLAY_COUNT_BY_MONTH=enable_play_count_by_month,
        ENABLE_TOP_10_PLATFORMS=enable_top_10_platforms,
        ENABLE_TOP_10_USERS=enable_top_10_users,
    )


def create_test_config_privacy_focused() -> TGraphBotConfig:
    """
    Create a test configuration optimized for privacy.
    
    This function provides a configuration that disables user-specific features
    and enables privacy-focused settings.
    
    Returns:
        TGraphBotConfig: Privacy-focused configuration
        
    Example:
        >>> config = create_test_config_privacy_focused()
        >>> assert config.CENSOR_USERNAMES is True
        >>> assert config.ENABLE_TOP_10_USERS is False
    """
    from config.schema import TGraphBotConfig
    
    return TGraphBotConfig(
        TAUTULLI_API_KEY="test_api_key_privacy",
        TAUTULLI_URL="http://localhost:8181/api/v2",
        DISCORD_TOKEN="test_discord_token_privacy",
        CHANNEL_ID=123456789,
        
        # Privacy-focused settings
        CENSOR_USERNAMES=True,
        ENABLE_TOP_10_USERS=False,  # Disable user-specific graphs
        
        # Disable user-related annotations
        ANNOTATE_TOP_10_USERS=False,
    )


def create_graph_factory_with_config(config: TGraphBotConfig) -> GraphFactory:
    """
    Create a GraphFactory instance with the specified configuration.
    
    This utility function standardizes the creation of GraphFactory instances
    for testing, ensuring consistent setup patterns.
    
    Args:
        config: The TGraphBotConfig to use for the factory
        
    Returns:
        GraphFactory: Configured GraphFactory instance
        
    Raises:
        ImportError: If GraphFactory cannot be imported
        
    Example:
        >>> config = create_test_config_minimal()
        >>> factory = create_graph_factory_with_config(config)
        >>> assert factory.config is config
    """
    try:
        from graphs.graph_modules.graph_factory import GraphFactory
    except ImportError as e:
        msg = f"Failed to import GraphFactory: {e}"
        raise ImportError(msg) from e
    
    return GraphFactory(config)


class TestGraph(ABC):
    """Base class for test graph implementations."""
    
    def __init__(
        self,
        *,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str = "#ffffff",
    ) -> None:
        """Initialize test graph with default parameters."""
        from graphs.graph_modules.base_graph import BaseGraph
        
        # Create a concrete implementation for testing
        class ConcreteTestGraph(BaseGraph):
            @override
            def generate(self, data: Mapping[str, object]) -> str:
                """Generate a test graph."""
                try:
                    _ = self.setup_figure()
                    if self.axes is not None:
                        _ = self.axes.plot([1, 2, 3], [1, 4, 2])  # pyright: ignore[reportUnknownMemberType]
                        _ = self.axes.set_title(self.get_title())  # pyright: ignore[reportUnknownMemberType]
                    
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        output_path = tmp.name
                        
                    return self.save_figure(output_path=output_path)
                finally:
                    self.cleanup()
            
            @override
            def get_title(self) -> str:
                """Get the title for this test graph."""
                return "Test Graph"
        
        self._graph: BaseGraph = ConcreteTestGraph(
            width=width,
            height=height,
            dpi=dpi,
            background_color=background_color,
        )
    
    @property
    def graph(self) -> BaseGraph:
        """Get the underlying BaseGraph instance."""
        return self._graph


def create_memory_test_graph() -> TestGraph:
    """
    Create a test graph specifically designed for memory testing.
    
    This function creates a graph implementation that includes proper cleanup
    and is suitable for memory management testing scenarios.
    
    Returns:
        TestGraph: A test graph instance for memory testing
        
    Example:
        >>> test_graph = create_memory_test_graph()
        >>> graph = test_graph.graph
        >>> with graph:
        ...     # Use graph for testing
        ...     pass
        >>> assert graph.figure is None  # Cleaned up
    """
    return TestGraph()


@contextmanager
def matplotlib_cleanup() -> Generator[None, None, None]:
    """
    Context manager for matplotlib resource cleanup in tests.
    
    This context manager ensures that matplotlib figures are properly cleaned up
    after test execution, preventing memory leaks and interference between tests.
    
    Yields:
        None
        
    Example:
        >>> with matplotlib_cleanup():
        ...     # Create and use matplotlib figures
        ...     fig = plt.figure()
        ...     # Figures are automatically cleaned up
    """
    initial_figures = set(plt.get_fignums())
    
    try:
        yield
    finally:
        # Clean up any figures created during the test
        current_figures = set(plt.get_fignums())
        new_figures = current_figures - initial_figures
        
        for fig_num in new_figures:
            try:
                plt.close(fig_num)
            except Exception:
                # Ignore cleanup errors - figure might already be closed
                pass
        
        # Force garbage collection to help with memory cleanup
        _ = gc.collect()


@contextmanager
def memory_monitoring() -> Generator[dict[str, float], None, None]:
    """
    Context manager for monitoring memory usage during tests.
    
    This context manager tracks memory usage before and after test execution,
    providing information about memory consumption patterns.
    
    Yields:
        dict[str, float]: Dictionary with memory usage information
        
    Example:
        >>> with memory_monitoring() as memory_info:
        ...     # Perform memory-intensive operations
        ...     pass
        >>> print(f"Memory used: {memory_info['memory_used_mb']:.2f} MB")
    """
    process = psutil.Process()
    
    # Get initial memory usage
    initial_memory = process.memory_info()
    initial_rss_mb: float = initial_memory.rss / 1024 / 1024
    
    memory_info: dict[str, float] = {
        'initial_memory_mb': initial_rss_mb,
        'peak_memory_mb': initial_rss_mb,
        'final_memory_mb': 0.0,
        'memory_used_mb': 0.0,
    }
    
    try:
        yield memory_info
    finally:
        # Get final memory usage
        final_memory = process.memory_info()
        final_rss_mb: float = final_memory.rss / 1024 / 1024
        
        memory_info['final_memory_mb'] = final_rss_mb
        memory_info['memory_used_mb'] = final_rss_mb - initial_rss_mb
        memory_info['peak_memory_mb'] = max(memory_info['peak_memory_mb'], final_rss_mb)


def assert_graph_properties(
    graph: BaseGraph,
    *,
    expected_width: int = 12,
    expected_height: int = 8,
    expected_dpi: int = 100,
    expected_background_color: str = "#ffffff",
) -> None:
    """
    Assert that a graph has the expected properties.
    
    This utility function provides standardized assertions for graph properties,
    ensuring consistent validation across tests.
    
    Args:
        graph: The BaseGraph instance to validate
        expected_width: Expected figure width
        expected_height: Expected figure height
        expected_dpi: Expected figure DPI
        expected_background_color: Expected background color
        
    Raises:
        AssertionError: If any property doesn't match expected value
        
    Example:
        >>> graph = create_memory_test_graph().graph
        >>> assert_graph_properties(graph)  # Uses defaults
        >>> assert_graph_properties(
        ...     graph,
        ...     expected_width=10,
        ...     expected_background_color="#f0f0f0"
        ... )
    """
    assert graph.width == expected_width, f"Expected width {expected_width}, got {graph.width}"
    assert graph.height == expected_height, f"Expected height {expected_height}, got {graph.height}"
    assert graph.dpi == expected_dpi, f"Expected DPI {expected_dpi}, got {graph.dpi}"
    assert graph.background_color == expected_background_color, f"Expected background color {expected_background_color}, got {graph.background_color}"


def assert_graph_cleanup(graph: BaseGraph) -> None:
    """
    Assert that a graph has been properly cleaned up.
    
    This utility function validates that matplotlib resources have been
    properly cleaned up after graph usage.
    
    Args:
        graph: The BaseGraph instance to validate
        
    Raises:
        AssertionError: If cleanup was not performed correctly
        
    Example:
        >>> graph = create_memory_test_graph().graph
        >>> graph.setup_figure()
        >>> graph.cleanup()
        >>> assert_graph_cleanup(graph)  # Validates cleanup
    """
    assert graph.figure is None, "Figure should be None after cleanup"
    assert graph.axes is None, "Axes should be None after cleanup"


def assert_factory_enabled_graphs(
    factory: GraphFactory,
    expected_types: set[str],
) -> None:
    """
    Assert that a GraphFactory has the expected enabled graph types.
    
    This utility function validates that a factory has the correct set of
    enabled graph types, useful for configuration testing.
    
    Args:
        factory: The GraphFactory instance to validate
        expected_types: Set of expected enabled graph type names
        
    Raises:
        AssertionError: If enabled types don't match expected types
        
    Example:
        >>> config = create_test_config_selective(
        ...     enable_daily_play_count=True,
        ...     enable_top_10_users=False
        ... )
        >>> factory = create_graph_factory_with_config(config)
        >>> expected = {"daily_play_count", "play_count_by_month"}
        >>> assert_factory_enabled_graphs(factory, expected)
    """
    enabled_types = set(factory.get_enabled_graph_types())
    assert enabled_types == expected_types, f"Expected types {expected_types}, got {enabled_types}"


def create_mock_graph_data() -> dict[str, object]:
    """
    Create mock data for graph generation testing.
    
    This function provides standardized mock data that can be used across
    different graph generation tests.
    
    Returns:
        dict[str, object]: Mock data suitable for graph generation
        
    Example:
        >>> data = create_mock_graph_data()
        >>> assert "data" in data
        >>> assert isinstance(data["data"], list)
    """
    return {
        "data": [
            {
                "date": "2024-01-01",
                "user": "test_user_1",
                "title": "Test Movie 1",
                "media_type": "movie",
                "platform": "Test Platform 1"
            },
            {
                "date": "2024-01-02",
                "user": "test_user_2",
                "title": "Test Show S01E01",
                "media_type": "episode",
                "platform": "Test Platform 2"
            },
            {
                "date": "2024-01-03",
                "user": "test_user_1",
                "title": "Test Movie 2",
                "media_type": "movie",
                "platform": "Test Platform 1"
            }
        ]
    }


@contextmanager
def patch_matplotlib_save() -> Generator[MagicMock, None, None]:
    """
    Context manager to patch matplotlib savefig for testing.
    
    This context manager patches matplotlib's savefig function to avoid
    actual file I/O during testing while still allowing validation of
    the save behavior.
    
    Yields:
        MagicMock: Mock object for the savefig function
        
    Example:
        >>> with patch_matplotlib_save() as mock_savefig:
        ...     # Generate graph that calls savefig
        ...     graph = create_memory_test_graph().graph
        ...     # Validate savefig was called
        ...     mock_savefig.assert_called()
    """
    with patch('matplotlib.pyplot.savefig') as mock_savefig:
        yield mock_savefig


def validate_no_memory_leaks(
    operation_func: Callable[[], None],
    *,
    max_memory_increase_mb: float = 10.0,
    iterations: int = 5,
) -> None:
    """
    Validate that an operation doesn't cause significant memory leaks.
    
    This function runs an operation multiple times and validates that
    memory usage doesn't increase beyond acceptable limits.
    
    Args:
        operation_func: Function to test for memory leaks
        max_memory_increase_mb: Maximum acceptable memory increase in MB
        iterations: Number of iterations to run the operation
        
    Raises:
        AssertionError: If memory increase exceeds the maximum
        
    Example:
        >>> def test_operation():
        ...     graph = create_memory_test_graph().graph
        ...     with graph:
        ...         graph.setup_figure()
        >>> validate_no_memory_leaks(test_operation, max_memory_increase_mb=5.0)
    """
    process = psutil.Process()
    initial_memory: float = process.memory_info().rss / 1024 / 1024
    
    # Run the operation multiple times
    for _ in range(iterations):
        operation_func()
        _ = gc.collect()  # Force garbage collection
    
    final_memory: float = process.memory_info().rss / 1024 / 1024
    memory_increase: float = final_memory - initial_memory
    
    assert memory_increase <= max_memory_increase_mb, \
        f"Memory increased by {memory_increase:.2f}MB, which exceeds the {max_memory_increase_mb}MB limit" 