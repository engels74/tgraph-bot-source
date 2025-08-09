"""
Utility functions for graph modules in TGraph Bot.

This module contains utility functions used by the graph modules,
such as date formatting, folder management, username censoring,
and data processing utilities.
"""

import logging
import re
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, TypeVar
from typing_extensions import NotRequired

from ....utils.cli.paths import get_path_config

if TYPE_CHECKING:
    pass


# Type definitions for processed data structures
class ProcessedPlayRecord(TypedDict):
    """Structure for processed play history records."""

    date: str
    user: str
    platform: str
    media_type: str
    duration: int
    stopped: int
    paused_counter: int
    datetime: datetime
    # Stream type fields for new graph types (optional for backward compatibility)
    transcode_decision: NotRequired[str]  # direct play, copy, transcode
    video_resolution: NotRequired[str]  # source resolution (e.g., "1920x1080")
    stream_video_resolution: NotRequired[str]  # transcoded output resolution
    video_codec: NotRequired[str]  # video codec (h264, hevc, etc.)
    audio_codec: NotRequired[str]  # audio codec (aac, ac3, dts, etc.)
    container: NotRequired[str]  # file container format (mp4, mkv, etc.)


class UserAggregateRecord(TypedDict):
    """Structure for aggregated user data."""

    username: str
    play_count: int


class PlatformAggregateRecord(TypedDict):
    """Structure for aggregated platform data."""

    platform: str
    play_count: int


class MediaTypeAggregateRecord(TypedDict):
    """Structure for aggregated media type data."""

    media_type: str
    display_name: str
    play_count: int
    color: str


class StreamTypeAggregateRecord(TypedDict):
    """Structure for aggregated stream type data."""

    stream_type: str  # direct play, copy, transcode
    display_name: str
    play_count: int
    color: str


class ResolutionAggregateRecord(TypedDict):
    """Structure for aggregated resolution data."""

    resolution: str  # e.g., "1920x1080", "3840x2160"
    play_count: int


class ConcurrentStreamRecord(TypedDict):
    """Structure for concurrent stream count data."""

    date: str
    peak_concurrent: int
    stream_type_breakdown: dict[str, int]  # concurrent count per stream type


class ResolutionStreamTypeAggregateRecord(TypedDict):
    """Structure for aggregated resolution and stream type data."""

    resolution: str  # e.g., "1920x1080", "3840x2160"
    stream_type: str  # direct play, copy, transcode
    display_name: str  # formatted display name for stream type
    play_count: int
    color: str  # color for this stream type


# Type aliases for common data structures
GraphData = dict[str, int] | dict[int, int] | list[dict[str, object]]
ProcessedRecords = list[ProcessedPlayRecord]
UserAggregates = list[UserAggregateRecord]
PlatformAggregates = list[PlatformAggregateRecord]
MediaTypeAggregates = list[MediaTypeAggregateRecord]
StreamTypeAggregates = list[StreamTypeAggregateRecord]
ResolutionAggregates = list[ResolutionAggregateRecord]
ConcurrentStreamAggregates = list[ConcurrentStreamRecord]
ResolutionStreamTypeAggregates = dict[str, list[ResolutionStreamTypeAggregateRecord]]
SeparatedGraphData = dict[str, dict[str, int]]
SeparatedUserAggregates = dict[str, UserAggregates]
SeparatedPlatformAggregates = dict[str, PlatformAggregates]
SeparatedStreamTypeAggregates = dict[str, StreamTypeAggregates]
SeparatedResolutionAggregates = dict[str, ResolutionAggregates]

logger = logging.getLogger(__name__)

T = TypeVar("T")


def format_date(date_obj: datetime, format_string: str = "%Y-%m-%d") -> str:
    """
    Format a datetime object to a string.

    Args:
        date_obj: The datetime object to format
        format_string: The format string to use

    Returns:
        Formatted date string
    """
    return date_obj.strftime(format_string)


def parse_date(date_string: str, format_string: str = "%Y-%m-%d") -> datetime:
    """
    Parse a date string to a datetime object.

    Args:
        date_string: The date string to parse
        format_string: The format string to use

    Returns:
        Parsed datetime object
    """
    return datetime.strptime(date_string, format_string)


