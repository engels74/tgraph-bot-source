"""Data transformation and privacy utilities for TGraph Bot.

This module provides data models and transformation functions for:
- Converting Tautulli API responses to StreamRecord objects
- Aggregating stream data by various dimensions
- Anonymizing usernames for privacy

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import TypedDict

# Type alias for aggregation results
type AggregationResult[T] = dict[T, int]


class TautulliStreamRecord(TypedDict):
    """Tautulli API stream record structure.

    This TypedDict defines the structure of stream records returned
    from the Tautulli API.
    """

    date: int  # Unix timestamp
    media_type: str  # "movie" or "episode"
    stream_type: str  # "direct play", "transcode", or "copy"
    platform: str  # Client platform name
    user: str  # Username
    stream_video_resolution: str  # e.g., "1080p", "720p"
    stream_video_full_resolution: str  # e.g., "1920x1080"


@dataclass(slots=True, frozen=True)
class StreamRecord:
    """Immutable stream record with normalized data.

    This dataclass represents a single stream event with normalized
    and validated data. It is immutable (frozen) and uses slots for
    memory efficiency (40% savings).

    Attributes:
        timestamp: When the stream occurred (UTC)
        media_type: Normalized media type ("movie", "tv", "music")
        stream_type: Normalized stream type (lowercase)
        platform: Client platform name
        user: Username
        source_resolution: Original media resolution
        stream_resolution: Stream delivery resolution
    """

    timestamp: datetime
    media_type: str
    stream_type: str
    platform: str
    user: str
    source_resolution: str
    stream_resolution: str


@dataclass(slots=True)
class AggregatedData:
    """Aggregated data for graph generation.

    This dataclass holds aggregated stream data ready for visualization.
    Uses slots for memory efficiency.

    Attributes:
        dates: List of datetime values for time-series data
        counts: List of count values corresponding to dates/labels
        labels: List of string labels for categorical data
    """

    dates: list[datetime]
    counts: list[int]
    labels: list[str]


@dataclass(slots=True)
class GraphMetadata:
    """Metadata about a generated graph.

    This dataclass contains information about a graph that was generated.
    Uses slots for memory efficiency.

    Attributes:
        graph_type: Type of graph (e.g., "daily_play_count", "top_platforms")
        file_path: Path to the generated graph image file
        generated_at: When the graph was generated (UTC)
        data_range_days: Number of days of data included in the graph
    """

    graph_type: str
    file_path: str
    generated_at: datetime
    data_range_days: int


def create_stream_record(tautulli_record: Mapping[str, object]) -> StreamRecord:
    """Create a StreamRecord from a Tautulli API response.

    This function transforms raw Tautulli API data into a normalized,
    type-safe StreamRecord. It performs the following transformations:
    - Converts Unix timestamp to datetime (UTC)
    - Normalizes media types ("episode" -> "tv", "track" -> "music")
    - Normalizes stream types to lowercase
    - Extracts resolution information

    Args:
        tautulli_record: Raw Tautulli API response dictionary

    Returns:
        Immutable StreamRecord with normalized data

    Requirements:
        - 13.1: Transform Tautulli responses to typed records
        - 13.2: Normalize data for consistent processing
    """
    # Extract and validate timestamp
    timestamp_unix = int(tautulli_record["date"])  # pyright: ignore[reportArgumentType]
    timestamp = datetime.fromtimestamp(timestamp_unix, tz=timezone.utc)

    # Normalize media type
    raw_media_type = str(tautulli_record["media_type"])
    if raw_media_type == "episode":
        media_type = "tv"
    elif raw_media_type == "track":
        media_type = "music"
    else:
        media_type = raw_media_type

    # Normalize stream type to lowercase
    stream_type = str(tautulli_record["stream_type"]).lower()

    return StreamRecord(
        timestamp=timestamp,
        media_type=media_type,
        stream_type=stream_type,
        platform=str(tautulli_record["platform"]),
        user=str(tautulli_record["user"]),
        source_resolution=str(tautulli_record["stream_video_full_resolution"]),
        stream_resolution=str(tautulli_record["stream_video_resolution"]),
    )


def aggregate_by_date(
    records: Sequence[StreamRecord],
) -> AggregationResult[date]:
    """Aggregate stream records by date.

    Groups records by calendar date and counts occurrences.
    Results are sorted chronologically.

    Args:
        records: Sequence of stream records to aggregate

    Returns:
        Dictionary mapping dates to stream counts, sorted chronologically

    Requirements:
        - 13.2: Aggregate data by date
    """
    if not records:
        return {}

    aggregation: dict[date, int] = {}
    for record in records:
        record_date = record.timestamp.date()
        aggregation[record_date] = aggregation.get(record_date, 0) + 1

    # Return sorted by date
    return dict(sorted(aggregation.items()))


def aggregate_by_day_of_week(
    records: Sequence[StreamRecord],
) -> AggregationResult[str]:
    """Aggregate stream records by day of week.

    Groups records by day of week (Monday=0, Sunday=6) and counts occurrences.
    Always returns all 7 days, even if count is zero.

    Args:
        records: Sequence of stream records to aggregate

    Returns:
        Dictionary mapping day names to stream counts (7 days total)

    Requirements:
        - 13.2: Aggregate data by day of week
    """
    day_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    # Initialize all days to 0
    aggregation: dict[str, int] = {day: 0 for day in day_names}

    for record in records:
        day_index = record.timestamp.weekday()
        day_name = day_names[day_index]
        aggregation[day_name] += 1

    return aggregation


def aggregate_by_hour(
    records: Sequence[StreamRecord],
) -> AggregationResult[int]:
    """Aggregate stream records by hour of day.

    Groups records by hour (0-23) and counts occurrences.
    Always returns all 24 hours, even if count is zero.

    Args:
        records: Sequence of stream records to aggregate

    Returns:
        Dictionary mapping hours (0-23) to stream counts

    Requirements:
        - 13.2: Aggregate data by hour
    """
    # Initialize all hours to 0
    aggregation: dict[int, int] = {hour: 0 for hour in range(24)}

    for record in records:
        hour = record.timestamp.hour
        aggregation[hour] += 1

    return aggregation


def aggregate_by_platform(
    records: Sequence[StreamRecord],
) -> AggregationResult[str]:
    """Aggregate stream records by platform.

    Groups records by platform and counts occurrences.
    Results are sorted by count (descending).

    Args:
        records: Sequence of stream records to aggregate

    Returns:
        Dictionary mapping platforms to stream counts, sorted by count descending

    Requirements:
        - 13.2: Aggregate data by platform
    """
    if not records:
        return {}

    aggregation: dict[str, int] = {}
    for record in records:
        platform = record.platform
        aggregation[platform] = aggregation.get(platform, 0) + 1

    # Sort by count descending
    return dict(sorted(aggregation.items(), key=lambda x: x[1], reverse=True))


def aggregate_by_user(
    records: Sequence[StreamRecord],
) -> AggregationResult[str]:
    """Aggregate stream records by user.

    Groups records by username and counts occurrences.
    Results are sorted by count (descending).

    Args:
        records: Sequence of stream records to aggregate

    Returns:
        Dictionary mapping usernames to stream counts, sorted by count descending

    Requirements:
        - 13.2: Aggregate data by user
    """
    if not records:
        return {}

    aggregation: dict[str, int] = {}
    for record in records:
        user = record.user
        aggregation[user] = aggregation.get(user, 0) + 1

    # Sort by count descending
    return dict(sorted(aggregation.items(), key=lambda x: x[1], reverse=True))


def aggregate_by_month(
    records: Sequence[StreamRecord],
) -> AggregationResult[date]:
    """Aggregate stream records by month.

    Groups records by month (first day of month) and counts occurrences.
    Results are sorted chronologically.

    Args:
        records: Sequence of stream records to aggregate

    Returns:
        Dictionary mapping month start dates to stream counts, sorted chronologically

    Requirements:
        - 13.2: Aggregate data by month
    """
    if not records:
        return {}

    aggregation: dict[date, int] = {}
    for record in records:
        # Use first day of month as key
        month_key = record.timestamp.date().replace(day=1)
        aggregation[month_key] = aggregation.get(month_key, 0) + 1

    # Return sorted by date
    return dict(sorted(aggregation.items()))


def anonymize_usernames(
    records: Sequence[StreamRecord],
) -> list[StreamRecord]:
    """Anonymize usernames with consistent labels.

    Replaces usernames with anonymized labels ("User 1", "User 2", etc.)
    while maintaining consistency - the same username always gets the
    same label. Labels are assigned based on order of first appearance.

    Since StreamRecord is frozen, this creates new StreamRecord instances
    with anonymized usernames.

    Args:
        records: Sequence of stream records to anonymize

    Returns:
        List of StreamRecord instances with anonymized usernames

    Requirements:
        - 13.1: Apply username anonymization
        - 13.3: Maintain consistent anonymized labels
        - 13.4: Map same username to same label
        - 13.5: Preserve all other record fields
    """
    if not records:
        return []

    # Build username mapping based on first appearance order
    username_mapping: dict[str, str] = {}
    user_counter = 1

    for record in records:
        if record.user not in username_mapping:
            username_mapping[record.user] = f"User {user_counter}"
            user_counter += 1

    # Create new records with anonymized usernames
    anonymized_records: list[StreamRecord] = []
    for record in records:
        anonymized_record = StreamRecord(
            timestamp=record.timestamp,
            media_type=record.media_type,
            stream_type=record.stream_type,
            platform=record.platform,
            user=username_mapping[record.user],
            source_resolution=record.source_resolution,
            stream_resolution=record.stream_resolution,
        )
        anonymized_records.append(anonymized_record)

    return anonymized_records
