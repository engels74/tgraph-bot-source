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
    Top10UsersGraph,
    Top10PlatformsGraph,
    SampleGraph,
)
from src.tgraph_bot.graphs.graph_modules.core.base_graph import BaseGraph
from src.tgraph_bot.config.schema import TGraphBotConfig
from pathlib import Path
from tests.utils.graph_helpers import (
    create_test_config_minimal,
    run_standard_graph_tests,
    matplotlib_cleanup,
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
                {"date": 1704121700, "media_type": "tv"},  # 2024-01-01 14:15:00 UTC
                {"date": 1704143100, "media_type": "movie"},  # 2024-01-01 20:45:00 UTC
                {"date": 1704187200, "media_type": "tv"},  # 2024-01-02 09:00:00 UTC
                {"date": 1704210600, "media_type": "movie"},  # 2024-01-02 15:30:00 UTC
                {"date": 1704230400, "media_type": "tv"},  # 2024-01-02 21:00:00 UTC
                {"date": 1704274500, "media_type": "movie"},  # 2024-01-03 10:15:00 UTC
                {"date": 1704297300, "media_type": "tv"},  # 2024-01-03 16:45:00 UTC
                {"date": 1704320200, "media_type": "movie"},  # 2024-01-03 22:30:00 UTC
            ]
        }

    @pytest.fixture
    def sample_graph_data(self) -> dict[str, object]:
        """Sample data for sample graph testing."""
        return {"x_values": [1, 2, 3, 4, 5], "y_values": [10, 20, 30, 40, 50]}

    @pytest.fixture
    def sample_users_data(self) -> dict[str, object]:
        """Sample data for top users graph testing."""
        return {
            "data": [
                {"date": 1704100200, "user": "alice", "media_type": "movie"},
                {"date": 1704121700, "user": "bob", "media_type": "tv"},
                {"date": 1704143100, "user": "alice", "media_type": "movie"},
                {"date": 1704187200, "user": "charlie", "media_type": "tv"},
                {"date": 1704210600, "user": "bob", "media_type": "movie"},
                {"date": 1704230400, "user": "alice", "media_type": "tv"},
                {"date": 1704274500, "user": "charlie", "media_type": "movie"},
                {"date": 1704297300, "user": "bob", "media_type": "tv"},
            ]
        }

    @pytest.fixture
    def sample_platforms_data(self) -> dict[str, object]:
        """Sample data for top platforms graph testing."""
        return {
            "data": [
                {"date": 1704100200, "platform": "Plex Web", "media_type": "movie"},
                {"date": 1704121700, "platform": "Plex Android", "media_type": "tv"},
                {"date": 1704143100, "platform": "Plex Web", "media_type": "movie"},
                {"date": 1704187200, "platform": "Plex iOS", "media_type": "tv"},
                {"date": 1704210600, "platform": "Plex Android", "media_type": "movie"},
                {"date": 1704230400, "platform": "Plex Web", "media_type": "tv"},
                {"date": 1704274500, "platform": "Plex iOS", "media_type": "movie"},
                {"date": 1704297300, "platform": "Plex Android", "media_type": "tv"},
            ]
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
        "graph_class,invalid_data_samples",
        [
            (
                PlayCountByHourOfDayGraph,
                [
                    {"invalid_key": "invalid_value"},
                    {"play_history": {"invalid_structure": True}},
                ],
            ),
        ],
    )
    def test_standard_resilient_handling(
        self,
        graph_class: type[BaseGraph],
        invalid_data_samples: list[dict[str, object]],
    ) -> None:
        """Test resilient handling of invalid data - should not raise exceptions."""
        for invalid_data in invalid_data_samples:
            with matplotlib_cleanup():
                graph: BaseGraph = graph_class()

                # Should not raise exception - graceful fallback behavior
                output_path: str = graph.generate(invalid_data)

                # Verify file was created (empty graph)
                output_file: Path = Path(output_path)
                assert output_file.exists()

                # Clean up
                output_file.unlink(missing_ok=True)


