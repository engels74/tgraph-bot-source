"""
Consolidated tests for standard graph functionality.

This module consolidates tests for graph implementations that primarily use
the run_standard_graph_tests() utility function, reducing redundancy and
improving maintainability.

Consolidated from:
- test_play_count_by_hourofday_graph.py (standard tests)
- Other graph test files that only use standard test patterns

The tests are parameterized to cover multiple graph types with their
specific sample data and expected behaviors.
"""

import pytest

from src.tgraph_bot.graphs.graph_modules import (
    PlayCountByHourOfDayGraph,
    SampleGraph,
)
from src.tgraph_bot.graphs.graph_modules.core.base_graph import BaseGraph
from tests.utils.graph_helpers import (
    create_test_config_minimal,
    run_standard_graph_tests,
    run_standard_graph_error_tests,
)
from tests.utils.test_helpers import (
    assert_graph_output_valid,
    assert_file_cleanup_successful,
)


class TestStandardGraphs:
    """Consolidated tests for graphs that follow standard patterns."""

    @pytest.fixture
    def sample_hourofday_data(self) -> dict[str, object]:
        """Sample data for hour of day graph testing."""
        return {
            "data": [
                {"date": 1704100200, "media_type": "movie"},  # 2024-01-01 08:30:00 UTC
                {"date": 1704121700, "media_type": "tv"},     # 2024-01-01 14:15:00 UTC
                {"date": 1704143100, "media_type": "movie"},  # 2024-01-01 20:45:00 UTC
                {"date": 1704187200, "media_type": "tv"},     # 2024-01-02 09:00:00 UTC
                {"date": 1704210600, "media_type": "movie"},  # 2024-01-02 15:30:00 UTC
                {"date": 1704230400, "media_type": "tv"},     # 2024-01-02 21:00:00 UTC
                {"date": 1704274500, "media_type": "movie"},  # 2024-01-03 10:15:00 UTC
                {"date": 1704297300, "media_type": "tv"},     # 2024-01-03 16:45:00 UTC
                {"date": 1704320200, "media_type": "movie"},  # 2024-01-03 22:30:00 UTC
            ]
        }

    @pytest.fixture
    def sample_graph_data(self) -> dict[str, object]:
        """Sample data for sample graph testing."""
        return {
            "x_values": [1, 2, 3, 4, 5],
            "y_values": [10, 20, 30, 40, 50]
        }

    @pytest.mark.parametrize(
        "graph_class,sample_data_fixture,expected_title,expected_file_pattern",
        [
            (
                PlayCountByHourOfDayGraph,
                "sample_hourofday_data",
                "Play Count by Hour of Day (Last 30 days)",
                "play_count_by_hourofday",
            ),
        ],
    )
    def test_standard_graph_functionality(
        self,
        graph_class: type,
        sample_data_fixture: str,
        expected_title: str,
        expected_file_pattern: str,
        request: pytest.FixtureRequest,
    ) -> None:
        """Test standard graph functionality using generic test utilities."""
        # Get the sample data from the fixture
        sample_data: dict[str, object] = request.getfixturevalue(sample_data_fixture)  # pyright: ignore[reportAny]

        run_standard_graph_tests(
            graph_class,
            sample_data,
            expected_title,
            expected_file_pattern=expected_file_pattern,
        )

    @pytest.mark.parametrize(
        "graph_class,invalid_data_samples,expected_error_patterns",
        [
            (
                PlayCountByHourOfDayGraph,
                [
                    {"invalid_key": "invalid_value"},
                    {"play_history": "not_a_dict"},
                    {"play_history": {"invalid_structure": True}},
                ],
                [
                    "Missing 'data' in play history extraction",
                    "Missing 'data' in play history extraction",
                    "Missing 'data' in play history extraction",
                ],
            ),
        ],
    )
    def test_standard_error_handling(
        self,
        graph_class: type,
        invalid_data_samples: list[dict[str, object]],
        expected_error_patterns: list[str],
    ) -> None:
        """Test error handling using generic test utilities."""
        run_standard_graph_error_tests(
            graph_class, invalid_data_samples, expected_error_patterns
        )

    @pytest.mark.parametrize(
        "graph_class,config_attribute,config_value,expected_title",
        [
            (
                PlayCountByHourOfDayGraph,
                "TIME_RANGE_DAYS",
                7,
                "Play Count by Hour of Day (Last 7 days)",
            ),
            (
                PlayCountByHourOfDayGraph,
                "TIME_RANGE_DAYS",
                14,
                "Play Count by Hour of Day (Last 14 days)",
            ),
        ],
    )
    def test_configuration_based_titles(
        self,
        graph_class: type[BaseGraph],
        config_attribute: str,
        config_value: object,
        expected_title: str,
    ) -> None:
        """Test that graphs generate correct titles based on configuration."""
        config = create_test_config_minimal()
        setattr(config, config_attribute, config_value)

        graph = graph_class(config=config)
        assert graph.get_title() == expected_title

    @pytest.mark.parametrize(
        "graph_class,config_attribute,config_value",
        [
            (
                PlayCountByHourOfDayGraph,
                "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY",
                True,
            ),
            (
                PlayCountByHourOfDayGraph,
                "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY",
                False,
            ),
        ],
    )
    def test_configuration_access(
        self,
        graph_class: type[BaseGraph],
        config_attribute: str,
        config_value: object,
    ) -> None:
        """Test that graphs can access configuration values correctly."""
        config = create_test_config_minimal()
        setattr(config, config_attribute, config_value)

        graph = graph_class(config=config)
        
        # Test configuration access
        actual_value = graph.get_config_value(config_attribute, not config_value)
        assert actual_value == config_value


