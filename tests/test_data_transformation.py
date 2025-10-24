"""Tests for data transformation and privacy features.

This test suite validates the data transformation system including:
- StreamRecord creation from Tautulli API responses
- Data aggregation functions (by date, day, hour, platform, user, month)
- Username anonymization logic with consistent labels
- Edge case handling (empty data, single record, duplicate timestamps)

Requirements tested: 13.1, 13.2, 13.3, 13.4, 13.5
"""

# pyright: reportExplicitAny=false

from datetime import UTC, datetime
from typing import Any

import pytest

# Import the data models and functions
from tgraph_bot.graphs.data import (
    StreamRecord,
    aggregate_by_date,
    aggregate_by_day_of_week,
    aggregate_by_hour,
    aggregate_by_month,
    aggregate_by_platform,
    aggregate_by_user,
    anonymize_usernames,
    create_stream_record,
)


# Fixtures for test data
@pytest.fixture
def sample_tautulli_record() -> dict[str, Any]:
    """Fixture providing a sample Tautulli API response record."""
    return {
        "date": 1704067200,  # 2024-01-01 00:00:00 UTC
        "media_type": "movie",
        "stream_type": "direct play",
        "transcode_decision": "direct play",
        "platform": "Plex for Android",
        "player": "Plex for Android (Mobile)",
        "user": "JohnDoe",
        "stream_video_resolution": "1080p",
        "stream_video_full_resolution": "1920x1080",
        "duration": 7200,
        "play_duration": 7200,
        "percent_complete": 100,
        "location": "lan",
    }


@pytest.fixture
def sample_tautulli_tv_record() -> dict[str, Any]:
    """Fixture providing a sample Tautulli API response for TV show."""
    return {
        "date": 1704070800,  # 2024-01-01 01:00:00 UTC
        "media_type": "episode",
        "stream_type": "transcode",
        "transcode_decision": "transcode",
        "platform": "Plex for iOS",
        "player": "Plex for iOS (iPhone)",
        "user": "JaneDoe",
        "stream_video_resolution": "720p",
        "stream_video_full_resolution": "1280x720",
        "duration": 2700,
        "play_duration": 2400,
        "percent_complete": 89,
        "location": "wan",
    }


@pytest.fixture
def multiple_tautulli_records() -> list[dict[str, Any]]:
    """Fixture providing multiple Tautulli API response records for testing aggregation."""
    return [
        {
            "date": 1704067200,  # 2024-01-01 00:00:00 UTC (Monday)
            "media_type": "movie",
            "stream_type": "direct play",
            "transcode_decision": "direct play",
            "platform": "Plex for Android",
            "player": "Plex for Android (Mobile)",
            "user": "Alice",
            "stream_video_resolution": "1080p",
            "stream_video_full_resolution": "1920x1080",
        },
        {
            "date": 1704070800,  # 2024-01-01 01:00:00 UTC (Monday)
            "media_type": "episode",
            "stream_type": "transcode",
            "transcode_decision": "transcode",
            "platform": "Plex for iOS",
            "player": "Plex for iOS (iPhone)",
            "user": "Bob",
            "stream_video_resolution": "720p",
            "stream_video_full_resolution": "1280x720",
        },
        {
            "date": 1704153600,  # 2024-01-02 00:00:00 UTC (Tuesday)
            "media_type": "movie",
            "stream_type": "direct play",
            "transcode_decision": "direct play",
            "platform": "Plex for Android",
            "player": "Plex for Android (Mobile)",
            "user": "Alice",
            "stream_video_resolution": "4K",
            "stream_video_full_resolution": "3840x2160",
        },
        {
            "date": 1704157200,  # 2024-01-02 01:00:00 UTC (Tuesday)
            "media_type": "movie",
            "stream_type": "copy",
            "transcode_decision": "direct stream",
            "platform": "Plex Web",
            "player": "Plex Web (Chrome)",
            "user": "Charlie",
            "stream_video_resolution": "1080p",
            "stream_video_full_resolution": "1920x1080",
        },
        {
            "date": 1704240000,  # 2024-01-03 00:00:00 UTC (Wednesday)
            "media_type": "episode",
            "stream_type": "transcode",
            "transcode_decision": "transcode",
            "platform": "Plex for Android",
            "player": "Plex for Android (Mobile)",
            "user": "Bob",
            "stream_video_resolution": "480p",
            "stream_video_full_resolution": "720x480",
        },
    ]


