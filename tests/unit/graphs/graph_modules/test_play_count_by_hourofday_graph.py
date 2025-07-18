"""
Tests for PlayCountByHourOfDayGraph functionality.

This module tests the PlayCountByHourOfDayGraph class including:
- Graph generation
- Data validation  
- Empty data handling
- Hour-specific functionality
"""

import pytest

from src.tgraph_bot.graphs.graph_modules.tautulli_graphs.play_count_by_hourofday_graph import PlayCountByHourOfDayGraph
from tests.utils.graph_helpers import (
    create_test_config_minimal,
    run_standard_graph_tests,
    run_standard_graph_error_tests,
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

    def test_standard_graph_functionality(self, sample_hourofday_data: dict[str, object]) -> None:
        """Test standard graph functionality using generic test utilities."""
        run_standard_graph_tests(
            PlayCountByHourOfDayGraph,
            sample_hourofday_data,
            "Play Count by Hour of Day (Last 30 days)",
            expected_file_pattern="play_count_by_hourofday"
        )

    def test_graph_initialization_with_config(self) -> None:
        """Test graph initialization with configuration."""
        config = create_test_config_minimal()
        config.TIME_RANGE_DAYS = 7
        
        graph = PlayCountByHourOfDayGraph(config=config)
        assert graph.get_title() == "Play Count by Hour of Day (Last 7 days)"

    def test_error_handling(self) -> None:
        """Test error handling using generic test utilities."""
        invalid_data_samples: list[dict[str, object]] = [
            {"invalid_key": "invalid_value"},
            {"play_history": "not_a_dict"},
            {"play_history": {"invalid_structure": True}},
        ]
        expected_error_patterns = [
            "Invalid play history data",
            "Missing or invalid 'play_history' data",
            "Invalid play history data",
        ]
        
        run_standard_graph_error_tests(
            PlayCountByHourOfDayGraph,
            invalid_data_samples,
            expected_error_patterns
        )

    def test_hour_specific_configuration(self) -> None:
        """Test hour-of-day specific configuration functionality."""
        config = create_test_config_minimal()
        config.TIME_RANGE_DAYS = 14
        config.ANNOTATE_PLAY_COUNT_BY_HOUROFDAY = True
        
        graph = PlayCountByHourOfDayGraph(config=config)
        
        # Test hour-specific title generation
        assert graph.get_title() == "Play Count by Hour of Day (Last 14 days)"
        
        # Test hour-specific configuration access
        assert graph.get_config_value("ANNOTATE_PLAY_COUNT_BY_HOUROFDAY", False) is True
