"""Tests for GraphFactory with configurable graph dimensions."""

from __future__ import annotations

from typing import cast
from unittest.mock import patch

from src.tgraph_bot.graphs.graph_modules.graph_factory import GraphFactory
from src.tgraph_bot.config.schema import TGraphBotConfig


class TestGraphFactoryDimensions:
    """Test cases for GraphFactory with configurable graph dimensions."""

    def test_graph_factory_passes_default_dimensions(self) -> None:
        """Test that GraphFactory passes default dimension values to graphs."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        factory = GraphFactory(config)
        
        # Mock the graph classes to capture initialization parameters
        with patch('src.tgraph_bot.graphs.graph_modules.graph_factory.DailyPlayCountGraph') as mock_daily:
            _ = factory.create_graph_by_type("daily_play_count")
            
            # Verify that the graph was created with dimension parameters
            mock_daily.assert_called_once_with(
                config=config,
                width=12,   # Default from config
                height=8,   # Default from config
                dpi=100,    # Default from config
            )

    def test_graph_factory_passes_custom_dimensions(self) -> None:
        """Test that GraphFactory passes custom dimension values from config."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 16,
            "GRAPH_HEIGHT": 12,
            "GRAPH_DPI": 150,
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        factory = GraphFactory(config)
        
        with patch('src.tgraph_bot.graphs.graph_modules.graph_factory.Top10UsersGraph') as mock_top_users:
            _ = factory.create_graph_by_type("top_10_users")
            
            # Verify that the graph was created with custom dimensions
            mock_top_users.assert_called_once_with(
                config=config,
                width=16,   # Custom from config
                height=12,  # Custom from config
                dpi=150,    # Custom from config
            )

    def test_graph_factory_applies_dimensions_to_all_graph_types(self) -> None:
        """Test that GraphFactory applies dimensions to all graph types."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 14,
            "GRAPH_HEIGHT": 10,
            "GRAPH_DPI": 120,
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        factory = GraphFactory(config)
        
        graph_types = [
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "play_count_by_month",
            "top_10_platforms",
            "top_10_users",
        ]
        
        for graph_type in graph_types:
            # Get the class name from the graph type
            class_name_map = {
                "daily_play_count": "DailyPlayCountGraph",
                "play_count_by_dayofweek": "PlayCountByDayOfWeekGraph",
                "play_count_by_hourofday": "PlayCountByHourOfDayGraph",
                "play_count_by_month": "PlayCountByMonthGraph",
                "top_10_platforms": "Top10PlatformsGraph",
                "top_10_users": "Top10UsersGraph",
            }
            
            class_name = class_name_map[graph_type]
            
            with patch(f'src.tgraph_bot.graphs.graph_modules.graph_factory.{class_name}') as mock_graph:
                _ = factory.create_graph_by_type(graph_type)
                
                # Verify dimensions were passed to each graph type
                mock_graph.assert_called_once_with(
                    config=config,
                    width=14,
                    height=10,
                    dpi=120,
                )

    def test_create_enabled_graphs_applies_dimensions(self) -> None:
        """Test that create_enabled_graphs applies dimensions to all enabled graphs."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 10,
            "GRAPH_HEIGHT": 6,
            "GRAPH_DPI": 96,
            "ENABLE_DAILY_PLAY_COUNT": True,
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": False,
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY": True,
            "ENABLE_PLAY_COUNT_BY_MONTH": False,
            "ENABLE_TOP_10_PLATFORMS": False,
            "ENABLE_TOP_10_USERS": True,
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        factory = GraphFactory(config)
        
        # Mock all graph classes
        with patch('src.tgraph_bot.graphs.graph_modules.graph_factory.DailyPlayCountGraph') as mock_daily, \
             patch('src.tgraph_bot.graphs.graph_modules.graph_factory.PlayCountByHourOfDayGraph') as mock_hourly, \
             patch('src.tgraph_bot.graphs.graph_modules.graph_factory.Top10UsersGraph') as mock_users:
            
            # Create enabled graphs
            _ = factory.create_enabled_graphs()
            
            # Verify that only enabled graphs were created with correct dimensions
            mock_daily.assert_called_once_with(config=config, width=10, height=6, dpi=96)
            mock_hourly.assert_called_once_with(config=config, width=10, height=6, dpi=96)
            mock_users.assert_called_once_with(config=config, width=10, height=6, dpi=96)

    def test_graph_factory_with_dict_config(self) -> None:
        """Test that GraphFactory works with dictionary configuration."""
        config_dict = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 15,
            "GRAPH_HEIGHT": 9,
            "GRAPH_DPI": 144,
        }
        factory = GraphFactory(cast(dict[str, object], config_dict))
        
        with patch('src.tgraph_bot.graphs.graph_modules.graph_factory.DailyPlayCountGraph') as mock_daily:
            _ = factory.create_graph_by_type("daily_play_count")
            
            # Verify that dictionary config values were used
            mock_daily.assert_called_once_with(
                config=config_dict,
                width=15,
                height=9,
                dpi=144,
            )

    def test_graph_factory_fallback_to_defaults_when_missing(self) -> None:
        """Test that GraphFactory falls back to defaults when dimension config is missing."""
        config_dict = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            # Missing GRAPH_WIDTH, GRAPH_HEIGHT, GRAPH_DPI
        }
        factory = GraphFactory(cast(dict[str, object], config_dict))
        
        with patch('src.tgraph_bot.graphs.graph_modules.graph_factory.DailyPlayCountGraph') as mock_daily:
            _ = factory.create_graph_by_type("daily_play_count")
            
            # Verify that default values were used
            mock_daily.assert_called_once_with(
                config=config_dict,
                width=12,   # Default
                height=8,   # Default
                dpi=100,    # Default
            )

    def test_graph_factory_with_partial_dimension_config(self) -> None:
        """Test that GraphFactory handles partial dimension configuration."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 14,
            # Missing GRAPH_HEIGHT, GRAPH_DPI - should use defaults
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        factory = GraphFactory(config)
        
        with patch('src.tgraph_bot.graphs.graph_modules.graph_factory.Top10PlatformsGraph') as mock_platforms:
            _ = factory.create_graph_by_type("top_10_platforms")
            
            # Verify that partial config was used with defaults for missing values
            mock_platforms.assert_called_once_with(
                config=config,
                width=14,   # From config
                height=8,   # Default
                dpi=100,    # Default
            )

    def test_sample_graph_receives_dimensions(self) -> None:
        """Test that sample graph also receives dimension configuration."""
        config_dict = {
            "GRAPH_WIDTH": 8,
            "GRAPH_HEIGHT": 6,
            "GRAPH_DPI": 72,
            "ENABLE_SAMPLE_GRAPH": True,
        }
        factory = GraphFactory(cast(dict[str, object], config_dict))
        
        with patch('src.tgraph_bot.graphs.graph_modules.graph_factory.SampleGraph') as mock_sample:
            _ = factory.create_graph_by_type("sample_graph")
            
            # Verify that sample graph received dimensions
            mock_sample.assert_called_once_with(
                config=config_dict,
                width=8,
                height=6,
                dpi=72,
            )

    def test_graph_factory_dimension_extraction_methods(self) -> None:
        """Test internal methods for extracting dimensions from config."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 18,
            "GRAPH_HEIGHT": 14,
            "GRAPH_DPI": 200,
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        factory = GraphFactory(config)
        
        # Test that the factory can extract dimensions from config
        # This tests the internal _get_graph_dimensions method
        dimensions = factory._get_graph_dimensions()  # pyright: ignore[reportPrivateUsage]
        assert dimensions == {"width": 18, "height": 14, "dpi": 200}

    def test_graph_factory_dimension_extraction_with_dict_config(self) -> None:
        """Test dimension extraction from dictionary configuration."""
        config_dict = {
            "GRAPH_WIDTH": 13,
            "GRAPH_HEIGHT": 7,
            "GRAPH_DPI": 110,
        }
        factory = GraphFactory(cast(dict[str, object], config_dict))
        
        # Test dimension extraction from dict
        dimensions = factory._get_graph_dimensions()  # pyright: ignore[reportPrivateUsage]
        assert dimensions == {"width": 13, "height": 7, "dpi": 110}

    def test_graph_factory_dimension_extraction_defaults(self) -> None:
        """Test that dimension extraction provides defaults when config is missing."""
        config_dict = {}  # Empty config
        factory = GraphFactory(cast(dict[str, object], config_dict))
        
        # Test that defaults are provided
        dimensions = factory._get_graph_dimensions()  # pyright: ignore[reportPrivateUsage]
        assert dimensions == {"width": 12, "height": 8, "dpi": 100}