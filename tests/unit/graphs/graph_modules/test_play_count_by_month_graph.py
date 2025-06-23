"""
Tests for PlayCountByMonthGraph functionality.

This module tests the PlayCountByMonthGraph class including:
- Graph generation
- Stacked bar chart functionality
- Media type separation
- Data validation
"""

from pathlib import Path

import pytest

from config.schema import TGraphBotConfig
from graphs.graph_modules.tautulli_graphs.play_count_by_month_graph import PlayCountByMonthGraph
from tests.utils.graph_helpers import (
    create_test_config_minimal,
    matplotlib_cleanup,
)


class TestPlayCountByMonthGraph:
    """Test cases for the PlayCountByMonthGraph class."""

    @pytest.fixture
    def sample_month_data(self) -> dict[str, object]:
        """Create sample data for monthly graph testing."""
        return {
            "monthly_plays": {
                "categories": ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"],
                "series": [
                    {
                        "name": "TV",
                        "data": [250, 280, 320, 300, 380, 290]
                    },
                    {
                        "name": "Movies",
                        "data": [150, 120, 180, 140, 200, 160]
                    }
                ]
            }
        }

    def test_graph_initialization(self) -> None:
        """Test PlayCountByMonthGraph initialization."""
        graph = PlayCountByMonthGraph()
        assert graph.get_title() == "Play Count by Month (Last 12 months)"

    def test_graph_initialization_with_config(self) -> None:
        """Test graph initialization with configuration."""
        config = create_test_config_minimal()
        config.ENABLE_STACKED_BAR_CHARTS = True
        
        graph = PlayCountByMonthGraph(config=config)
        assert graph.get_stacked_bar_charts_enabled() is True
        assert graph.get_media_type_separation_enabled() is True

    def test_stacked_bar_charts_enabled_configuration(self) -> None:
        """Test that stacked bar charts configuration is properly read."""
        # Test with stacked charts enabled
        config_enabled = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token",
            CHANNEL_ID=123456789,
            ENABLE_MEDIA_TYPE_SEPARATION=True,
            ENABLE_STACKED_BAR_CHARTS=True,
        )
        graph_enabled = PlayCountByMonthGraph(config=config_enabled)
        assert graph_enabled.get_stacked_bar_charts_enabled() is True
        assert graph_enabled.get_media_type_separation_enabled() is True

        # Test with stacked charts disabled
        config_disabled = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token",
            CHANNEL_ID=123456789,
            ENABLE_MEDIA_TYPE_SEPARATION=True,
            ENABLE_STACKED_BAR_CHARTS=False,
        )
        graph_disabled = PlayCountByMonthGraph(config=config_disabled)
        assert graph_disabled.get_stacked_bar_charts_enabled() is False
        assert graph_disabled.get_media_type_separation_enabled() is True

    def test_generate_with_stacked_bars_enabled(self, sample_month_data: dict[str, object]) -> None:
        """Test graph generation with stacked bar charts enabled."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            config.ENABLE_MEDIA_TYPE_SEPARATION = True
            config.ENABLE_STACKED_BAR_CHARTS = True
            
            graph = PlayCountByMonthGraph(config=config)
            
            output_path = graph.generate(sample_month_data)
            
            # Verify file was created
            assert Path(output_path).exists()
            assert output_path.endswith('.png')
            assert 'play_count_by_month' in output_path
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)

    def test_generate_with_stacked_bars_disabled(self, sample_month_data: dict[str, object]) -> None:
        """Test graph generation with stacked bar charts disabled."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            config.ENABLE_MEDIA_TYPE_SEPARATION = True
            config.ENABLE_STACKED_BAR_CHARTS = False
            
            graph = PlayCountByMonthGraph(config=config)
            
            output_path = graph.generate(sample_month_data)
            
            # Verify file was created
            assert Path(output_path).exists()
            assert output_path.endswith('.png')
            assert 'play_count_by_month' in output_path
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)

    def test_generate_with_media_separation_disabled(self, sample_month_data: dict[str, object]) -> None:
        """Test graph generation with media type separation disabled."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            config.ENABLE_MEDIA_TYPE_SEPARATION = False
            config.ENABLE_STACKED_BAR_CHARTS = True  # Should be ignored when separation is off
            
            graph = PlayCountByMonthGraph(config=config)
            
            output_path = graph.generate(sample_month_data)
            
            # Verify file was created
            assert Path(output_path).exists()
            assert output_path.endswith('.png')
            assert 'play_count_by_month' in output_path
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)

    def test_generate_with_empty_data(self) -> None:
        """Test graph generation with empty data."""
        with matplotlib_cleanup():
            graph = PlayCountByMonthGraph()
            empty_data: dict[str, object] = {"monthly_plays": {"categories": [], "series": []}}
            
            output_path = graph.generate(empty_data)
            
            # Verify file was created even with empty data
            assert Path(output_path).exists()
            assert output_path.endswith('.png')
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)

    def test_configuration_inheritance(self) -> None:
        """Test that configuration methods work correctly."""
        config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token",
            CHANNEL_ID=123456789,
            ENABLE_MEDIA_TYPE_SEPARATION=True,
            ENABLE_STACKED_BAR_CHARTS=True,
            TV_COLOR="#1f77b4",
            MOVIE_COLOR="#ff7f0e",
            CENSOR_USERNAMES=True,
        )
        
        graph = PlayCountByMonthGraph(config=config)
        
        # Test configuration access methods
        assert graph.get_stacked_bar_charts_enabled() is True
        assert graph.get_media_type_separation_enabled() is True
        assert graph.get_tv_color() == "#1f77b4"
        assert graph.get_movie_color() == "#ff7f0e"
        assert graph.should_censor_usernames() is True

    def test_monthly_time_range_configuration(self) -> None:
        """Test that monthly time range configuration is respected."""
        config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token",
            CHANNEL_ID=123456789,
            TIME_RANGE_MONTHS=6,  # Custom time range
        )
        
        graph = PlayCountByMonthGraph(config=config)
        
        # Verify config is properly set
        assert graph.config is not None
        # Type guard to ensure we're working with TGraphBotConfig
        assert not isinstance(graph.config, dict), "Config should be TGraphBotConfig, not dict"
        config_obj: TGraphBotConfig = graph.config
        assert config_obj.TIME_RANGE_MONTHS == 6 