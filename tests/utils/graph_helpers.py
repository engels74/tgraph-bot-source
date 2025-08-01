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

from typing import TYPE_CHECKING, override
from unittest.mock import MagicMock, patch

import matplotlib.pyplot as plt
import psutil

if TYPE_CHECKING:
    from src.tgraph_bot.graphs.graph_modules.core.base_graph import BaseGraph
    from src.tgraph_bot.graphs.graph_modules.core.graph_factory import GraphFactory
    from src.tgraph_bot.config.schema import TGraphBotConfig


def create_test_config_comprehensive() -> TGraphBotConfig:
    """
    Create a comprehensive test configuration with all customization options.

    This function provides a standardized comprehensive configuration for tests
    that need to validate all customization features and options.

    Returns:
        TGraphBotConfig: Comprehensive configuration with all options enabled

    Example:
        >>> config = create_test_config_comprehensive()
        >>> assert config.graphs.features.enabled_types.daily_play_count is True
        >>> assert config.graphs.appearance.colors.tv == "#2E86AB"
    """
    from src.tgraph_bot.config.schema import (
        TGraphBotConfig, ServicesConfig, TautulliConfig, DiscordConfig,
        AutomationConfig, SchedulingConfig, DataRetentionConfig,
        DataCollectionConfig, TimeRangesConfig, PrivacyConfig,
        GraphsConfig, GraphFeaturesConfig, EnabledTypesConfig,
        GraphAppearanceConfig, ColorsConfig, GridConfig,
        AnnotationsConfig, BasicAnnotationsConfig, EnabledOnConfig,
    )

    return TGraphBotConfig(
        services=ServicesConfig(
            tautulli=TautulliConfig(
                api_key="test_api_key_comprehensive",
                url="http://localhost:8181/api/v2",
            ),
            discord=DiscordConfig(
                token="test_discord_token_comprehensive",
                channel_id=123456789,
            ),
        ),
        automation=AutomationConfig(
            scheduling=SchedulingConfig(
                update_days=14,
            ),
            data_retention=DataRetentionConfig(
                keep_days=21,
            ),
        ),
        data_collection=DataCollectionConfig(
            time_ranges=TimeRangesConfig(
                days=60,
            ),
            privacy=PrivacyConfig(
                censor_usernames=True,
            ),
        ),
        graphs=GraphsConfig(
            features=GraphFeaturesConfig(
                enabled_types=EnabledTypesConfig(
                    daily_play_count=True,
                    play_count_by_dayofweek=True,
                    play_count_by_hourofday=True,
                    play_count_by_month=True,
                    top_10_platforms=True,
                    top_10_users=True,
                ),
                media_type_separation=True,
                stacked_bar_charts=True,
            ),
            appearance=GraphAppearanceConfig(
                colors=ColorsConfig(
                    tv="#2E86AB",
                    movie="#A23B72",
                    background="#F8F9FA",
                ),
                grid=GridConfig(
                    enabled=True,
                ),
                annotations=AnnotationsConfig(
                    basic=BasicAnnotationsConfig(
                        color="#C73E1D",
                        outline_color="#FFFFFF",
                        enable_outline=True,
                    ),
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
        >>> assert config.services.tautulli.api_key == "test_api_key_minimal"
        >>> assert config.graphs.appearance.colors.tv == "#1f77b4"  # Default value
    """
    from src.tgraph_bot.config.schema import (
        TGraphBotConfig, ServicesConfig, TautulliConfig, DiscordConfig,
    )

    return TGraphBotConfig(
        services=ServicesConfig(
            tautulli=TautulliConfig(
                api_key="test_api_key_minimal",
                url="http://localhost:8181/api/v2",
            ),
            discord=DiscordConfig(
                token="test_discord_token_minimal",
                channel_id=123456789,
            ),
        ),
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
        >>> assert config.graphs.features.enabled_types.top_10_users is False
        >>> assert config.graphs.features.enabled_types.top_10_platforms is True
    """
    from src.tgraph_bot.config.schema import (
        TGraphBotConfig, ServicesConfig, TautulliConfig, DiscordConfig,
        GraphsConfig, GraphFeaturesConfig, EnabledTypesConfig,
    )

    return TGraphBotConfig(
        services=ServicesConfig(
            tautulli=TautulliConfig(
                api_key="test_api_key_selective",
                url="http://localhost:8181/api/v2",
            ),
            discord=DiscordConfig(
                token="test_discord_token_selective",
                channel_id=123456789,
            ),
        ),
        graphs=GraphsConfig(
            features=GraphFeaturesConfig(
                enabled_types=EnabledTypesConfig(
                    daily_play_count=enable_daily_play_count,
                    play_count_by_dayofweek=enable_play_count_by_dayofweek,
                    play_count_by_hourofday=enable_play_count_by_hourofday,
                    play_count_by_month=enable_play_count_by_month,
                    top_10_platforms=enable_top_10_platforms,
                    top_10_users=enable_top_10_users,
                ),
            ),
        ),
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
        >>> assert config.data_collection.privacy.censor_usernames is True
        >>> assert config.graphs.features.enabled_types.top_10_users is False
    """
    from src.tgraph_bot.config.schema import (
        TGraphBotConfig, ServicesConfig, TautulliConfig, DiscordConfig,
        DataCollectionConfig, PrivacyConfig,
        GraphsConfig, GraphFeaturesConfig, EnabledTypesConfig,
        GraphAppearanceConfig, AnnotationsConfig, EnabledOnConfig,
    )

    return TGraphBotConfig(
        services=ServicesConfig(
            tautulli=TautulliConfig(
                api_key="test_api_key_privacy",
                url="http://localhost:8181/api/v2",
            ),
            discord=DiscordConfig(
                token="test_discord_token_privacy",
                channel_id=123456789,
            ),
        ),
        data_collection=DataCollectionConfig(
            privacy=PrivacyConfig(
                censor_usernames=True,
            ),
        ),
        graphs=GraphsConfig(
            features=GraphFeaturesConfig(
                enabled_types=EnabledTypesConfig(
                    top_10_users=False,  # Disable user-specific graphs
                ),
            ),
            appearance=GraphAppearanceConfig(
                annotations=AnnotationsConfig(
                    enabled_on=EnabledOnConfig(
                        top_10_users=False,  # Disable user-related annotations
                    ),
                ),
            ),
        ),
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
        from src.tgraph_bot.graphs.graph_modules.core.graph_factory import GraphFactory
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
        from src.tgraph_bot.graphs.graph_modules.core.base_graph import BaseGraph

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

                    with tempfile.NamedTemporaryFile(
                        suffix=".png", delete=False
                    ) as tmp:
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
                plt.close(fig_num)  # pyright: ignore[reportUnknownMemberType] # matplotlib cleanup
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
    initial_rss_mb: float = initial_memory.rss / 1024 / 1024  # pyright: ignore[reportAny]

    memory_info: dict[str, float] = {
        "initial_memory_mb": initial_rss_mb,
        "peak_memory_mb": initial_rss_mb,
        "final_memory_mb": 0.0,
        "memory_used_mb": 0.0,
    }

    try:
        yield memory_info
    finally:
        # Get final memory usage
        final_memory = process.memory_info()
        final_rss_mb: float = final_memory.rss / 1024 / 1024  # pyright: ignore[reportAny]

        memory_info["final_memory_mb"] = final_rss_mb
        memory_info["memory_used_mb"] = final_rss_mb - initial_rss_mb
        memory_info["peak_memory_mb"] = max(memory_info["peak_memory_mb"], final_rss_mb)


def assert_graph_properties(
    graph: BaseGraph,
    *,
    expected_width: int = 14,
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
    assert graph.width == expected_width, (
        f"Expected width {expected_width}, got {graph.width}"
    )
    assert graph.height == expected_height, (
        f"Expected height {expected_height}, got {graph.height}"
    )
    assert graph.dpi == expected_dpi, f"Expected DPI {expected_dpi}, got {graph.dpi}"
    assert graph.background_color == expected_background_color, (
        f"Expected background color {expected_background_color}, got {graph.background_color}"
    )


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
    assert enabled_types == expected_types, (
        f"Expected types {expected_types}, got {enabled_types}"
    )


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
                "platform": "Test Platform 1",
            },
            {
                "date": "2024-01-02",
                "user": "test_user_2",
                "title": "Test Show S01E01",
                "media_type": "episode",
                "platform": "Test Platform 2",
            },
            {
                "date": "2024-01-03",
                "user": "test_user_1",
                "title": "Test Movie 2",
                "media_type": "movie",
                "platform": "Test Platform 1",
            },
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
    with patch("matplotlib.pyplot.savefig") as mock_savefig:
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
    initial_memory: float = process.memory_info().rss / 1024 / 1024  # pyright: ignore[reportAny]

    # Run the operation multiple times
    for _ in range(iterations):
        operation_func()
        _ = gc.collect()  # Force garbage collection

    final_memory: float = process.memory_info().rss / 1024 / 1024  # pyright: ignore[reportAny]
    memory_increase: float = final_memory - initial_memory

    assert memory_increase <= max_memory_increase_mb, (
        f"Memory increased by {memory_increase:.2f}MB, which exceeds the {max_memory_increase_mb}MB limit"
    )


def run_standard_graph_tests(
    graph_class: type[BaseGraph],
    sample_data: dict[str, object],
    expected_title: str,
    *,
    config: TGraphBotConfig | None = None,
    expected_file_pattern: str | None = None,
) -> None:
    """
    Run standard graph tests for any graph implementation.

    This function consolidates common test patterns that should be applied
    to all graph implementations, reducing code duplication in individual
    graph test files.

    Args:
        graph_class: The graph class to test
        sample_data: Sample data for graph generation
        expected_title: Expected graph title
        config: Optional configuration for testing
        expected_file_pattern: Optional pattern that should appear in output filename

    Raises:
        AssertionError: If any standard test fails

    Example:
        >>> from src.tgraph_bot.graphs.graph_modules.tautulli_graphs.daily_play_count_graph import DailyPlayCountGraph
        >>> sample_data = {"play_history": {"data": []}}
        >>> run_standard_graph_tests(
        ...     DailyPlayCountGraph,
        ...     sample_data,
        ...     "Daily Play Count (Last 30 days)",
        ...     expected_file_pattern="daily_play_count"
        ... )
    """
    from pathlib import Path

    # Test 1: Basic initialization
    graph = graph_class(config=config) if config else graph_class()
    assert graph.get_title() == expected_title

    # Test 2: Custom dimensions
    graph_custom = graph_class(width=14, height=10, dpi=120)
    assert graph_custom.width == 14
    assert graph_custom.height == 10
    assert graph_custom.dpi == 120

    # Test 3: Graph generation with valid data
    with matplotlib_cleanup():
        graph = graph_class(config=config) if config else graph_class()
        output_path = graph.generate(sample_data)

        # Verify file was created
        assert Path(output_path).exists()
        assert output_path.endswith(".png")

        # Check filename pattern if provided
        if expected_file_pattern:
            assert expected_file_pattern in output_path

        # Clean up
        Path(output_path).unlink(missing_ok=True)

    # Test 4: Empty data handling
    with matplotlib_cleanup():
        graph = graph_class(config=config) if config else graph_class()
        empty_data: dict[str, object] = {"data": []}

        output_path = graph.generate(empty_data)

        # Verify file was created even with empty data
        assert Path(output_path).exists()
        assert output_path.endswith(".png")

        # Clean up
        Path(output_path).unlink(missing_ok=True)


def run_standard_graph_error_tests(
    graph_class: type[BaseGraph],
    invalid_data_samples: list[dict[str, object]],
    expected_error_patterns: list[str],
) -> None:
    """
    Run standard error handling tests for graph implementations.

    This function tests that graph implementations properly handle
    invalid data and raise appropriate errors with meaningful messages.

    Args:
        graph_class: The graph class to test
        invalid_data_samples: List of invalid data samples to test
        expected_error_patterns: List of expected error message patterns

    Raises:
        AssertionError: If error handling doesn't work as expected

    Example:
        >>> from src.tgraph_bot.graphs.graph_modules.tautulli_graphs.daily_play_count_graph import DailyPlayCountGraph
        >>> invalid_samples = [{"invalid_key": "invalid_value"}]
        >>> error_patterns = ["Invalid play history data"]
        >>> run_standard_graph_error_tests(
        ...     DailyPlayCountGraph,
        ...     invalid_samples,
        ...     error_patterns
        ... )
    """
    import pytest

    assert len(invalid_data_samples) == len(expected_error_patterns), (
        "Number of invalid data samples must match number of error patterns"
    )

    for invalid_data, error_pattern in zip(
        invalid_data_samples, expected_error_patterns, strict=True
    ):
        with matplotlib_cleanup():
            graph = graph_class()

            with pytest.raises(ValueError, match=error_pattern):
                _ = graph.generate(invalid_data)