def get_date_range(days: int) -> tuple[datetime, datetime]:
    """
    Get a date range from today going back the specified number of days.

    Args:
        days: Number of days to go back

    Returns:
        Tuple of (start_date, end_date)
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


def ensure_graph_directory(base_path: str = "graphs") -> Path:
    """
    Ensure the graph output directory exists.

    Args:
        base_path: Base path for graph storage

    Returns:
        Path object for the graph directory
    """
    graph_dir = Path(base_path)
    graph_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured graph directory exists: {graph_dir}")
    return graph_dir


def generate_dated_graph_path(
    base_date: datetime | None = None, user_email: str | None = None
) -> Path:
    """
    Generate a date-based path for graph storage following the new structure.

    Args:
        base_date: Date to use for directory structure (defaults to current date)
        user_email: User email for user-specific graphs (optional)

    Returns:
        Path object for the date-based graph directory

    Examples:
        - Server graphs: data/graphs/2025-01-21/
        - User graphs: data/graphs/2025-01-21/users/user_at_example.com/
    """
    if base_date is None:
        base_date = datetime.now()

    date_str = base_date.strftime("%Y-%m-%d")
    path_config = get_path_config()

    if user_email is not None:
        # Sanitize email for use in file path
        sanitized_email = user_email.replace("@", "_at_").replace(".", "_")
        graph_path = path_config.get_graph_path(date_str, "users", sanitized_email)
    else:
        graph_path = path_config.get_graph_path(date_str)

    # Ensure the directory exists
    graph_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured dated graph directory exists: {graph_path}")

    return graph_path


def get_current_graph_storage_path(user_email: str | None = None) -> Path:
    """
    Get the current graph storage path using the new date-based structure.

    This is the main function that should be used for all new graph storage.

    Args:
        user_email: User email for user-specific graphs (optional)

    Returns:
        Path object for today's graph storage directory
    """
    return generate_dated_graph_path(user_email=user_email)


def cleanup_old_files(directory: Path, keep_days: int = 7) -> int:
    """
    Clean up old files in a directory based on age.

    Args:
        directory: Directory to clean up
        keep_days: Number of days to keep files

    Returns:
        Number of files deleted
    """
    if not directory.exists():
        return 0

    cutoff_time = datetime.now() - timedelta(days=keep_days)
    deleted_count = 0

    for file_path in directory.iterdir():
        if file_path.is_file():
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old file: {file_path}")
                except OSError as e:
                    logger.warning(f"Failed to delete file {file_path}: {e}")

    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old files from {directory}")

    return deleted_count


def censor_username(username: str, censor_enabled: bool = True) -> str:
    """
    Censor a username for privacy if censoring is enabled.

    Args:
        username: The username to potentially censor
        censor_enabled: Whether censoring is enabled

    Returns:
        Censored or original username
    """
    if not censor_enabled:
        return username

    if len(username) <= 2:
        return "*" * len(username)

    # Show first and last character, censor the middle
    return username[0] + "*" * (len(username) - 2) + username[-1]


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing or replacing invalid characters.

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(" .")

    # Ensure filename is not empty
    if not sanitized:
        sanitized = "unnamed"

    return sanitized


def generate_graph_filename(
    graph_type: str, timestamp: datetime | None = None, user_id: str | None = None
) -> str:
    """
    Generate a standardized filename for a graph.

    Args:
        graph_type: Type of graph (e.g., "daily_play_count")
        timestamp: Timestamp to include in filename (defaults to now)
        user_id: User ID for personal graphs

    Returns:
        Generated filename
    """
    if timestamp is None:
        timestamp = datetime.now()

    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

    if user_id:
        filename = f"{graph_type}_user_{user_id}_{timestamp_str}.png"
    else:
        filename = f"{graph_type}_{timestamp_str}.png"

    return sanitize_filename(filename)


def format_duration(seconds: int) -> str:
    """
    Format a duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds == 0:
            return f"{minutes}m"
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes == 0:
            return f"{hours}h"
        return f"{hours}h {remaining_minutes}m"


def validate_color(color: str) -> bool:
    """
    Validate if a string is a valid color format.

    Args:
        color: Color string to validate

    Returns:
        True if valid color format, False otherwise
    """
    # Check for hex color format
    hex_pattern = r"^#[0-9A-Fa-f]{6}$"
    if re.match(hex_pattern, color):
        return True

    # Check for named colors (basic validation)
    named_colors = {
        "red",
        "green",
        "blue",
        "yellow",
        "orange",
        "purple",
        "pink",
        "brown",
        "black",
        "white",
        "gray",
        "grey",
        "cyan",
        "magenta",
    }
    if color.lower() in named_colors:
        return True

    return False


# Data Processing Utilities for Graph Generation


