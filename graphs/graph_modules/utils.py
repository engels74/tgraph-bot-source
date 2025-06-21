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
from typing import TypeVar, TYPE_CHECKING, TypedDict

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


# Type aliases for common data structures
GraphData = dict[str, int] | dict[int, int] | list[dict[str, object]]
ProcessedRecords = list[ProcessedPlayRecord]
UserAggregates = list[UserAggregateRecord]
PlatformAggregates = list[PlatformAggregateRecord]
MediaTypeAggregates = list[MediaTypeAggregateRecord]
SeparatedGraphData = dict[str, dict[str, int]]

logger = logging.getLogger(__name__)

T = TypeVar('T')


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
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(' .')
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = "unnamed"
        
    return sanitized


def generate_graph_filename(
    graph_type: str,
    timestamp: datetime | None = None,
    user_id: str | None = None
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
    hex_pattern = r'^#[0-9A-Fa-f]{6}$'
    if re.match(hex_pattern, color):
        return True
        
    # Check for named colors (basic validation)
    named_colors = {
        'red', 'green', 'blue', 'yellow', 'orange', 'purple', 'pink',
        'brown', 'black', 'white', 'gray', 'grey', 'cyan', 'magenta'
    }
    if color.lower() in named_colors:
        return True
        
    return False


# Data Processing Utilities for Graph Generation

def validate_graph_data(data: Mapping[str, object], required_keys: list[str]) -> tuple[bool, str]:
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


def safe_get_nested_value(data: Mapping[str, object], keys: list[str], default: object = None) -> object:
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
            current = current[key]  # pyright: ignore[reportUnknownVariableType]
        else:
            return default
    return current  # pyright: ignore[reportUnknownVariableType]


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
    history_data = safe_get_nested_value(raw_data, ['data'], [])

    if not isinstance(history_data, list):
        raise ValueError("Play history data must be a list")

    processed_records: ProcessedRecords = []

    for record in history_data:  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(record, dict):
            logger.warning("Skipping invalid record: not a dictionary")
            continue

        try:
            # Extract and validate required fields with proper type conversion
            date_value = safe_get_nested_value(record, ['date'], '')  # pyright: ignore[reportUnknownArgumentType]
            user_value = safe_get_nested_value(record, ['user'], '')  # pyright: ignore[reportUnknownArgumentType]
            platform_value = safe_get_nested_value(record, ['platform'], '')  # pyright: ignore[reportUnknownArgumentType]
            media_type_value = safe_get_nested_value(record, ['media_type'], '')  # pyright: ignore[reportUnknownArgumentType]
            duration_value = safe_get_nested_value(record, ['duration'], 0)  # pyright: ignore[reportUnknownArgumentType]
            stopped_value = safe_get_nested_value(record, ['stopped'], 0)  # pyright: ignore[reportUnknownArgumentType]
            paused_counter_value = safe_get_nested_value(record, ['paused_counter'], 0)  # pyright: ignore[reportUnknownArgumentType]

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
                'date': str(date_value),
                'user': str(user_value),
                'platform': str(platform_value),
                'media_type': str(media_type_value),
                'duration': int(duration_value) if isinstance(duration_value, (int, float)) else 0,
                'stopped': int(stopped_value) if isinstance(stopped_value, (int, float)) else 0,
                'paused_counter': int(paused_counter_value) if isinstance(paused_counter_value, (int, float)) else 0,
                'datetime': datetime_obj,
            }

            # Add to processed records
            processed_records.append(processed_record)

        except Exception as e:
            logger.warning(f"Error processing record: {e}")
            continue

    logger.info(f"Processed {len(processed_records)} valid records from {len(history_data)} total")  # pyright: ignore[reportUnknownArgumentType]
    return processed_records


def aggregate_by_date(records: ProcessedRecords) -> dict[str, int]:
    """
    Aggregate play records by date.

    Args:
        records: List of processed play history records

    Returns:
        Dictionary mapping date strings to play counts
    """
    date_counts: dict[str, int] = defaultdict(int)

    for record in records:
        if 'datetime' in record:
            date_str = record['datetime'].strftime('%Y-%m-%d')
            date_counts[date_str] += 1

    return dict(date_counts)


def aggregate_by_day_of_week(records: ProcessedRecords) -> dict[str, int]:
    """
    Aggregate play records by day of week.

    Args:
        records: List of processed play history records

    Returns:
        Dictionary mapping day names to play counts
    """
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_counts: dict[str, int] = {day: 0 for day in day_names}

    for record in records:
        if 'datetime' in record:
            day_name = day_names[record['datetime'].weekday()]
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
        if 'datetime' in record:
            hour = record['datetime'].hour
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
        if 'datetime' in record:
            month_str = record['datetime'].strftime('%Y-%m')
            month_counts[month_str] += 1

    return dict(month_counts)


def aggregate_top_users(records: ProcessedRecords, limit: int = 10, censor: bool = True) -> UserAggregates:
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
        username = record.get('user', 'Unknown')
        if username:
            user_counts[username] += 1

    # Sort by play count and take top N
    sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    result: UserAggregates = []
    for username, count in sorted_users:
        processed_username = censor_username(username) if censor else username
        result.append({
            'username': processed_username,
            'play_count': count
        })

    return result