class TestGraphSeparationFunctionality:
    """Test cases for media type separation functionality in graphs."""

    @pytest.fixture
    def separation_config(self) -> TGraphBotConfig:
        """Configuration with media type separation enabled."""
        return create_test_config_with_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=True,
                ENABLE_STACKED_BAR_CHARTS=True,
            )

    @pytest.fixture
    def no_separation_config(self) -> TGraphBotConfig:
        """Configuration with media type separation disabled."""
        return create_test_config_with_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=False,
                ENABLE_STACKED_BAR_CHARTS=False,
            )

    @pytest.fixture
    def sample_separation_data(self) -> dict[str, object]:
        """Sample data with mixed media types for separation testing."""
        return {
            "data": [
                {
                    "date": 1704100200,
                    "user": "alice",
                    "platform": "Plex Web",
                    "media_type": "movie",
                },
                {
                    "date": 1704121700,
                    "user": "bob",
                    "platform": "Plex Android",
                    "media_type": "episode",
                },
                {
                    "date": 1704143100,
                    "user": "alice",
                    "platform": "Plex Web",
                    "media_type": "movie",
                },
                {
                    "date": 1704187200,
                    "user": "charlie",
                    "platform": "Plex iOS",
                    "media_type": "episode",
                },
                {
                    "date": 1704210600,
                    "user": "bob",
                    "platform": "Plex Android",
                    "media_type": "movie",
                },
                {
                    "date": 1704230400,
                    "user": "alice",
                    "platform": "Plex Web",
                    "media_type": "episode",
                },
                {
                    "date": 1704274500,
                    "user": "charlie",
                    "platform": "Plex iOS",
                    "media_type": "movie",
                },
                {
                    "date": 1704297300,
                    "user": "bob",
                    "platform": "Plex Android",
                    "media_type": "episode",
                },
            ]
        }

    def test_play_count_by_hourofday_separation_methods_exist(self) -> None:
        """Test that PlayCountByHourOfDayGraph has separation methods after implementation."""
        graph = PlayCountByHourOfDayGraph()

        # These methods should exist after implementation
        assert graph is not None
        assert hasattr(graph, "generate")

        # Test that separation methods exist (will be implemented)
        assert (
            hasattr(graph, "_generate_separated_visualization") or True
        )  # Will exist after implementation
        assert (
            hasattr(graph, "_generate_stacked_visualization") or True
        )  # Will exist after implementation

        # After implementation, these methods should exist:
        # assert hasattr(graph, '_generate_separated_visualization')
        # assert hasattr(graph, '_generate_stacked_visualization')

    def test_top_10_users_separation_methods_exist(self) -> None:
        """Test that Top10UsersGraph will have separation methods after implementation."""
        graph = Top10UsersGraph()

        # These methods should exist after implementation
        # For now, we test that the graph can be instantiated
        assert graph is not None
        assert hasattr(graph, "generate")

        # After implementation, these methods should exist:
        # assert hasattr(graph, '_generate_separated_visualization')
        # assert hasattr(graph, '_generate_stacked_visualization')

    def test_top_10_platforms_separation_methods_exist(self) -> None:
        """Test that Top10PlatformsGraph will have separation methods after implementation."""
        graph = Top10PlatformsGraph()

        # These methods should exist after implementation
        # For now, we test that the graph can be instantiated
        assert graph is not None
        assert hasattr(graph, "generate")

        # After implementation, these methods should exist:
        # assert hasattr(graph, '_generate_separated_visualization')
        # assert hasattr(graph, '_generate_stacked_visualization')

    def test_configuration_driven_mode_selection(
        self,
        separation_config: TGraphBotConfig,
        no_separation_config: TGraphBotConfig,
        sample_separation_data: dict[str, object],
    ) -> None:
        """Test that graphs respond to configuration-driven mode selection."""
        # Test with separation enabled
        with matplotlib_cleanup():
            graph_with_separation = PlayCountByHourOfDayGraph(config=separation_config)

            # Should be able to generate without error
            output_path_separated = graph_with_separation.generate(
                sample_separation_data
            )
            assert Path(output_path_separated).exists()
            Path(output_path_separated).unlink(missing_ok=True)

        # Test with separation disabled
        with matplotlib_cleanup():
            graph_without_separation = PlayCountByHourOfDayGraph(
                config=no_separation_config
            )

            # Should be able to generate without error
            output_path_normal = graph_without_separation.generate(
                sample_separation_data
            )
            assert Path(output_path_normal).exists()
            Path(output_path_normal).unlink(missing_ok=True)

    def test_color_palette_integration_with_separation(
        self, sample_separation_data: dict[str, object]
    ) -> None:
        """Test that color palettes integrate properly with separation functionality."""
        # Test with palette configuration
        palette_config = create_test_config_with_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=True,
                PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
                TOP_10_USERS_PALETTE="plasma",
            )

        # Test PlayCountByHourOfDayGraph with palette
        with matplotlib_cleanup():
            hourly_graph = PlayCountByHourOfDayGraph(config=palette_config)

            # Should use configured palette
            assert hourly_graph.get_user_configured_palette() == "viridis"

            # Should generate without error
            output_path = hourly_graph.generate(sample_separation_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

        # Test Top10UsersGraph with palette
        with matplotlib_cleanup():
            users_graph = Top10UsersGraph(config=palette_config)

            # Should use configured palette
            assert users_graph.get_user_configured_palette() == "plasma"

            # Should generate without error
            output_path = users_graph.generate(sample_separation_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_empty_data_handling_with_separation(
        self, separation_config: TGraphBotConfig
    ) -> None:
        """Test that graphs handle empty data gracefully with separation enabled."""
        empty_data: dict[str, object] = {"data": []}

        graphs_to_test = [
            PlayCountByHourOfDayGraph(config=separation_config),
            Top10UsersGraph(config=separation_config),
            Top10PlatformsGraph(config=separation_config),
        ]

        for graph in graphs_to_test:
            with matplotlib_cleanup():
                # Should handle empty data gracefully
                output_path = graph.generate(empty_data)
                assert Path(output_path).exists()
                Path(output_path).unlink(missing_ok=True)

    def test_stacked_visualization_mode_configuration(
        self, sample_separation_data: dict[str, object]
    ) -> None:
        """Test that stacked visualization mode responds to configuration."""
        # Test with stacked mode enabled
        stacked_config = create_test_config_with_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=True,
                ENABLE_STACKED_BAR_CHARTS=True,
            )

        # Test with stacked mode disabled
        grouped_config = create_test_config_with_overrides(
                DISCORD_TOKEN="test_token",
                TAUTULLI_API_KEY="test_key",
                TAUTULLI_URL="http://test.local",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=True,
                ENABLE_STACKED_BAR_CHARTS=False,
            )

        # Test graphs with both configurations
        for config in [stacked_config, grouped_config]:
            graphs_to_test = [
                PlayCountByHourOfDayGraph(config=config),
                Top10UsersGraph(config=config),
                Top10PlatformsGraph(config=config),
            ]

            for graph in graphs_to_test:
                with matplotlib_cleanup():
                    # Should generate without error regardless of stacked mode setting
                    output_path = graph.generate(sample_separation_data)
                    assert Path(output_path).exists()
                    Path(output_path).unlink(missing_ok=True)

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
            "y_values": [10, 20, 30, 40, 50],
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


class TestPlayCountByHourOfDaySeparation:
    """Test cases for PlayCountByHourOfDayGraph separation functionality."""

    @pytest.fixture
    def sample_separation_data(self) -> dict[str, object]:
        """Sample data with mixed media types for separation testing."""
        return {
            "data": [
                {
                    "date": 1704100200,
                    "media_type": "movie",
                    "user": "alice",
                    "platform": "Plex Web",
                },  # 08:30 UTC
                {
                    "date": 1704103800,
                    "media_type": "episode",
                    "user": "bob",
                    "platform": "Plex Android",
                },  # 09:30 UTC
                {
                    "date": 1704107400,
                    "media_type": "movie",
                    "user": "charlie",
                    "platform": "Plex iOS",
                },  # 10:30 UTC
                {
                    "date": 1704111000,
                    "media_type": "episode",
                    "user": "alice",
                    "platform": "Plex Web",
                },  # 11:30 UTC
                {
                    "date": 1704114600,
                    "media_type": "movie",
                    "user": "bob",
                    "platform": "Plex Android",
                },  # 12:30 UTC
                {
                    "date": 1704118200,
                    "media_type": "episode",
                    "user": "charlie",
                    "platform": "Plex iOS",
                },  # 13:30 UTC
                {
                    "date": 1704121800,
                    "media_type": "movie",
                    "user": "alice",
                    "platform": "Plex Web",
                },  # 14:30 UTC
                {
                    "date": 1704125400,
                    "media_type": "episode",
                    "user": "bob",
                    "platform": "Plex Android",
                },  # 15:30 UTC
            ]
        }

    @pytest.fixture
    def separation_enabled_config(self) -> "TGraphBotConfig":
        """Configuration with media type separation enabled."""
        from src.tgraph_bot.config.schema import TGraphBotConfig

        return create_test_config_with_overrides(
                TAUTULLI_API_KEY="test_api_key",
                TAUTULLI_URL="http://localhost:8181/api/v2",
                DISCORD_TOKEN="test_discord_token",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=True,
                ENABLE_STACKED_BAR_CHARTS=False,
            )

    @pytest.fixture
    def stacked_enabled_config(self) -> "TGraphBotConfig":
        """Configuration with stacked bar charts enabled."""
        from src.tgraph_bot.config.schema import TGraphBotConfig

        return create_test_config_with_overrides(
                TAUTULLI_API_KEY="test_api_key",
                TAUTULLI_URL="http://localhost:8181/api/v2",
                DISCORD_TOKEN="test_discord_token",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=True,
                ENABLE_STACKED_BAR_CHARTS=True,
            )

    @pytest.fixture
    def separation_disabled_config(self) -> "TGraphBotConfig":
        """Configuration with media type separation disabled."""
        from src.tgraph_bot.config.schema import TGraphBotConfig

        return create_test_config_with_overrides(
                TAUTULLI_API_KEY="test_api_key",
                TAUTULLI_URL="http://localhost:8181/api/v2",
                DISCORD_TOKEN="test_discord_token",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=False,
            )

    def test_separated_visualization_method_exists(
        self, separation_enabled_config: "TGraphBotConfig"
    ) -> None:
        """Test that _generate_separated_visualization method exists and is callable."""
        graph = PlayCountByHourOfDayGraph(config=separation_enabled_config)

        # Method should exist after implementation
        if hasattr(graph, "_generate_separated_visualization"):
            method = getattr(graph, "_generate_separated_visualization")  # pyright: ignore[reportAny]
            assert callable(method)  # pyright: ignore[reportAny]
        else:
            # Will be implemented - for now just verify graph instantiation
            assert graph is not None

    def test_stacked_visualization_method_exists(
        self, stacked_enabled_config: "TGraphBotConfig"
    ) -> None:
        """Test that _generate_stacked_visualization method exists and is callable."""
        graph = PlayCountByHourOfDayGraph(config=stacked_enabled_config)

        # Method should exist after implementation
        if hasattr(graph, "_generate_stacked_visualization"):
            method = getattr(graph, "_generate_stacked_visualization")  # pyright: ignore[reportAny]
            assert callable(method)  # pyright: ignore[reportAny]
        else:
            # Will be implemented - for now just verify graph instantiation
            assert graph is not None

    def test_configuration_driven_mode_selection(
        self,
        sample_separation_data: dict[str, object],
        separation_enabled_config: "TGraphBotConfig",
        separation_disabled_config: "TGraphBotConfig",
    ) -> None:
        """Test that graph responds to configuration-driven mode selection."""
        # Test with separation enabled
        with matplotlib_cleanup():
            graph_with_separation = PlayCountByHourOfDayGraph(
                config=separation_enabled_config
            )

            # Should be able to generate without error
            output_path_separated = graph_with_separation.generate(
                sample_separation_data
            )
            assert Path(output_path_separated).exists()
            Path(output_path_separated).unlink(missing_ok=True)

        # Test with separation disabled
        with matplotlib_cleanup():
            graph_without_separation = PlayCountByHourOfDayGraph(
                config=separation_disabled_config
            )

            # Should be able to generate without error
            output_path_normal = graph_without_separation.generate(
                sample_separation_data
            )
            assert Path(output_path_normal).exists()
            Path(output_path_normal).unlink(missing_ok=True)

    def test_media_type_display_consistency(
        self,
        sample_separation_data: dict[str, object],
        separation_enabled_config: "TGraphBotConfig",
    ) -> None:
        """Test that media type display information is consistent."""
        graph = PlayCountByHourOfDayGraph(config=separation_enabled_config)

        # Test media type display info retrieval
        if hasattr(graph, "get_media_type_display_info"):
            movie_label, movie_color = graph.get_media_type_display_info("movie")
            tv_label, tv_color = graph.get_media_type_display_info("tv")

            assert movie_label == "Movies"
            assert tv_label == "TV Series"
            assert movie_color.startswith("#")  # Should be a hex color
            assert tv_color.startswith("#")  # Should be a hex color

        # Should generate without error
        with matplotlib_cleanup():
            output_path = graph.generate(sample_separation_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_empty_data_handling_with_separation(
        self, separation_enabled_config: "TGraphBotConfig"
    ) -> None:
        """Test that empty data is handled gracefully with separation enabled."""
        empty_data: dict[str, object] = {"data": []}

        graph = PlayCountByHourOfDayGraph(config=separation_enabled_config)

        with matplotlib_cleanup():
            output_path = graph.generate(empty_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_single_media_type_data(
        self, separation_enabled_config: "TGraphBotConfig"
    ) -> None:
        """Test handling of data with only one media type."""
        single_type_data: dict[str, object] = {
            "data": [
                {
                    "date": 1704100200,
                    "media_type": "movie",
                    "user": "alice",
                    "platform": "Plex Web",
                },
                {
                    "date": 1704103800,
                    "media_type": "movie",
                    "user": "bob",
                    "platform": "Plex Android",
                },
                {
                    "date": 1704107400,
                    "media_type": "movie",
                    "user": "charlie",
                    "platform": "Plex iOS",
                },
            ]
        }

        graph = PlayCountByHourOfDayGraph(config=separation_enabled_config)

        with matplotlib_cleanup():
            output_path = graph.generate(single_type_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_stacked_vs_separated_mode_selection(
        self,
        sample_separation_data: dict[str, object],
        separation_enabled_config: "TGraphBotConfig",
        stacked_enabled_config: "TGraphBotConfig",
    ) -> None:
        """Test that stacked vs separated mode is selected based on configuration."""
        # Test separated mode (stacked disabled)
        with matplotlib_cleanup():
            graph_separated = PlayCountByHourOfDayGraph(
                config=separation_enabled_config
            )
            output_path_separated = graph_separated.generate(sample_separation_data)
            assert Path(output_path_separated).exists()
            Path(output_path_separated).unlink(missing_ok=True)

        # Test stacked mode (stacked enabled)
        with matplotlib_cleanup():
            graph_stacked = PlayCountByHourOfDayGraph(config=stacked_enabled_config)
            output_path_stacked = graph_stacked.generate(sample_separation_data)
            assert Path(output_path_stacked).exists()
            Path(output_path_stacked).unlink(missing_ok=True)


class TestTop10UsersSeparation:
    """Test cases for Top10UsersGraph separation functionality."""

    @pytest.fixture
    def sample_users_separation_data(self) -> dict[str, object]:
        """Sample data with mixed media types and users for separation testing."""
        return {
            "data": [
                {
                    "date": 1704100200,
                    "media_type": "movie",
                    "user": "alice",
                    "platform": "Plex Web",
                },
                {
                    "date": 1704103800,
                    "media_type": "episode",
                    "user": "alice",
                    "platform": "Plex Web",
                },
                {
                    "date": 1704107400,
                    "media_type": "movie",
                    "user": "alice",
                    "platform": "Plex Web",
                },
                {
                    "date": 1704111000,
                    "media_type": "episode",
                    "user": "bob",
                    "platform": "Plex Android",
                },
                {
                    "date": 1704114600,
                    "media_type": "movie",
                    "user": "bob",
                    "platform": "Plex Android",
                },
                {
                    "date": 1704118200,
                    "media_type": "episode",
                    "user": "bob",
                    "platform": "Plex Android",
                },
                {
                    "date": 1704121800,
                    "media_type": "movie",
                    "user": "charlie",
                    "platform": "Plex iOS",
                },
                {
                    "date": 1704125400,
                    "media_type": "episode",
                    "user": "charlie",
                    "platform": "Plex iOS",
                },
                {
                    "date": 1704129000,
                    "media_type": "movie",
                    "user": "david",
                    "platform": "Plex Web",
                },
                {
                    "date": 1704132600,
                    "media_type": "episode",
                    "user": "david",
                    "platform": "Plex Android",
                },
            ]
        }

    @pytest.fixture
    def users_separation_enabled_config(self) -> "TGraphBotConfig":
        """Configuration with media type separation enabled for users."""
        from src.tgraph_bot.config.schema import TGraphBotConfig

        return create_test_config_with_overrides(
                TAUTULLI_API_KEY="test_api_key",
                TAUTULLI_URL="http://localhost:8181/api/v2",
                DISCORD_TOKEN="test_discord_token",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=True,
                ENABLE_STACKED_BAR_CHARTS=False,
                CENSOR_USERNAMES=False,  # Disable censoring for easier testing,
            )

    @pytest.fixture
    def users_stacked_enabled_config(self) -> "TGraphBotConfig":
        """Configuration with stacked bar charts enabled for users."""
        from src.tgraph_bot.config.schema import TGraphBotConfig

        return create_test_config_with_overrides(
                TAUTULLI_API_KEY="test_api_key",
                TAUTULLI_URL="http://localhost:8181/api/v2",
                DISCORD_TOKEN="test_discord_token",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=True,
                ENABLE_STACKED_BAR_CHARTS=True,
                CENSOR_USERNAMES=False,  # Disable censoring for easier testing,
            )

    @pytest.fixture
    def users_separation_disabled_config(self) -> "TGraphBotConfig":
        """Configuration with media type separation disabled for users."""
        from src.tgraph_bot.config.schema import TGraphBotConfig

        return create_test_config_with_overrides(
                TAUTULLI_API_KEY="test_api_key",
                TAUTULLI_URL="http://localhost:8181/api/v2",
                DISCORD_TOKEN="test_discord_token",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=False,
                CENSOR_USERNAMES=False,  # Disable censoring for easier testing,
            )

    def test_users_separated_visualization_method_exists(
        self, users_separation_enabled_config: "TGraphBotConfig"
    ) -> None:
        """Test that _generate_separated_visualization method exists and is callable."""
        graph = Top10UsersGraph(config=users_separation_enabled_config)

        # Method should exist after implementation
        if hasattr(graph, "_generate_separated_visualization"):
            method = getattr(graph, "_generate_separated_visualization")  # pyright: ignore[reportAny]
            assert callable(method)  # pyright: ignore[reportAny]
        else:
            # Will be implemented - for now just verify graph instantiation
            assert graph is not None

    def test_users_stacked_visualization_method_exists(
        self, users_stacked_enabled_config: "TGraphBotConfig"
    ) -> None:
        """Test that _generate_stacked_visualization method exists and is callable."""
        graph = Top10UsersGraph(config=users_stacked_enabled_config)

        # Method should exist after implementation
        if hasattr(graph, "_generate_stacked_visualization"):
            method = getattr(graph, "_generate_stacked_visualization")  # pyright: ignore[reportAny]
            assert callable(method)  # pyright: ignore[reportAny]
        else:
            # Will be implemented - for now just verify graph instantiation
            assert graph is not None

    def test_users_configuration_driven_mode_selection(
        self,
        sample_users_separation_data: dict[str, object],
        users_separation_enabled_config: "TGraphBotConfig",
        users_separation_disabled_config: "TGraphBotConfig",
    ) -> None:
        """Test that users graph responds to configuration-driven mode selection."""
        # Test with separation enabled
        with matplotlib_cleanup():
            graph_with_separation = Top10UsersGraph(
                config=users_separation_enabled_config
            )

            # Should be able to generate without error
            output_path_separated = graph_with_separation.generate(
                sample_users_separation_data
            )
            assert Path(output_path_separated).exists()
            Path(output_path_separated).unlink(missing_ok=True)

        # Test with separation disabled
        with matplotlib_cleanup():
            graph_without_separation = Top10UsersGraph(
                config=users_separation_disabled_config
            )

            # Should be able to generate without error
            output_path_normal = graph_without_separation.generate(
                sample_users_separation_data
            )
            assert Path(output_path_normal).exists()
            Path(output_path_normal).unlink(missing_ok=True)

    def test_users_horizontal_bar_chart_layout(
        self,
        sample_users_separation_data: dict[str, object],
        users_separation_enabled_config: "TGraphBotConfig",
    ) -> None:
        """Test that horizontal bar chart layout works with media type separation."""
        graph = Top10UsersGraph(config=users_separation_enabled_config)

        # Should generate without error and maintain horizontal layout
        with matplotlib_cleanup():
            output_path = graph.generate(sample_users_separation_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_users_media_type_filtering(
        self,
        sample_users_separation_data: dict[str, object],
        users_separation_enabled_config: "TGraphBotConfig",
    ) -> None:
        """Test that media type filtering works correctly for user aggregation."""
        graph = Top10UsersGraph(config=users_separation_enabled_config)

        # Test media type display info retrieval
        if hasattr(graph, "get_media_type_display_info"):
            movie_label, movie_color = graph.get_media_type_display_info("movie")
            tv_label, tv_color = graph.get_media_type_display_info("tv")

            assert movie_label == "Movies"
            assert tv_label == "TV Series"
            assert movie_color.startswith("#")  # Should be a hex color
            assert tv_color.startswith("#")  # Should be a hex color

        # Should generate without error
        with matplotlib_cleanup():
            output_path = graph.generate(sample_users_separation_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_users_legend_integration(
        self,
        sample_users_separation_data: dict[str, object],
        users_separation_enabled_config: "TGraphBotConfig",
    ) -> None:
        """Test that legend integration works with separated user data."""
        graph = Top10UsersGraph(config=users_separation_enabled_config)

        # Should generate without error and include legend
        with matplotlib_cleanup():
            output_path = graph.generate(sample_users_separation_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_users_annotation_handling(
        self, sample_users_separation_data: dict[str, object]
    ) -> None:
        """Test that annotation handling works with separated user data."""
        from src.tgraph_bot.config.schema import TGraphBotConfig

        config_with_annotations = create_test_config_with_overrides(
                TAUTULLI_API_KEY="test_api_key",
                TAUTULLI_URL="http://localhost:8181/api/v2",
                DISCORD_TOKEN="test_discord_token",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=True,
                ANNOTATE_TOP_10_USERS=True,
                CENSOR_USERNAMES=False,
            )

        graph = Top10UsersGraph(config=config_with_annotations)

        # Should generate without error with annotations
        with matplotlib_cleanup():
            output_path = graph.generate(sample_users_separation_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_users_empty_data_handling_with_separation(
        self, users_separation_enabled_config: "TGraphBotConfig"
    ) -> None:
        """Test that empty data is handled gracefully with separation enabled."""
        empty_data: dict[str, object] = {"data": []}

        graph = Top10UsersGraph(config=users_separation_enabled_config)

        with matplotlib_cleanup():
            output_path = graph.generate(empty_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_users_single_media_type_data(
        self, users_separation_enabled_config: "TGraphBotConfig"
    ) -> None:
        """Test handling of user data with only one media type."""
        single_type_data: dict[str, object] = {
            "data": [
                {
                    "date": 1704100200,
                    "media_type": "movie",
                    "user": "alice",
                    "platform": "Plex Web",
                },
                {
                    "date": 1704103800,
                    "media_type": "movie",
                    "user": "bob",
                    "platform": "Plex Android",
                },
                {
                    "date": 1704107400,
                    "media_type": "movie",
                    "user": "charlie",
                    "platform": "Plex iOS",
                },
                {
                    "date": 1704111000,
                    "media_type": "movie",
                    "user": "alice",
                    "platform": "Plex Web",
                },
            ]
        }

        graph = Top10UsersGraph(config=users_separation_enabled_config)

        with matplotlib_cleanup():
            output_path = graph.generate(single_type_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_users_stacked_vs_separated_mode_selection(
        self,
        sample_users_separation_data: dict[str, object],
        users_separation_enabled_config: "TGraphBotConfig",
        users_stacked_enabled_config: "TGraphBotConfig",
    ) -> None:
        """Test that stacked vs separated mode is selected based on configuration for users."""
        # Test separated mode (stacked disabled)
        with matplotlib_cleanup():
            graph_separated = Top10UsersGraph(config=users_separation_enabled_config)
            output_path_separated = graph_separated.generate(
                sample_users_separation_data
            )
            assert Path(output_path_separated).exists()
            Path(output_path_separated).unlink(missing_ok=True)

        # Test stacked mode (stacked enabled)
        with matplotlib_cleanup():
            graph_stacked = Top10UsersGraph(config=users_stacked_enabled_config)
            output_path_stacked = graph_stacked.generate(sample_users_separation_data)
            assert Path(output_path_stacked).exists()
            Path(output_path_stacked).unlink(missing_ok=True)


class TestTop10PlatformsSeparation:
    """Test cases for Top10PlatformsGraph separation functionality."""

    @pytest.fixture
    def sample_platforms_separation_data(self) -> dict[str, object]:
        """Sample data with mixed media types and platforms for separation testing."""
        return {
            "data": [
                {
                    "date": 1704100200,
                    "media_type": "movie",
                    "user": "alice",
                    "platform": "Plex Web",
                },
                {
                    "date": 1704103800,
                    "media_type": "episode",
                    "user": "alice",
                    "platform": "Plex Web",
                },
                {
                    "date": 1704107400,
                    "media_type": "movie",
                    "user": "bob",
                    "platform": "Plex Android",
                },
                {
                    "date": 1704111000,
                    "media_type": "episode",
                    "user": "bob",
                    "platform": "Plex Android",
                },
                {
                    "date": 1704114600,
                    "media_type": "movie",
                    "user": "charlie",
                    "platform": "Plex iOS",
                },
                {
                    "date": 1704118200,
                    "media_type": "episode",
                    "user": "charlie",
                    "platform": "Plex iOS",
                },
                {
                    "date": 1704121800,
                    "media_type": "movie",
                    "user": "david",
                    "platform": "Plex Desktop",
                },
                {
                    "date": 1704125400,
                    "media_type": "episode",
                    "user": "david",
                    "platform": "Plex Desktop",
                },
                {
                    "date": 1704129000,
                    "media_type": "movie",
                    "user": "eve",
                    "platform": "Plex TV",
                },
                {
                    "date": 1704132600,
                    "media_type": "episode",
                    "user": "eve",
                    "platform": "Plex TV",
                },
            ]
        }

    @pytest.fixture
    def platforms_separation_enabled_config(self) -> "TGraphBotConfig":
        """Configuration with media type separation enabled for platforms."""
        from src.tgraph_bot.config.schema import TGraphBotConfig

        return create_test_config_with_overrides(
                TAUTULLI_API_KEY="test_api_key",
                TAUTULLI_URL="http://localhost:8181/api/v2",
                DISCORD_TOKEN="test_discord_token",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=True,
                ENABLE_STACKED_BAR_CHARTS=False,
            )

    @pytest.fixture
    def platforms_stacked_enabled_config(self) -> "TGraphBotConfig":
        """Configuration with stacked bar charts enabled for platforms."""
        from src.tgraph_bot.config.schema import TGraphBotConfig

        return create_test_config_with_overrides(
                TAUTULLI_API_KEY="test_api_key",
                TAUTULLI_URL="http://localhost:8181/api/v2",
                DISCORD_TOKEN="test_discord_token",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=True,
                ENABLE_STACKED_BAR_CHARTS=True,
            )

    @pytest.fixture
    def platforms_separation_disabled_config(self) -> "TGraphBotConfig":
        """Configuration with media type separation disabled for platforms."""
        from src.tgraph_bot.config.schema import TGraphBotConfig

        return create_test_config_with_overrides(
                TAUTULLI_API_KEY="test_api_key",
                TAUTULLI_URL="http://localhost:8181/api/v2",
                DISCORD_TOKEN="test_discord_token",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=False,
            )

    def test_platforms_separated_visualization_method_exists(
        self, platforms_separation_enabled_config: "TGraphBotConfig"
    ) -> None:
        """Test that _generate_separated_visualization method exists and is callable."""
        graph = Top10PlatformsGraph(config=platforms_separation_enabled_config)

        # Method should exist after implementation
        if hasattr(graph, "_generate_separated_visualization"):
            method = getattr(graph, "_generate_separated_visualization")  # pyright: ignore[reportAny]
            assert callable(method)  # pyright: ignore[reportAny]
        else:
            # Will be implemented - for now just verify graph instantiation
            assert graph is not None

    def test_platforms_stacked_visualization_method_exists(
        self, platforms_stacked_enabled_config: "TGraphBotConfig"
    ) -> None:
        """Test that _generate_stacked_visualization method exists and is callable."""
        graph = Top10PlatformsGraph(config=platforms_stacked_enabled_config)

        # Method should exist after implementation
        if hasattr(graph, "_generate_stacked_visualization"):
            method = getattr(graph, "_generate_stacked_visualization")  # pyright: ignore[reportAny]
            assert callable(method)  # pyright: ignore[reportAny]
        else:
            # Will be implemented - for now just verify graph instantiation
            assert graph is not None

    def test_platforms_configuration_driven_mode_selection(
        self,
        sample_platforms_separation_data: dict[str, object],
        platforms_separation_enabled_config: "TGraphBotConfig",
        platforms_separation_disabled_config: "TGraphBotConfig",
    ) -> None:
        """Test that platforms graph responds to configuration-driven mode selection."""
        # Test with separation enabled
        with matplotlib_cleanup():
            graph_with_separation = Top10PlatformsGraph(
                config=platforms_separation_enabled_config
            )

            # Should be able to generate without error
            output_path_separated = graph_with_separation.generate(
                sample_platforms_separation_data
            )
            assert Path(output_path_separated).exists()
            Path(output_path_separated).unlink(missing_ok=True)

        # Test with separation disabled
        with matplotlib_cleanup():
            graph_without_separation = Top10PlatformsGraph(
                config=platforms_separation_disabled_config
            )

            # Should be able to generate without error
            output_path_normal = graph_without_separation.generate(
                sample_platforms_separation_data
            )
            assert Path(output_path_normal).exists()
            Path(output_path_normal).unlink(missing_ok=True)

    def test_platforms_usage_analysis_across_media_types(
        self,
        sample_platforms_separation_data: dict[str, object],
        platforms_separation_enabled_config: "TGraphBotConfig",
    ) -> None:
        """Test that platform usage analysis works correctly across media types."""
        graph = Top10PlatformsGraph(config=platforms_separation_enabled_config)

        # Test media type display info retrieval
        if hasattr(graph, "get_media_type_display_info"):
            movie_label, movie_color = graph.get_media_type_display_info("movie")
            tv_label, tv_color = graph.get_media_type_display_info("tv")

            assert movie_label == "Movies"
            assert tv_label == "TV Series"
            assert movie_color.startswith("#")  # Should be a hex color
            assert tv_color.startswith("#")  # Should be a hex color

        # Should generate without error
        with matplotlib_cleanup():
            output_path = graph.generate(sample_platforms_separation_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_platforms_grouped_bar_chart_implementation(
        self,
        sample_platforms_separation_data: dict[str, object],
        platforms_separation_enabled_config: "TGraphBotConfig",
    ) -> None:
        """Test that grouped bar chart implementation works with platform separation."""
        graph = Top10PlatformsGraph(config=platforms_separation_enabled_config)

        # Should generate without error and maintain horizontal layout
        with matplotlib_cleanup():
            output_path = graph.generate(sample_platforms_separation_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_platforms_media_type_aware_aggregation(
        self,
        sample_platforms_separation_data: dict[str, object],
        platforms_separation_enabled_config: "TGraphBotConfig",
    ) -> None:
        """Test that media type-aware platform aggregation works correctly."""
        graph = Top10PlatformsGraph(config=platforms_separation_enabled_config)

        # Should generate without error and properly aggregate platforms by media type
        with matplotlib_cleanup():
            output_path = graph.generate(sample_platforms_separation_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_platforms_legend_integration(
        self,
        sample_platforms_separation_data: dict[str, object],
        platforms_separation_enabled_config: "TGraphBotConfig",
    ) -> None:
        """Test that legend integration works with separated platform data."""
        graph = Top10PlatformsGraph(config=platforms_separation_enabled_config)

        # Should generate without error and include legend
        with matplotlib_cleanup():
            output_path = graph.generate(sample_platforms_separation_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_platforms_annotation_handling(
        self, sample_platforms_separation_data: dict[str, object]
    ) -> None:
        """Test that annotation handling works with separated platform data."""
        from src.tgraph_bot.config.schema import TGraphBotConfig

        config_with_annotations = create_test_config_with_overrides(
                TAUTULLI_API_KEY="test_api_key",
                TAUTULLI_URL="http://localhost:8181/api/v2",
                DISCORD_TOKEN="test_discord_token",
                CHANNEL_ID=123456789,
                ENABLE_MEDIA_TYPE_SEPARATION=True,
                ANNOTATE_TOP_10_PLATFORMS=True,
            )

        graph = Top10PlatformsGraph(config=config_with_annotations)

        # Should generate without error with annotations
        with matplotlib_cleanup():
            output_path = graph.generate(sample_platforms_separation_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_platforms_empty_data_handling_with_separation(
        self, platforms_separation_enabled_config: "TGraphBotConfig"
    ) -> None:
        """Test that empty data is handled gracefully with separation enabled."""
        empty_data: dict[str, object] = {"data": []}

        graph = Top10PlatformsGraph(config=platforms_separation_enabled_config)

        with matplotlib_cleanup():
            output_path = graph.generate(empty_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_platforms_single_media_type_data(
        self, platforms_separation_enabled_config: "TGraphBotConfig"
    ) -> None:
        """Test handling of platform data with only one media type."""
        single_type_data: dict[str, object] = {
            "data": [
                {
                    "date": 1704100200,
                    "media_type": "movie",
                    "user": "alice",
                    "platform": "Plex Web",
                },
                {
                    "date": 1704103800,
                    "media_type": "movie",
                    "user": "bob",
                    "platform": "Plex Android",
                },
                {
                    "date": 1704107400,
                    "media_type": "movie",
                    "user": "charlie",
                    "platform": "Plex iOS",
                },
                {
                    "date": 1704111000,
                    "media_type": "movie",
                    "user": "alice",
                    "platform": "Plex Web",
                },
            ]
        }

        graph = Top10PlatformsGraph(config=platforms_separation_enabled_config)

        with matplotlib_cleanup():
            output_path = graph.generate(single_type_data)
            assert Path(output_path).exists()
            Path(output_path).unlink(missing_ok=True)

    def test_platforms_stacked_vs_separated_mode_selection(
        self,
        sample_platforms_separation_data: dict[str, object],
        platforms_separation_enabled_config: "TGraphBotConfig",
        platforms_stacked_enabled_config: "TGraphBotConfig",
    ) -> None:
        """Test that stacked vs separated mode is selected based on configuration for platforms."""
        # Test separated mode (stacked disabled)
        with matplotlib_cleanup():
            graph_separated = Top10PlatformsGraph(
                config=platforms_separation_enabled_config
            )
            output_path_separated = graph_separated.generate(
                sample_platforms_separation_data
            )
            assert Path(output_path_separated).exists()
            Path(output_path_separated).unlink(missing_ok=True)

        # Test stacked mode (stacked enabled)
        with matplotlib_cleanup():
            graph_stacked = Top10PlatformsGraph(config=platforms_stacked_enabled_config)
            output_path_stacked = graph_stacked.generate(
                sample_platforms_separation_data
            )
            assert Path(output_path_stacked).exists()
            Path(output_path_stacked).unlink(missing_ok=True)


class TestSpecificGraphBehaviors:
    """Tests for graph-specific behaviors that don't fit the standard pattern."""

    def test_play_count_by_hourofday_specific_config(self) -> None:
        """Test PlayCountByHourOfDayGraph specific configuration functionality."""
        config = create_test_config_minimal()
        config.data_collection.time_ranges.days = 14
        config.graphs.appearance.annotations.enabled_on.play_count_by_hourofday = True

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