def validate_graph_data(
    data: Mapping[str, object], required_keys: list[str]
) -> tuple[bool, str]:
    """
    Validate that graph data contains all required keys.

    Args:
        data: The data dictionary to validate
        required_keys: List of keys that must be present

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Data must be a dictionary"

    for key in required_keys:
        if key not in data:
            return False, f"Missing required key: {key}"

    return True, ""


def safe_get_nested_value(
    data: Mapping[str, object], keys: list[str], default: object = None
) -> object:
    """
    Safely get a nested value from a dictionary using a list of keys.

    Args:
        data: Dictionary to search in
        keys: List of keys to traverse (e.g., ['response', 'data', 'items'])
        default: Default value to return if key path doesn't exist

    Returns:
        The value at the key path, or default if not found
    """
    current: Mapping[str, object] | object = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false  
def process_play_history_data(raw_data: Mapping[str, object]) -> ProcessedRecords:
    """
    Process raw play history data from Tautulli API into a standardized format.

    Args:
        raw_data: Raw data from Tautulli API

    Returns:
        List of processed play history records

    Raises:
        ValueError: If data format is invalid
    """
    # Extract the actual data from the API response
    history_data = safe_get_nested_value(raw_data, ["data"], [])

    if not isinstance(history_data, list):
        raise ValueError("Play history data must be a list")

    processed_records: ProcessedRecords = []

    for record in history_data:
        if not isinstance(record, dict):
            logger.warning("Skipping invalid record: not a dictionary")
            continue

        try:
            # Extract and validate required fields with proper type conversion
            date_value = safe_get_nested_value(record, ["date"], "")
            user_value = safe_get_nested_value(record, ["user"], "")
            platform_value = safe_get_nested_value(record, ["platform"], "")
            media_type_value = safe_get_nested_value(record, ["media_type"], "")
            duration_value = safe_get_nested_value(record, ["duration"], 0)
            stopped_value = safe_get_nested_value(record, ["stopped"], 0)
            paused_counter_value = safe_get_nested_value(record, ["paused_counter"], 0)
            # Extract stream type fields (for new stream type graphs)
            transcode_decision_value = safe_get_nested_value(
                record, ["transcode_decision"], "unknown"
            )
            video_resolution_value = safe_get_nested_value(
                record, ["video_resolution"], "unknown"
            )
            stream_video_resolution_value = safe_get_nested_value(
                record, ["stream_video_resolution"], "unknown"
            )
            video_codec_value = safe_get_nested_value(
                record, ["video_codec"], "unknown"
            )
            audio_codec_value = safe_get_nested_value(
                record, ["audio_codec"], "unknown"
            )
            container_value = safe_get_nested_value(record, ["container"], "unknown")

            # Convert timestamps to datetime objects if they're valid
            if date_value:
                try:
                    # Safely convert to int, handling various input types
                    if isinstance(date_value, (int, float)):
                        timestamp = int(date_value)
                    elif isinstance(date_value, str):
                        timestamp = int(date_value)
                    else:
                        logger.warning(f"Invalid timestamp type: {type(date_value)}")
                        continue

                    datetime_obj = datetime.fromtimestamp(timestamp)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid timestamp: {date_value}, error: {e}")
                    continue
            else:
                logger.warning("Missing date in record")
                continue

            # Construct a properly typed ProcessedPlayRecord
            processed_record: ProcessedPlayRecord = {
                "date": str(date_value),
                "user": str(user_value),
                "platform": str(platform_value),
                "media_type": str(media_type_value),
                "duration": int(duration_value)
                if isinstance(duration_value, (int, float))
                else 0,
                "stopped": int(stopped_value)
                if isinstance(stopped_value, (int, float))
                else 0,
                "paused_counter": int(paused_counter_value)
                if isinstance(paused_counter_value, (int, float))
                else 0,
                "datetime": datetime_obj,
                # Stream type fields for new graph functionality
                "transcode_decision": str(transcode_decision_value),
                "video_resolution": str(video_resolution_value),
                "stream_video_resolution": str(stream_video_resolution_value),
                "video_codec": str(video_codec_value),
                "audio_codec": str(audio_codec_value),
                "container": str(container_value),
            }

            # Add to processed records
            processed_records.append(processed_record)

        except Exception as e:
            logger.warning(f"Error processing record: {e}")
            continue

    logger.info(
        f"Processed {len(processed_records)} valid records from {len(history_data)} total"    )
    return processed_records


def _extract_resolution_with_fallback(
    record: dict[str, object],
    resolution_field: str,
    width_field: str,
    height_field: str,
) -> str:
    """
    Extract resolution from a record with fallback to width/height combination.

    Args:
        record: The play history record dictionary
        resolution_field: Primary resolution field name (e.g., "video_resolution")
        width_field: Fallback width field name (e.g., "width")
        height_field: Fallback height field name (e.g., "height")

    Returns:
        Resolution string (e.g., "1920x1080") or "unknown" if not available
    """
    # Try primary resolution field first
    resolution_value = safe_get_nested_value(record, [resolution_field], "unknown")
    if resolution_value and str(resolution_value) != "unknown":
        return str(resolution_value)

    # Fallback to width/height combination
    width_value = safe_get_nested_value(record, [width_field], None)
    height_value = safe_get_nested_value(record, [height_field], None)

    # Validate width and height values
    try:
        if width_value is not None and height_value is not None:
            width = (
                int(width_value) if isinstance(width_value, (int, float, str)) else None
            )
            height = (
                int(height_value)
                if isinstance(height_value, (int, float, str))
                else None
            )

            # Check for valid dimensions (must be positive integers)
            if width and height and width > 0 and height > 0:
                return f"{width}x{height}"
    except (ValueError, TypeError):
        # Invalid width/height values, fallback to unknown
        pass

    return "unknown"


# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
def process_play_history_data_enhanced(
    raw_data: Mapping[str, object],
) -> ProcessedRecords:
    """
    Enhanced version of process_play_history_data with resolution field fallback logic.

    This function provides fallback support for resolution fields by attempting to
    combine width/height fields when the primary resolution fields are not available.

    Args:
        raw_data: Raw data from Tautulli API

    Returns:
        List of processed play history records with enhanced resolution handling

    Raises:
        ValueError: If data format is invalid
    """
    # Extract the actual data from the API response
    history_data = safe_get_nested_value(raw_data, ["data"], [])
    
    if not isinstance(history_data, list):
        raise ValueError("Play history data must be a list")

    processed_records: ProcessedRecords = []

    # Debug: Log the fields available in the first record to understand the API structure
    if history_data and len(history_data) > 0:
        first_record = history_data[0]
        if isinstance(first_record, dict):
            available_fields = list(first_record.keys())
            logger.debug(
                f"Available fields in Tautulli API response: {available_fields}"
            )

            # Log resolution-related fields specifically
            resolution_fields = [
                f
                for f in available_fields
                if "resolution" in f.lower()
                or "width" in f.lower()
                or "height" in f.lower()
            ]
            logger.info(f"Resolution-related fields found: {resolution_fields}")

            # Log a sample of the first few field values for debugging
            sample_fields = [
                "video_resolution",
                "stream_video_resolution",
                "width",
                "height",
                "stream_video_width",
                "stream_video_height",
                "transcode_width",
                "transcode_height",
            ]
            sample_values = {}
            for field in sample_fields:
                if field in first_record:
                    sample_values[field] = first_record[field]
            logger.info(f"Sample resolution field values: {sample_values}")

    for record in history_data:
        if not isinstance(record, dict):
            logger.warning("Skipping invalid record: not a dictionary")
            continue

        try:
            # Extract and validate required fields with proper type conversion
            date_value = safe_get_nested_value(record, ["date"], "")
            user_value = safe_get_nested_value(record, ["user"], "")
            platform_value = safe_get_nested_value(record, ["platform"], "")
            media_type_value = safe_get_nested_value(record, ["media_type"], "")
            duration_value = safe_get_nested_value(record, ["duration"], 0)
            stopped_value = safe_get_nested_value(record, ["stopped"], 0)
            paused_counter_value = safe_get_nested_value(record, ["paused_counter"], 0)
            # Extract stream type fields
            transcode_decision_value = safe_get_nested_value(
                record, ["transcode_decision"], "unknown"
            )
            video_codec_value = safe_get_nested_value(
                record, ["video_codec"], "unknown"
            )
            audio_codec_value = safe_get_nested_value(
                record, ["audio_codec"], "unknown"
            )
            container_value = safe_get_nested_value(record, ["container"], "unknown")

            # Enhanced resolution extraction with fallback logic
            video_resolution_value = _extract_resolution_with_fallback(
                record, "video_resolution", "width", "height"
            )
            stream_video_resolution_value = _extract_resolution_with_fallback(
                record,
                "stream_video_resolution",
                "stream_video_width",
                "stream_video_height",
            )

            # Convert timestamps to datetime objects if they're valid
            if date_value:
                try:
                    # Safely convert to int, handling various input types
                    if isinstance(date_value, (int, float)):
                        timestamp = int(date_value)
                    elif isinstance(date_value, str):
                        timestamp = int(date_value)
                    else:
                        logger.warning(f"Invalid timestamp type: {type(date_value)}")
                        continue

                    datetime_obj = datetime.fromtimestamp(timestamp)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid timestamp: {date_value}, error: {e}")
                    continue
            else:
                logger.warning("Missing date in record")
                continue

            # Construct a properly typed ProcessedPlayRecord
            processed_record: ProcessedPlayRecord = {
                "date": str(date_value),
                "user": str(user_value),
                "platform": str(platform_value),
                "media_type": str(media_type_value),
                "duration": int(duration_value)
                if isinstance(duration_value, (int, float))
                else 0,
                "stopped": int(stopped_value)
                if isinstance(stopped_value, (int, float))
                else 0,
                "paused_counter": int(paused_counter_value)
                if isinstance(paused_counter_value, (int, float))
                else 0,
                "datetime": datetime_obj,
                # Enhanced stream type fields with fallback resolution logic
                "transcode_decision": str(transcode_decision_value),
                "video_resolution": video_resolution_value,
                "stream_video_resolution": stream_video_resolution_value,
                "video_codec": str(video_codec_value),
                "audio_codec": str(audio_codec_value),
                "container": str(container_value),
            }

            # Add to processed records
            processed_records.append(processed_record)

        except Exception as e:
            logger.warning(f"Error processing record: {e}")
            continue

    logger.info(
        f"Enhanced processing completed: {len(processed_records)} valid records from {len(history_data)} total"    )
    return processed_records


def aggregate_by_date(
    records: ProcessedRecords,
    fill_missing_dates: bool = True,
    time_range_days: int = 30,
) -> dict[str, int]:
    """
    Aggregate play records by date.

    Args:
        records: List of processed play history records
        fill_missing_dates: Whether to fill in missing dates with zero counts
        time_range_days: Number of days to include when filling missing dates

    Returns:
        Dictionary mapping date strings to play counts
    """
    date_counts: dict[str, int] = defaultdict(int)

    for record in records:
        if "datetime" in record:
            date_str = record["datetime"].strftime("%Y-%m-%d")
            date_counts[date_str] += 1

    # Fill in missing dates with zero counts if requested
    if fill_missing_dates:
        from datetime import datetime, timedelta

        # Calculate the date range to fill
        end_date = datetime.now()
        start_date = end_date - timedelta(
            days=time_range_days - 1
        )  # -1 because we include today

        # Generate all dates in the range
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str not in date_counts:
                date_counts[date_str] = 0
            current_date += timedelta(days=1)

    return dict(date_counts)


def aggregate_by_day_of_week(records: ProcessedRecords) -> dict[str, int]:
    """
    Aggregate play records by day of week.

    Args:
        records: List of processed play history records

    Returns:
        Dictionary mapping day names to play counts
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
    day_counts: dict[str, int] = {day: 0 for day in day_names}

    for record in records:
        if "datetime" in record:
            day_name = day_names[record["datetime"].weekday()]
            day_counts[day_name] += 1

    return day_counts


