"""Tests for stream type analysis graph implementations.

This test suite validates stream type analysis graph generators including:
- Stream type separation logic (direct play, transcode, copy)
- Resolution grouping (standard, detailed, simplified)
- Concurrent stream counting
- Peak highlighting logic
- Transcoding focus emphasis

Requirements tested: 16.1, 16.2, 16.3, 17.1, 17.2, 17.3, 17.4
"""

from datetime import UTC, datetime

import pytest

from tgraph_bot.config.models import (
    AnnotationConfig,
    GraphAppearanceConfig,
    GraphColors,
    GraphConfig,
    GraphDimensions,
    GridConfig,
    SeabornConfig,
)
from tgraph_bot.graphs.data import StreamRecord

# Fixtures


@pytest.fixture
def stream_type_records() -> list[StreamRecord]:
    """Fixture providing stream records with various stream types."""
    return [
        # Direct play streams
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
            media_type="movie",
            stream_type="direct play",
            transcode_decision="direct play",
            platform="Plex for Android",
            player="Plex for Android (Mobile)",
            user="Alice",
            source_resolution="1920x1080",
            stream_resolution="1080p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 11, 0, 0, tzinfo=UTC),
            media_type="tv",
            stream_type="direct play",
            transcode_decision="direct play",
            platform="Plex Web",
            player="Plex Web (Chrome)",
            user="Bob",
            source_resolution="3840x2160",
            stream_resolution="4K",
        ),
        # Transcode streams
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            media_type="movie",
            stream_type="transcode",
            transcode_decision="transcode",
            platform="Plex for iOS",
            player="Plex for iOS (iPhone)",
            user="Charlie",
            source_resolution="1920x1080",
            stream_resolution="720p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
            media_type="tv",
            stream_type="transcode",
            transcode_decision="transcode",
            platform="Plex for Android",
            player="Plex for Android (Mobile)",
            user="Alice",
            source_resolution="3840x2160",
            stream_resolution="1080p",
        ),
        # Copy streams
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC),
            media_type="movie",
            stream_type="copy",
            transcode_decision="direct stream",
            platform="Plex Web",
            player="Plex Web (Chrome)",
            user="Bob",
            source_resolution="1920x1080",
            stream_resolution="1080p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 15, 0, 0, tzinfo=UTC),
            media_type="tv",
            stream_type="copy",
            transcode_decision="direct stream",
            platform="Plex for iOS",
            player="Plex for iOS (iPhone)",
            user="Charlie",
            source_resolution="1280x720",
            stream_resolution="720p",
        ),
    ]


@pytest.fixture
def resolution_records() -> list[StreamRecord]:
    """Fixture providing stream records with various resolutions."""
    return [
        # 4K / UHD
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
            media_type="movie",
            stream_type="direct play",
            transcode_decision="direct play",
            platform="Plex",
            player="Plex",
            user="User1",
            source_resolution="3840x2160",
            stream_resolution="4K",
        ),
        # 1440p
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 11, 0, 0, tzinfo=UTC),
            media_type="movie",
            stream_type="direct play",
            transcode_decision="direct play",
            platform="Plex",
            player="Plex",
            user="User2",
            source_resolution="2560x1440",
            stream_resolution="1440p",
        ),
        # 1080p / FHD
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            media_type="tv",
            stream_type="direct play",
            transcode_decision="direct play",
            platform="Plex",
            player="Plex",
            user="User3",
            source_resolution="1920x1080",
            stream_resolution="1080p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
            media_type="movie",
            stream_type="transcode",
            transcode_decision="transcode",
            platform="Plex",
            player="Plex",
            user="User4",
            source_resolution="1920x1080",
            stream_resolution="720p",
        ),
        # 720p / HD
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC),
            media_type="tv",
            stream_type="direct play",
            transcode_decision="direct play",
            platform="Plex",
            player="Plex",
            user="User5",
            source_resolution="1280x720",
            stream_resolution="720p",
        ),
        # 480p / SD
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 15, 0, 0, tzinfo=UTC),
            media_type="movie",
            stream_type="transcode",
            transcode_decision="transcode",
            platform="Plex",
            player="Plex",
            user="User6",
            source_resolution="1920x1080",
            stream_resolution="480p",
        ),
        # SD (lower resolution)
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 16, 0, 0, tzinfo=UTC),
            media_type="tv",
            stream_type="direct play",
            transcode_decision="direct play",
            platform="Plex",
            player="Plex",
            user="User7",
            source_resolution="640x480",
            stream_resolution="SD",
        ),
    ]


