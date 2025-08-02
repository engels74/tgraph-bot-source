"""
Test suite for stream type graphs in TGraph Bot.

This module provides comprehensive tests for the 6 new stream type graph implementations:
1. Daily Play Count by Stream Type (line graph)
2. Daily Concurrent Stream Count by Stream Type (line graph) 
3. Play Count by Source Resolution (bar chart)
4. Play Count by Stream Resolution (bar chart)
5. Play Count by Platform and Stream Type (bar chart)
6. Play Count by User and Stream Type (bar chart)

Following TDD principles, these tests are written before implementation to define
expected behavior and ensure code quality.
"""

import pytest
import logging
from pathlib import Path
from typing import Dict, Any, List

from src.tgraph_bot.config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)
from tests.utils.graph_helpers import (
    create_test_config_minimal,
    run_standard_graph_tests,
    matplotlib_cleanup,
)
from tests.utils.test_helpers import (
    create_test_config_custom,
    assert_graph_output_valid,
    assert_file_cleanup_successful,
)


class TestStreamTypeGraphs:
    """Test suite for all stream type graph implementations."""

    # Test Data Fixtures
    # ==================

    @pytest.fixture
    def sample_stream_type_data(self) -> Dict[str, Any]:
        """
        Sample data with stream type information for testing.
        
        This fixture provides realistic Tautulli API data including stream types,
        resolutions, and transcode decisions that would be returned by the
        get_history API endpoint.
        """
        return {
            "data": [
                {
                    "date": 1704100200,  # 2024-01-01 08:30:00 UTC
                    "user": "alice",
                    "platform": "Plex Web",
                    "media_type": "movie",
                    "transcode_decision": "direct play",
                    "video_resolution": "1920x1080",
                    "stream_video_resolution": "1920x1080",
                    "video_codec": "h264",
                    "audio_codec": "aac",
                    "container": "mp4",
                    "duration": 7200,  # 2 hours
                    "stopped": 7200,
                    "paused_counter": 0,
                },
                {
                    "date": 1704103800,  # 2024-01-01 09:30:00 UTC (concurrent)
                    "user": "bob", 
                    "platform": "Plex Android",
                    "media_type": "tv",
                    "transcode_decision": "transcode",
                    "video_resolution": "3840x2160",
                    "stream_video_resolution": "1920x1080", 
                    "video_codec": "hevc",
                    "audio_codec": "ac3",
                    "container": "mkv",
                    "duration": 2700,  # 45 minutes
                    "stopped": 2700,
                    "paused_counter": 1,
                },
                {
                    "date": 1704121700,  # 2024-01-01 14:15:00 UTC
                    "user": "charlie",
                    "platform": "Plex iOS", 
                    "media_type": "movie",
                    "transcode_decision": "copy",
                    "video_resolution": "1920x1080",
                    "stream_video_resolution": "1920x1080",
                    "video_codec": "h264",
                    "audio_codec": "aac",
                    "container": "mp4",
                    "duration": 5400,  # 1.5 hours
                    "stopped": 5400,
                    "paused_counter": 0,
                },
                {
                    "date": 1704187200,  # 2024-01-02 09:00:00 UTC
                    "user": "alice",
                    "platform": "Plex Web",
                    "media_type": "tv",
                    "transcode_decision": "direct play",
                    "video_resolution": "1920x1080",
                    "stream_video_resolution": "1920x1080", 
                    "video_codec": "h264",
                    "audio_codec": "aac",
                    "container": "mp4",
                    "duration": 3600,  # 1 hour
                    "stopped": 3600,
                    "paused_counter": 2,
                },
                {
                    "date": 1704190800,  # 2024-01-02 10:00:00 UTC (concurrent)
                    "user": "bob",
                    "platform": "Plex Android",
                    "media_type": "movie", 
                    "transcode_decision": "transcode",
                    "video_resolution": "3840x2160",
                    "stream_video_resolution": "1280x720",
                    "video_codec": "hevc",
                    "audio_codec": "dts",
                    "container": "mkv",
                    "duration": 7800,  # 2.17 hours
                    "stopped": 7800,
                    "paused_counter": 0,
                },
                {
                    "date": 1704210600,  # 2024-01-02 15:30:00 UTC
                    "user": "diana",
                    "platform": "Plex TV",
                    "media_type": "tv",
                    "transcode_decision": "direct play",
                    "video_resolution": "1280x720",
                    "stream_video_resolution": "1280x720",
                    "video_codec": "h264", 
                    "audio_codec": "aac",
                    "container": "mp4",
                    "duration": 1800,  # 30 minutes
                    "stopped": 1800,
                    "paused_counter": 1,
                },
            ]
        }

    @pytest.fixture  
    def sample_empty_stream_data(self) -> Dict[str, Any]:
        """Empty data fixture for testing empty data scenarios."""
        return {"data": []}

    @pytest.fixture
    def sample_concurrent_stream_data(self) -> Dict[str, Any]:
        """
        Sample data specifically designed for concurrent stream testing.
        
        Includes overlapping time periods to test concurrent stream counting logic.
        """
        return {
            "data": [
                # Day 1: Peak concurrent streams = 3
                {
                    "date": 1704100200,  # 10:30 - 12:30 (2h movie)
                    "user": "alice",
                    "platform": "Plex Web", 
                    "media_type": "movie",
                    "transcode_decision": "direct play",
                    "duration": 7200,
                    "stopped": 7200,
                },
                {
                    "date": 1704103800,  # 11:30 - 12:15 (45m TV episode) - overlaps with alice
                    "user": "bob",
                    "platform": "Plex Android",
                    "media_type": "tv", 
                    "transcode_decision": "transcode",
                    "duration": 2700,
                    "stopped": 2700,
                },
                {
                    "date": 1704106200,  # 12:10 - 12:40 (30m TV episode) - overlaps with both
                    "user": "charlie",
                    "platform": "Plex iOS",
                    "media_type": "tv",
                    "transcode_decision": "copy", 
                    "duration": 1800,
                    "stopped": 1800,
                },
                # Day 2: Peak concurrent streams = 2  
                {
                    "date": 1704187200,  # 09:00 - 10:00 (1h TV)
                    "user": "alice", 
                    "platform": "Plex Web",
                    "media_type": "tv",
                    "transcode_decision": "direct play",
                    "duration": 3600,
                    "stopped": 3600,
                },
                {
                    "date": 1704190800,  # 10:00 - 12:10 (2.17h movie) - slight overlap
                    "user": "bob",
                    "platform": "Plex Android",
                    "media_type": "movie",
                    "transcode_decision": "transcode", 
                    "duration": 7800,
                    "stopped": 7800,
                },
            ]
        }

    # Stream Type Graph Tests (TDD - Write Tests First)
    # ================================================

    @pytest.mark.parametrize(
        "graph_class_name,expected_title_contains,sample_data_fixture",
        [
            ("DailyPlayCountByStreamTypeGraph", "Daily Play Count by Stream Type", "sample_stream_type_data"),
            ("DailyConcurrentStreamCountByStreamTypeGraph", "Daily Concurrent Stream Count by Stream Type", "sample_concurrent_stream_data"),
            ("PlayCountBySourceResolutionGraph", "Play Count by Source Resolution", "sample_stream_type_data"),
            ("PlayCountByStreamResolutionGraph", "Play Count by Stream Resolution", "sample_stream_type_data"),
            ("PlayCountByPlatformAndStreamTypeGraph", "Play Count by Platform and Stream Type", "sample_stream_type_data"), 
            ("PlayCountByUserAndStreamTypeGraph", "Play Count by User and Stream Type", "sample_stream_type_data"),
        ],
    )
    def test_stream_type_graph_basic_functionality(
        self,
        graph_class_name: str,
        expected_title_contains: str, 
        sample_data_fixture: str,
        request: pytest.FixtureRequest,
    ) -> None:
        """
        Test basic functionality for all stream type graphs.
        
        This test will initially fail as the graph classes don't exist yet (TDD).
        Once implemented, it validates:
        - Graph can be instantiated
        - Title is correct
        - Graph can process sample data 
        - Output file is generated
        """
        # This test will fail initially - that's expected with TDD
        pytest.skip("Graph classes not yet implemented - TDD placeholder")
        
        # Future implementation will look like:
        # sample_data = request.getfixturevalue(sample_data_fixture)
        # config = create_test_config_minimal()
        # 
        # # Import will fail initially
        # graph_module = __import__(f"src.tgraph_bot.graphs.graph_modules.implementations.tautulli.{graph_class_name.lower()}", fromlist=[graph_class_name])
        # graph_class = getattr(graph_module, graph_class_name)
        # 
        # graph = graph_class(config=config)
        # assert expected_title_contains in graph.get_title()
        # 
        # output_path = graph.generate(sample_data)
        # assert_graph_output_valid(output_path)

    def test_daily_play_count_by_stream_type_separation(
        self, sample_stream_type_data: dict[str, object]
    ) -> None:
        """
        Test stream type separation in daily play count graph.
        
        Should create separate lines for each transcode decision:
        - Direct Play
        - Copy  
        - Transcode
        """
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.daily_play_count_by_stream_type_graph import DailyPlayCountByStreamTypeGraph
        
        config = create_test_config_minimal()
        graph = DailyPlayCountByStreamTypeGraph(config=config)
        
        # Test that the graph can be instantiated and has correct title
        assert "Daily Play Count by Stream Type" in graph.get_title()
        
        # Test graph generation with sample data
        try:
            output_path = graph.generate(sample_stream_type_data)
            assert_graph_output_valid(output_path)
            logger.info(f"Successfully generated graph: {output_path}")
        except Exception as e:
            pytest.fail(f"Graph generation failed: {e}")
        finally:
            # Ensure cleanup
            graph.cleanup()
        
        # Future test implementation:
        # config = create_test_config_custom({
        #     "graphs": {
        #         "per_graph": {
        #             "daily_play_count_by_stream_type": {
        #                 "stream_type_separation": True
        #             }
        #         }
        #     }
        # })
        # 
        # graph = DailyPlayCountByStreamTypeGraph(config=config)
        # output_path = graph.generate(sample_stream_type_data)
        # 
        # # Validate that graph shows separate lines for different stream types
        # assert_graph_output_valid(output_path)

    def test_concurrent_stream_counting_logic(
        self, sample_concurrent_stream_data: Dict[str, Any]
    ) -> None:
        """
        Test concurrent stream counting algorithm.
        
        Should correctly identify overlapping streams and count peak concurrent usage.
        """
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.daily_concurrent_stream_count_by_stream_type_graph import DailyConcurrentStreamCountByStreamTypeGraph
        
        config = create_test_config_minimal()
        graph = DailyConcurrentStreamCountByStreamTypeGraph(config=config)
        
        # Test that the graph can be instantiated and has correct title
        assert "Daily Concurrent Stream Count by Stream Type" in graph.get_title()
        
        # Test graph generation with concurrent stream sample data
        try:
            output_path = graph.generate(sample_concurrent_stream_data)
            assert_graph_output_valid(output_path)
            logger.info(f"Successfully generated concurrent stream graph: {output_path}")
        except Exception as e:
            pytest.fail(f"Concurrent stream graph generation failed: {e}")
        finally:
            # Ensure cleanup
            graph.cleanup()
        
        # Future test logic:
        # - Parse stream start/end times from data
        # - Identify overlapping periods
        # - Count peak concurrent streams per day
        # - Separate by stream type (direct play vs transcode)

    def test_resolution_aggregation_source_vs_stream(
        self, sample_stream_type_data: Dict[str, Any]
    ) -> None:
        """
        Test that source and stream resolution graphs show different data.
        
        Source resolution: original file resolution
        Stream resolution: transcoded output resolution
        """
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_source_resolution_graph import PlayCountBySourceResolutionGraph
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_stream_resolution_graph import PlayCountByStreamResolutionGraph
        
        config = create_test_config_minimal()
        
        # Test Source Resolution Graph
        source_graph = PlayCountBySourceResolutionGraph(config=config)
        assert "Play Count by Source Resolution" in source_graph.get_title()
        
        try:
            source_output = source_graph.generate(sample_stream_type_data)
            assert_graph_output_valid(source_output)
            logger.info(f"Successfully generated source resolution graph: {source_output}")
        except Exception as e:
            pytest.fail(f"Source resolution graph generation failed: {e}")
        finally:
            source_graph.cleanup()
        
        # Test Stream Resolution Graph
        stream_graph = PlayCountByStreamResolutionGraph(config=config)
        assert "Play Count by Stream Resolution" in stream_graph.get_title()
        
        try:
            stream_output = stream_graph.generate(sample_stream_type_data)
            assert_graph_output_valid(stream_output)
            logger.info(f"Successfully generated stream resolution graph: {stream_output}")
        except Exception as e:
            pytest.fail(f"Stream resolution graph generation failed: {e}")
        finally:
            stream_graph.cleanup()
        
        # Future test should verify:
        # - Source resolution uses 'video_resolution' field
        # - Stream resolution uses 'stream_video_resolution' field
        # - Different counts when transcoding occurs

    def test_platform_and_stream_type_combination(
        self, sample_stream_type_data: Dict[str, Any]
    ) -> None:
        """
        Test platform + stream type combination graph.
        
        Should show platforms with stream type breakdown (stacked or grouped bars).
        """
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_platform_and_stream_type_graph import PlayCountByPlatformAndStreamTypeGraph
        
        config = create_test_config_minimal()
        graph = PlayCountByPlatformAndStreamTypeGraph(config=config)
        
        # Test that the graph can be instantiated and has correct title
        assert "Play Count by Platform and Stream Type" in graph.get_title()
        
        # Test graph generation with sample data
        try:
            output_path = graph.generate(sample_stream_type_data)
            assert_graph_output_valid(output_path)
            logger.info(f"Successfully generated platform+stream type graph: {output_path}")
        except Exception as e:
            pytest.fail(f"Platform and stream type graph generation failed: {e}")
        finally:
            # Ensure cleanup
            graph.cleanup()

    def test_user_and_stream_type_combination(
        self, sample_stream_type_data: Dict[str, Any]
    ) -> None:
        """
        Test user + stream type combination graph.
        
        Should show users with stream type breakdown (stacked or grouped bars).
        """
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_user_and_stream_type_graph import PlayCountByUserAndStreamTypeGraph
        
        config = create_test_config_minimal()
        graph = PlayCountByUserAndStreamTypeGraph(config=config)
        
        # Test that the graph can be instantiated and has correct title
        assert "Play Count by User and Stream Type" in graph.get_title()
        
        # Test graph generation with sample data
        try:
            output_path = graph.generate(sample_stream_type_data)
            assert_graph_output_valid(output_path)
            logger.info(f"Successfully generated user+stream type graph: {output_path}")
        except Exception as e:
            pytest.fail(f"User and stream type graph generation failed: {e}")
        finally:
            # Ensure cleanup
            graph.cleanup()

    # Edge Cases and Error Handling
    # =============================

    def test_empty_stream_data_handling(
        self, sample_empty_stream_data: Dict[str, Any]
    ) -> None:
        """Test that all stream type graphs handle empty data gracefully."""
        pytest.skip("Stream type graphs not yet implemented - TDD placeholder")

    def test_missing_stream_fields_handling(self) -> None:
        """Test handling of data missing stream type fields."""
        pytest.skip("Stream type graphs not yet implemented - TDD placeholder")
        
        # Future test with data missing transcode_decision, resolutions, etc.

    def test_invalid_stream_data_validation(self) -> None:
        """Test validation of invalid stream type data."""
        pytest.skip("Stream type graphs not yet implemented - TDD placeholder")

    # Configuration Tests  
    # ===================

    def test_stream_type_separation_config(self) -> None:
        """Test stream type separation configuration option."""
        pytest.skip("Stream type graphs not yet implemented - TDD placeholder")

    def test_stacked_vs_grouped_bar_config(self) -> None:
        """Test stacked vs grouped bar chart configuration."""
        pytest.skip("Stream type graphs not yet implemented - TDD placeholder")

    def test_palette_configuration_for_stream_graphs(self) -> None:
        """Test custom palette configuration for stream type graphs.""" 
        pytest.skip("Stream type graphs not yet implemented - TDD placeholder")

    # Cleanup Tests
    # =============

    def test_matplotlib_cleanup_after_stream_graphs(self) -> None:
        """Test proper matplotlib resource cleanup.""" 
        pytest.skip("Stream type graphs not yet implemented - TDD placeholder")

    # Helper Methods (for future use)
    # ===============================

    def _validate_stream_type_data_fields(self, data: Dict[str, Any]) -> bool:
        """Validate that data contains required stream type fields."""
        required_fields = [
            "transcode_decision",
            "video_resolution", 
            "stream_video_resolution",
            "video_codec",
            "audio_codec"
        ]
        
        if "data" not in data or not data["data"]:
            return False
            
        for record in data["data"]:
            for field in required_fields:
                if field not in record:
                    return False
                    
        return True

    def _extract_concurrent_streams_by_date(self, data: Dict[str, Any]) -> Dict[str, int]:
        """Extract peak concurrent streams per date from sample data."""
        # Future implementation for concurrent stream counting logic
        # This will be used by the actual implementation
        return {}

    def _extract_resolution_counts(
        self, data: Dict[str, Any], resolution_field: str
    ) -> Dict[str, int]:
        """Extract resolution counts from data using specified field."""
        # Future helper for resolution-based aggregation
        return {}