def aggregate_by_hour_of_day(records: ProcessedRecords) -> dict[int, int]:
    """
    Aggregate play records by hour of day.

    Args:
        records: List of processed play history records

    Returns:
        Dictionary mapping hour (0-23) to play counts
    """
    hour_counts: dict[int, int] = {hour: 0 for hour in range(24)}

    for record in records:
        if "datetime" in record:
            hour = record["datetime"].hour
            hour_counts[hour] += 1

    return hour_counts


def aggregate_by_month(records: ProcessedRecords) -> dict[str, int]:
    """
    Aggregate play records by month.

    Args:
        records: List of processed play history records

    Returns:
        Dictionary mapping month strings (YYYY-MM) to play counts
    """
    month_counts: dict[str, int] = defaultdict(int)

    for record in records:
        if "datetime" in record:
            month_str = record["datetime"].strftime("%Y-%m")
            month_counts[month_str] += 1

    return dict(month_counts)


def aggregate_top_users(
    records: ProcessedRecords, limit: int = 10, censor: bool = True
) -> UserAggregates:
    """
    Aggregate play records to get top users by play count.

    Args:
        records: List of processed play history records
        limit: Maximum number of users to return
        censor: Whether to censor usernames

    Returns:
        List of user dictionaries with username and play count
    """
    user_counts: dict[str, int] = defaultdict(int)

    for record in records:
        username = record.get("user", "Unknown")
        if username:
            user_counts[username] += 1

    # Sort by play count and take top N
    sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    result: UserAggregates = []
    for username, count in sorted_users:
        processed_username = censor_username(username) if censor else username
        result.append({"username": processed_username, "play_count": count})

    return result


def aggregate_top_platforms(
    records: ProcessedRecords, limit: int = 10
) -> PlatformAggregates:
    """
    Aggregate play records to get top platforms by play count.

    Args:
        records: List of processed play history records
        limit: Maximum number of platforms to return

    Returns:
        List of platform dictionaries with platform name and play count
    """
    platform_counts: dict[str, int] = defaultdict(int)

    for record in records:
        platform = record.get("platform", "Unknown")
        if platform:
            platform_counts[platform] += 1

    # Sort by play count and take top N
    sorted_platforms = sorted(
        platform_counts.items(), key=lambda x: x[1], reverse=True
    )[:limit]

    result: PlatformAggregates = []
    for platform, count in sorted_platforms:
        result.append({"platform": platform, "play_count": count})

    return result


def handle_empty_data(graph_type: str) -> GraphData:
    """
    Handle empty data cases by returning appropriate empty data structures.

    Args:
        graph_type: Type of graph to generate empty data for

    Returns:
        Empty data structure appropriate for the graph type
    """
    if graph_type == "daily":
        return {}
    elif graph_type == "users":
        return []
    elif graph_type == "platforms":
        return []
    elif graph_type == "hourly":
        return {hour: 0 for hour in range(24)}
    elif graph_type == "monthly":
        return {}
    else:
        return {}


