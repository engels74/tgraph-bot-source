"""
Tests for PlayCountByDayOfWeekGraph functionality.

This module tests the PlayCountByDayOfWeekGraph class including:
- Graph generation
- Stacked bar chart functionality
- Media type separation
- Data validation
"""

from pathlib import Path

import pytest

from config.schema import TGraphBotConfig
from graphs.graph_modules.tautulli_graphs.play_count_by_dayofweek_graph import PlayCountByDayOfWeekGraph
from tests.utils.graph_helpers import (
    create_test_config_minimal,
    matplotlib_cleanup,
)


class TestPlayCountByDayOfWeekGraph:
    """Test cases for the PlayCountByDayOfWeekGraph class."""

    @pytest.fixture
    def sample_dayofweek_data(self) -> dict[str, object]:
        """Create sample data for day of week graph testing."""
        return {
            "play_history": {
                "data": [
                    {"date": "2024-01-01", "media_type": "movie"},
                    {"date": "2024-01-01", "media_type": "tv"},
                    {"date": "2024-01-02", "media_type": "movie"},
                    {"date": "2024-01-02", "media_type": "tv"},
                    {"date": "2024-01-03", "media_type": "movie"},
                    {"date": "2024-01-03", "media_type": "tv"},
                    {"date": "2024-01-04", "media_type": "movie"},
                    {"date": "2024-01-04", "media_type": "tv"},
                    {"date": "2024-01-05", "media_type": "movie"},
                    {"date": "2024-01-05", "media_type": "tv"},
                    {"date": "2024-01-06", "media_type": "movie"},
                    {"date": "2024-01-06", "media_type": "tv"},
                    {"date": "2024-01-07", "media_type": "movie"},
                    {"date": "2024-01-07", "media_type": "tv"},
                ]
            }
        }

    def test_graph_initialization(self) -> None:
        """Test PlayCountByDayOfWeekGraph initialization."""
        graph = PlayCountByDayOfWeekGraph()
        assert graph.get_title() == "Play Count by Day of Week (Last 30 days)"

    def test_graph_initialization_with_config(self) -> None:
        """Test graph initialization with configuration."""
        config = create_test_config_minimal()
        config.ENABLE_STACKED_BAR_CHARTS = True
        
        graph = PlayCountByDayOfWeekGraph(config=config)
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
        graph_enabled = PlayCountByDayOfWeekGraph(config=config_enabled)
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
        graph_disabled = PlayCountByDayOfWeekGraph(config=config_disabled)
        assert graph_disabled.get_stacked_bar_charts_enabled() is False
        assert graph_disabled.get_media_type_separation_enabled() is True

    def test_generate_with_stacked_bars_enabled(self, sample_dayofweek_data: dict[str, object]) -> None:
        """Test graph generation with stacked bar charts enabled."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            config.ENABLE_MEDIA_TYPE_SEPARATION = True
            config.ENABLE_STACKED_BAR_CHARTS = True
            
            graph = PlayCountByDayOfWeekGraph(config=config)
            
            output_path = graph.generate(sample_dayofweek_data)
            
            # Verify file was created
            assert Path(output_path).exists()
            assert output_path.endswith('.png')
            assert 'play_count_by_dayofweek' in output_path
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)

    def test_generate_with_stacked_bars_disabled(self, sample_dayofweek_data: dict[str, object]) -> None:
        """Test graph generation with stacked bar charts disabled."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            config.ENABLE_MEDIA_TYPE_SEPARATION = True
            config.ENABLE_STACKED_BAR_CHARTS = False
            
            graph = PlayCountByDayOfWeekGraph(config=config)
            
            output_path = graph.generate(sample_dayofweek_data)
            
            # Verify file was created
            assert Path(output_path).exists()
            assert output_path.endswith('.png')
            assert 'play_count_by_dayofweek' in output_path
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)

    def test_generate_with_media_separation_disabled(self, sample_dayofweek_data: dict[str, object]) -> None:
        """Test graph generation with media type separation disabled."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            config.ENABLE_MEDIA_TYPE_SEPARATION = False
            config.ENABLE_STACKED_BAR_CHARTS = True  # Should be ignored when separation is off
            
            graph = PlayCountByDayOfWeekGraph(config=config)
            
            output_path = graph.generate(sample_dayofweek_data)
            
            # Verify file was created
            assert Path(output_path).exists()
            assert output_path.endswith('.png')
            assert 'play_count_by_dayofweek' in output_path
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)

    def test_generate_with_empty_data(self) -> None:
        """Test graph generation with empty data."""
        with matplotlib_cleanup():
            graph = PlayCountByDayOfWeekGraph()
            empty_data: dict[str, object] = {"play_history": {"data": []}}
            
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
        
        graph = PlayCountByDayOfWeekGraph(config=config)
        
        # Test configuration access methods
        assert graph.get_stacked_bar_charts_enabled() is True
        assert graph.get_media_type_separation_enabled() is True
        assert graph.get_tv_color() == "#1f77b4"
        assert graph.get_movie_color() == "#ff7f0e"
        assert graph.should_censor_usernames() is True 