class TestStreamRecordCreation:
    """Tests for creating StreamRecord from Tautulli API responses."""

    def test_create_stream_record_from_movie(
        self, sample_tautulli_record: dict[str, Any]
    ) -> None:
        """Test creating StreamRecord from a movie Tautulli response."""
        record = create_stream_record(sample_tautulli_record)

        assert isinstance(record, StreamRecord)
        assert record.timestamp == datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        assert record.media_type == "movie"
        assert record.stream_type == "direct play"
        assert record.platform == "Plex for Android"
        assert record.user == "JohnDoe"
        assert record.source_resolution == "1920x1080"
        assert record.stream_resolution == "1080p"

    def test_create_stream_record_from_tv_episode(
        self, sample_tautulli_tv_record: dict[str, Any]
    ) -> None:
        """Test creating StreamRecord from a TV episode Tautulli response."""
        record = create_stream_record(sample_tautulli_tv_record)

        assert isinstance(record, StreamRecord)
        assert record.timestamp == datetime(2024, 1, 1, 1, 0, 0, tzinfo=UTC)
        assert record.media_type == "tv"  # "episode" should be normalized to "tv"
        assert record.stream_type == "transcode"
        assert record.platform == "Plex for iOS"
        assert record.user == "JaneDoe"
        assert record.source_resolution == "1280x720"
        assert record.stream_resolution == "720p"

    @pytest.mark.parametrize(
        "media_type,expected",
        [
            ("movie", "movie"),
            ("episode", "tv"),
            ("track", "music"),  # If music is supported
        ],
    )
    def test_create_stream_record_normalizes_media_type(
        self, sample_tautulli_record: dict[str, Any], media_type: str, expected: str
    ) -> None:
        """Test that media_type is normalized correctly."""
        sample_tautulli_record["media_type"] = media_type
        record = create_stream_record(sample_tautulli_record)
        assert record.media_type == expected

    @pytest.mark.parametrize(
        "stream_type,expected",
        [
            ("direct play", "direct play"),
            ("Direct Play", "direct play"),  # Case normalization
            ("transcode", "transcode"),
            ("Transcode", "transcode"),
            ("copy", "copy"),
            ("Copy", "copy"),
        ],
    )
    def test_create_stream_record_normalizes_stream_type(
        self, sample_tautulli_record: dict[str, Any], stream_type: str, expected: str
    ) -> None:
        """Test that stream_type is normalized to lowercase."""
        sample_tautulli_record["stream_type"] = stream_type
        record = create_stream_record(sample_tautulli_record)
        assert record.stream_type == expected

    def test_create_stream_record_is_frozen(
        self, sample_tautulli_record: dict[str, Any]
    ) -> None:
        """Test that StreamRecord is immutable (frozen=True)."""
        record = create_stream_record(sample_tautulli_record)

        with pytest.raises((AttributeError, TypeError)):
            record.user = "Modified"  # pyright: ignore[reportAttributeAccessIssue]

    def test_create_stream_record_with_missing_fields(self) -> None:
        """Test creating StreamRecord with missing optional fields (duration, location)."""
        minimal_record = {
            "date": 1704067200,
            "media_type": "movie",
            "stream_type": "direct play",
            "transcode_decision": "direct play",
            "platform": "Unknown",
            "player": "Unknown Player",
            "user": "Guest",
            "stream_video_resolution": "",
            "stream_video_full_resolution": "",
            # Optional fields not included: duration, play_duration, percent_complete, location
        }

        record = create_stream_record(minimal_record)
        assert record.stream_resolution == ""
        assert record.source_resolution == ""


