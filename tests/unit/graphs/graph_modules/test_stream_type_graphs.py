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

import logging
import pytest
from typing import Any

from tests.utils.graph_helpers import (
    create_test_config_minimal,
)
from tests.utils.test_helpers import (
    assert_graph_output_valid,
)

logger = logging.getLogger(__name__)


class TestStreamTypeGraphs:
    """Test suite for all stream type graph implementations."""

    # Test Data Fixtures
    # ==================

    @pytest.fixture
    def sample_stream_type_data(self) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
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
    def sample_empty_stream_data(self) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
        """Empty data fixture for testing empty data scenarios."""
        return {"data": []}

    @pytest.fixture
    def sample_concurrent_stream_data(self) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
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


    def test_daily_play_count_by_stream_type_separation(
        self, sample_stream_type_data: dict[str, Any]  # pyright: ignore[reportExplicitAny]
    ) -> None:
        """
        Test stream type separation in daily play count graph.

        Should create separate lines for each transcode decision:
        - Direct Play
        - Copy
        - Transcode
        """
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.daily_play_count_by_stream_type_graph import (
            DailyPlayCountByStreamTypeGraph,
        )

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
        self, sample_concurrent_stream_data: dict[str, Any]  # pyright: ignore[reportExplicitAny]
    ) -> None:
        """
        Test concurrent stream counting algorithm.

        Should correctly identify overlapping streams and count peak concurrent usage.
        """
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.daily_concurrent_stream_count_by_stream_type_graph import (
            DailyConcurrentStreamCountByStreamTypeGraph,
        )

        config = create_test_config_minimal()
        graph = DailyConcurrentStreamCountByStreamTypeGraph(config=config)

        # Test that the graph can be instantiated and has correct title
        assert "Daily Concurrent Stream Count by Stream Type" in graph.get_title()

        # Test graph generation with concurrent stream sample data
        try:
            output_path = graph.generate(sample_concurrent_stream_data)
            assert_graph_output_valid(output_path)
            logger.info(
                f"Successfully generated concurrent stream graph: {output_path}"
            )
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
        self, sample_stream_type_data: dict[str, Any]  # pyright: ignore[reportExplicitAny]
    ) -> None:
        """
        Test that source and stream resolution graphs show different data.

        Source resolution: original file resolution
        Stream resolution: transcoded output resolution
        """
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_source_resolution_graph import (
            PlayCountBySourceResolutionGraph,
        )
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_stream_resolution_graph import (
            PlayCountByStreamResolutionGraph,
        )

        config = create_test_config_minimal()

        # Test Source Resolution Graph
        source_graph = PlayCountBySourceResolutionGraph(config=config)
        assert "Play Count by Source Resolution" in source_graph.get_title()

        try:
            source_output = source_graph.generate(sample_stream_type_data)
            assert_graph_output_valid(source_output)
            logger.info(
                f"Successfully generated source resolution graph: {source_output}"
            )
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
            logger.info(
                f"Successfully generated stream resolution graph: {stream_output}"
            )
        except Exception as e:
            pytest.fail(f"Stream resolution graph generation failed: {e}")
        finally:
            stream_graph.cleanup()

        # Future test should verify:
        # - Source resolution uses 'video_resolution' field
        # - Stream resolution uses 'stream_video_resolution' field
        # - Different counts when transcoding occurs

    def test_platform_and_stream_type_combination(
        self, sample_stream_type_data: dict[str, Any]  # pyright: ignore[reportExplicitAny]
    ) -> None:
        """
        Test platform + stream type combination graph.

        Should show platforms with stream type breakdown (stacked or grouped bars).
        """
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_platform_and_stream_type_graph import (
            PlayCountByPlatformAndStreamTypeGraph,
        )

        config = create_test_config_minimal()
        graph = PlayCountByPlatformAndStreamTypeGraph(config=config)

        # Test that the graph can be instantiated and has correct title
        assert "Play Count by Platform and Stream Type" in graph.get_title()

        # Test graph generation with sample data
        try:
            output_path = graph.generate(sample_stream_type_data)
            assert_graph_output_valid(output_path)
            logger.info(
                f"Successfully generated platform+stream type graph: {output_path}"
            )
        except Exception as e:
            pytest.fail(f"Platform and stream type graph generation failed: {e}")
        finally:
            # Ensure cleanup
            graph.cleanup()

    def test_user_and_stream_type_combination(
        self, sample_stream_type_data: dict[str, Any]  # pyright: ignore[reportExplicitAny]
    ) -> None:
        """
        Test user + stream type combination graph.

        Should show users with stream type breakdown (stacked or grouped bars).
        """
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_user_and_stream_type_graph import (
            PlayCountByUserAndStreamTypeGraph,
        )

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

    def test_platform_graph_uses_stacked_horizontal_annotations(
        self, sample_stream_type_data: dict[str, Any]  # pyright: ignore[reportExplicitAny]
    ) -> None:
        """
        Ensure platform+stream type graph uses stacked horizontal segment annotations
        (segment labels + totals) instead of simple horizontal bar patch annotations.
        """
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_platform_and_stream_type_graph import (
            PlayCountByPlatformAndStreamTypeGraph,
        )
        from src.tgraph_bot.graphs.graph_modules.utils.annotation_helper import AnnotationHelper
        from unittest.mock import patch

        config = create_test_config_minimal()
        graph = PlayCountByPlatformAndStreamTypeGraph(config=config)

        with (
            patch.object(AnnotationHelper, "annotate_stacked_horizontal_bar_segments") as mock_stacked,
            patch.object(AnnotationHelper, "annotate_horizontal_bar_patches") as mock_simple,
        ):
            output_path = graph.generate(sample_stream_type_data)
            assert_graph_output_valid(output_path)
            # Stacked annotations should be used, simple should not
            assert mock_stacked.call_count == 1
            assert mock_simple.call_count == 0

    def test_user_graph_uses_stacked_horizontal_annotations(
        self, sample_stream_type_data: dict[str, Any]  # pyright: ignore[reportExplicitAny]
    ) -> None:
        """
        Ensure user+stream type graph uses stacked horizontal segment annotations
        (segment labels + totals) instead of simple horizontal bar patch annotations.
        """
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_user_and_stream_type_graph import (
            PlayCountByUserAndStreamTypeGraph,
        )
        from src.tgraph_bot.graphs.graph_modules.utils.annotation_helper import AnnotationHelper
        from unittest.mock import patch

        config = create_test_config_minimal()
        graph = PlayCountByUserAndStreamTypeGraph(config=config)

        with (
            patch.object(AnnotationHelper, "annotate_stacked_horizontal_bar_segments") as mock_stacked,
            patch.object(AnnotationHelper, "annotate_horizontal_bar_patches") as mock_simple,
        ):
            output_path = graph.generate(sample_stream_type_data)
            assert_graph_output_valid(output_path)
            # Stacked annotations should be used, simple should not
            assert mock_stacked.call_count == 1
            assert mock_simple.call_count == 0


    # Helper Methods (for future use)
    # ===============================

    def _validate_stream_type_data_fields(self, data: dict[str, Any]) -> bool:  # pyright: ignore[reportExplicitAny]
        """Validate that data contains required stream type fields."""
        required_fields = [
            "transcode_decision",
            "video_resolution",
            "stream_video_resolution",
            "video_codec",
            "audio_codec",
        ]

        if "data" not in data or not data["data"]:
            return False

        for record in data["data"]:  # pyright: ignore[reportAny]
            record_typed = record  # pyright: ignore[reportAny]
            for field in required_fields:
                if field not in record_typed:
                    return False

        return True

    def _extract_concurrent_streams_by_date(
        self, _data: dict[str, Any]  # pyright: ignore[reportExplicitAny]
    ) -> dict[str, int]:
        """Extract peak concurrent streams per date from sample data."""
        # Future implementation for concurrent stream counting logic
        # This will be used by the actual implementation
        return {}

    def _extract_resolution_counts(
        self, _data: dict[str, Any]  # pyright: ignore[reportExplicitAny], _resolution_field: str
    ) -> dict[str, int]:
        """Extract resolution counts from data using specified field."""
        # Future helper for resolution-based aggregation
        return {}