def classify_media_type(media_type: str) -> str:
    """
    Classify a Tautulli media type into standardized categories.

    This function is maintained for backward compatibility.
    New code should use MediaTypeProcessor directly.

    Args:
        media_type: The raw media type from Tautulli API

    Returns:
        Standardized media type ('movie', 'tv', 'music', 'other')
    """
    # Use MediaTypeProcessor for consistent classification
    from ..data.media_type_processor import MediaTypeProcessor

    processor = MediaTypeProcessor()
    return processor.classify_media_type(media_type)


def get_media_type_display_info() -> dict[str, dict[str, str]]:
    """
    Get display information for media types including colors and labels.

    This function is maintained for backward compatibility.
    New code should use MediaTypeProcessor directly.

    Returns:
        Dictionary mapping media type to display info (name, color)
    """
    # Use MediaTypeProcessor for consistent display info
    from ..data.media_type_processor import MediaTypeProcessor

    processor = MediaTypeProcessor()
    return processor.get_all_display_info()


def aggregate_by_date_separated(
    records: ProcessedRecords,
    fill_missing_dates: bool = True,
    time_range_days: int = 30,
) -> SeparatedGraphData:
    """
    Aggregate play records by date with media type separation.

    Args:
        records: List of processed play history records
        fill_missing_dates: Whether to fill in missing dates with zero counts
        time_range_days: Number of days to include when filling missing dates

    Returns:
        Dictionary mapping media types to date-count dictionaries
    """
    separated_data: SeparatedGraphData = {}

    for record in records:
        if "datetime" not in record:
            continue

        date_str = record["datetime"].strftime("%Y-%m-%d")
        media_type = classify_media_type(record.get("media_type", ""))

        if media_type not in separated_data:
            separated_data[media_type] = {}

        if date_str not in separated_data[media_type]:
            separated_data[media_type][date_str] = 0

        separated_data[media_type][date_str] += 1

    # Fill in missing dates with zero counts if requested
    if fill_missing_dates:
        from datetime import datetime, timedelta

        # Calculate the date range to fill
        end_date = datetime.now()
        start_date = end_date - timedelta(
            days=time_range_days - 1
        )  # -1 because we include today

        # Generate all dates in the range and fill for each media type
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")

            # Ensure each media type has entries for all dates
            for media_type in separated_data:
                if date_str not in separated_data[media_type]:
                    separated_data[media_type][date_str] = 0

            current_date += timedelta(days=1)

    return separated_data


def aggregate_by_day_of_week_separated(records: ProcessedRecords) -> SeparatedGraphData:
    """
    Aggregate play records by day of week with media type separation.

    Args:
        records: List of processed play history records

    Returns:
        Dictionary mapping media types to day-count dictionaries
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
    separated_data: SeparatedGraphData = {}

    for record in records:
        if "datetime" not in record:
            continue

        day_name = day_names[record["datetime"].weekday()]
        media_type = classify_media_type(record.get("media_type", ""))

        if media_type not in separated_data:
            separated_data[media_type] = {day: 0 for day in day_names}

        separated_data[media_type][day_name] += 1

    return separated_data


def aggregate_by_hour_of_day_separated(
    records: ProcessedRecords,
) -> dict[str, dict[int, int]]:
    """
    Aggregate play records by hour of day with media type separation.

    Args:
        records: List of processed play history records

    Returns:
        Dictionary mapping media types to hour-count dictionaries
    """
    separated_data: dict[str, dict[int, int]] = {}

    for record in records:
        if "datetime" not in record:
            continue

        hour = record["datetime"].hour
        media_type = classify_media_type(record.get("media_type", ""))

        if media_type not in separated_data:
            separated_data[media_type] = {h: 0 for h in range(24)}

        separated_data[media_type][hour] += 1

    return separated_data


def aggregate_by_month_separated(records: ProcessedRecords) -> SeparatedGraphData:
    """
    Aggregate play records by month with media type separation.

    Args:
        records: List of processed play history records

    Returns:
        Dictionary mapping media types to month-count dictionaries
    """
    separated_data: SeparatedGraphData = {}

    for record in records:
        if "datetime" not in record:
            continue

        month_str = record["datetime"].strftime("%Y-%m")
        media_type = classify_media_type(record.get("media_type", ""))

        if media_type not in separated_data:
            separated_data[media_type] = {}

        if month_str not in separated_data[media_type]:
            separated_data[media_type][month_str] = 0

        separated_data[media_type][month_str] += 1

    return separated_data


def aggregate_top_users_separated(
    records: ProcessedRecords, limit: int = 10, censor: bool = True
) -> SeparatedUserAggregates:
    """
    Aggregate play records to get top users by play count with media type separation.

    Args:
        records: List of processed play history records
        limit: Maximum number of users to return per media type
        censor: Whether to censor usernames

    Returns:
        Dictionary mapping media types to lists of user dictionaries with username and play count
    """
    # Group records by media type first
    media_type_records: dict[str, ProcessedRecords] = defaultdict(list)

    for record in records:
        media_type = classify_media_type(record.get("media_type", ""))
        media_type_records[media_type].append(record)

    # Aggregate users for each media type
    separated_data: SeparatedUserAggregates = {}

    for media_type, type_records in media_type_records.items():
        # Use existing aggregate_top_users function for consistency
        user_aggregates = aggregate_top_users(type_records, limit=limit, censor=censor)
        separated_data[media_type] = user_aggregates

    return separated_data


def aggregate_top_platforms_separated(
    records: ProcessedRecords, limit: int = 10
) -> SeparatedPlatformAggregates:
    """
    Aggregate play records to get top platforms by play count with media type separation.

    Args:
        records: List of processed play history records
        limit: Maximum number of platforms to return per media type

    Returns:
        Dictionary mapping media types to lists of platform dictionaries with platform and play count
    """
    # Group records by media type first
    media_type_records: dict[str, ProcessedRecords] = defaultdict(list)

    for record in records:
        media_type = classify_media_type(record.get("media_type", ""))
        media_type_records[media_type].append(record)

    # Aggregate platforms for each media type
    separated_data: SeparatedPlatformAggregates = {}

    for media_type, type_records in media_type_records.items():
        # Use existing aggregate_top_platforms function for consistency
        platform_aggregates = aggregate_top_platforms(type_records, limit=limit)
        separated_data[media_type] = platform_aggregates

    return separated_data


def create_seaborn_style_context(enable_grid: bool = True) -> dict[str, object]:
    """
    Create a Seaborn style context for modern, professional graphs.

    Args:
        enable_grid: Whether to enable grid lines

    Returns:
        Dictionary of style parameters for Seaborn
    """
    return {
        "axes.grid": enable_grid,
        "axes.grid.axis": "y",
        "grid.linewidth": 0.5,
        "grid.alpha": 0.7,
        "axes.edgecolor": "black",
        "axes.linewidth": 1.2,
        "xtick.bottom": True,
        "xtick.top": False,
        "ytick.left": True,
        "ytick.right": False,
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 11,
        "axes.titlesize": 16,
        "axes.labelsize": 12,
        "legend.fontsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
    }


def apply_modern_seaborn_styling() -> None:
    """
    Apply modern Seaborn styling for professional-looking graphs.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns

    # Set the modern style
    sns.set_style(
        "whitegrid",
        {
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.linewidth": 0.5,
            "grid.alpha": 0.7,
            "axes.edgecolor": "#333333",
            "axes.linewidth": 1.2,
        },
    )

    # Set modern color palette
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    sns.set_palette(colors)

    # Configure matplotlib parameters for better appearance
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.titlesize": 16,
            "axes.titleweight": "bold",
            "axes.labelsize": 12,
            "legend.fontsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "figure.titlesize": 18,
            "legend.frameon": True,
            "legend.fancybox": True,
            "legend.shadow": True,
            "legend.framealpha": 0.9,
        }
    )


