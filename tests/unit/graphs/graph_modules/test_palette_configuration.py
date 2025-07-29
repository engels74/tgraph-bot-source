"""
Test cases for color palette configuration functionality.

This module tests the priority-based palette system to ensure that
user-configured palettes take precedence over automatic media type palettes.
"""


from tgraph_bot.config.schema import TGraphBotConfig
from tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_hourofday_graph import (
    PlayCountByHourOfDayGraph,
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