def aggregate_top_platforms(records: ProcessedRecords, limit: int = 10) -> PlatformAggregates:
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
        platform = record.get('platform', 'Unknown')
        if platform:
            platform_counts[platform] += 1

    # Sort by play count and take top N
    sorted_platforms = sorted(platform_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    result: PlatformAggregates = []
    for platform, count in sorted_platforms:
        result.append({
            'platform': platform,
            'play_count': count
        })

    return result


def handle_empty_data(graph_type: str) -> GraphData:
    """
    Handle empty data cases by returning appropriate empty data structures.

    Args:
        graph_type: Type of graph to generate empty data for

    Returns:
        Empty data structure appropriate for the graph type
    """
    if graph_type == 'daily':
        return {}
    elif graph_type == 'users':
        return []
    elif graph_type == 'platforms':
        return []
    elif graph_type == 'hourly':
        return {hour: 0 for hour in range(24)}
    elif graph_type == 'monthly':
        return {}
    else:
        return {}


def classify_media_type(media_type: str) -> str:
    """
    Classify a Tautulli media type into standardized categories.
    
    Args:
        media_type: The raw media type from Tautulli API
        
    Returns:
        Standardized media type ('movie', 'tv', 'music', 'other')
    """
    if not media_type:
        return 'other'
    
    media_type_lower = media_type.lower()
    
    if media_type_lower in ['movie']:
        return 'movie'
    elif media_type_lower in ['episode', 'show', 'tv']:
        return 'tv'
    elif media_type_lower in ['track', 'album', 'artist', 'music']:
        return 'music'
    else:
        return 'other'


def get_media_type_display_info() -> dict[str, dict[str, str]]:
    """
    Get display information for media types including colors and labels.
    
    Returns:
        Dictionary mapping media type to display info (name, color)
    """
    return {
        'movie': {
            'display_name': 'Movies',
            'color': '#ff7f0e'  # Orange - matches MOVIE_COLOR default
        },
        'tv': {
            'display_name': 'TV Series',
            'color': '#1f77b4'  # Blue - matches TV_COLOR default
        },
        'music': {
            'display_name': 'Music',
            'color': '#2ca02c'  # Green
        },
        'other': {
            'display_name': 'Other',
            'color': '#d62728'  # Red
        }
    }


def aggregate_by_date_separated(records: ProcessedRecords) -> SeparatedGraphData:
    """
    Aggregate play records by date with media type separation.
    
    Args:
        records: List of processed play history records
        
    Returns:
        Dictionary mapping media types to date-count dictionaries
    """
    separated_data: SeparatedGraphData = {}
    
    for record in records:
        if 'datetime' not in record:
            continue
            
        date_str = record['datetime'].strftime('%Y-%m-%d')
        media_type = classify_media_type(record.get('media_type', ''))
        
        if media_type not in separated_data:
            separated_data[media_type] = {}
            
        if date_str not in separated_data[media_type]:
            separated_data[media_type][date_str] = 0
            
        separated_data[media_type][date_str] += 1
    
    return separated_data


def aggregate_by_day_of_week_separated(records: ProcessedRecords) -> SeparatedGraphData:
    """
    Aggregate play records by day of week with media type separation.
    
    Args:
        records: List of processed play history records
        
    Returns:
        Dictionary mapping media types to day-count dictionaries
    """
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    separated_data: SeparatedGraphData = {}
    
    for record in records:
        if 'datetime' not in record:
            continue
            
        day_name = day_names[record['datetime'].weekday()]
        media_type = classify_media_type(record.get('media_type', ''))
        
        if media_type not in separated_data:
            separated_data[media_type] = {day: 0 for day in day_names}
            
        separated_data[media_type][day_name] += 1
    
    return separated_data


def aggregate_by_hour_of_day_separated(records: ProcessedRecords) -> dict[str, dict[int, int]]:
    """
    Aggregate play records by hour of day with media type separation.
    
    Args:
        records: List of processed play history records
        
    Returns:
        Dictionary mapping media types to hour-count dictionaries
    """
    separated_data: dict[str, dict[int, int]] = {}
    
    for record in records:
        if 'datetime' not in record:
            continue
            
        hour = record['datetime'].hour
        media_type = classify_media_type(record.get('media_type', ''))
        
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
        if 'datetime' not in record:
            continue
            
        month_str = record['datetime'].strftime('%Y-%m')
        media_type = classify_media_type(record.get('media_type', ''))
        
        if media_type not in separated_data:
            separated_data[media_type] = {}
            
        if month_str not in separated_data[media_type]:
            separated_data[media_type][month_str] = 0
            
        separated_data[media_type][month_str] += 1
    
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
        'axes.grid': enable_grid,
        'axes.grid.axis': 'y',
        'grid.linewidth': 0.5,
        'grid.alpha': 0.7,
        'axes.edgecolor': 'black',
        'axes.linewidth': 1.2,
        'xtick.bottom': True,
        'xtick.top': False,
        'ytick.left': True,
        'ytick.right': False,
        'axes.spines.left': True,
        'axes.spines.bottom': True,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'font.size': 11,
        'axes.titlesize': 16,
        'axes.labelsize': 12,
        'legend.fontsize': 11,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10
    }


def apply_modern_seaborn_styling() -> None:
    """
    Apply modern Seaborn styling for professional-looking graphs.
    """
    import seaborn as sns
    import matplotlib.pyplot as plt
    
    # Set the modern style
    sns.set_style("whitegrid", {
        'axes.grid': True,
        'axes.grid.axis': 'y',
        'grid.linewidth': 0.5,
        'grid.alpha': 0.7,
        'axes.edgecolor': '#333333',
        'axes.linewidth': 1.2,
    })
    
    # Set modern color palette
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    sns.set_palette(colors)
    
    # Configure matplotlib parameters for better appearance
    plt.rcParams.update({
        'font.size': 11,
        'axes.titlesize': 16,
        'axes.titleweight': 'bold',
        'axes.labelsize': 12,
        'legend.fontsize': 11,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'figure.titlesize': 18,
        'legend.frameon': True,
        'legend.fancybox': True,
        'legend.shadow': True,
        'legend.framealpha': 0.9
    })
