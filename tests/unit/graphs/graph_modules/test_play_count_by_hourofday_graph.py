"""
Tests for PlayCountByHourOfDayGraph functionality.

This module tests the PlayCountByHourOfDayGraph class including:
- Graph generation
- Data validation
- Empty data handling
"""

from pathlib import Path

import pytest

from src.tgraph_bot.config.schema import TGraphBotConfig
from src.tgraph_bot.graphs.graph_modules.tautulli_graphs.play_count_by_hourofday_graph import PlayCountByHourOfDayGraph
from tests.utils.graph_helpers import (
    create_test_config_minimal,
    matplotlib_cleanup,
)


class TestPlayCountByHourOfDayGraph:
    """Test cases for the PlayCountByHourOfDayGraph class."""

    @pytest.fixture
    def sample_hourofday_data(self) -> dict[str, object]:
        """Sample data for hour of day graph testing."""
        return {
            "play_history": {
                "data": [
                    {"date": "2024-01-01 08:30:00", "media_type": "movie"},
                    {"date": "2024-01-01 14:15:00", "media_type": "tv"},
                    {"date": "2024-01-01 20:45:00", "media_type": "movie"},
                    {"date": "2024-01-02 09:00:00", "media_type": "tv"},
                    {"date": "2024-01-02 15:30:00", "media_type": "movie"},
                    {"date": "2024-01-02 21:00:00", "media_type": "tv"},
                    {"date": "2024-01-03 10:15:00", "media_type": "movie"},
                    {"date": "2024-01-03 16:45:00", "media_type": "tv"},
                    {"date": "2024-01-03 22:30:00", "media_type": "movie"},
                ]
            }
        }

    def test_graph_initialization(self) -> None:
        """Test PlayCountByHourOfDayGraph initialization."""
        graph = PlayCountByHourOfDayGraph()
        assert graph.get_title() == "Play Count by Hour of Day (Last 30 days)"

    def test_graph_initialization_with_config(self) -> None:
        """Test graph initialization with configuration."""
        config = create_test_config_minimal()
        config.TIME_RANGE_DAYS = 7
        
        graph = PlayCountByHourOfDayGraph(config=config)
        assert graph.get_title() == "Play Count by Hour of Day (Last 7 days)"

    def test_graph_initialization_with_dimensions(self) -> None:
        """Test graph initialization with custom dimensions."""
        graph = PlayCountByHourOfDayGraph(width=14, height=10, dpi=120)
        assert graph.width == 14
        assert graph.height == 10
        assert graph.dpi == 120

    def test_generate_with_valid_data(self, sample_hourofday_data: dict[str, object]) -> None:
        """Test graph generation with valid data."""
        with matplotlib_cleanup():
            graph = PlayCountByHourOfDayGraph()
            
            output_path = graph.generate(sample_hourofday_data)
            
            # Verify file was created
            assert Path(output_path).exists()
            assert output_path.endswith('.png')
            assert 'play_count_by_hourofday' in output_path
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)

    def test_generate_with_empty_data(self) -> None:
        """Test graph generation with empty data."""
        with matplotlib_cleanup():
            graph = PlayCountByHourOfDayGraph()
            empty_data: dict[str, object] = {"play_history": {"data": []}}
            
            output_path = graph.generate(empty_data)
            
            # Verify file was created even with empty data
            assert Path(output_path).exists()
            assert output_path.endswith('.png')
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)

    def test_generate_with_invalid_data(self) -> None:
        """Test graph generation with invalid data structure."""
        with matplotlib_cleanup():
            graph = PlayCountByHourOfDayGraph()
            invalid_data: dict[str, object] = {"invalid_key": "invalid_value"}
            
            with pytest.raises(ValueError, match="Invalid play history data"):
                _ = graph.generate(invalid_data)

    def test_configuration_inheritance(self) -> None:
        """Test that configuration methods work correctly."""
        config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token",
            CHANNEL_ID=123456789,
            TIME_RANGE_DAYS=14,
            ANNOTATE_PLAY_COUNT_BY_HOUROFDAY=True,
        )
        
        graph = PlayCountByHourOfDayGraph(config=config)
        
        # Test configuration access methods
        assert graph.get_title() == "Play Count by Hour of Day (Last 14 days)"
        assert graph.get_config_value("ANNOTATE_PLAY_COUNT_BY_HOUROFDAY", False) is True

    def test_uses_data_processor_and_visualization_mixin(self, sample_hourofday_data: dict[str, object]) -> None:
        """Test that the graph uses DataProcessor and VisualizationMixin patterns."""
        with matplotlib_cleanup():
            graph = PlayCountByHourOfDayGraph()
            
            # Verify the graph has the mixin methods
            assert hasattr(graph, 'configure_seaborn_style_with_grid')
            assert hasattr(graph, 'setup_figure_with_styling')
            assert hasattr(graph, 'finalize_and_save_figure')
            assert hasattr(graph, 'handle_empty_data_with_message')
            
            # Test that generation works (implicitly tests DataProcessor usage)
            output_path = graph.generate(sample_hourofday_data)

            # Verify file was created
            assert Path(output_path).exists()

            # Clean up
            Path(output_path).unlink(missing_ok=True)