class TestDataAggregationByDate:
    """Tests for aggregating stream records by date."""

    def test_aggregate_by_date_empty_data(self) -> None:
        """Test aggregating empty data returns empty result."""
        result = aggregate_by_date([])
        assert result == {}

    def test_aggregate_by_date_single_record(
        self, sample_tautulli_record: dict[str, Any]
    ) -> None:
        """Test aggregating a single record."""
        record = create_stream_record(sample_tautulli_record)
        result = aggregate_by_date([record])

        assert len(result) == 1
        # Should have date as key
        date_key = datetime(2024, 1, 1, tzinfo=UTC).date()
        assert date_key in result
        assert result[date_key] == 1

    def test_aggregate_by_date_multiple_records_same_day(
        self, multiple_tautulli_records: list[dict[str, Any]]
    ) -> None:
        """Test aggregating multiple records on the same day."""
        records = [create_stream_record(r) for r in multiple_tautulli_records[:2]]
        result = aggregate_by_date(records)

        date_key = datetime(2024, 1, 1, tzinfo=UTC).date()
        assert result[date_key] == 2

    def test_aggregate_by_date_multiple_days(
        self, multiple_tautulli_records: list[dict[str, Any]]
    ) -> None:
        """Test aggregating records across multiple days."""
        records = [create_stream_record(r) for r in multiple_tautulli_records]
        result = aggregate_by_date(records)

        assert len(result) == 3  # 3 different days
        assert result[datetime(2024, 1, 1, tzinfo=UTC).date()] == 2
        assert result[datetime(2024, 1, 2, tzinfo=UTC).date()] == 2
        assert result[datetime(2024, 1, 3, tzinfo=UTC).date()] == 1

    def test_aggregate_by_date_preserves_chronological_order(
        self, multiple_tautulli_records: list[dict[str, Any]]
    ) -> None:
        """Test that aggregated dates are in chronological order."""
        records = [create_stream_record(r) for r in multiple_tautulli_records]
        result = aggregate_by_date(records)

        dates = list(result.keys())
        assert dates == sorted(dates)


class TestDataAggregationByDayOfWeek:
    """Tests for aggregating stream records by day of week."""

    def test_aggregate_by_day_of_week_empty_data(self) -> None:
        """Test aggregating empty data returns empty or zero result."""
        result = aggregate_by_day_of_week([])
        assert result == {} or all(v == 0 for v in result.values())

    def test_aggregate_by_day_of_week_single_record(
        self, sample_tautulli_record: dict[str, Any]
    ) -> None:
        """Test aggregating a single record by day of week."""
        record = create_stream_record(sample_tautulli_record)
        result = aggregate_by_day_of_week([record])

        # 2024-01-01 is a Monday (weekday 0)
        assert "Monday" in result
        assert result["Monday"] == 1

    def test_aggregate_by_day_of_week_multiple_records(
        self, multiple_tautulli_records: list[dict[str, Any]]
    ) -> None:
        """Test aggregating records across different days of week."""
        records = [create_stream_record(r) for r in multiple_tautulli_records]
        result = aggregate_by_day_of_week(records)

        # Based on test data:
        # 2024-01-01 (Monday): 2 records
        # 2024-01-02 (Tuesday): 2 records
        # 2024-01-03 (Wednesday): 1 record
        assert result["Monday"] == 2
        assert result["Tuesday"] == 2
        assert result["Wednesday"] == 1

    def test_aggregate_by_day_of_week_includes_all_days(
        self, sample_tautulli_record: dict[str, Any]
    ) -> None:
        """Test that result includes all days of week (even with zero counts)."""
        record = create_stream_record(sample_tautulli_record)
        result = aggregate_by_day_of_week([record])

        # Should have 7 days
        assert len(result) == 7


class TestDataAggregationByHour:
    """Tests for aggregating stream records by hour of day."""

    def test_aggregate_by_hour_empty_data(self) -> None:
        """Test aggregating empty data returns empty or zero result."""
        result = aggregate_by_hour([])
        assert result == {} or all(v == 0 for v in result.values())

    def test_aggregate_by_hour_single_record(
        self, sample_tautulli_record: dict[str, Any]
    ) -> None:
        """Test aggregating a single record by hour."""
        record = create_stream_record(sample_tautulli_record)
        result = aggregate_by_hour([record])

        # Sample record is at 00:00:00, so hour 0
        assert result[0] == 1

    def test_aggregate_by_hour_multiple_records(
        self, multiple_tautulli_records: list[dict[str, Any]]
    ) -> None:
        """Test aggregating multiple records by hour."""
        records = [create_stream_record(r) for r in multiple_tautulli_records]
        result = aggregate_by_hour(records)

        # Based on test data:
        # Hour 0: 3 records
        # Hour 1: 2 records
        assert result[0] == 3
        assert result[1] == 2

    def test_aggregate_by_hour_includes_all_hours(
        self, sample_tautulli_record: dict[str, Any]
    ) -> None:
        """Test that result includes all 24 hours (even with zero counts)."""
        record = create_stream_record(sample_tautulli_record)
        result = aggregate_by_hour([record])

        # Should have 24 hours (0-23)
        assert len(result) == 24
        assert all(hour in result for hour in range(24))


