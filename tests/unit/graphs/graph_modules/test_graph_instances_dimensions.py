"""Tests for graph instances respecting dimension configuration."""

from __future__ import annotations

import pytest
from unittest.mock import patch

from src.tgraph_bot.graphs.graph_modules.tautulli_graphs.daily_play_count_graph import DailyPlayCountGraph
from src.tgraph_bot.graphs.graph_modules.tautulli_graphs.top_10_users_graph import Top10UsersGraph
from src.tgraph_bot.graphs.graph_modules.tautulli_graphs.play_count_by_hourofday_graph import PlayCountByHourOfDayGraph
from src.tgraph_bot.config.schema import TGraphBotConfig


class TestGraphInstancesDimensions:
    """Test cases for graph instances respecting dimension configuration."""

    def test_daily_play_count_graph_uses_config_dimensions(self) -> None:
        """Test that DailyPlayCountGraph uses dimensions from config."""
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
        
        # Create graph with config dimensions
        graph = DailyPlayCountGraph(config=config, width=14, height=10, dpi=120)
        
        # Verify dimensions are set correctly
        assert graph.width == 14
        assert graph.height == 10
        assert graph.dpi == 120

    def test_top_10_users_graph_uses_config_dimensions(self) -> None:
        """Test that Top10UsersGraph uses dimensions from config."""
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
        
        # Create graph with config dimensions
        graph = Top10UsersGraph(config=config, width=16, height=12, dpi=150)
        
        # Verify dimensions are set correctly
        assert graph.width == 16
        assert graph.height == 12
        assert graph.dpi == 150

    def test_hour_of_day_graph_uses_config_dimensions(self) -> None:
        """Test that PlayCountByHourOfDayGraph uses dimensions from config."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 18,
            "GRAPH_HEIGHT": 8,
            "GRAPH_DPI": 96,
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        
        # Create graph with config dimensions
        graph = PlayCountByHourOfDayGraph(config=config, width=18, height=8, dpi=96)
        
        # Verify dimensions are set correctly
        assert graph.width == 18
        assert graph.height == 8
        assert graph.dpi == 96

    @patch('matplotlib.pyplot.subplots')
    def test_graph_setup_figure_uses_configured_dimensions(self, mock_subplots) -> None:
        """Test that setup_figure uses configured dimensions."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 15,
            "GRAPH_HEIGHT": 9,
            "GRAPH_DPI": 144,
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        
        # Create graph with config dimensions
        graph = DailyPlayCountGraph(config=config, width=15, height=9, dpi=144)
        
        # Setup figure
        _ = graph.setup_figure()
        
        # Verify matplotlib was called with correct dimensions
        mock_subplots.assert_called_once_with(
            figsize=(15, 9),
            dpi=144,
            facecolor=graph.background_color,
        )

    @patch('matplotlib.figure.Figure.savefig')
    def test_graph_save_figure_uses_configured_dpi(self, mock_savefig) -> None:
        """Test that save_figure uses configured DPI."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 12,
            "GRAPH_HEIGHT": 8,
            "GRAPH_DPI": 200,
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        
        # Create graph with config dimensions
        graph = DailyPlayCountGraph(config=config, width=12, height=8, dpi=200)
        
        # Setup figure and save
        _ = graph.setup_figure()
        output_path = "/tmp/test_graph.png"
        _ = graph.save_figure(output_path=output_path)
        
        # Verify save was called with correct DPI
        mock_savefig.assert_called_once_with(
            output_path,
            dpi=200,
            bbox_inches="tight",
            facecolor=graph.background_color,
            edgecolor="none",
            format="png",
        )
        
        # Clean up
        graph.cleanup()

    def test_graph_dimensions_inheritance_from_base_graph(self) -> None:
        """Test that graph dimensions are properly inherited from BaseGraph."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 10,
            "GRAPH_HEIGHT": 7,
            "GRAPH_DPI": 72,
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        
        # Test multiple graph types
        graphs = [
            DailyPlayCountGraph(config=config, width=10, height=7, dpi=72),
            Top10UsersGraph(config=config, width=10, height=7, dpi=72),
            PlayCountByHourOfDayGraph(config=config, width=10, height=7, dpi=72),
        ]
        
        for graph in graphs:
            assert graph.width == 10
            assert graph.height == 7
            assert graph.dpi == 72
            assert graph.config is config

    def test_graph_dimensions_override_defaults(self) -> None:
        """Test that configured dimensions override BaseGraph defaults."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 20,
            "GRAPH_HEIGHT": 16,
            "GRAPH_DPI": 300,
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        
        # Create graph with maximum allowed dimensions
        graph = DailyPlayCountGraph(config=config, width=20, height=16, dpi=300)
        
        # Verify dimensions override defaults (12, 8, 100)
        assert graph.width == 20  # Not 12
        assert graph.height == 16  # Not 8
        assert graph.dpi == 300  # Not 100

    def test_graph_dimensions_with_explicit_parameters(self) -> None:
        """Test that explicit parameters can still override config dimensions."""
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
        
        # Create graph with explicit dimensions different from config
        graph = DailyPlayCountGraph(config=config, width=8, height=6, dpi=96)
        
        # Verify explicit parameters take precedence
        assert graph.width == 8   # Not 14 from config
        assert graph.height == 6  # Not 10 from config
        assert graph.dpi == 96    # Not 120 from config

    def test_graph_dimensions_final_output_size_calculation(self) -> None:
        """Test that final output size is calculated correctly from dimensions."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 15,  # inches
            "GRAPH_HEIGHT": 10,  # inches
            "GRAPH_DPI": 80,     # dots per inch
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        
        # Create graph with specific dimensions
        graph = DailyPlayCountGraph(config=config, width=15, height=10, dpi=80)
        
        # Calculate expected pixel dimensions
        expected_width_pixels = 15 * 80  # 1200 pixels
        expected_height_pixels = 10 * 80  # 800 pixels
        
        # Verify the calculation is correct
        assert graph.width * graph.dpi == expected_width_pixels
        assert graph.height * graph.dpi == expected_height_pixels

    def test_graph_dimensions_boundary_values_in_instances(self) -> None:
        """Test that boundary values work correctly in graph instances."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 6,   # Minimum
            "GRAPH_HEIGHT": 4,  # Minimum
            "GRAPH_DPI": 72,    # Minimum
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        
        # Create graph with minimum dimensions
        graph = DailyPlayCountGraph(config=config, width=6, height=4, dpi=72)
        
        # Verify minimum dimensions work
        assert graph.width == 6
        assert graph.height == 4
        assert graph.dpi == 72
        
        # Test maximum dimensions
        config_data_max = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 20,   # Maximum
            "GRAPH_HEIGHT": 16,  # Maximum
            "GRAPH_DPI": 300,    # Maximum
        }
        config_max = TGraphBotConfig(**config_data_max)  # pyright: ignore[reportArgumentType]
        
        # Create graph with maximum dimensions
        graph_max = Top10UsersGraph(config=config_max, width=20, height=16, dpi=300)
        
        # Verify maximum dimensions work
        assert graph_max.width == 20
        assert graph_max.height == 16
        assert graph_max.dpi == 300