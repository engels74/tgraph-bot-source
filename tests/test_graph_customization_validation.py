"""
Comprehensive validation tests for graph customization options and feature toggles.

This module systematically tests all customization options including colors,
annotations, grid settings, feature toggles, and username censoring to ensure
they work correctly across all graph types.
# pyright: reportPrivateUsage=false, reportAny=false
"""

from __future__ import annotations



from config.schema import TGraphBotConfig
from graphs.graph_modules.graph_factory import GraphFactory


class TestGraphCustomizationValidation:
    """Test cases for validating all graph customization options."""

    def test_color_customization_validation(self) -> None:
        """Test that all color customization options work correctly."""
        config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            TV_COLOR="#ff0000",
            MOVIE_COLOR="#00ff00",
            GRAPH_BACKGROUND_COLOR="#f0f0f0",
            ANNOTATION_COLOR="#0000ff",
            ANNOTATION_OUTLINE_COLOR="#ffffff"
        )

        factory = GraphFactory(config)

        # Test each graph type with custom colors
        graph_types = [
            "daily_play_count",
            "top_10_users",
            "play_count_by_hourofday",
            "play_count_by_dayofweek",
            "play_count_by_month",
            "top_10_platforms"
        ]

        for graph_type in graph_types:
            graph = factory.create_graph_by_type(graph_type)

            # Verify colors are applied to the graph's config
            assert graph.config.TV_COLOR == "#ff0000"  # pyright: ignore[reportOptionalMemberAccess]
            assert graph.config.MOVIE_COLOR == "#00ff00"  # pyright: ignore[reportOptionalMemberAccess]
            assert graph.config.GRAPH_BACKGROUND_COLOR == "#f0f0f0"  # pyright: ignore[reportOptionalMemberAccess]
            assert graph.config.ANNOTATION_COLOR == "#0000ff"  # pyright: ignore[reportOptionalMemberAccess]
            assert graph.config.ANNOTATION_OUTLINE_COLOR == "#ffffff"  # pyright: ignore[reportOptionalMemberAccess]

            # Verify graph can be instantiated with custom colors
            assert graph.background_color == "#f0f0f0"

    def test_feature_toggle_validation(self) -> None:
        """Test that all feature toggles work correctly."""
        # Test all graphs disabled
        config_all_disabled = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            ENABLE_DAILY_PLAY_COUNT=False,
            ENABLE_PLAY_COUNT_BY_DAYOFWEEK=False,
            ENABLE_PLAY_COUNT_BY_HOUROFDAY=False,
            ENABLE_PLAY_COUNT_BY_MONTH=False,
            ENABLE_TOP_10_PLATFORMS=False,
            ENABLE_TOP_10_USERS=False,
        )

        factory = GraphFactory(config_all_disabled)
        graphs = factory.create_enabled_graphs()
        assert len(graphs) == 0
        
        # Test selective enabling
        config_selective = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            ENABLE_DAILY_PLAY_COUNT=True,
            ENABLE_PLAY_COUNT_BY_DAYOFWEEK=False,
            ENABLE_PLAY_COUNT_BY_HOUROFDAY=True,
            ENABLE_PLAY_COUNT_BY_MONTH=False,
            ENABLE_TOP_10_PLATFORMS=True,
            ENABLE_TOP_10_USERS=False,
        )

        factory = GraphFactory(config_selective)
        graphs = factory.create_enabled_graphs()
        assert len(graphs) == 3
        
        enabled_types = factory.get_enabled_graph_types()
        expected_enabled = {
            "daily_play_count",
            "play_count_by_hourofday", 
            "top_10_platforms"
        }
        assert set(enabled_types) == expected_enabled

    def test_annotation_settings_validation(self) -> None:
        """Test that annotation settings work correctly for all graph types."""
        # Test with annotations enabled
        config_annotations_enabled = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            ANNOTATE_DAILY_PLAY_COUNT=True,
            ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK=True,
            ANNOTATE_PLAY_COUNT_BY_HOUROFDAY=True,
            ANNOTATE_TOP_10_PLATFORMS=True,
            ANNOTATE_TOP_10_USERS=True,
            ANNOTATE_PLAY_COUNT_BY_MONTH=True,
            ENABLE_ANNOTATION_OUTLINE=True
        )

        factory = GraphFactory(config_annotations_enabled)

        # Test each graph type with annotations
        graph_types = [
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "top_10_platforms",
            "top_10_users",
            "play_count_by_month"
        ]

        for graph_type in graph_types:
            graph = factory.create_graph_by_type(graph_type)

            # Verify annotation settings are applied
            assert graph.config.ENABLE_ANNOTATION_OUTLINE is True  # pyright: ignore[reportOptionalMemberAccess]

    def test_grid_settings_validation(self) -> None:
        """Test that grid settings work correctly."""
        # Test with grid enabled
        config_grid_enabled = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            ENABLE_GRAPH_GRID=True
        )

        factory = GraphFactory(config_grid_enabled)
        graph = factory.create_graph_by_type("daily_play_count")

        assert graph.config.ENABLE_GRAPH_GRID is True  # pyright: ignore[reportOptionalMemberAccess]

        # Test with grid disabled
        config_grid_disabled = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            ENABLE_GRAPH_GRID=False
        )

        factory = GraphFactory(config_grid_disabled)
        graph = factory.create_graph_by_type("daily_play_count")

        assert graph.config.ENABLE_GRAPH_GRID is False  # pyright: ignore[reportOptionalMemberAccess]

    def test_username_censoring_validation(self) -> None:
        """Test that username censoring works correctly."""
        # Test with censoring enabled
        config_censor_enabled = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            CENSOR_USERNAMES=True
        )

        factory = GraphFactory(config_censor_enabled)
        graph = factory.create_graph_by_type("top_10_users")

        assert graph.should_censor_usernames() is True

        # Test with censoring disabled
        config_censor_disabled = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            CENSOR_USERNAMES=False
        )

        factory = GraphFactory(config_censor_disabled)
        graph = factory.create_graph_by_type("top_10_users")

        assert graph.should_censor_usernames() is False

    def test_comprehensive_customization_integration(self) -> None:
        """Test all customization options working together."""
        comprehensive_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            # Colors
            TV_COLOR="#ff4444",
            MOVIE_COLOR="#44ff44",
            GRAPH_BACKGROUND_COLOR="#f8f8f8",
            ANNOTATION_COLOR="#4444ff",
            ANNOTATION_OUTLINE_COLOR="#222222",
            # Feature toggles
            ENABLE_DAILY_PLAY_COUNT=True,
            ENABLE_TOP_10_USERS=True,
            ENABLE_PLAY_COUNT_BY_HOUROFDAY=False,
            # Settings
            ENABLE_GRAPH_GRID=True,
            CENSOR_USERNAMES=True,
            ENABLE_ANNOTATION_OUTLINE=True,
            # Annotations
            ANNOTATE_DAILY_PLAY_COUNT=True,
            ANNOTATE_TOP_10_USERS=False
        )

        factory = GraphFactory(comprehensive_config)

        # Verify only enabled graphs are created
        enabled_types = factory.get_enabled_graph_types()

        # Should have daily_play_count and top_10_users, but not hourofday
        assert "daily_play_count" in enabled_types
        assert "top_10_users" in enabled_types
        assert "play_count_by_hourofday" not in enabled_types

        # Test each enabled graph with all settings
        for graph_type in enabled_types:
            graph = factory.create_graph_by_type(graph_type)

            # Verify all settings are applied
            assert graph.config.TV_COLOR == "#ff4444"  # pyright: ignore[reportOptionalMemberAccess]
            assert graph.config.MOVIE_COLOR == "#44ff44"  # pyright: ignore[reportOptionalMemberAccess]
            assert graph.config.ENABLE_GRAPH_GRID is True  # pyright: ignore[reportOptionalMemberAccess]
            assert graph.config.CENSOR_USERNAMES is True  # pyright: ignore[reportOptionalMemberAccess]
