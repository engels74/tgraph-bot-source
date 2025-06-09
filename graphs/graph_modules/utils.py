"""
Utility functions for graph modules in TGraph Bot.

This module contains utility functions used by the graph modules,
such as date formatting, folder management, and username censoring.
"""

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


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
    timestamp: Optional[datetime] = None,
    user_id: Optional[str] = None
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
