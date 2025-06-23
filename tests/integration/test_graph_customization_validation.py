"""
Comprehensive validation tests for graph customization options and feature toggles.

This module systematically tests all customization options including colors,
annotations, grid settings, feature toggles, and username censoring to ensure
they work correctly across all graph types.

"""

from __future__ import annotations

import pytest
from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing_extensions import override

from src.tgraph_bot.config.schema import TGraphBotConfig
from src.tgraph_bot.graphs.graph_modules.graph_factory import GraphFactory
from tests.utils.graph_helpers import (
    create_test_config_minimal,
    create_graph_factory_with_config,
    matplotlib_cleanup,
)

if TYPE_CHECKING:
    from src.tgraph_bot.config.schema import TGraphBotConfig


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
            assert graph.config is not None
            # Type guard to ensure we're working with TGraphBotConfig
            assert not isinstance(graph.config, dict), "Config should be TGraphBotConfig, not dict"
            config_obj: TGraphBotConfig = graph.config
            
            assert config_obj.TV_COLOR == "#ff0000"
            assert config_obj.MOVIE_COLOR == "#00ff00"
            assert config_obj.GRAPH_BACKGROUND_COLOR == "#f0f0f0"
            assert config_obj.ANNOTATION_COLOR == "#0000ff"
            assert config_obj.ANNOTATION_OUTLINE_COLOR == "#ffffff"

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
            assert graph.config is not None
            # Type guard to ensure we're working with TGraphBotConfig
            assert not isinstance(graph.config, dict), "Config should be TGraphBotConfig, not dict"
            annotation_config_obj: TGraphBotConfig = graph.config
            
            assert annotation_config_obj.ENABLE_ANNOTATION_OUTLINE is True

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

        assert graph.config is not None
        # Type guard to ensure we're working with TGraphBotConfig
        assert not isinstance(graph.config, dict), "Config should be TGraphBotConfig, not dict"
        config_obj: TGraphBotConfig = graph.config
        assert config_obj.ENABLE_GRAPH_GRID is True

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

        assert graph.config is not None
        # Type guard to ensure we're working with TGraphBotConfig
        assert not isinstance(graph.config, dict), "Config should be TGraphBotConfig, not dict"
        config_obj_disabled: TGraphBotConfig = graph.config
        assert config_obj_disabled.ENABLE_GRAPH_GRID is False

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
            assert graph.config is not None
            # Type guard to ensure we're working with TGraphBotConfig
            assert not isinstance(graph.config, dict), "Config should be TGraphBotConfig, not dict"
            config_obj: TGraphBotConfig = graph.config
            
            assert config_obj.TV_COLOR == "#ff4444"
            assert config_obj.MOVIE_COLOR == "#44ff44"
            assert config_obj.ENABLE_GRAPH_GRID is True
            assert config_obj.CENSOR_USERNAMES is True

    def test_invalid_color_format_handling(self) -> None:
        """Test that invalid color formats are handled gracefully."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            
            # Test with invalid color format - should fall back to defaults
            # This tests the color validation in the BaseGraph class
            with pytest.raises(ValueError, match="Invalid background color format"):
                from src.tgraph_bot.graphs.graph_modules.base_graph import BaseGraph
                # Create a mock graph class to test invalid color handling
                class TestGraph(BaseGraph):
                    @override
                    def generate(self, data: Mapping[str, object]) -> str:
                        return "test.png"
                    
                    @override
                    def get_title(self) -> str:
                        return "Test Graph"
                
                # This should raise ValueError due to invalid color
                _ = TestGraph(config=config, background_color="invalid_color")

    def test_boolean_flag_customization(self) -> None:
        """Test that boolean flag customizations are properly applied."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            # Set boolean flags
            config.ENABLE_GRAPH_GRID = True
            config.CENSOR_USERNAMES = False
            config.ENABLE_ANNOTATION_OUTLINE = True
            
            factory = create_graph_factory_with_config(config)
            graph = factory.create_graph_by_type("daily_play_count")
            
            # Verify boolean flags are applied
            assert graph.config is not None
            # Type guard to ensure we're working with TGraphBotConfig
            assert not isinstance(graph.config, dict), "Config should be TGraphBotConfig, not dict"
            config_obj: TGraphBotConfig = graph.config
            
            assert config_obj.ENABLE_ANNOTATION_OUTLINE is True
            
            # Test methods that use these flags
            assert graph.get_grid_enabled() is True
            assert graph.should_censor_usernames() is False
            assert graph.is_annotation_outline_enabled() is True

    def test_grid_enabling_consistency(self) -> None:
        """Test that grid enabling is consistent across different graph types."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            config.ENABLE_GRAPH_GRID = True
            
            factory = create_graph_factory_with_config(config)
            
            # Test various graph types
            graph_types = ["daily_play_count", "top_10_users", "play_count_by_hourofday"]
            
            for graph_type in graph_types:
                graph = factory.create_graph_by_type(graph_type)
                
                # Verify grid is enabled for all graph types
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), "Config should be TGraphBotConfig, not dict"
                config_obj: TGraphBotConfig = graph.config
                
                assert config_obj.ENABLE_GRAPH_GRID is True
                assert graph.get_grid_enabled() is True
                
                # Cleanup
                graph.cleanup()

    def test_grid_disabling_consistency(self) -> None:
        """Test that grid disabling is consistent across different graph types."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            config.ENABLE_GRAPH_GRID = False
            
            factory = create_graph_factory_with_config(config)
            
            # Test various graph types
            graph_types = ["daily_play_count", "top_10_users", "play_count_by_hourofday"]
            
            for graph_type in graph_types:
                graph = factory.create_graph_by_type(graph_type)
                
                # Verify grid is disabled for all graph types
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), "Config should be TGraphBotConfig, not dict"
                config_obj: TGraphBotConfig = graph.config
                
                assert config_obj.ENABLE_GRAPH_GRID is False
                assert graph.get_grid_enabled() is False
                
                # Cleanup
                graph.cleanup()

    def test_stacked_bar_charts_configuration_validation(self) -> None:
        """Test that stacked bar charts configuration works correctly."""
        with matplotlib_cleanup():
            # Test with stacked bar charts enabled
            config_enabled = create_test_config_minimal()
            config_enabled.ENABLE_MEDIA_TYPE_SEPARATION = True
            config_enabled.ENABLE_STACKED_BAR_CHARTS = True
            
            factory_enabled = create_graph_factory_with_config(config_enabled)
            
            # Test graphs that support stacked bar charts
            stacked_graph_types = ["play_count_by_dayofweek", "play_count_by_month"]
            
            for graph_type in stacked_graph_types:
                graph = factory_enabled.create_graph_by_type(graph_type)
                
                # Verify stacked bar charts are enabled
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), "Config should be TGraphBotConfig, not dict"
                config_obj: TGraphBotConfig = graph.config
                
                assert config_obj.ENABLE_STACKED_BAR_CHARTS is True
                assert graph.get_stacked_bar_charts_enabled() is True
                assert graph.get_media_type_separation_enabled() is True
                
                # Cleanup
                graph.cleanup()

            # Test with stacked bar charts disabled
            config_disabled = create_test_config_minimal()
            config_disabled.ENABLE_MEDIA_TYPE_SEPARATION = True
            config_disabled.ENABLE_STACKED_BAR_CHARTS = False
            
            factory_disabled = create_graph_factory_with_config(config_disabled)
            
            for graph_type in stacked_graph_types:
                graph = factory_disabled.create_graph_by_type(graph_type)
                
                # Verify stacked bar charts are disabled
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), "Config should be TGraphBotConfig, not dict"
                config_obj_disabled: TGraphBotConfig = graph.config
                
                assert config_obj_disabled.ENABLE_STACKED_BAR_CHARTS is False
                assert graph.get_stacked_bar_charts_enabled() is False
                assert graph.get_media_type_separation_enabled() is True  # Media separation can still be enabled
                
                # Cleanup
                graph.cleanup()

    def test_privacy_settings_validation(self) -> None:
        """Test that privacy settings are properly validated and applied."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            # Enable privacy settings
            config.CENSOR_USERNAMES = True
            
            factory = create_graph_factory_with_config(config)
            
            # Test user-related graphs
            user_graphs = ["top_10_users"]
            for graph_type in user_graphs:
                graph = factory.create_graph_by_type(graph_type)
                
                # Verify privacy settings are applied
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), "Config should be TGraphBotConfig, not dict"
                config_obj: TGraphBotConfig = graph.config
                
                assert config_obj.CENSOR_USERNAMES is True
                assert graph.should_censor_usernames() is True
                
                # Test username formatting
                test_username = "TestUser123"
                censored = graph.format_username(test_username, censor_enabled=True)
                assert censored != test_username  # Should be censored
                
                uncensored = graph.format_username(test_username, censor_enabled=False)
                assert uncensored == test_username  # Should be unchanged
                
                # Cleanup
                graph.cleanup()

    def test_comprehensive_customization_validation(self) -> None:
        """Test comprehensive customization settings validation."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            # Apply comprehensive customizations
            config.TV_COLOR = "#FF6B6B"
            config.MOVIE_COLOR = "#4ECDC4"
            config.ENABLE_GRAPH_GRID = True
            config.CENSOR_USERNAMES = True
            
            factory = create_graph_factory_with_config(config)
            graph = factory.create_graph_by_type("daily_play_count")
            
            # Comprehensive validation
            assert graph.config is not None
            # Type guard to ensure we're working with TGraphBotConfig
            assert not isinstance(graph.config, dict), "Config should be TGraphBotConfig, not dict"
            config_obj: TGraphBotConfig = graph.config
            
            assert config_obj.TV_COLOR == "#ff6b6b"  # Normalized to lowercase
            assert config_obj.MOVIE_COLOR == "#4ecdc4"  # Normalized to lowercase
            assert config_obj.ENABLE_GRAPH_GRID is True
            assert config_obj.CENSOR_USERNAMES is True
            
            # Test that graph methods return expected values
            assert graph.get_tv_color() == "#ff6b6b"
            assert graph.get_movie_color() == "#4ecdc4"
            assert graph.get_grid_enabled() is True
            assert graph.should_censor_usernames() is True
            
            # Cleanup
            graph.cleanup()

    def test_annotation_customization_validation(self) -> None:
        """Test that annotation customization settings are properly validated."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            # Set annotation customizations with valid colors
            config.ANNOTATION_COLOR = "#ff0000"  # Valid red color
            config.ANNOTATION_OUTLINE_COLOR = "#000000"
            config.ENABLE_ANNOTATION_OUTLINE = True
            
            factory = create_graph_factory_with_config(config)
            graph = factory.create_graph_by_type("daily_play_count")
            
            # Verify annotation settings
            assert graph.config is not None
            assert graph.get_annotation_color() == "#ff0000"
            assert graph.get_annotation_outline_color() == "#000000"
            assert graph.is_annotation_outline_enabled() is True
            
            # Cleanup
            graph.cleanup()

    def test_default_values_consistency(self) -> None:
        """Test that default values are consistent when not specified."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            
            factory = create_graph_factory_with_config(config)
            graph = factory.create_graph_by_type("daily_play_count")
            
            # Verify default values are applied
            assert graph.get_tv_color() == "#1f77b4"  # Default matplotlib blue
            assert graph.get_movie_color() == "#ff7f0e"  # Default matplotlib orange
            assert graph.get_annotation_color() == "#ff0000"  # Default red
            assert graph.get_annotation_outline_color() == "#000000"  # Default black
            assert graph.get_grid_enabled() is False  # Default disabled
            assert graph.should_censor_usernames() is True  # Default privacy enabled
            assert graph.is_annotation_outline_enabled() is True  # Default enabled
            
            # Cleanup
            graph.cleanup()
