# graphs/graph_modules/utils.py

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os
import logging
import shutil
from collections import defaultdict

def format_date(date: datetime) -> str:
    """Format a datetime object to a string (YYYY-MM-DD).

    :param date: The datetime object to format
    :return: A formatted date string
    """
    return date.strftime("%Y-%m-%d")

def get_date_range(days: int) -> List[datetime]:
    """
    Get a list of datetime objects for the specified number of days up to today.
    
    :param days: The number of days to generate
    :return: A list of datetime objects
    """
    end_date = datetime.now().astimezone()
    start_date = end_date - timedelta(days=days - 1)
    return [start_date + timedelta(days=i) for i in range(days)]

def get_color(series_name: str, config: Dict[str, Any]) -> str:
    """
    Get the color for a given series name.
    
    :param series_name: The name of the series
    :param config: The configuration dictionary
    :return: The color code for the series
    """
    if series_name == "TV":
        return config.get("TV_COLOR", "#FF0000").strip('"')
    elif series_name == "Movies":
        return config.get("MOVIE_COLOR", "#00FF00").strip('"')
    else:
        return "#1f77b4"  # Default color

def ensure_folder_exists(folder: str):
    """
    Ensure that the specified folder exists, creating it if necessary.
    
    :param folder: The path to the folder
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
    logging.info(f"Ensured folder exists: {folder}")

def cleanup_old_folders(base_folder: str, keep_days: int, translations: Dict[str, str]):
    """
    Clean up old folders, keeping only the specified number of most recent ones.
    
    :param base_folder: The base folder containing dated subfolders
    :param keep_days: The number of recent folders to keep
    :param translations: The translations dictionary
    """
    if not os.path.exists(base_folder):
        return

    folders = [f for f in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, f))]
    folders.sort(reverse=True)
    for folder in folders[keep_days:]:
        folder_path = os.path.join(base_folder, folder)
        if not os.path.exists(folder_path):
            continue
        try:
            shutil.rmtree(folder_path)
        except Exception as e:
            logging.error(translations.get(
                "error_deleting_folder",
                "Error deleting folder {folder}: {error}"
            ).format(folder=folder, error=str(e)))
    logging.info(translations.get(
        "log_cleaned_up_old_folders",
        "Cleaned up folders, keeping last {keep_days} days."
    ).format(keep_days=keep_days))

def censor_username(username: str, should_censor: bool) -> str:
    """
    Censor a username if required.
    
    :param username: The username to potentially censor
    :param should_censor: Whether censoring should be applied
    :return: The censored or uncensored username
    """
    if not should_censor:
        return username
    length = len(username)
    if length <= 2:
        return "*" * length
    half_length = length // 2
    return username[:half_length] + "*" * (length - half_length)

def is_valid_date_string(date_string: str) -> bool:
    """
    Check if a string is a valid date in the format YYYY-MM-DD.

    :param date_string: The string to check
    :return: True if the string is a valid date, False otherwise
    """
    try:
        if not isinstance(date_string, str):
            return False
        if not date_string.count('-') == 2:
            return False
        date = datetime.strptime(date_string, "%Y-%m-%d")
        # Ensure reasonable date range
        min_date = datetime(1970, 1, 1)
        max_date = datetime.now() + timedelta(days=365)
        return min_date <= date <= max_date
    except ValueError:
        return False

def parse_time(value: str) -> Optional[datetime.time]:
    """
    Parse a time string into a datetime.time object.

    :param value: The time string to parse (format: HH:MM)
    :return: A datetime.time object, or None if parsing fails
    """
    try:
        if not value or not isinstance(value, str):
            raise ValueError("Empty or invalid input")
        return datetime.strptime(value.strip("\"'"), "%H:%M").time()
    except ValueError as e:
        logging.error(
            f"Invalid time format: {value}. Use HH:MM format (00:00-23:59). Error: {str(e)}"
        )
        return None

def get_sorted_date_folders(base_folder: str) -> List[str]:
    """
    Get a sorted list of date folders in the base folder.

    :param base_folder: The base folder containing date folders
    :return: A list of folder names sorted in descending order
    """
    if not isinstance(base_folder, str):
        logging.error(f"Invalid base folder type: {type(base_folder)}")
        return []

    if not os.path.exists(base_folder):
        logging.warning(f"Base folder {base_folder} does not exist.")
        return []

    try:
        folders = [
            f for f in os.listdir(base_folder) 
            if os.path.isdir(os.path.join(base_folder, f)) and is_valid_date_string(f)
        ]
        logging.debug(f"Found {len(folders)} valid date folders in {base_folder}")
        return sorted(folders, reverse=True)
    except OSError as e:
        logging.error(f"Error accessing folder {base_folder}: {str(e)}")
        return []

def format_delta_time(delta: timedelta) -> str:
    """
    Format a timedelta object into a human-readable string.

    :param delta: The timedelta to format
    :return: A formatted string representation of the time difference
    """
    units = {
        'day': delta.days,
        'hour': delta.seconds // 3600,
        'minute': (delta.seconds % 3600) // 60,
        'second': delta.seconds % 60
    }
    
    parts = [
        f"{value} {unit}{'s' if value != 1 else ''}"
        for unit, value in units.items()
        if value > 0
    ]

    if not parts:
        return "0 seconds"
    return ", ".join(parts)

def get_readable_file_size(size_in_bytes: int) -> str:
    """
    Convert file size in bytes to a human-readable format.

    :param size_in_bytes: File size in bytes
    :return: A string representation of the file size (e.g., "5.2 MB")
    :raises ValueError: If size is not a number
    """
    if not isinstance(size_in_bytes, (int, float)):
        raise ValueError("Size must be a number")
    if size_in_bytes < 0:
        return f"-{get_readable_file_size(abs(size_in_bytes))}"
    if size_in_bytes == 0:
        return "0 B"

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.1f} PB"

def get_next_update_time(last_update: datetime, update_days: int, fixed_update_time: str = None) -> datetime:
    """
    Calculate the next update time based on the last update and configuration.
    
    :param last_update: The datetime of the last update
    :param update_days: The number of days between updates
    :param fixed_update_time: Optional fixed time for updates (format: HH:MM)
    :return: The datetime of the next scheduled update
    """
    next_update = last_update + timedelta(days=update_days)
    
    if fixed_update_time:
        fixed_time = parse_time(fixed_update_time)
        if fixed_time:
            next_update = next_update.replace(
                hour=fixed_time.hour,
                minute=fixed_time.minute,
                second=0,
                microsecond=0
            )
    
    # Ensure next_update is in the future
    now = datetime.now(tz=next_update.tzinfo)
    if next_update <= now:
        days_behind = (now - next_update).days + 1
        days_to_add = ((days_behind + update_days - 1) // update_days) * update_days
        next_update += timedelta(days=days_to_add)
    
    return next_update

def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate configuration values.
    
    :param config: The configuration dictionary to validate
    :return: A list of error messages
    """
    errors = []
    required_keys = ["TAUTULLI_API_KEY", "TAUTULLI_URL", "DISCORD_TOKEN", "CHANNEL_ID"]
    for key in required_keys:
        if key not in config or not config[key]:
            errors.append(f"Missing or empty required configuration: {key}")

    # Validate URL format
    if "TAUTULLI_URL" in config and config["TAUTULLI_URL"]:
        if not config["TAUTULLI_URL"].startswith(("http://", "https://")):
            errors.append("TAUTULLI_URL must start with http:// or https://")

    if "UPDATE_DAYS" in config and (not isinstance(config["UPDATE_DAYS"], int) or config["UPDATE_DAYS"] <= 0):
        errors.append(
            f"UPDATE_DAYS must be a positive integer, got {config['UPDATE_DAYS']} "
            f"of type {type(config['UPDATE_DAYS']).__name__}"
        )

    if "KEEP_DAYS" in config and (not isinstance(config["KEEP_DAYS"], int) or config["KEEP_DAYS"] <= 0):
        errors.append(
            f"KEEP_DAYS must be a positive integer, got {config['KEEP_DAYS']} "
            f"of type {type(config['KEEP_DAYS']).__name__}"
        )

    return errors

def log_error(message: str, error: Exception, translations: Dict[str, str]):
    """
    Log an error message with translation support.

    :param message: The error message key in the translations dictionary
    :param error: The exception object
    :param translations: The translations dictionary
    """
    if not isinstance(translations, dict):
        translations = {}
    if not isinstance(error, Exception):
        error = Exception(str(error))

    try:
        logging.error(translations.get(message, message).format_map(
            defaultdict(str, error=str(error))
        ))
    except Exception as e:
        logging.error(f"Error while formatting log message: {str(e)}")
        logging.error(f"Original error: {str(error)}")

def log_info(message: str, translations: Dict[str, str], **kwargs):
    """
    Log an info message with translation support.

    :param message: The info message key in the translations dictionary
    :param translations: The translations dictionary
    :param kwargs: Additional formatting arguments for the translated message
    """
    if not isinstance(translations, dict):
        translations = {}

    try:
        logging.info(translations.get(message, message).format_map(
            defaultdict(str, **kwargs)
        ))
    except Exception as e:
        logging.error(f"Error while formatting log message: {str(e)}")
        logging.info(message)  # Fallback to original message