class TestDataAggregationByPlatform:
    """Tests for aggregating stream records by platform."""

    def test_aggregate_by_platform_empty_data(self) -> None:
        """Test aggregating empty data returns empty result."""
        result = aggregate_by_platform([])
        assert result == {}

    def test_aggregate_by_platform_single_record(
        self, sample_tautulli_record: dict[str, Any]
    ) -> None:
        """Test aggregating a single record by platform."""
        record = create_stream_record(sample_tautulli_record)
        result = aggregate_by_platform([record])

        assert result["Plex for Android"] == 1

    def test_aggregate_by_platform_multiple_records(
        self, multiple_tautulli_records: list[dict[str, Any]]
    ) -> None:
        """Test aggregating multiple records by platform."""
        records = [create_stream_record(r) for r in multiple_tautulli_records]
        result = aggregate_by_platform(records)

        assert result["Plex for Android"] == 3
        assert result["Plex for iOS"] == 1
        assert result["Plex Web"] == 1

    def test_aggregate_by_platform_sorted_by_count(
        self, multiple_tautulli_records: list[dict[str, Any]]
    ) -> None:
        """Test that platforms are sorted by count in descending order."""
        records = [create_stream_record(r) for r in multiple_tautulli_records]
        result = aggregate_by_platform(records)

        # Convert to list to check order
        platforms = list(result.items())
        counts = [count for _, count in platforms]

        # Counts should be in descending order
        assert counts == sorted(counts, reverse=True)


class TestDataAggregationByUser:
    """Tests for aggregating stream records by user."""

    def test_aggregate_by_user_empty_data(self) -> None:
        """Test aggregating empty data returns empty result."""
        result = aggregate_by_user([])
        assert result == {}

    def test_aggregate_by_user_single_record(
        self, sample_tautulli_record: dict[str, Any]
    ) -> None:
        """Test aggregating a single record by user."""
        record = create_stream_record(sample_tautulli_record)
        result = aggregate_by_user([record])

        assert result["JohnDoe"] == 1

    def test_aggregate_by_user_multiple_records(
        self, multiple_tautulli_records: list[dict[str, Any]]
    ) -> None:
        """Test aggregating multiple records by user."""
        records = [create_stream_record(r) for r in multiple_tautulli_records]
        result = aggregate_by_user(records)

        assert result["Alice"] == 2
        assert result["Bob"] == 2
        assert result["Charlie"] == 1

    def test_aggregate_by_user_sorted_by_count(
        self, multiple_tautulli_records: list[dict[str, Any]]
    ) -> None:
        """Test that users are sorted by count in descending order."""
        records = [create_stream_record(r) for r in multiple_tautulli_records]
        result = aggregate_by_user(records)

        # Convert to list to check order
        users = list(result.items())
        counts = [count for _, count in users]

        # Counts should be in descending order
        assert counts == sorted(counts, reverse=True)


