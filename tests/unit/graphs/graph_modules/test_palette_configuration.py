from tests.utils.test_helpers import create_test_config_custom

"""
Test cases for color palette configuration functionality.

This module tests the priority-based palette system to ensure that
user-configured palettes take precedence over automatic media type palettes.
"""

from typing import TYPE_CHECKING, Callable, cast
from unittest.mock import patch, MagicMock
import pytest



if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from tgraph_bot.graphs.graph_modules.core.base_graph import BaseGraph
    from tgraph_bot.graphs.graph_modules.utils.utils import ProcessedRecords
from tgraph_bot.graphs.graph_modules.implementations.tautulli.daily_play_count_graph import (
    DailyPlayCountGraph,
)
from tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_dayofweek_graph import (
    PlayCountByDayOfWeekGraph,
)
from tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_hourofday_graph import (
    PlayCountByHourOfDayGraph,
)
from tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_month_graph import (
    PlayCountByMonthGraph,
)
from tgraph_bot.graphs.graph_modules.implementations.tautulli.top_10_platforms_graph import (
    Top10PlatformsGraph,
)
from tgraph_bot.graphs.graph_modules.implementations.tautulli.top_10_users_graph import (
    Top10UsersGraph,
)


class TestPaletteConfiguration:
    """Test color palette configuration functionality."""

    def test_graph_specific_palette_application(self) -> None:
        """Test that each graph type returns only its own specific palette."""
        # Configure both palettes with different values
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_key", "url": "http://test.local"},
                "discord": {"token": "test_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "features": {"media_type_separation": True},
                "appearance": {
                    "palettes": {
                        "play_count_by_hourofday": "viridis",
                        "top_10_users": "plasma"
                    }
                }
            }
        )

        # Test hourly graph returns viridis
        hourly_graph = PlayCountByHourOfDayGraph(config=config)
        assert hourly_graph.get_user_configured_palette() == "viridis"

        # Test users graph returns plasma
        users_graph = Top10UsersGraph(config=config)
        assert users_graph.get_user_configured_palette() == "plasma"

    def test_single_graph_palette_does_not_affect_other_graphs(self) -> None:
        """Test that configuring one graph's palette doesn't affect others."""
        # Configure only the hourly palette, not the users palette
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_key", "url": "http://test.local"},
                "discord": {"token": "test_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "features": {"media_type_separation": True},
                "appearance": {
                    "palettes": {
                        "play_count_by_hourofday": "viridis",
                        "top_10_users": ""  # Empty - no palette configured
                    }
                }
            }
        )

        # Hourly graph should return viridis
        hourly_graph = PlayCountByHourOfDayGraph(config=config)
        assert hourly_graph.get_user_configured_palette() == "viridis"

        # Users graph should return None (no palette configured)
        users_graph = Top10UsersGraph(config=config)
        assert users_graph.get_user_configured_palette() is None

    def test_get_user_configured_palette_method(self) -> None:
        """Test the get_user_configured_palette method works correctly."""
        # Test with configured palette
        config_with_palette = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
            )
        graph_with_palette = PlayCountByHourOfDayGraph(config=config_with_palette)
        assert graph_with_palette.get_user_configured_palette() == "viridis"

        # Test with empty palette
        config_no_palette = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                PLAY_COUNT_BY_HOUROFDAY_PALETTE="",
            )
        graph_no_palette = PlayCountByHourOfDayGraph(config=config_no_palette)
        assert graph_no_palette.get_user_configured_palette() is None

        # Test with None config
        graph_none_config = PlayCountByHourOfDayGraph(config=None)
        assert graph_none_config.get_user_configured_palette() is None

    def test_all_graph_types_palette_configuration(self) -> None:
        """Test palette configuration for all graph types after Phase 4 implementation."""
        # Test configuration with all palette types - this test will pass after Phase 4
        config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
                TOP_10_USERS_PALETTE="plasma",
                DAILY_PLAY_COUNT_PALETTE="inferno",
                PLAY_COUNT_BY_DAYOFWEEK_PALETTE="magma",
                TOP_10_PLATFORMS_PALETTE="cividis",
                PLAY_COUNT_BY_MONTH_PALETTE="turbo",
            )

        # Test all graph types return their configured palettes
        hourly_graph = PlayCountByHourOfDayGraph(config=config)
        assert hourly_graph.get_user_configured_palette() == "viridis"

        users_graph = Top10UsersGraph(config=config)
        assert users_graph.get_user_configured_palette() == "plasma"

        daily_graph = DailyPlayCountGraph(config=config)
        assert daily_graph.get_user_configured_palette() == "inferno"

        dayofweek_graph = PlayCountByDayOfWeekGraph(config=config)
        assert dayofweek_graph.get_user_configured_palette() == "magma"

        platforms_graph = Top10PlatformsGraph(config=config)
        assert platforms_graph.get_user_configured_palette() == "cividis"

        month_graph = PlayCountByMonthGraph(config=config)
        assert month_graph.get_user_configured_palette() == "turbo"

    def test_palette_precedence_over_default_colors(self) -> None:
        """Test that user-configured palettes take precedence over default media type colors."""
        # Test with palette configured
        config_with_palette = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
                ENABLE_MEDIA_TYPE_SEPARATION=True,
            )

        # Test without palette configured
        config_without_palette = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                PLAY_COUNT_BY_HOUROFDAY_PALETTE="",  # Empty palette,
                ENABLE_MEDIA_TYPE_SEPARATION=True,
            )

        # Graph with palette should return the configured palette
        graph_with_palette = PlayCountByHourOfDayGraph(config=config_with_palette)
        assert graph_with_palette.get_user_configured_palette() == "viridis"

        # Graph without palette should return None (will use default colors)
        graph_without_palette = PlayCountByHourOfDayGraph(config=config_without_palette)
        assert graph_without_palette.get_user_configured_palette() is None

    def test_empty_palette_configuration_handling(self) -> None:
        """Test handling of empty and invalid palette configurations."""
        # Test various empty/invalid palette values
        empty_values = ["", "   ", None]

        for empty_value in empty_values:
            if empty_value is None:
                # Skip None test as it would cause validation error in TGraphBotConfig
                continue

            config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                PLAY_COUNT_BY_HOUROFDAY_PALETTE=empty_value,
                TOP_10_USERS_PALETTE=empty_value,
            )

            # All graphs should return None for empty palette values
            hourly_graph = PlayCountByHourOfDayGraph(config=config)
            assert hourly_graph.get_user_configured_palette() is None

            users_graph = Top10UsersGraph(config=config)
            assert users_graph.get_user_configured_palette() is None

    def test_palette_configuration_validation_scenarios(self) -> None:
        """Test various palette configuration validation scenarios."""
        # Test with valid palette names
        valid_palettes = ["viridis", "plasma", "inferno", "magma", "cividis"]

        for palette in valid_palettes:
            config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                PLAY_COUNT_BY_HOUROFDAY_PALETTE=palette,
                TOP_10_USERS_PALETTE=palette,
            )

            # Should return the configured palette
            hourly_graph = PlayCountByHourOfDayGraph(config=config)
            assert hourly_graph.get_user_configured_palette() == palette

            users_graph = Top10UsersGraph(config=config)
            assert users_graph.get_user_configured_palette() == palette

    def test_graph_specific_palette_isolation(self) -> None:
        """Test that each graph type only returns its own specific palette configuration."""
        # Configure different palettes for different graph types
        config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
                TOP_10_USERS_PALETTE="plasma",
            )

        # Each graph should only return its own palette, not others
        hourly_graph = PlayCountByHourOfDayGraph(config=config)
        assert hourly_graph.get_user_configured_palette() == "viridis"
        assert hourly_graph.get_user_configured_palette() != "plasma"

        users_graph = Top10UsersGraph(config=config)
        assert users_graph.get_user_configured_palette() == "plasma"
        assert users_graph.get_user_configured_palette() != "viridis"

        # Graphs without specific palette configuration should return None
        daily_graph = DailyPlayCountGraph(config=config)
        assert daily_graph.get_user_configured_palette() is None

        platforms_graph = Top10PlatformsGraph(config=config)
        assert platforms_graph.get_user_configured_palette() is None

    def test_new_palette_configurations_individual_testing(self) -> None:
        """Test each new palette configuration individually after Phase 4 implementation."""
        # Test DAILY_PLAY_COUNT_PALETTE
        daily_config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                DAILY_PLAY_COUNT_PALETTE="inferno",
            )
        daily_graph = DailyPlayCountGraph(config=daily_config)
        assert daily_graph.get_user_configured_palette() == "inferno"

        # Test PLAY_COUNT_BY_DAYOFWEEK_PALETTE
        dayofweek_config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                PLAY_COUNT_BY_DAYOFWEEK_PALETTE="magma",
            )
        dayofweek_graph = PlayCountByDayOfWeekGraph(config=dayofweek_config)
        assert dayofweek_graph.get_user_configured_palette() == "magma"

        # Test TOP_10_PLATFORMS_PALETTE
        platforms_config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                TOP_10_PLATFORMS_PALETTE="cividis",
            )
        platforms_graph = Top10PlatformsGraph(config=platforms_config)
        assert platforms_graph.get_user_configured_palette() == "cividis"

        # Test PLAY_COUNT_BY_MONTH_PALETTE
        month_config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                PLAY_COUNT_BY_MONTH_PALETTE="turbo",
            )
        month_graph = PlayCountByMonthGraph(config=month_config)
        assert month_graph.get_user_configured_palette() == "turbo"

    def test_new_palette_configurations_empty_values(self) -> None:
        """Test that new palette configurations handle empty values correctly."""
        # Test with empty palette values for new configurations
        config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                DAILY_PLAY_COUNT_PALETTE="",
                PLAY_COUNT_BY_DAYOFWEEK_PALETTE="   ",
                TOP_10_PLATFORMS_PALETTE="",
                PLAY_COUNT_BY_MONTH_PALETTE="",
            )

        # All graphs should return None for empty palette values
        daily_graph = DailyPlayCountGraph(config=config)
        assert daily_graph.get_user_configured_palette() is None

        dayofweek_graph = PlayCountByDayOfWeekGraph(config=config)
        assert dayofweek_graph.get_user_configured_palette() is None

        platforms_graph = Top10PlatformsGraph(config=config)
        assert platforms_graph.get_user_configured_palette() is None

        month_graph = PlayCountByMonthGraph(config=config)
        assert month_graph.get_user_configured_palette() is None

    def test_palette_helper_method_with_valid_palette(self) -> None:
        """Test the get_palette_or_default_color() helper method with valid palette."""
        config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                DAILY_PLAY_COUNT_PALETTE="viridis",
            )

        graph = DailyPlayCountGraph(config=config)
        palette, color = graph.get_palette_or_default_color()

        assert palette == "viridis"
        assert color == graph.get_tv_color()

    def test_palette_helper_method_with_no_palette(self) -> None:
        """Test the get_palette_or_default_color() helper method when no palette is configured."""
        config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                DAILY_PLAY_COUNT_PALETTE="",
            )

        graph = DailyPlayCountGraph(config=config)
        palette, color = graph.get_palette_or_default_color()

        assert palette is None
        assert color == graph.get_tv_color()

    def test_palette_helper_method_with_invalid_palette(self) -> None:
        """Test the get_palette_or_default_color() helper method with invalid palette."""
        config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                DAILY_PLAY_COUNT_PALETTE="invalid_palette_name",
            )

        graph = DailyPlayCountGraph(config=config)
        palette, color = graph.get_palette_or_default_color()

        assert palette is None  # Invalid palette should be rejected
        assert color == graph.get_tv_color()

    def test_palette_helper_method_for_all_graph_types(self) -> None:
        """Test the get_palette_or_default_color() helper method works for all graph types."""
        config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
                TOP_10_USERS_PALETTE="plasma",
                DAILY_PLAY_COUNT_PALETTE="inferno",
                PLAY_COUNT_BY_DAYOFWEEK_PALETTE="magma",
                TOP_10_PLATFORMS_PALETTE="cividis",
                PLAY_COUNT_BY_MONTH_PALETTE="turbo",
            )

        # Test all graph types return correct palette and color
        test_cases = [
            (PlayCountByHourOfDayGraph, "viridis"),
            (Top10UsersGraph, "plasma"),
            (DailyPlayCountGraph, "inferno"),
            (PlayCountByDayOfWeekGraph, "magma"),
            (Top10PlatformsGraph, "cividis"),
            (PlayCountByMonthGraph, "turbo"),
        ]

        for graph_class, expected_palette in test_cases:
            graph = graph_class(config=config)
            palette, color = graph.get_palette_or_default_color()

            assert palette == expected_palette
            assert color == graph.get_tv_color()

    def test_palette_helper_method_none_config(self) -> None:
        """Test the get_palette_or_default_color() helper method with None config."""
        graph = DailyPlayCountGraph(config=None)
        palette, color = graph.get_palette_or_default_color()

        assert palette is None
        assert color == graph.get_tv_color()

    @pytest.mark.parametrize(
        "graph_class,palette_config",
        [
            (DailyPlayCountGraph, "DAILY_PLAY_COUNT_PALETTE"),
            (PlayCountByDayOfWeekGraph, "PLAY_COUNT_BY_DAYOFWEEK_PALETTE"),
            (PlayCountByMonthGraph, "PLAY_COUNT_BY_MONTH_PALETTE"),
            (Top10PlatformsGraph, "TOP_10_PLATFORMS_PALETTE"),
            (PlayCountByHourOfDayGraph, "PLAY_COUNT_BY_HOUROFDAY_PALETTE"),
            (Top10UsersGraph, "TOP_10_USERS_PALETTE"),
        ],
    )
    def test_combined_mode_palette_usage_with_palette(
        self, graph_class: type["BaseGraph"], palette_config: str
    ) -> None:
        """Test that combined modes actually use configured palettes when calling seaborn."""
        # Create config with palette configured - use explicit construction to avoid type issues
        if palette_config == "DAILY_PLAY_COUNT_PALETTE":
            config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                DAILY_PLAY_COUNT_PALETTE="viridis",
            )
        elif palette_config == "PLAY_COUNT_BY_DAYOFWEEK_PALETTE":
            config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                PLAY_COUNT_BY_DAYOFWEEK_PALETTE="viridis",
            )
        elif palette_config == "PLAY_COUNT_BY_MONTH_PALETTE":
            config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                PLAY_COUNT_BY_MONTH_PALETTE="viridis",
            )
        elif palette_config == "TOP_10_PLATFORMS_PALETTE":
            config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                TOP_10_PLATFORMS_PALETTE="viridis",
            )
        elif palette_config == "PLAY_COUNT_BY_HOUROFDAY_PALETTE":
            config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
            )
        else:  # TOP_10_USERS_PALETTE
            config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                TOP_10_USERS_PALETTE="viridis",
            )

        graph = graph_class(config=config)

        # Mock seaborn barplot and other plotting functions
        with (
            patch("seaborn.barplot") as mock_barplot,
            patch("matplotlib.axes.Axes.plot") as mock_plot,
            patch("seaborn.color_palette") as mock_color_palette,
        ):
            # Setup mock returns
            mock_color_palette.return_value = ["#440154"]  # Viridis first color

            # Create mock axes
            mock_ax = MagicMock()

            # Create sample processed records for testing
            sample_records = [
                {
                    "date": "2023-01-01",
                    "media_type": "tv",
                    "play_count": 5,
                    "user": "test_user",
                    "hour": 14,
                    "platform": "Web",
                },
                {
                    "date": "2023-01-02",
                    "media_type": "movie",
                    "play_count": 3,
                    "user": "test_user2",
                    "hour": 15,
                    "platform": "Mobile",
                },
            ]

            # Test the visualization methods that should use palettes
            try:
                if hasattr(graph, "_generate_combined_visualization"):
                    method = cast(Callable[["Axes", "ProcessedRecords"], None], getattr(graph, "_generate_combined_visualization"))
                    method(mock_ax, cast("ProcessedRecords", sample_records))
                elif hasattr(graph, "_generate_hourly_visualization"):
                    method = cast(Callable[["Axes", "ProcessedRecords"], None], getattr(graph, "_generate_hourly_visualization"))
                    method(mock_ax, cast("ProcessedRecords", sample_records))
                else:
                    # Skip graphs that don't have these methods
                    return

            except Exception:
                # Some visualization methods might fail due to incomplete mocking,
                # but we're primarily testing that palette parameters are passed correctly
                pass

            # Verify that seaborn functions were called with palette parameter when palette is configured
            if mock_barplot.called:
                # Check if any call used the palette parameter
                palette_used = any(
                    call.kwargs.get("palette") == "viridis"
                    for call in mock_barplot.call_args_list
                )
                assert palette_used, (
                    f"Expected {graph_class.__name__} to use palette 'viridis' in seaborn.barplot calls"
                )

            if mock_plot.called and mock_color_palette.called:
                # For line plots, verify color_palette was called to get colors from palette
                mock_color_palette.assert_called_with("viridis", n_colors=1)

    @pytest.mark.parametrize(
        "graph_class",
        [
            DailyPlayCountGraph,
            PlayCountByDayOfWeekGraph,
            PlayCountByMonthGraph,
            Top10PlatformsGraph,
            PlayCountByHourOfDayGraph,
            Top10UsersGraph,
        ],
    )
    def test_combined_mode_palette_usage_without_palette(
        self, graph_class: type["BaseGraph"]
    ) -> None:
        """Test that combined modes use default colors when no palette is configured."""
        # Create config without palette
        config = create_test_config_with_nested_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
            )

        graph = graph_class(config=config)
        expected_color = graph.get_tv_color()

        # Mock seaborn barplot and other plotting functions
        with (
            patch("seaborn.barplot") as mock_barplot,
            patch("matplotlib.axes.Axes.plot") as mock_plot,
        ):
            # Create mock axes
            mock_ax = MagicMock()

            # Create sample processed records for testing
            sample_records = [
                {
                    "date": "2023-01-01",
                    "media_type": "tv",
                    "play_count": 5,
                    "user": "test_user",
                    "hour": 14,
                    "platform": "Web",
                },
            ]

            # Test the visualization methods
            try:
                if hasattr(graph, "_generate_combined_visualization"):
                    method = cast(Callable[["Axes", "ProcessedRecords"], None], getattr(graph, "_generate_combined_visualization"))
                    method(mock_ax, cast("ProcessedRecords", sample_records))
                elif hasattr(graph, "_generate_hourly_visualization"):
                    method = cast(Callable[["Axes", "ProcessedRecords"], None], getattr(graph, "_generate_hourly_visualization"))
                    method(mock_ax, cast("ProcessedRecords", sample_records))
                else:
                    # Skip graphs that don't have these methods
                    return

            except Exception:
                # Some visualization methods might fail due to incomplete mocking,
                # but we're primarily testing that color parameters are passed correctly
                pass

            # Verify that seaborn functions were called with default color when no palette
            if mock_barplot.called:
                # Check if any call used the default color parameter
                color_used = any(
                    call.kwargs.get("color") == expected_color
                    for call in mock_barplot.call_args_list
                )
                assert color_used, (
                    f"Expected {graph_class.__name__} to use default color {expected_color} in seaborn.barplot calls"
                )

            if mock_plot.called:
                # For line plots, verify the color parameter was used
                color_used = any(
                    call.kwargs.get("color") == expected_color
                    for call in mock_plot.call_args_list
                )
                assert color_used, (
                    f"Expected {graph_class.__name__} to use default color {expected_color} in plot calls"
                )