# Stream Type Aggregation Functions
# ==================================


def aggregate_by_stream_type(
    records: ProcessedRecords, use_separated_visualization: bool = False
) -> StreamTypeAggregates | SeparatedStreamTypeAggregates:
    """
    Aggregate play records by stream type (transcode decision).

    Args:
        records: List of processed play history records
        use_separated_visualization: Whether to separate by media type

    Returns:
        Aggregated stream type data, optionally separated by media type
    """
    if use_separated_visualization:
        separated_data: SeparatedStreamTypeAggregates = {"tv": [], "movie": []}

        # Count by media type and stream type
        stream_type_counts: dict[str, defaultdict[str, int]] = {"tv": defaultdict(int), "movie": defaultdict(int)}

        for record in records:
            media_type = record["media_type"]
            stream_type = record.get("transcode_decision", "unknown")

            if media_type in stream_type_counts:
                stream_type_counts[media_type][stream_type] += 1

        # Convert to aggregate records format
        for media_type, stream_counts in stream_type_counts.items():
            media_aggregates: StreamTypeAggregates = []
            for stream_type, count in stream_counts.items():
                display_name = get_stream_type_display_name(stream_type)
                color = get_stream_type_color(stream_type)

                media_aggregates.append(
                    StreamTypeAggregateRecord(
                        stream_type=stream_type,
                        display_name=display_name,
                        play_count=count,
                        color=color,
                    )
                )

            separated_data[media_type] = media_aggregates

        return separated_data
    else:
        # Simple aggregation without media type separation
        stream_type_counts_simple: defaultdict[str, int] = defaultdict(int)

        for record in records:
            stream_type: str = record.get("transcode_decision", "unknown")
            stream_type_counts_simple[stream_type] += 1

        aggregates: StreamTypeAggregates = []
        for stream_type, count in stream_type_counts_simple.items():
            display_name = get_stream_type_display_name(stream_type)
            color = get_stream_type_color(stream_type)

            aggregates.append(
                StreamTypeAggregateRecord(
                    stream_type=stream_type,
                    display_name=display_name,
                    play_count=count,
                    color=color,
                )
            )

        return aggregates


def aggregate_by_resolution(
    records: ProcessedRecords, resolution_field: str = "video_resolution"
) -> ResolutionAggregates:
    """
    Aggregate play records by resolution.

    Args:
        records: List of processed play history records
        resolution_field: Field to use for resolution ("video_resolution" for source,
                         "stream_video_resolution" for transcoded output)

    Returns:
        Aggregated resolution data sorted by play count
    """
    resolution_counts: defaultdict[str, int] = defaultdict(int)
    unknown_count = 0
    total_records = len(records)

    for record in records:
        resolution: str | None = record.get(resolution_field)
        if resolution and resolution != "unknown":
            resolution_counts[resolution] += 1
        else:
            unknown_count += 1

    # Log statistics to help with debugging
    logger.info(
        f"Resolution aggregation for field '{resolution_field}': "
        + f"{len(resolution_counts)} unique resolutions, "
        + f"{unknown_count} unknown values out of {total_records} total records"
    )

    # If we have no valid resolutions but have unknown values, include them
    # This helps identify when Tautulli API is not providing resolution data
    if not resolution_counts and unknown_count > 0:
        logger.warning(
            f"No valid {resolution_field} data found, all {unknown_count} records have unknown resolution. "
            + "This may indicate missing resolution data in Tautulli API response."
        )
        resolution_counts["unknown"] = unknown_count

    # Convert to aggregate records and sort by play count
    aggregates: ResolutionAggregates = []
    for resolution, count in resolution_counts.items():
        aggregates.append(
            ResolutionAggregateRecord(resolution=resolution, play_count=count)
        )

    # Sort by play count (descending)
    aggregates.sort(key=lambda x: x["play_count"], reverse=True)

    return aggregates


