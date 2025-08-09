"""
Tests for resolution field mapping and fallback logic.

This module tests the enhanced resolution data extraction that handles
both the preferred fields (video_resolution, stream_video_resolution)
and fallback to width/height field combinations.
"""

from datetime import datetime

from src.tgraph_bot.graphs.graph_modules.utils.utils import (
    ProcessedPlayRecord,
    ProcessedRecords,
    aggregate_by_resolution,
)


class TestResolutionFieldMapping:
    """Test resolution field mapping and fallback logic."""

    def test_standard_resolution_fields_work(self) -> None:
        """Test that standard resolution fields work when present."""
        records: ProcessedRecords = [
            ProcessedPlayRecord(
                date="1640995200",
                user="testuser",
                platform="web",
                media_type="movie",
                duration=7200,
                stopped=7200,
                paused_counter=0,
                datetime=datetime.fromtimestamp(1640995200),
                transcode_decision="direct play",
                video_resolution="1920x1080",
                stream_video_resolution="1920x1080",
                video_codec="h264",
                audio_codec="aac",
                container="mp4",
            ),
            ProcessedPlayRecord(
                date="1640995300",
                user="testuser2",
                platform="mobile",
                media_type="movie",
                duration=3600,
                stopped=3600,
                paused_counter=0,
                datetime=datetime.fromtimestamp(1640995300),
                transcode_decision="transcode",
                video_resolution="3840x2160",
                stream_video_resolution="1280x720",
                video_codec="hevc",
                audio_codec="ac3",
                container="mkv",
            ),
        ]

        # Test source resolution aggregation
        source_result = aggregate_by_resolution(
            records, resolution_field="video_resolution"
        )
        assert len(source_result) == 2
        # When play counts are equal, order is not guaranteed, so check for presence
        source_resolutions = [r["resolution"] for r in source_result]
        assert "3840x2160" in source_resolutions
        assert "1920x1080" in source_resolutions
        # Each should have play count of 1
        for result in source_result:
            assert result["play_count"] == 1

        # Test stream resolution aggregation
        stream_result = aggregate_by_resolution(
            records, resolution_field="stream_video_resolution"
        )
        assert len(stream_result) == 2
        # When play counts are equal, order is not guaranteed, so check for presence
        stream_resolutions = [r["resolution"] for r in stream_result]
        assert "1920x1080" in stream_resolutions
        assert "1280x720" in stream_resolutions
        # Each should have play count of 1
        for result in stream_result:
            assert result["play_count"] == 1

    def test_fallback_to_width_height_fields(self) -> None:
        """Test fallback to width/height fields when resolution fields are unknown."""
        # This test defines the expected behavior - we need to implement the functionality
        # to make this test pass

        # Mock records with unknown resolution but valid width/height
        test_data = {
            "data": [
                {
                    "date": "1640995200",
                    "user": "testuser",
                    "platform": "web",
                    "media_type": "movie",
                    "duration": 7200,
                    "stopped": 7200,
                    "paused_counter": 0,
                    "transcode_decision": "direct play",
                    "video_resolution": "unknown",  # Missing primary field
                    "width": 1920,  # Fallback source width
                    "height": 1080,  # Fallback source height
                    "stream_video_resolution": "unknown",  # Missing primary field
                    "stream_video_width": 1920,  # Fallback stream width
                    "stream_video_height": 1080,  # Fallback stream height
                    "video_codec": "h264",
                    "audio_codec": "aac",
                    "container": "mp4",
                },
                {
                    "date": "1640995300",
                    "user": "testuser2",
                    "platform": "mobile",
                    "media_type": "movie",
                    "duration": 3600,
                    "stopped": 3600,
                    "paused_counter": 0,
                    "transcode_decision": "transcode",
                    "video_resolution": "unknown",  # Missing primary field
                    "width": 3840,  # Fallback source width
                    "height": 2160,  # Fallback source height
                    "stream_video_resolution": "unknown",  # Missing primary field
                    "stream_video_width": 1280,  # Fallback stream width
                    "stream_video_height": 720,  # Fallback stream height
                    "video_codec": "hevc",
                    "audio_codec": "ac3",
                    "container": "mkv",
                },
            ]
        }

        # Import the enhanced processing function (to be implemented)
        from src.tgraph_bot.graphs.graph_modules.utils.utils import (
            process_play_history_data_enhanced,
        )

        # Process the data with enhanced resolution mapping
        processed_records = process_play_history_data_enhanced(test_data)

        # The enhanced function should create resolution strings from width/height
        assert len(processed_records) == 2
        assert processed_records[0].get("video_resolution") == "1920x1080"
        assert processed_records[0].get("stream_video_resolution") == "1920x1080"
        assert processed_records[1].get("video_resolution") == "3840x2160"
        assert processed_records[1].get("stream_video_resolution") == "1280x720"

        # Test aggregation with the enhanced data
        source_result = aggregate_by_resolution(
            processed_records, resolution_field="video_resolution"
        )
        assert len(source_result) == 2
        # When play counts are equal, order is not guaranteed, so check for presence
        source_resolutions = [r["resolution"] for r in source_result]
        assert "3840x2160" in source_resolutions
        assert "1920x1080" in source_resolutions
        # Each should have play count of 1
        for result in source_result:
            assert result["play_count"] == 1

        stream_result = aggregate_by_resolution(
            processed_records, resolution_field="stream_video_resolution"
        )
        assert len(stream_result) == 2
        # When play counts are equal, order is not guaranteed, so check for presence
        stream_resolutions = [r["resolution"] for r in stream_result]
        assert "1920x1080" in stream_resolutions
        assert "1280x720" in stream_resolutions
        # Each should have play count of 1
        for result in stream_result:
            assert result["play_count"] == 1

    def test_mixed_resolution_data_sources(self) -> None:
        """Test handling of mixed data where some records have resolution fields and others need fallback."""
        test_data = {
            "data": [
                {
                    # Record with standard resolution fields
                    "date": "1640995200",
                    "user": "testuser",
                    "platform": "web",
                    "media_type": "movie",
                    "duration": 7200,
                    "stopped": 7200,
                    "paused_counter": 0,
                    "transcode_decision": "direct play",
                    "video_resolution": "1920x1080",  # Has primary field
                    "stream_video_resolution": "1920x1080",  # Has primary field
                    "video_codec": "h264",
                    "audio_codec": "aac",
                    "container": "mp4",
                },
                {
                    # Record needing fallback to width/height
                    "date": "1640995300",
                    "user": "testuser2",
                    "platform": "mobile",
                    "media_type": "movie",
                    "duration": 3600,
                    "stopped": 3600,
                    "paused_counter": 0,
                    "transcode_decision": "transcode",
                    "video_resolution": "unknown",  # Missing primary field
                    "width": 3840,  # Fallback source width
                    "height": 2160,  # Fallback source height
                    "stream_video_resolution": "unknown",  # Missing primary field
                    "stream_video_width": 1280,  # Fallback stream width
                    "stream_video_height": 720,  # Fallback stream height
                    "video_codec": "hevc",
                    "audio_codec": "ac3",
                    "container": "mkv",
                },
            ]
        }

        from src.tgraph_bot.graphs.graph_modules.utils.utils import (
            process_play_history_data_enhanced,
        )

        processed_records = process_play_history_data_enhanced(test_data)

        # Should handle both types of records correctly
        assert len(processed_records) == 2
        assert (
            processed_records[0].get("video_resolution") == "1920x1080"
        )  # From primary field
        assert (
            processed_records[0].get("stream_video_resolution") == "1920x1080"
        )  # From primary field
        assert (
            processed_records[1].get("video_resolution") == "3840x2160"
        )  # From width/height fallback
        assert (
            processed_records[1].get("stream_video_resolution") == "1280x720"
        )  # From width/height fallback

    def test_no_resolution_data_available(self) -> None:
        """Test behavior when no resolution data is available at all."""
        test_data = {
            "data": [
                {
                    "date": "1640995200",
                    "user": "testuser",
                    "platform": "web",
                    "media_type": "movie",
                    "duration": 7200,
                    "stopped": 7200,
                    "paused_counter": 0,
                    "transcode_decision": "direct play",
                    "video_resolution": "unknown",  # Missing primary field
                    # No width/height fields available either
                    "stream_video_resolution": "unknown",  # Missing primary field
                    # No stream width/height fields available either
                    "video_codec": "h264",
                    "audio_codec": "aac",
                    "container": "mp4",
                },
            ]
        }

        from src.tgraph_bot.graphs.graph_modules.utils.utils import (
            process_play_history_data_enhanced,
        )

        processed_records = process_play_history_data_enhanced(test_data)

        # Should fall back to "unknown" when no resolution data is available
        assert len(processed_records) == 1
        assert processed_records[0].get("video_resolution") == "unknown"
        assert processed_records[0].get("stream_video_resolution") == "unknown"

        # Aggregation should still work and include the unknown entries
        source_result = aggregate_by_resolution(
            processed_records, resolution_field="video_resolution"
        )
        assert len(source_result) == 1
        assert source_result[0]["resolution"] == "unknown"
        assert source_result[0]["play_count"] == 1

    def test_invalid_width_height_combinations(self) -> None:
        """Test handling of invalid or missing width/height combinations."""
        test_data = {
            "data": [
                {
                    "date": "1640995200",
                    "user": "testuser",
                    "platform": "web",
                    "media_type": "movie",
                    "duration": 7200,
                    "stopped": 7200,
                    "paused_counter": 0,
                    "transcode_decision": "direct play",
                    "video_resolution": "unknown",
                    "width": 1920,  # Has width
                    # Missing height - should fallback to unknown
                    "stream_video_resolution": "unknown",
                    "stream_video_width": 0,  # Invalid width (zero)
                    "stream_video_height": 720,  # Valid height but invalid width
                    "video_codec": "h264",
                    "audio_codec": "aac",
                    "container": "mp4",
                },
            ]
        }

        from src.tgraph_bot.graphs.graph_modules.utils.utils import (
            process_play_history_data_enhanced,
        )

        processed_records = process_play_history_data_enhanced(test_data)

        # Should fallback to unknown for invalid width/height combinations
        assert len(processed_records) == 1
        assert processed_records[0].get("video_resolution") == "unknown"  # Missing height
        assert (
            processed_records[0].get("stream_video_resolution") == "unknown"
        )  # Invalid width (0)
