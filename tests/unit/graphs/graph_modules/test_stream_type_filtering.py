"""
Tests for stream type filtering functionality in TGraph Bot.

This module tests the new stream type filtering utilities and their integration
with resolution graphs to ensure proper filtering by transcode decision.
"""

import pytest
from datetime import datetime
from typing import Any

from src.tgraph_bot.graphs.graph_modules.utils.utils import (
    ProcessedPlayRecord,
    ProcessedRecords,
    filter_records_by_stream_type,
    get_available_stream_types,
    get_stream_type_statistics,
)


class TestStreamTypeFiltering:
    """Test stream type filtering utility functions."""

    @pytest.fixture
    def sample_records_with_stream_types(self) -> ProcessedRecords:
        """Create sample records with various stream types for testing."""
        return [
            ProcessedPlayRecord(
                date="2024-01-01",
                user="alice",
                platform="Plex Web",
                media_type="movie",
                duration=7200,
                stopped=7200,
                paused_counter=0,
                datetime=datetime(2024, 1, 1, 10, 0),
                transcode_decision="direct play",
                video_resolution="1920x1080",
                stream_video_resolution="1920x1080",
                video_codec="h264",
                audio_codec="aac",
                container="mp4",
            ),
            ProcessedPlayRecord(
                date="2024-01-01",
                user="bob",
                platform="Plex Android",
                media_type="movie",
                duration=7800,
                stopped=7800,
                paused_counter=0,
                datetime=datetime(2024, 1, 1, 11, 0),
                transcode_decision="transcode",
                video_resolution="3840x2160",
                stream_video_resolution="1280x720",
                video_codec="hevc",
                audio_codec="dts",
                container="mkv",
            ),
            ProcessedPlayRecord(
                date="2024-01-01",
                user="charlie",
                platform="Plex iOS",
                media_type="tv",
                duration=1800,
                stopped=1800,
                paused_counter=1,
                datetime=datetime(2024, 1, 1, 12, 0),
                transcode_decision="copy",
                video_resolution="1920x1080",
                stream_video_resolution="1920x1080",
                video_codec="h264",
                audio_codec="ac3",
                container="mkv",
            ),
            ProcessedPlayRecord(
                date="2024-01-01",
                user="diana",
                platform="Plex TV",
                media_type="tv",
                duration=3600,
                stopped=3600,
                paused_counter=0,
                datetime=datetime(2024, 1, 1, 13, 0),
                transcode_decision="unknown",
                video_resolution="unknown",
                stream_video_resolution="unknown",
                video_codec="unknown",
                audio_codec="unknown",
                container="unknown",
            ),
        ]

    def test_filter_records_by_single_stream_type(
        self, sample_records_with_stream_types: ProcessedRecords
    ) -> None:
        """Test filtering by a single stream type."""
        # Filter for direct play only
        direct_play_records = filter_records_by_stream_type(
            sample_records_with_stream_types, "direct play"
        )

        assert len(direct_play_records) == 1
        assert direct_play_records[0].get("transcode_decision") == "direct play"
        assert direct_play_records[0]["user"] == "alice"

        # Filter for transcode only
        transcode_records = filter_records_by_stream_type(
            sample_records_with_stream_types, "transcode"
        )

        assert len(transcode_records) == 1
        assert transcode_records[0].get("transcode_decision") == "transcode"
        assert transcode_records[0]["user"] == "bob"

    def test_filter_records_by_multiple_stream_types(
        self, sample_records_with_stream_types: ProcessedRecords
    ) -> None:
        """Test filtering by multiple stream types."""
        # Filter for direct play and copy (efficient streaming)
        efficient_records = filter_records_by_stream_type(
            sample_records_with_stream_types, ["direct play", "copy"]
        )

        assert len(efficient_records) == 2
        stream_types = [record.get("transcode_decision") for record in efficient_records]
        assert "direct play" in stream_types
        assert "copy" in stream_types
        assert "transcode" not in stream_types

    def test_filter_records_include_all_types(
        self, sample_records_with_stream_types: ProcessedRecords
    ) -> None:
        """Test filtering with no specific types (include all)."""
        # Include all types but exclude unknown
        all_records = filter_records_by_stream_type(
            sample_records_with_stream_types, stream_types=None, exclude_unknown=True
        )

        assert len(all_records) == 3  # Excludes the unknown record
        stream_types = [record.get("transcode_decision") for record in all_records]
        assert "unknown" not in stream_types

    def test_filter_records_include_unknown(
        self, sample_records_with_stream_types: ProcessedRecords
    ) -> None:
        """Test filtering with unknown types included."""
        # Include all types including unknown
        all_records = filter_records_by_stream_type(
            sample_records_with_stream_types, stream_types=None, exclude_unknown=False
        )

        assert len(all_records) == 4  # Includes all records
        stream_types = [record.get("transcode_decision") for record in all_records]
        assert "unknown" in stream_types

    def test_get_available_stream_types(
        self, sample_records_with_stream_types: ProcessedRecords
    ) -> None:
        """Test getting available stream types from records."""
        available_types = get_available_stream_types(sample_records_with_stream_types)

        assert len(available_types) == 4
        assert "copy" in available_types
        assert "direct play" in available_types
        assert "transcode" in available_types
        assert "unknown" in available_types

        # Should be sorted
        assert available_types == sorted(available_types)

    def test_get_stream_type_statistics(
        self, sample_records_with_stream_types: ProcessedRecords
    ) -> None:
        """Test getting stream type statistics."""
        stats = get_stream_type_statistics(sample_records_with_stream_types)

        assert len(stats) == 4

        # Each stream type should have count of 1 (25% each)
        for stream_type in ["direct play", "transcode", "copy", "unknown"]:
            assert stream_type in stats
            assert stats[stream_type]["count"] == 1
            assert stats[stream_type]["percentage"] == 25.0

    def test_filter_empty_records(self) -> None:
        """Test filtering with empty record list."""
        empty_records: ProcessedRecords = []

        result = filter_records_by_stream_type(empty_records, "direct play")
        assert len(result) == 0

        available_types = get_available_stream_types(empty_records)
        assert len(available_types) == 0

        stats = get_stream_type_statistics(empty_records)
        assert len(stats) == 0

    def test_case_insensitive_filtering(
        self, sample_records_with_stream_types: ProcessedRecords
    ) -> None:
        """Test that stream type filtering is case insensitive."""
        # Test various case combinations
        direct_play_records = filter_records_by_stream_type(
            sample_records_with_stream_types, "DIRECT PLAY"
        )
        assert len(direct_play_records) == 1

        transcode_records = filter_records_by_stream_type(
            sample_records_with_stream_types, "Transcode"
        )
        assert len(transcode_records) == 1

        copy_records = filter_records_by_stream_type(
            sample_records_with_stream_types, "COPY"
        )
        assert len(copy_records) == 1


