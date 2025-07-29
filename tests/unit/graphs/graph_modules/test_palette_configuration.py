"""
Test cases for color palette configuration functionality.

This module tests the priority-based palette system to ensure that
user-configured palettes take precedence over automatic media type palettes.
"""


from tgraph_bot.config.schema import TGraphBotConfig
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
        config = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
            TOP_10_USERS_PALETTE="plasma",
            ENABLE_MEDIA_TYPE_SEPARATION=True,
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
        config = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
            TOP_10_USERS_PALETTE="",  # Empty - no palette configured
            ENABLE_MEDIA_TYPE_SEPARATION=True,
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
        config_with_palette = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
        )
        graph_with_palette = PlayCountByHourOfDayGraph(config=config_with_palette)
        assert graph_with_palette.get_user_configured_palette() == "viridis"

        # Test with empty palette
        config_no_palette = TGraphBotConfig(
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
        """Test palette configuration for all graph types."""
        # NOTE: This test documents the expected palette configuration keys
        # that will be implemented in Phase 4 of the plan

        # Test configuration with all palette types
        config = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            # Existing palette configurations (should work)
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
            TOP_10_USERS_PALETTE="plasma",
            # Missing palette configurations (will be implemented)
            # DAILY_PLAY_COUNT_PALETTE="inferno",
            # PLAY_COUNT_BY_DAYOFWEEK_PALETTE="magma",
            # TOP_10_PLATFORMS_PALETTE="cividis",
            # PLAY_COUNT_BY_MONTH_PALETTE="turbo",
        )

        # Test existing palette configurations
        hourly_graph = PlayCountByHourOfDayGraph(config=config)
        assert hourly_graph.get_user_configured_palette() == "viridis"

        users_graph = Top10UsersGraph(config=config)
        assert users_graph.get_user_configured_palette() == "plasma"

        # Test graphs that don't have palette configuration yet
        # These should return None until Phase 4 is implemented
        daily_graph = DailyPlayCountGraph(config=config)
        assert daily_graph.get_user_configured_palette() is None

        dayofweek_graph = PlayCountByDayOfWeekGraph(config=config)
        assert dayofweek_graph.get_user_configured_palette() is None

        platforms_graph = Top10PlatformsGraph(config=config)
        assert platforms_graph.get_user_configured_palette() is None

        month_graph = PlayCountByMonthGraph(config=config)
        assert month_graph.get_user_configured_palette() is None

    def test_palette_precedence_over_default_colors(self) -> None:
        """Test that user-configured palettes take precedence over default media type colors."""
        # Test with palette configured
        config_with_palette = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
            ENABLE_MEDIA_TYPE_SEPARATION=True,
        )

        # Test without palette configured
        config_without_palette = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="",  # Empty palette
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

            config = TGraphBotConfig(
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
            config = TGraphBotConfig(
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
        config = TGraphBotConfig(
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