def aggregate_by_resolution_and_stream_type(
    records: ProcessedRecords, resolution_field: str = "video_resolution"
) -> ResolutionStreamTypeAggregates:
    """
    Aggregate play records by resolution with stream type breakdown.

    Args:
        records: List of processed play history records
        resolution_field: Field to use for resolution ("video_resolution" for source,
                         "stream_video_resolution" for transcoded output)

    Returns:
        Dictionary mapping resolution to list of stream type aggregates
    """
    # Count by resolution and stream type
    resolution_stream_counts: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
    unknown_count = 0
    total_records = len(records)

    for record in records:
        resolution: str | None = record.get(resolution_field)
        stream_type: str = record.get("transcode_decision", "unknown")

        if resolution and resolution != "unknown":
            resolution_stream_counts[resolution][stream_type] += 1
        else:
            unknown_count += 1

    # Log statistics to help with debugging
    logger.info(
        f"Resolution and stream type aggregation for field '{resolution_field}': "
        + f"{len(resolution_stream_counts)} unique resolutions, "
        + f"{unknown_count} unknown values out of {total_records} total records"
    )

    # If we have no valid resolutions but have unknown values, include them
    if not resolution_stream_counts and unknown_count > 0:
        logger.warning(
            f"No valid {resolution_field} data found, all {unknown_count} records have unknown resolution. "
            + "This may indicate missing resolution data in Tautulli API response."
        )
        # Add unknown resolution with stream type breakdown
        for record in records:
            if not record[resolution_field] or record[resolution_field] == "unknown":  # type: ignore[misc]
                stream_type = record.get("transcode_decision", "unknown")
                resolution_stream_counts["unknown"][stream_type] += 1

    # Convert to aggregate format
    result: ResolutionStreamTypeAggregates = {}
    for resolution, stream_counts in resolution_stream_counts.items():
        aggregates: list[ResolutionStreamTypeAggregateRecord] = []
        for stream_type, count in stream_counts.items():
            display_name = get_stream_type_display_name(stream_type)
            color = get_stream_type_color(stream_type)

            aggregates.append(
                ResolutionStreamTypeAggregateRecord(
                    resolution=resolution,
                    stream_type=stream_type,
                    display_name=display_name,
                    play_count=count,
                    color=color,
                )
            )

        # Sort by play count (descending)
        aggregates.sort(key=lambda x: x["play_count"], reverse=True)
        result[resolution] = aggregates

    # Sort resolutions by total play count (descending)
    resolution_totals = {
        resolution: sum(agg["play_count"] for agg in aggregates)
        for resolution, aggregates in result.items()
    }
    sorted_resolutions = sorted(
        resolution_totals.keys(), key=lambda x: resolution_totals[x], reverse=True
    )

    # Return sorted result
    return {resolution: result[resolution] for resolution in sorted_resolutions}


def aggregate_by_platform_and_stream_type(
    records: ProcessedRecords, limit: int = 10
) -> dict[str, StreamTypeAggregates]:
    """
    Aggregate play records by platform with stream type breakdown.

    Args:
        records: List of processed play history records
        limit: Maximum number of platforms to include

    Returns:
        Dictionary mapping platform names to stream type aggregates
    """
    # First count total plays per platform to determine top platforms
    platform_totals: dict[str, int] = defaultdict(int)
    for record in records:
        platform_totals[record["platform"]] += 1

    # Get top platforms
    top_platforms = sorted(platform_totals.items(), key=lambda x: x[1], reverse=True)[
        :limit
    ]
    top_platform_names = {platform for platform, _ in top_platforms}

    # Count stream types for each top platform
    platform_stream_counts: dict[str, dict[str, int]] = {}
    for platform in top_platform_names:
        platform_stream_counts[platform] = defaultdict(int)

    for record in records:
        platform = record["platform"]
        if platform in top_platform_names:
            stream_type = record.get("transcode_decision", "unknown")
            platform_stream_counts[platform][stream_type] += 1

    # Convert to aggregate format
    result: dict[str, StreamTypeAggregates] = {}
    for platform, stream_counts in platform_stream_counts.items():
        aggregates: StreamTypeAggregates = []
        for stream_type, count in stream_counts.items():
            display_name = get_stream_type_display_name(stream_type)
            color = get_stream_type_color(stream_type)

            aggregates.append(
                StreamTypeAggregateRecord(
                    stream_type=stream_type,
                    display_name=display_name,
                    play_count=count,
                    color=color,
                )
            )

        result[platform] = aggregates

    return result


def aggregate_by_user_and_stream_type(
    records: ProcessedRecords, limit: int = 10
) -> dict[str, StreamTypeAggregates]:
    """
    Aggregate play records by user with stream type breakdown.

    Args:
        records: List of processed play history records
        limit: Maximum number of users to include

    Returns:
        Dictionary mapping usernames to stream type aggregates
    """
    # First count total plays per user to determine top users
    user_totals: dict[str, int] = defaultdict(int)
    for record in records:
        user_totals[record["user"]] += 1

    # Get top users
    top_users = sorted(user_totals.items(), key=lambda x: x[1], reverse=True)[:limit]
    top_user_names = {user for user, _ in top_users}

    # Count stream types for each top user
    user_stream_counts: dict[str, dict[str, int]] = {}
    for user in top_user_names:
        user_stream_counts[user] = defaultdict(int)

    for record in records:
        user = record["user"]
        if user in top_user_names:
            stream_type = record.get("transcode_decision", "unknown")
            user_stream_counts[user][stream_type] += 1

    # Convert to aggregate format
    result: dict[str, StreamTypeAggregates] = {}
    for user, stream_counts in user_stream_counts.items():
        aggregates: StreamTypeAggregates = []
        for stream_type, count in stream_counts.items():
            display_name = get_stream_type_display_name(stream_type)
            color = get_stream_type_color(stream_type)

            aggregates.append(
                StreamTypeAggregateRecord(
                    stream_type=stream_type,
                    display_name=display_name,
                    play_count=count,
                    color=color,
                )
            )

        result[user] = aggregates

    return result