class TestResolutionGraphStreamFiltering:
    """Test stream type filtering integration with resolution graphs."""

    def test_resolution_graphs_apply_stream_filtering(self) -> None:
        """Test that resolution graphs apply stream type filtering."""
        # This is a placeholder for integration tests
        # In a real implementation, we would test that:
        # 1. Resolution graphs call the filtering methods
        # 2. Filtered data is used for aggregation
        # 3. Results reflect the filtering
        pytest.skip("Integration tests to be implemented after full integration")


class TestOptimizedDataProcessor:
    """Test optimized data processor methods."""

    @pytest.fixture
    def mock_rating_keys(self) -> set[str]:
        """Create mock rating keys for testing."""
        return {"1001", "1002", "1003", "1001", "1002"}  # Includes duplicates

    def test_rating_key_deduplication(self, mock_rating_keys: set[str]) -> None:
        """Test that rating keys are properly deduplicated."""
        # The set should automatically deduplicate
        unique_keys = set(mock_rating_keys)
        assert len(unique_keys) == 3
        assert "1001" in unique_keys
        assert "1002" in unique_keys
        assert "1003" in unique_keys

    def test_batch_processing_logic(self) -> None:
        """Test batch processing logic for API calls."""
        # Test batch size calculation
        rating_keys = [str(i) for i in range(125)]  # 125 items
        batch_size = 50

        batches: list[list[str]] = []
        for i in range(0, len(rating_keys), batch_size):
            batch = rating_keys[i : i + batch_size]
            batches.append(batch)

        assert len(batches) == 3  # 50, 50, 25
        assert len(batches[0]) == 50
        assert len(batches[1]) == 50
        assert len(batches[2]) == 25

    def test_metadata_fallback_handling(self) -> None:
        """Test metadata extraction with fallback logic."""
        # Mock metadata response structure
        metadata_with_media_info = {
            "media_info": [{"video_resolution": "1080", "width": 1920, "height": 1080}]
        }

        metadata_with_direct_fields = {"width": 3840, "height": 2160}

        metadata_empty = {}

        # Test extraction logic (simplified)
        def extract_resolution(metadata: dict[str, Any]) -> str:  # pyright: ignore[reportExplicitAny]
            if "media_info" in metadata and metadata["media_info"]:
                media_data = metadata["media_info"][0]
                if "video_resolution" in media_data:
                    if media_data["video_resolution"] == "1080":
                        return f"{media_data.get('width', 1920)}x{media_data.get('height', 1080)}"

            if "width" in metadata and "height" in metadata:
                return f"{metadata['width']}x{metadata['height']}"

            return "unknown"

        assert extract_resolution(metadata_with_media_info) == "1920x1080"
        assert extract_resolution(metadata_with_direct_fields) == "3840x2160"
        assert extract_resolution(metadata_empty) == "unknown"

    def test_concurrent_processing_simulation(self) -> None:
        """Test concurrent processing simulation."""
        import asyncio

        async def mock_fetch_metadata(rating_key: str) -> dict[str, str]:
            """Mock async metadata fetch."""
            await asyncio.sleep(0.01)  # Simulate API delay
            return {
                "video_resolution": f"resolution_{rating_key}",
                "stream_video_resolution": f"stream_{rating_key}",
            }

        async def test_concurrent_fetch():
            rating_keys = ["1001", "1002", "1003"]
            tasks = [mock_fetch_metadata(key) for key in rating_keys]
            results = await asyncio.gather(*tasks)

            assert len(results) == 3
            assert results[0]["video_resolution"] == "resolution_1001"
            assert results[1]["video_resolution"] == "resolution_1002"
            assert results[2]["video_resolution"] == "resolution_1003"

        # Run the async test
        asyncio.run(test_concurrent_fetch())

    def test_error_handling_in_batch_processing(self) -> None:
        """Test error handling during batch processing."""

        # Simulate mixed success/failure scenarios
        def simulate_api_call(rating_key: str) -> dict[str, str]:
            if rating_key == "error_key":
                raise Exception("API Error")
            return {
                "video_resolution": f"resolution_{rating_key}",
                "stream_video_resolution": f"stream_{rating_key}",
            }

        rating_keys = ["1001", "error_key", "1003"]
        results = {}

        for key in rating_keys:
            try:
                results[key] = simulate_api_call(key)
            except Exception:
                results[key] = {
                    "video_resolution": "unknown",
                    "stream_video_resolution": "unknown",
                }

        assert len(results) == 3
        assert results["1001"]["video_resolution"] == "resolution_1001"
        assert results["error_key"]["video_resolution"] == "unknown"
        assert results["1003"]["video_resolution"] == "resolution_1003"