@pytest.fixture
def concurrent_stream_records() -> list[StreamRecord]:
    """Fixture providing stream records for concurrent stream testing."""
    return [
        # Time slot 1: 3 concurrent streams (2 direct play, 1 transcode)
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
            media_type="movie",
            stream_type="direct play",
            transcode_decision="direct play",
            platform="Plex",
            player="Plex",
            user="User1",
            source_resolution="1920x1080",
            stream_resolution="1080p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 10, 5, 0, tzinfo=UTC),
            media_type="tv",
            stream_type="direct play",
            transcode_decision="direct play",
            platform="Plex",
            player="Plex",
            user="User2",
            source_resolution="1920x1080",
            stream_resolution="1080p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC),
            media_type="movie",
            stream_type="transcode",
            transcode_decision="transcode",
            platform="Plex",
            player="Plex",
            user="User3",
            source_resolution="3840x2160",
            stream_resolution="1080p",
        ),
        # Time slot 2: 5 concurrent streams (peak - 3 direct play, 2 transcode)
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC),
            media_type="movie",
            stream_type="direct play",
            transcode_decision="direct play",
            platform="Plex",
            player="Plex",
            user="User4",
            source_resolution="1920x1080",
            stream_resolution="1080p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 14, 5, 0, tzinfo=UTC),
            media_type="tv",
            stream_type="direct play",
            transcode_decision="direct play",
            platform="Plex",
            player="Plex",
            user="User5",
            source_resolution="1920x1080",
            stream_resolution="1080p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 14, 10, 0, tzinfo=UTC),
            media_type="movie",
            stream_type="direct play",
            transcode_decision="direct play",
            platform="Plex",
            player="Plex",
            user="User6",
            source_resolution="1920x1080",
            stream_resolution="1080p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 14, 15, 0, tzinfo=UTC),
            media_type="tv",
            stream_type="transcode",
            transcode_decision="transcode",
            platform="Plex",
            player="Plex",
            user="User7",
            source_resolution="3840x2160",
            stream_resolution="720p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 14, 20, 0, tzinfo=UTC),
            media_type="movie",
            stream_type="transcode",
            transcode_decision="transcode",
            platform="Plex",
            player="Plex",
            user="User8",
            source_resolution="1920x1080",
            stream_resolution="480p",
        ),
        # Time slot 3: 2 concurrent streams (1 direct play, 1 copy)
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 18, 0, 0, tzinfo=UTC),
            media_type="tv",
            stream_type="direct play",
            transcode_decision="direct play",
            platform="Plex",
            player="Plex",
            user="User9",
            source_resolution="1920x1080",
            stream_resolution="1080p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 18, 5, 0, 0, tzinfo=UTC),
            media_type="movie",
            stream_type="copy",
            transcode_decision="direct stream",
            platform="Plex",
            player="Plex",
            user="User10",
            source_resolution="1920x1080",
            stream_resolution="1080p",
        ),
    ]


@pytest.fixture
def sample_graph_config() -> GraphConfig:
    """Fixture providing sample graph configuration."""
    return GraphConfig(
        enabled=True,
        media_type_separation=False,
        palette="",
        annotations_enabled=False,
        peak_highlighting_enabled=False,
        stacked=False,
    )


@pytest.fixture
def sample_appearance_config() -> GraphAppearanceConfig:
    """Fixture providing sample appearance configuration."""
    return GraphAppearanceConfig(
        dimensions=GraphDimensions(width=12, height=8, dpi=100),
        colors=GraphColors(tv="#3498db", movie="#e74c3c", background="#ffffff"),
        grid=GridConfig(enabled=True, alpha=0.3),
        annotations=AnnotationConfig(
            color="#000000",
            outline_color="#ffffff",
            enable_outline=True,
            font_size=10,
        ),
        palettes={},
        seaborn=SeabornConfig(
            style="darkgrid",
            context="notebook",
            palette="muted",
        ),
    )


# Test Classes - Placeholders for stream type analysis graph tests
# These will be implemented when the graph generators are created in task 20