def calculate_concurrent_streams_by_date(
    records: ProcessedRecords, separate_by_stream_type: bool = True
) -> ConcurrentStreamAggregates:
    """
    Calculate peak concurrent streams per date.

    Args:
        records: List of processed play history records
        separate_by_stream_type: Whether to track concurrent streams by stream type

    Returns:
        List of concurrent stream records per date
    """
    from datetime import timedelta

    # Group records by date
    records_by_date: dict[str, list[ProcessedPlayRecord]] = defaultdict(list)
    for record in records:
        date_key = record["datetime"].strftime("%Y-%m-%d")
        records_by_date[date_key].append(record)

    concurrent_aggregates: ConcurrentStreamAggregates = []

    for date_str, day_records in records_by_date.items():
        # Create list of stream events (start and end times)
        stream_events: list[
            tuple[datetime, str, str]
        ] = []  # (time, event_type, stream_type)

        for record in day_records:
            start_time = record["datetime"]
            end_time = start_time + timedelta(seconds=record["duration"])
            stream_type = record.get("transcode_decision", "unknown")

            stream_events.append((start_time, "start", stream_type))
            stream_events.append((end_time, "end", stream_type))

        # Sort events by time
        stream_events.sort(key=lambda x: x[0])

        # Calculate peak concurrent streams
        current_concurrent = 0
        peak_concurrent = 0
        stream_type_concurrent: dict[str, int] = defaultdict(int)
        peak_stream_type_breakdown: dict[str, int] = defaultdict(int)

        for _, event_type, stream_type in stream_events:
            if event_type == "start":
                current_concurrent += 1
                if separate_by_stream_type:
                    stream_type_concurrent[stream_type] += 1
            else:
                current_concurrent -= 1
                if separate_by_stream_type:
                    stream_type_concurrent[stream_type] -= 1

            # Track peak
            if current_concurrent > peak_concurrent:
                peak_concurrent = current_concurrent
                if separate_by_stream_type:
                    peak_stream_type_breakdown = dict(stream_type_concurrent)

        concurrent_aggregates.append(
            ConcurrentStreamRecord(
                date=date_str,
                peak_concurrent=peak_concurrent,
                stream_type_breakdown=peak_stream_type_breakdown if separate_by_stream_type else {},
            )
        )

    # Sort by date
    concurrent_aggregates.sort(key=lambda x: x["date"])

    return concurrent_aggregates


# Stream Type Filtering Functions
# ===============================


def filter_records_by_stream_type(
    records: ProcessedRecords,
    stream_types: list[str] | str | None = None,
    exclude_unknown: bool = True,
) -> ProcessedRecords:
    """
    Filter processed records by stream type (transcode decision).

    Args:
        records: List of processed play history records
        stream_types: Stream type(s) to include. Can be:
            - None: Include all stream types (default)
            - str: Single stream type (e.g., "direct play")
            - list[str]: Multiple stream types (e.g., ["direct play", "copy"])
        exclude_unknown: Whether to exclude records with unknown stream types

    Returns:
        Filtered list of records matching the specified stream types

    Examples:
        # Filter for only direct play streams
        direct_play_records = filter_records_by_stream_type(records, "direct play")

        # Filter for direct play and direct stream
        efficient_streams = filter_records_by_stream_type(
            records, ["direct play", "copy"]
        )

        # Get all records including unknown
        all_records = filter_records_by_stream_type(records, exclude_unknown=False)
    """
    if not records:
        return []

    # Normalize stream_types to a list
    if stream_types is None:
        target_types = None  # Include all types
    elif isinstance(stream_types, str):
        target_types = [stream_types.lower()]
    else:
        target_types = [st.lower() for st in stream_types]

    filtered_records: ProcessedRecords = []

    for record in records:
        stream_type = record.get("transcode_decision", "unknown").lower()

        # Skip unknown types if requested
        if exclude_unknown and stream_type == "unknown":
            continue

        # Include all types if no specific types requested
        if target_types is None:
            filtered_records.append(record)
        # Include only if stream type matches
        elif stream_type in target_types:
            filtered_records.append(record)

    return filtered_records


def get_available_stream_types(records: ProcessedRecords) -> list[str]:
    """
    Get list of unique stream types present in the records.

    Args:
        records: List of processed play history records

    Returns:
        Sorted list of unique stream types found in the data
    """
    if not records:
        return []

    stream_types: set[str] = set()
    for record in records:
        stream_type = record.get("transcode_decision", "unknown")
        if stream_type:  # Skip empty/None values
            stream_types.add(stream_type)

    return sorted(list(stream_types))


def get_stream_type_statistics(
    records: ProcessedRecords,
) -> dict[str, dict[str, int | float]]:
    """
    Get statistics about stream type distribution in the records.

    Args:
        records: List of processed play history records

    Returns:
        Dictionary with stream type statistics including counts and percentages
    """
    if not records:
        return {}

    total_records = len(records)
    stream_type_counts: dict[str, int] = defaultdict(int)

    for record in records:
        stream_type = record.get("transcode_decision", "unknown")
        stream_type_counts[stream_type] += 1

    statistics: dict[str, dict[str, int | float]] = {}
    for stream_type, count in stream_type_counts.items():
        percentage = (count / total_records) * 100
        statistics[stream_type] = {"count": count, "percentage": round(percentage, 2)}

    return statistics


# Helper functions for stream type display and styling
# ===================================================


def get_stream_type_display_name(stream_type: str) -> str:
    """Get user-friendly display name for stream type."""
    display_names = {
        "direct play": "Direct Play",
        "copy": "Direct Stream",
        "transcode": "Transcode",
        "unknown": "Unknown",
    }
    return display_names.get(stream_type.lower(), stream_type.title())


def get_stream_type_color(stream_type: str) -> str:
    """Get color for stream type visualization."""
    colors = {
        "direct play": "#2ca02c",  # Green - most efficient
        "copy": "#ff7f0e",  # Orange - moderate
        "transcode": "#d62728",  # Red - most resource intensive
        "unknown": "#7f7f7f",  # Gray - unknown
    }
    return colors.get(stream_type.lower(), "#1f77b4")  # Default blue


def get_stream_type_display_info() -> dict[str, dict[str, str]]:
    """
    Get comprehensive display information for stream types.

    Returns:
        Dictionary mapping stream types to display info (name and color)
    """
    return {
        "direct play": {"display_name": "Direct Play", "color": "#2ca02c"},
        "copy": {"display_name": "Direct Stream", "color": "#ff7f0e"},
        "transcode": {"display_name": "Transcode", "color": "#d62728"},
        "unknown": {"display_name": "Unknown", "color": "#7f7f7f"},
    }
