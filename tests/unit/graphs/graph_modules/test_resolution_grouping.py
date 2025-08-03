"""
Tests for resolution grouping functionality.

This module tests the resolution grouping strategies that reduce visual clutter
in resolution analytics by categorizing resolutions into meaningful groups.
"""

import pytest
from datetime import datetime
from collections.abc import Mapping

from src.tgraph_bot.graphs.graph_modules.utils.utils import ProcessedRecords


class TestResolutionGrouping:
    """Test resolution grouping strategies based on Tautulli research."""

    def test_group_resolution_by_strategy_simplified(self) -> None:
        """Test simplified grouping strategy (SD, HD, FHD, UHD)."""
        from src.tgraph_bot.graphs.graph_modules.utils.resolution_grouping import group_resolution_by_strategy
        
        # Test SD grouping
        assert group_resolution_by_strategy("720x480", "simplified") == "SD"
        assert group_resolution_by_strategy("720x576", "simplified") == "SD"
        assert group_resolution_by_strategy("854x480", "simplified") == "SD"
        
        # Test HD grouping
        assert group_resolution_by_strategy("1280x720", "simplified") == "HD"
        assert group_resolution_by_strategy("1366x768", "simplified") == "HD"
        
        # Test FHD grouping
        assert group_resolution_by_strategy("1920x1080", "simplified") == "FHD"
        assert group_resolution_by_strategy("1680x1050", "simplified") == "FHD"
        
        # Test UHD grouping
        assert group_resolution_by_strategy("3840x2160", "simplified") == "UHD"
        assert group_resolution_by_strategy("4096x2160", "simplified") == "UHD"
        assert group_resolution_by_strategy("2560x1440", "simplified") == "UHD"
        
        # Test Other category
        assert group_resolution_by_strategy("1024x768", "simplified") == "Other"
        assert group_resolution_by_strategy("unknown", "simplified") == "Other"

    def test_group_resolution_by_strategy_standard(self) -> None:
        """Test standard grouping strategy (4K, 1440p, 1080p, etc.)."""
        from src.tgraph_bot.graphs.graph_modules.utils.resolution_grouping import group_resolution_by_strategy
        
        # Test standard mappings following Tautulli approach
        assert group_resolution_by_strategy("3840x2160", "standard") == "4K"
        assert group_resolution_by_strategy("4096x2160", "standard") == "4K"
        assert group_resolution_by_strategy("2560x1440", "standard") == "1440p"
        assert group_resolution_by_strategy("1920x1080", "standard") == "1080p"
        assert group_resolution_by_strategy("1280x720", "standard") == "720p"
        assert group_resolution_by_strategy("854x480", "standard") == "480p"
        assert group_resolution_by_strategy("720x480", "standard") == "NTSC"
        assert group_resolution_by_strategy("720x576", "standard") == "PAL"
        
        # Test fallback to original resolution for unmapped values
        assert group_resolution_by_strategy("1024x768", "standard") == "1024x768"
        assert group_resolution_by_strategy("unknown", "standard") == "unknown"

    def test_group_resolution_by_strategy_detailed(self) -> None:
        """Test detailed grouping strategy (exact resolutions with friendly names)."""
        from src.tgraph_bot.graphs.graph_modules.utils.resolution_grouping import group_resolution_by_strategy
        
        # Test detailed formatting with friendly names
        assert group_resolution_by_strategy("3840x2160", "detailed") == "4K UHD (3840×2160)"
        assert group_resolution_by_strategy("4096x2160", "detailed") == "4K DCI (4096×2160)"
        assert group_resolution_by_strategy("1920x1080", "detailed") == "1080p (1920×1080)"
        assert group_resolution_by_strategy("1280x720", "detailed") == "720p (1280×720)"
        
        # Test mapped resolutions
        assert group_resolution_by_strategy("1024x768", "detailed") == "XGA (1024×768)"

        # Test fallback for unmapped resolutions
        assert group_resolution_by_strategy("1600x1200", "detailed") == "1600x1200"
        assert group_resolution_by_strategy("unknown", "detailed") == "Unknown (No resolution data from Tautulli)"

    def test_sort_resolutions_by_quality(self) -> None:
        """Test resolution sorting by quality (highest to lowest)."""
        from src.tgraph_bot.graphs.graph_modules.utils.resolution_grouping import sort_resolutions_by_quality
        
        # Test sorting with mixed quality resolutions
        unsorted_resolutions = ["720p", "4K", "1080p", "480p", "1440p", "Other", "NTSC"]
        expected_order = ["4K", "1440p", "1080p", "720p", "480p", "NTSC", "Other"]
        
        sorted_resolutions = sort_resolutions_by_quality(unsorted_resolutions)
        assert sorted_resolutions == expected_order

    def test_aggregate_by_resolution_with_grouping(self) -> None:
        """Test resolution aggregation with grouping applied."""
        # Create test records with various resolutions
        records: ProcessedRecords = [
            {
                "date": "2024-01-01",
                "datetime": datetime(2024, 1, 1),
                "user": "user1",
                "platform": "web",
                "media_type": "movie",
                "duration": 7200,
                "stopped": 7200,
                "paused_counter": 0,
                "transcode_decision": "direct play",
                "video_resolution": "3840x2160",  # Should group to "4K"
                "stream_video_resolution": "3840x2160",
                "video_codec": "h264",
                "audio_codec": "aac",
                "container": "mp4",
            },
            {
                "date": "2024-01-02",
                "datetime": datetime(2024, 1, 2),
                "user": "user2",
                "platform": "web",
                "media_type": "movie",
                "duration": 5400,
                "stopped": 5400,
                "paused_counter": 0,
                "transcode_decision": "transcode",
                "video_resolution": "4096x2160",  # Should also group to "4K"
                "stream_video_resolution": "1920x1080",  # Should group to "1080p"
                "video_codec": "h265",
                "audio_codec": "aac",
                "container": "mkv",
            },
            {
                "date": "2024-01-03",
                "datetime": datetime(2024, 1, 3),
                "user": "user3",
                "platform": "mobile",
                "media_type": "episode",
                "duration": 2700,
                "stopped": 2700,
                "paused_counter": 0,
                "transcode_decision": "direct play",
                "video_resolution": "1920x1080",  # Should group to "1080p"
                "stream_video_resolution": "1920x1080",
                "video_codec": "h264",
                "audio_codec": "aac",
                "container": "mp4",
            },
        ]

        # Test with standard grouping strategy
        from src.tgraph_bot.graphs.graph_modules.utils.resolution_grouping import aggregate_by_resolution_grouped
        
        result = aggregate_by_resolution_grouped(
            records, 
            resolution_field="video_resolution", 
            grouping_strategy="standard"
        )
        
        # Should have 2 groups: "4K" (2 plays) and "1080p" (1 play)
        assert len(result) == 2
        
        # Check that resolutions are grouped correctly
        resolution_counts = {item["resolution"]: item["play_count"] for item in result}
        assert resolution_counts["4K"] == 2  # Both 3840x2160 and 4096x2160
        assert resolution_counts["1080p"] == 1  # One 1920x1080
        
        # Should be sorted by play count (descending)
        assert result[0]["play_count"] >= result[1]["play_count"]

    def test_aggregate_by_resolution_and_stream_type_with_grouping(self) -> None:
        """Test resolution and stream type aggregation with grouping applied."""
        # Create test records
        records: ProcessedRecords = [
            {
                "date": "2024-01-01",
                "datetime": datetime(2024, 1, 1),
                "user": "user1",
                "platform": "web",
                "media_type": "movie",
                "duration": 7200,
                "stopped": 7200,
                "paused_counter": 0,
                "transcode_decision": "direct play",
                "video_resolution": "3840x2160",
                "stream_video_resolution": "3840x2160",
                "video_codec": "h264",
                "audio_codec": "aac",
                "container": "mp4",
            },
            {
                "date": "2024-01-02",
                "datetime": datetime(2024, 1, 2),
                "user": "user2",
                "platform": "web",
                "media_type": "movie",
                "duration": 5400,
                "stopped": 5400,
                "paused_counter": 0,
                "transcode_decision": "transcode",
                "video_resolution": "4096x2160",
                "stream_video_resolution": "1920x1080",
                "video_codec": "h265",
                "audio_codec": "aac",
                "container": "mkv",
            },
        ]

        from src.tgraph_bot.graphs.graph_modules.utils.resolution_grouping import aggregate_by_resolution_and_stream_type_grouped
        
        result = aggregate_by_resolution_and_stream_type_grouped(
            records,
            resolution_field="video_resolution",
            grouping_strategy="standard"
        )
        
        # Should have 1 group: "4K" with both direct play and transcode
        assert len(result) == 1
        assert "4K" in result
        
        # Check stream type breakdown within the 4K group
        four_k_aggregates = result["4K"]
        assert len(four_k_aggregates) == 2  # direct play and transcode
        
        stream_types = {agg["stream_type"] for agg in four_k_aggregates}
        assert "direct play" in stream_types
        assert "transcode" in stream_types

    def test_resolution_grouping_preserves_unknown_values(self) -> None:
        """Test that unknown resolution values are handled properly in grouping."""
        from src.tgraph_bot.graphs.graph_modules.utils.resolution_grouping import group_resolution_by_strategy
        
        # Test that unknown values are preserved appropriately in each strategy
        assert group_resolution_by_strategy("unknown", "simplified") == "Other"
        assert group_resolution_by_strategy("unknown", "standard") == "unknown"
        assert group_resolution_by_strategy("unknown", "detailed") == "Unknown (No resolution data from Tautulli)"
        
        # Test empty/None values
        assert group_resolution_by_strategy("", "simplified") == "Other"
        assert group_resolution_by_strategy("", "standard") == ""
        assert group_resolution_by_strategy("", "detailed") == ""

    def test_invalid_grouping_strategy_fallback(self) -> None:
        """Test fallback behavior for invalid grouping strategies."""
        from src.tgraph_bot.graphs.graph_modules.utils.resolution_grouping import group_resolution_by_strategy
        
        # Should fallback to detailed strategy for invalid strategy names
        result = group_resolution_by_strategy("1920x1080", "invalid_strategy")
        assert result == "1080p (1920×1080)"  # detailed format