class TestDataAggregationByMonth:
    """Tests for aggregating stream records by month."""

    def test_aggregate_by_month_empty_data(self) -> None:
        """Test aggregating empty data returns empty result."""
        result = aggregate_by_month([])
        assert result == {}

    def test_aggregate_by_month_single_record(
        self, sample_tautulli_record: dict[str, Any]
    ) -> None:
        """Test aggregating a single record by month."""
        record = create_stream_record(sample_tautulli_record)
        result = aggregate_by_month([record])

        # Should have January 2024
        month_key = datetime(2024, 1, 1, tzinfo=UTC).date().replace(day=1)
        assert result[month_key] == 1

    def test_aggregate_by_month_multiple_records_same_month(
        self, multiple_tautulli_records: list[dict[str, Any]]
    ) -> None:
        """Test aggregating multiple records in the same month."""
        records = [create_stream_record(r) for r in multiple_tautulli_records]
        result = aggregate_by_month(records)

        # All test records are in January 2024
        month_key = datetime(2024, 1, 1, tzinfo=UTC).date().replace(day=1)
        assert result[month_key] == 5

    def test_aggregate_by_month_multiple_months(self) -> None:
        """Test aggregating records across multiple months."""
        records_data = [
            {
                "date": 1704067200,  # January 2024
                "media_type": "movie",
                "stream_type": "direct play",
                "transcode_decision": "direct play",
                "platform": "Plex",
                "player": "Plex Web",
                "user": "User1",
                "stream_video_resolution": "1080p",
                "stream_video_full_resolution": "1920x1080",
            },
            {
                "date": 1706745600,  # February 2024
                "media_type": "movie",
                "stream_type": "direct play",
                "transcode_decision": "direct play",
                "platform": "Plex",
                "player": "Plex Web",
                "user": "User1",
                "stream_video_resolution": "1080p",
                "stream_video_full_resolution": "1920x1080",
            },
            {
                "date": 1709251200,  # March 2024
                "media_type": "movie",
                "stream_type": "direct play",
                "transcode_decision": "direct play",
                "platform": "Plex",
                "player": "Plex Web",
                "user": "User1",
                "stream_video_resolution": "1080p",
                "stream_video_full_resolution": "1920x1080",
            },
        ]
        records = [create_stream_record(r) for r in records_data]
        result = aggregate_by_month(records)

        assert len(result) == 3
        jan_key = datetime(2024, 1, 1, tzinfo=UTC).date().replace(day=1)
        feb_key = datetime(2024, 2, 1, tzinfo=UTC).date().replace(day=1)
        mar_key = datetime(2024, 3, 1, tzinfo=UTC).date().replace(day=1)

        assert result[jan_key] == 1
        assert result[feb_key] == 1
        assert result[mar_key] == 1


class TestUsernameAnonymization:
    """Tests for username anonymization logic with consistent labels.

    Requirements 13.1, 13.2, 13.3, 13.4, 13.5
    """

    def test_anonymize_usernames_empty_data(self) -> None:
        """Test anonymizing empty data returns empty result."""
        result = anonymize_usernames([])
        assert result == []

    def test_anonymize_usernames_single_record(
        self, sample_tautulli_record: dict[str, Any]
    ) -> None:
        """Test anonymizing a single record."""
        record = create_stream_record(sample_tautulli_record)
        result = anonymize_usernames([record])

        assert len(result) == 1
        assert result[0].user == "User 1"

    def test_anonymize_usernames_consistent_labels(
        self, multiple_tautulli_records: list[dict[str, Any]]
    ) -> None:
        """Test that the same username always gets the same anonymized label."""
        records = [create_stream_record(r) for r in multiple_tautulli_records]
        result = anonymize_usernames(records)

        # Alice appears twice (indices 0 and 2)
        alice_labels = [r.user for i, r in enumerate(result) if i in (0, 2)]
        assert len(set(alice_labels)) == 1, "Alice should have consistent label"

        # Bob appears twice (indices 1 and 4)
        bob_labels = [r.user for i, r in enumerate(result) if i in (1, 4)]
        assert len(set(bob_labels)) == 1, "Bob should have consistent label"

    def test_anonymize_usernames_unique_labels(
        self, multiple_tautulli_records: list[dict[str, Any]]
    ) -> None:
        """Test that different usernames get different anonymized labels."""
        records = [create_stream_record(r) for r in multiple_tautulli_records]
        result = anonymize_usernames(records)

        # Get unique anonymized labels
        unique_labels = {r.user for r in result}

        # Should have 3 unique users (Alice, Bob, Charlie)
        assert len(unique_labels) == 3

    def test_anonymize_usernames_format(
        self, multiple_tautulli_records: list[dict[str, Any]]
    ) -> None:
        """Test that anonymized labels follow 'User N' format."""
        records = [create_stream_record(r) for r in multiple_tautulli_records]
        result = anonymize_usernames(records)

        for record in result:
            assert record.user.startswith("User ")
            # Extract number part
            num_part = record.user.split(" ")[1]
            assert num_part.isdigit()

    def test_anonymize_usernames_preserves_other_fields(
        self, sample_tautulli_record: dict[str, Any]
    ) -> None:
        """Test that anonymization only changes username, not other fields."""
        record = create_stream_record(sample_tautulli_record)
        result = anonymize_usernames([record])

        assert result[0].timestamp == record.timestamp
        assert result[0].media_type == record.media_type
        assert result[0].stream_type == record.stream_type
        assert result[0].platform == record.platform
        assert result[0].source_resolution == record.source_resolution
        assert result[0].stream_resolution == record.stream_resolution

    def test_anonymize_usernames_ordering(
        self, multiple_tautulli_records: list[dict[str, Any]]
    ) -> None:
        """Test that user labels are assigned based on first appearance order."""
        records = [create_stream_record(r) for r in multiple_tautulli_records]
        result = anonymize_usernames(records)

        # First record (Alice) should be "User 1"
        assert result[0].user == "User 1"
        # Second record (Bob) should be "User 2"
        assert result[1].user == "User 2"
        # Fourth record (Charlie) should be "User 3"
        assert result[3].user == "User 3"

    @pytest.mark.parametrize(
        "username",
        ["Alice", "alice", "ALICE", "  Alice  "],
    )
    def test_anonymize_usernames_case_sensitivity(
        self, sample_tautulli_record: dict[str, Any], username: str
    ) -> None:
        """Test that username matching is case-sensitive (or case-insensitive as designed)."""
        sample_tautulli_record["user"] = username
        record = create_stream_record(sample_tautulli_record)
        result = anonymize_usernames([record])

        # Should all get the same label if case-insensitive,
        # or different labels if case-sensitive
        assert result[0].user.startswith("User ")