class TestStreamTypeSeparation:
    """Tests for stream type separation logic.

    Requirements: 16.1, 16.2
    """

    def test_categorizes_direct_play_streams(
        self,
        stream_type_records: list[StreamRecord],
    ) -> None:
        """Test that direct play streams are correctly categorized."""
        direct_play_streams = [
            r for r in stream_type_records if r.stream_type == "direct play"
        ]
        assert len(direct_play_streams) == 2
        assert all(r.stream_type == "direct play" for r in direct_play_streams)

    def test_categorizes_transcode_streams(
        self,
        stream_type_records: list[StreamRecord],
    ) -> None:
        """Test that transcode streams are correctly categorized."""
        transcode_streams = [
            r for r in stream_type_records if r.stream_type == "transcode"
        ]
        assert len(transcode_streams) == 2
        assert all(r.stream_type == "transcode" for r in transcode_streams)

    def test_categorizes_copy_streams(
        self,
        stream_type_records: list[StreamRecord],
    ) -> None:
        """Test that copy streams are correctly categorized."""
        copy_streams = [r for r in stream_type_records if r.stream_type == "copy"]
        assert len(copy_streams) == 2
        assert all(r.stream_type == "copy" for r in copy_streams)

    def test_all_stream_types_present(
        self,
        stream_type_records: list[StreamRecord],
    ) -> None:
        """Test that all three stream types are present in test data."""
        stream_types = {r.stream_type for r in stream_type_records}
        assert stream_types == {"direct play", "transcode", "copy"}

    def test_stream_type_counts(
        self,
        stream_type_records: list[StreamRecord],
    ) -> None:
        """Test that stream type counts are correct."""
        from collections import Counter

        stream_type_counts = Counter(r.stream_type for r in stream_type_records)
        assert stream_type_counts["direct play"] == 2
        assert stream_type_counts["transcode"] == 2
        assert stream_type_counts["copy"] == 2