class TestSampleGraphSpecific:
    """Tests specifically for SampleGraph which has different data structure."""

    def test_sample_graph_standard_functionality(self) -> None:
        """Test SampleGraph functionality with its specific data structure."""
        from pathlib import Path
        from tests.utils.graph_helpers import matplotlib_cleanup

        # Test data for SampleGraph
        sample_graph_data = {
            "x_values": [1, 2, 3, 4, 5],
            "y_values": [10, 20, 30, 40, 50]
        }

        # Test 1: Basic initialization
        graph = SampleGraph()
        assert graph.get_title() == "Sample Data Visualization"

        # Test 2: Custom dimensions
        graph_custom = SampleGraph(width=14, height=10, dpi=120)
        assert graph_custom.width == 14
        assert graph_custom.height == 10
        assert graph_custom.dpi == 120

        # Test 3: Graph generation with valid data
        with matplotlib_cleanup():
            graph = SampleGraph()
            output_path = graph.generate(sample_graph_data)

            # Verify file was created
            assert_graph_output_valid(
                output_path, expected_filename_pattern="sample_graph"
            )

            # Clean up
            Path(output_path).unlink(missing_ok=True)
            assert_file_cleanup_successful(output_path)

    def test_sample_graph_error_handling(self) -> None:
        """Test SampleGraph error handling with its specific error patterns."""
        from tests.utils.graph_helpers import matplotlib_cleanup
        import pytest

        invalid_data_samples: list[dict[str, object]] = [
            {"invalid_key": "invalid_value"},
            {"x_values": [1, 2, 3], "y_values": [10, 20, 30, 40, 50]},
            {"x_values": [], "y_values": []},
        ]
        expected_error_patterns = [
            "Both 'x_values' and 'y_values' are required in data",
            "x_values and y_values must have the same length",
            "Both 'x_values' and 'y_values' are required in data",
        ]

        for invalid_data, error_pattern in zip(
            invalid_data_samples, expected_error_patterns, strict=True
        ):
            with matplotlib_cleanup():
                graph = SampleGraph()

                with pytest.raises(ValueError, match=error_pattern):
                    _ = graph.generate(invalid_data)


class TestSpecificGraphBehaviors:
    """Tests for graph-specific behaviors that don't fit the standard pattern."""

    def test_play_count_by_hourofday_specific_config(self) -> None:
        """Test PlayCountByHourOfDayGraph specific configuration functionality."""
        config = create_test_config_minimal()
        config.TIME_RANGE_DAYS = 14
        config.ANNOTATE_PLAY_COUNT_BY_HOUROFDAY = True

        graph = PlayCountByHourOfDayGraph(config=config)

        # Test hour-specific title generation
        assert graph.get_title() == "Play Count by Hour of Day (Last 14 days)"

        # Test hour-specific configuration access
        assert graph.get_config_value("ANNOTATE_PLAY_COUNT_BY_HOUROFDAY", False) is True

    def test_sample_graph_custom_parameters(self) -> None:
        """Test SampleGraph with custom initialization parameters."""
        graph = SampleGraph(width=12, height=8, dpi=150, background_color="#f0f0f0")
        
        assert graph.width == 12
        assert graph.height == 8
        assert graph.dpi == 150
        assert graph.background_color == "#f0f0f0"

    def test_sample_graph_data_validation_edge_cases(self) -> None:
        """Test SampleGraph data validation edge cases."""
        graph = SampleGraph()

        # Test valid data
        valid_data = {"x_values": [1, 2, 3, 4, 5], "y_values": [10, 20, 30, 40, 50]}
        assert graph.validate_data(valid_data) is True

        # Test mismatched lengths
        invalid_data = {"x_values": [1, 2, 3], "y_values": [10, 20, 30, 40, 50]}
        assert graph.validate_data(invalid_data) is False

        # Test wrong types
        invalid_data = {"x_values": "not a list", "y_values": [10, 20, 30, 40, 50]}
        assert graph.validate_data(invalid_data) is False

        # Test empty values
        invalid_data: dict[str, object] = {"x_values": [], "y_values": []}
        assert graph.validate_data(invalid_data) is False

    def test_sample_graph_sample_data_structure(self) -> None:
        """Test that SampleGraph returns properly structured sample data."""
        graph = SampleGraph()
        sample_data = graph.get_sample_data()

        # Verify structure
        assert "x_values" in sample_data
        assert "y_values" in sample_data
        
        # Verify data types and lengths
        assert isinstance(sample_data["x_values"], list)
        assert isinstance(sample_data["y_values"], list)
        x_values: list[object] = sample_data["x_values"]  # pyright: ignore[reportUnknownVariableType]
        y_values: list[object] = sample_data["y_values"]  # pyright: ignore[reportUnknownVariableType]
        assert len(x_values) == len(y_values)
        assert len(x_values) > 0