# Integration Tests for Stream Type Features
# ==========================================

class TestStreamTypeIntegration:
    """Integration tests for stream type functionality across the system."""

    def test_graph_factory_creates_stream_type_graphs(self) -> None:
        """Test that GraphFactory can create all stream type graphs."""
        pytest.skip("Integration not yet implemented - TDD placeholder")

    def test_graph_registry_recognizes_stream_type_graphs(self) -> None:
        """Test that GraphTypeRegistry includes all stream type graphs."""
        pytest.skip("Integration not yet implemented - TDD placeholder")

    def test_config_schema_supports_stream_type_options(self) -> None:
        """Test that configuration schema supports stream type graph options."""
        pytest.skip("Integration not yet implemented - TDD placeholder")

    def test_data_processor_handles_stream_fields(self) -> None:
        """Test that DataProcessor can extract stream type fields."""
        pytest.skip("Integration not yet implemented - TDD placeholder")

# Performance Tests
# =================

class TestStreamTypePerformance:
    """Performance tests for stream type graph generation."""

    def test_large_dataset_performance(self) -> None:
        """Test performance with large datasets (1000+ records)."""
        pytest.skip("Performance tests not yet implemented - TDD placeholder")

    def test_concurrent_stream_calculation_performance(self) -> None:
        """Test performance of concurrent stream counting algorithm."""
        pytest.skip("Performance tests not yet implemented - TDD placeholder")