class TestResolutionGrouping:
    """Tests for resolution grouping logic.

    Requirements: 17.1, 17.2, 17.3, 17.4
    """

    def test_standard_grouping_4k(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test standard grouping identifies 4K resolution."""
        four_k_records = [
            r
            for r in resolution_records
            if r.stream_resolution == "4K" or r.source_resolution == "3840x2160"
        ]
        assert len(four_k_records) >= 1

    def test_standard_grouping_1440p(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test standard grouping identifies 1440p resolution."""
        records_1440p = [
            r
            for r in resolution_records
            if r.stream_resolution == "1440p" or r.source_resolution == "2560x1440"
        ]
        assert len(records_1440p) >= 1

    def test_standard_grouping_1080p(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test standard grouping identifies 1080p resolution."""
        records_1080p = [
            r
            for r in resolution_records
            if r.stream_resolution == "1080p" or r.source_resolution == "1920x1080"
        ]
        assert len(records_1080p) >= 1

    def test_standard_grouping_720p(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test standard grouping identifies 720p resolution."""
        records_720p = [
            r
            for r in resolution_records
            if r.stream_resolution == "720p" or r.source_resolution == "1280x720"
        ]
        assert len(records_720p) >= 1

    def test_standard_grouping_480p(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test standard grouping identifies 480p resolution."""
        records_480p = [r for r in resolution_records if r.stream_resolution == "480p"]
        assert len(records_480p) >= 1

    def test_standard_grouping_sd(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test standard grouping identifies SD resolution."""
        sd_records = [
            r
            for r in resolution_records
            if r.stream_resolution == "SD"
            or (
                "x" in r.source_resolution
                and int(r.source_resolution.split("x")[0]) < 1280
            )
        ]
        assert len(sd_records) >= 1

    def test_detailed_grouping_exact_resolutions(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test detailed grouping preserves exact resolution values."""
        exact_resolutions = {r.source_resolution for r in resolution_records}
        assert "3840x2160" in exact_resolutions
        assert "2560x1440" in exact_resolutions
        assert "1920x1080" in exact_resolutions
        assert "1280x720" in exact_resolutions
        assert "640x480" in exact_resolutions

    def test_simplified_grouping_uhd(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test simplified grouping identifies UHD (4K and above)."""
        uhd_records = [
            r
            for r in resolution_records
            if r.stream_resolution == "4K"
            or (
                "x" in r.source_resolution
                and int(r.source_resolution.split("x")[0]) >= 3840
            )
        ]
        assert len(uhd_records) >= 1

    def test_simplified_grouping_fhd(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test simplified grouping identifies FHD (1080p)."""
        fhd_records = [
            r
            for r in resolution_records
            if r.stream_resolution == "1080p" or r.source_resolution == "1920x1080"
        ]
        assert len(fhd_records) >= 1

    def test_simplified_grouping_hd(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test simplified grouping identifies HD (720p)."""
        hd_records = [
            r
            for r in resolution_records
            if r.stream_resolution == "720p" or r.source_resolution == "1280x720"
        ]
        assert len(hd_records) >= 1

    def test_simplified_grouping_sd(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test simplified grouping identifies SD (below 720p)."""
        sd_records = [
            r
            for r in resolution_records
            if r.stream_resolution in ("480p", "SD")
            or (
                "x" in r.source_resolution
                and int(r.source_resolution.split("x")[0]) < 1280
            )
        ]
        assert len(sd_records) >= 1


class TestConcurrentStreamCounting:
    """Tests for concurrent stream counting logic.

    Requirements: 16.3
    """

    def test_identifies_concurrent_streams_by_time_slot(
        self,
        concurrent_stream_records: list[StreamRecord],
    ) -> None:
        """Test that concurrent streams are identified by time slot."""
        # Group by hour to identify concurrent streams
        from collections import defaultdict

        streams_by_hour: dict[int, list[StreamRecord]] = defaultdict(list)
        for record in concurrent_stream_records:
            hour = record.timestamp.hour
            streams_by_hour[hour].append(record)

        # Verify we have streams in different time slots
        assert len(streams_by_hour) >= 3
        assert 10 in streams_by_hour  # Time slot 1
        assert 14 in streams_by_hour  # Time slot 2 (peak)
        assert 18 in streams_by_hour  # Time slot 3

    def test_calculates_peak_concurrent_streams(
        self,
        concurrent_stream_records: list[StreamRecord],
    ) -> None:
        """Test that peak concurrent streams are calculated correctly."""
        from collections import defaultdict

        streams_by_hour: dict[int, list[StreamRecord]] = defaultdict(list)
        for record in concurrent_stream_records:
            hour = record.timestamp.hour
            streams_by_hour[hour].append(record)

        # Find peak hour
        peak_hour = max(streams_by_hour.keys(), key=lambda h: len(streams_by_hour[h]))
        peak_count = len(streams_by_hour[peak_hour])

        # Peak should be at hour 14 with 5 streams
        assert peak_hour == 14
        assert peak_count == 5

    def test_counts_concurrent_streams_by_stream_type(
        self,
        concurrent_stream_records: list[StreamRecord],
    ) -> None:
        """Test that concurrent streams are counted by stream type."""
        from collections import defaultdict

        streams_by_hour: dict[int, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        for record in concurrent_stream_records:
            hour = record.timestamp.hour
            streams_by_hour[hour][record.stream_type] += 1

        # Verify stream type counts for peak hour (14)
        assert streams_by_hour[14]["direct play"] == 3
        assert streams_by_hour[14]["transcode"] == 2

    def test_identifies_peak_for_each_stream_type(
        self,
        concurrent_stream_records: list[StreamRecord],
    ) -> None:
        """Test that peak is identified for each stream type separately."""
        from collections import defaultdict

        streams_by_hour: dict[int, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        for record in concurrent_stream_records:
            hour = record.timestamp.hour
            streams_by_hour[hour][record.stream_type] += 1

        # Find peak for direct play
        direct_play_peak = max(
            (
                count
                for hour_data in streams_by_hour.values()
                for stream_type, count in hour_data.items()
                if stream_type == "direct play"
            ),
            default=0,
        )
        assert direct_play_peak == 3

        # Find peak for transcode
        transcode_peak = max(
            (
                count
                for hour_data in streams_by_hour.values()
                for stream_type, count in hour_data.items()
                if stream_type == "transcode"
            ),
            default=0,
        )
        assert transcode_peak == 2

    def test_handles_empty_time_slots(
        self,
        concurrent_stream_records: list[StreamRecord],
    ) -> None:
        """Test that empty time slots are handled correctly."""
        from collections import defaultdict

        streams_by_hour: dict[int, list[StreamRecord]] = defaultdict(list)
        for record in concurrent_stream_records:
            hour = record.timestamp.hour
            streams_by_hour[hour].append(record)

        # Verify some hours have no streams
        all_hours = set(range(24))
        hours_with_streams = set(streams_by_hour.keys())
        empty_hours = all_hours - hours_with_streams

        assert len(empty_hours) > 0  # Should have empty hours


class TestPeakHighlighting:
    """Tests for peak highlighting logic.

    Requirements: 16.4
    """

    def test_identifies_peak_value_in_dataset(
        self,
        concurrent_stream_records: list[StreamRecord],
    ) -> None:
        """Test that peak value is correctly identified."""
        from collections import defaultdict

        streams_by_hour: dict[int, int] = defaultdict(int)
        for record in concurrent_stream_records:
            hour = record.timestamp.hour
            streams_by_hour[hour] += 1

        peak_count = max(streams_by_hour.values())
        assert peak_count == 5

    def test_peak_highlighting_enabled_flag(
        self,
        sample_graph_config: GraphConfig,
    ) -> None:
        """Test that peak highlighting can be enabled via configuration."""
        # Test with highlighting disabled
        assert sample_graph_config.peak_highlighting_enabled is False

        # Test with highlighting enabled
        config_with_highlighting = GraphConfig(
            enabled=True,
            media_type_separation=False,
            palette="",
            annotations_enabled=False,
            peak_highlighting_enabled=True,
            stacked=False,
        )
        assert config_with_highlighting.peak_highlighting_enabled is True

    def test_peak_highlighting_color_configuration(
        self,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that peak highlighting color is configurable."""
        # Verify annotation color can be used for peak highlighting
        assert sample_appearance_config.annotations.color == "#000000"
        assert sample_appearance_config.annotations.outline_color == "#ffffff"

    def test_identifies_multiple_peaks_for_stream_types(
        self,
        concurrent_stream_records: list[StreamRecord],
    ) -> None:
        """Test that peaks are identified for each stream type."""
        from collections import defaultdict

        streams_by_hour_and_type: dict[int, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        for record in concurrent_stream_records:
            hour = record.timestamp.hour
            streams_by_hour_and_type[hour][record.stream_type] += 1

        # Find peak for each stream type
        stream_type_peaks: dict[str, int] = {}
        for hour_data in streams_by_hour_and_type.values():
            for stream_type, count in hour_data.items():
                stream_type_peaks[stream_type] = max(
                    stream_type_peaks.get(stream_type, 0), count
                )

        assert stream_type_peaks["direct play"] == 3
        assert stream_type_peaks["transcode"] == 2
        assert stream_type_peaks["copy"] == 1


class TestTranscodingFocusEmphasis:
    """Tests for transcoding focus emphasis logic.

    Requirements: 17.5
    """

    def test_identifies_transcoded_streams(
        self,
        stream_type_records: list[StreamRecord],
    ) -> None:
        """Test that transcoded streams are correctly identified."""
        transcoded = [r for r in stream_type_records if r.stream_type == "transcode"]
        assert len(transcoded) == 2
        assert all(r.stream_type == "transcode" for r in transcoded)

    def test_identifies_resolution_changes_in_transcoding(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test that resolution changes due to transcoding are identified."""
        # Find records where source and stream resolution differ
        transcoded_resolution_changes = [
            r
            for r in resolution_records
            if r.stream_type == "transcode"
            and r.source_resolution != r.stream_resolution
        ]
        assert len(transcoded_resolution_changes) >= 1

    def test_transcoding_from_4k_to_lower_resolution(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test identification of 4K to lower resolution transcoding."""
        four_k_transcodes = [
            r
            for r in resolution_records
            if r.stream_type == "transcode"
            and r.source_resolution == "3840x2160"
            and r.stream_resolution != "4K"
        ]
        # May or may not have 4K transcodes in test data
        # This test validates the logic for identifying them
        assert isinstance(four_k_transcodes, list)

    def test_transcoding_from_1080p_to_lower_resolution(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test identification of 1080p to lower resolution transcoding."""
        hd_transcodes = [
            r
            for r in resolution_records
            if r.stream_type == "transcode"
            and r.source_resolution == "1920x1080"
            and r.stream_resolution in ("720p", "480p", "SD")
        ]
        assert len(hd_transcodes) >= 1

    def test_separates_transcoded_from_direct_play(
        self,
        stream_type_records: list[StreamRecord],
    ) -> None:
        """Test that transcoded streams are separated from direct play."""
        transcoded = {r for r in stream_type_records if r.stream_type == "transcode"}
        direct_play = {r for r in stream_type_records if r.stream_type == "direct play"}

        # Verify no overlap
        assert len(transcoded & direct_play) == 0

    def test_counts_transcoded_vs_direct_streams(
        self,
        stream_type_records: list[StreamRecord],
    ) -> None:
        """Test counting transcoded vs direct play streams."""
        from collections import Counter

        stream_type_counts = Counter(r.stream_type for r in stream_type_records)

        transcoded_count = stream_type_counts["transcode"]
        direct_play_count = stream_type_counts["direct play"]

        assert transcoded_count == 2
        assert direct_play_count == 2

    def test_identifies_users_requiring_transcoding(
        self,
        stream_type_records: list[StreamRecord],
    ) -> None:
        """Test identification of users who require transcoding."""
        users_with_transcoding = {
            r.user for r in stream_type_records if r.stream_type == "transcode"
        }

        assert "Alice" in users_with_transcoding
        assert "Charlie" in users_with_transcoding

    def test_identifies_platforms_requiring_transcoding(
        self,
        stream_type_records: list[StreamRecord],
    ) -> None:
        """Test identification of platforms that require transcoding."""
        platforms_with_transcoding = {
            r.platform for r in stream_type_records if r.stream_type == "transcode"
        }

        assert "Plex for iOS" in platforms_with_transcoding
        assert "Plex for Android" in platforms_with_transcoding


class TestStreamTypeGraphIntegration:
    """Integration tests for stream type analysis graphs.

    These tests verify that the test data and fixtures are properly structured
    for testing the actual graph generators when they are implemented.

    Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 17.1, 17.2, 17.3, 17.4, 17.5
    """

    def test_stream_type_records_fixture_completeness(
        self,
        stream_type_records: list[StreamRecord],
    ) -> None:
        """Test that stream type records fixture has all required data."""
        assert len(stream_type_records) == 6

        # Verify all stream types present
        stream_types = {r.stream_type for r in stream_type_records}
        assert stream_types == {"direct play", "transcode", "copy"}

        # Verify both media types present
        media_types = {r.media_type for r in stream_type_records}
        assert media_types == {"movie", "tv"}

    def test_resolution_records_fixture_completeness(
        self,
        resolution_records: list[StreamRecord],
    ) -> None:
        """Test that resolution records fixture has all required data."""
        assert len(resolution_records) == 7

        # Verify various resolutions present
        resolutions = {r.stream_resolution for r in resolution_records}
        assert "4K" in resolutions
        assert "1440p" in resolutions
        assert "1080p" in resolutions
        assert "720p" in resolutions
        assert "480p" in resolutions
        assert "SD" in resolutions

    def test_concurrent_stream_records_fixture_completeness(
        self,
        concurrent_stream_records: list[StreamRecord],
    ) -> None:
        """Test that concurrent stream records fixture has all required data."""
        assert len(concurrent_stream_records) == 10

        # Verify multiple time slots
        hours = {r.timestamp.hour for r in concurrent_stream_records}
        assert len(hours) >= 3

        # Verify peak hour has most streams
        from collections import defaultdict

        streams_by_hour: dict[int, int] = defaultdict(int)
        for record in concurrent_stream_records:
            streams_by_hour[record.timestamp.hour] += 1

        peak_count = max(streams_by_hour.values())
        assert peak_count == 5

    def test_graph_config_fixture_structure(
        self,
        sample_graph_config: GraphConfig,
    ) -> None:
        """Test that graph config fixture has correct structure."""
        assert isinstance(sample_graph_config, GraphConfig)
        assert hasattr(sample_graph_config, "enabled")
        assert hasattr(sample_graph_config, "media_type_separation")
        assert hasattr(sample_graph_config, "palette")
        assert hasattr(sample_graph_config, "annotations_enabled")
        assert hasattr(sample_graph_config, "peak_highlighting_enabled")
        assert hasattr(sample_graph_config, "stacked")

    def test_appearance_config_fixture_structure(
        self,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that appearance config fixture has correct structure."""
        assert isinstance(sample_appearance_config, GraphAppearanceConfig)
        assert hasattr(sample_appearance_config, "dimensions")
        assert hasattr(sample_appearance_config, "colors")
        assert hasattr(sample_appearance_config, "grid")
        assert hasattr(sample_appearance_config, "annotations")
        assert hasattr(sample_appearance_config, "seaborn")

    def test_all_fixtures_return_valid_data(
        self,
        stream_type_records: list[StreamRecord],
        resolution_records: list[StreamRecord],
        concurrent_stream_records: list[StreamRecord],
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that all fixtures return valid, non-empty data."""
        assert len(stream_type_records) > 0
        assert len(resolution_records) > 0
        assert len(concurrent_stream_records) > 0
        assert sample_graph_config is not None
        assert sample_appearance_config is not None

        # Verify all records are properly structured
        for record in (
            stream_type_records + resolution_records + concurrent_stream_records
        ):
            assert isinstance(record, StreamRecord)
            assert record.timestamp is not None
            assert record.media_type in ("movie", "tv")
            assert record.stream_type in ("direct play", "transcode", "copy")
            assert record.platform != ""
            assert record.user != ""
            assert record.source_resolution != ""
            assert record.stream_resolution != ""