class TestEdgeCases:
    """Tests for edge cases in data transformation.

    Requirements 13.1, 13.2, 13.3, 13.4, 13.5
    """

    def test_empty_data_list(self) -> None:
        """Test handling empty data list across all aggregation functions."""
        assert aggregate_by_date([]) == {}
        assert aggregate_by_platform([]) == {}
        assert aggregate_by_user([]) == {}
        assert aggregate_by_month([]) == {}
        assert anonymize_usernames([]) == []

        # Day of week and hour should either return empty dict or dict with zeros
        dow_result = aggregate_by_day_of_week([])
        assert dow_result == {} or all(v == 0 for v in dow_result.values())

        hour_result = aggregate_by_hour([])
        assert hour_result == {} or all(v == 0 for v in hour_result.values())

    def test_single_record_handling(
        self, sample_tautulli_record: dict[str, Any]
    ) -> None:
        """Test that all functions handle single record correctly."""
        record = create_stream_record(sample_tautulli_record)

        # All aggregation functions should work with single record
        assert len(aggregate_by_date([record])) == 1
        assert len(aggregate_by_platform([record])) == 1
        assert len(aggregate_by_user([record])) == 1
        assert len(aggregate_by_month([record])) == 1
        assert len(anonymize_usernames([record])) == 1

    def test_duplicate_timestamps(self) -> None:
        """Test handling records with exact same timestamp."""
        records_data = [
            {
                "date": 1704067200,  # Same timestamp
                "media_type": "movie",
                "stream_type": "direct play",
                "transcode_decision": "direct play",
                "platform": "Platform1",
                "player": "Player1",
                "user": "User1",
                "stream_video_resolution": "1080p",
                "stream_video_full_resolution": "1920x1080",
            },
            {
                "date": 1704067200,  # Same timestamp
                "media_type": "episode",
                "stream_type": "transcode",
                "transcode_decision": "transcode",
                "platform": "Platform2",
                "player": "Player2",
                "user": "User2",
                "stream_video_resolution": "720p",
                "stream_video_full_resolution": "1280x720",
            },
        ]
        records = [create_stream_record(r) for r in records_data]

        # Should count both records for the same date
        date_result = aggregate_by_date(records)
        assert date_result[datetime(2024, 1, 1, tzinfo=UTC).date()] == 2

        # Should count both records for the same hour
        hour_result = aggregate_by_hour(records)
        assert hour_result[0] == 2

    def test_special_characters_in_usernames(self) -> None:
        """Test handling usernames with special characters."""
        records_data = [
            {
                "date": 1704067200,
                "media_type": "movie",
                "stream_type": "direct play",
                "transcode_decision": "direct play",
                "platform": "Plex",
                "player": "Plex Web",
                "user": "User-with-dash",
                "stream_video_resolution": "1080p",
                "stream_video_full_resolution": "1920x1080",
            },
            {
                "date": 1704070800,
                "media_type": "movie",
                "stream_type": "direct play",
                "transcode_decision": "direct play",
                "platform": "Plex",
                "player": "Plex Web",
                "user": "User_with_underscore",
                "stream_video_resolution": "1080p",
                "stream_video_full_resolution": "1920x1080",
            },
            {
                "date": 1704074400,
                "media_type": "movie",
                "stream_type": "direct play",
                "transcode_decision": "direct play",
                "platform": "Plex",
                "player": "Plex Web",
                "user": "User.with.dots",
                "stream_video_resolution": "1080p",
                "stream_video_full_resolution": "1920x1080",
            },
        ]
        records = [create_stream_record(r) for r in records_data]

        # Should handle all usernames
        user_result = aggregate_by_user(records)
        assert len(user_result) == 3

        # Anonymization should work
        anonymized = anonymize_usernames(records)
        assert len(anonymized) == 3
        assert all(r.user.startswith("User ") for r in anonymized)

    def test_empty_username(self) -> None:
        """Test handling record with empty username."""
        record_data = {
            "date": 1704067200,
            "media_type": "movie",
            "stream_type": "direct play",
            "transcode_decision": "direct play",
            "platform": "Plex",
            "player": "Plex Web",
            "user": "",
            "stream_video_resolution": "1080p",
            "stream_video_full_resolution": "1920x1080",
        }
        record = create_stream_record(record_data)

        # Should handle empty username
        user_result = aggregate_by_user([record])
        assert "" in user_result or "Unknown" in user_result

        # Anonymization should work (empty user gets a label)
        anonymized = anonymize_usernames([record])
        assert len(anonymized) == 1
        assert anonymized[0].user.startswith("User ")

    def test_very_large_dataset(self) -> None:
        """Test handling a large number of records efficiently."""
        # Create 1000 records
        records_data = [
            {
                "date": 1704067200 + (i * 3600),  # Increment by 1 hour
                "media_type": "movie" if i % 2 == 0 else "episode",
                "stream_type": "direct play",
                "transcode_decision": "direct play" if i % 3 == 0 else "transcode",
                "platform": f"Platform{i % 10}",
                "player": f"Player{i % 10}",
                "user": f"User{i % 50}",
                "stream_video_resolution": "1080p",
                "stream_video_full_resolution": "1920x1080",
            }
            for i in range(1000)
        ]
        records = [create_stream_record(r) for r in records_data]

        # Should handle large dataset
        assert len(records) == 1000

        # Aggregations should work
        platform_result = aggregate_by_platform(records)
        assert len(platform_result) == 10  # 10 unique platforms

        user_result = aggregate_by_user(records)
        assert len(user_result) == 50  # 50 unique users

        # Anonymization should work
        anonymized = anonymize_usernames(records)
        assert len(anonymized) == 1000
        unique_labels = {r.user for r in anonymized}
        assert len(unique_labels) == 50  # 50 unique anonymized labels

    @pytest.mark.parametrize(
        "invalid_date",
        [
            -1,  # Negative timestamp
            0,  # Zero timestamp
            2147483647,  # Max int32 (2038 problem)
        ],
    )
    def test_edge_case_timestamps(
        self, sample_tautulli_record: dict[str, Any], invalid_date: int
    ) -> None:
        """Test handling edge case timestamp values."""
        sample_tautulli_record["date"] = invalid_date
        record = create_stream_record(sample_tautulli_record)

        # Should create record (may use epoch or max date as fallback)
        assert isinstance(record, StreamRecord)
        assert isinstance(record.timestamp, datetime)
