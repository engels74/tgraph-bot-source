# graphs/graph_modules/utils.py

from typing import List, Dict, Any
from datetime import datetime, timedelta
import os
import logging
import shutil

def format_date(date: datetime) -> str:
    """
    Format a datetime object to a string.
    
    :param date: The datetime object to format
    :return: A formatted date string (YYYY-MM-DD)
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
        return config["TV_COLOR"].strip('"')
    elif series_name == "Movies":
        return config["MOVIE_COLOR"].strip('"')
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
    folders = [f for f in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, f))]
    folders.sort(reverse=True)
    for folder in folders[keep_days:]:
        try:
            shutil.rmtree(os.path.join(base_folder, folder))
        except Exception as e:
            logging.error(translations["error_deleting_folder"].format(folder=folder, error=str(e)))
    logging.info(translations["log_cleaned_up_old_folders"].format(keep_days=keep_days))

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

def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate the configuration dictionary.
    
    :param config: The configuration dictionary to validate
    :return: A list of error messages, empty if no errors
    """
    errors = []
    required_keys = ["TAUTULLI_API_KEY", "TAUTULLI_URL", "DISCORD_TOKEN", "CHANNEL_ID"]
    for key in required_keys:
        if key not in config or not config[key]:
            errors.append(f"Missing or empty required configuration: {key}")
    
    if "UPDATE_DAYS" in config and (not isinstance(config["UPDATE_DAYS"], int) or config["UPDATE_DAYS"] <= 0):
        errors.append("UPDATE_DAYS must be a positive integer")
    
    if "KEEP_DAYS" in config and (not isinstance(config["KEEP_DAYS"], int) or config["KEEP_DAYS"] <= 0):
        errors.append("KEEP_DAYS must be a positive integer")
    
    return errors

def format_time_value(value: str) -> str:
    """
    Format a time value, ensuring it's properly quoted.
    
    :param value: The time value to format
    :return: The formatted time value
    """
    value = value.strip().strip("\"'")
    return f'"{value}"'

def parse_time(value: str) -> datetime.time:
    """
    Parse a time string into a datetime.time object.
    
    :param value: The time string to parse (format: HH:MM)
    :return: A datetime.time object, or None if parsing fails
    """
    try:
        return datetime.strptime(value.strip("\"'"), "%H:%M").time()
    except ValueError:
        logging.error(f"Invalid time format: {value}. Use HH:MM format.")
        return None

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
            next_update = next_update.replace(hour=fixed_time.hour, minute=fixed_time.minute, second=0, microsecond=0)
    
    # Ensure next_update is in the future
    while next_update <= datetime.now():
        next_update += timedelta(days=update_days)
    
    return next_update

def format_delta_time(delta: timedelta) -> str:
    """
    Format a timedelta object into a human-readable string.
    
    :param delta: The timedelta to format
    :return: A formatted string representation of the time difference
    """
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    
    return ", ".join(parts)

def get_readable_file_size(size_in_bytes: int) -> str:
    """
    Convert file size in bytes to a human-readable format.

    :param size_in_bytes: File size in bytes
    :return: A string representation of the file size (e.g., "5.2 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.1f} PB"

def is_valid_date_string(date_string: str) -> bool:
    """
    Check if a string is a valid date in the format YYYY-MM-DD.

    :param date_string: The string to check
    :return: True if the string is a valid date, False otherwise
    """
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def get_sorted_date_folders(base_folder: str) -> List[str]:
    """
    Get a sorted list of date folders in the base folder.

    :param base_folder: The base folder containing date folders
    :return: A list of folder names sorted in descending order (newest first)
    """
    folders = [f for f in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, f)) and is_valid_date_string(f)]
    return sorted(folders, reverse=True)

def log_error(message: str, error: Exception, translations: Dict[str, str]):
    """
    Log an error message with translation support.

    :param message: The error message key in the translations dictionary
    :param error: The exception object
    :param translations: The translations dictionary
    """
    logging.error(translations.get(message, message).format(error=str(error)))

def log_info(message: str, translations: Dict[str, str], **kwargs):
    """
    Log an info message with translation support.

    :param message: The info message key in the translations dictionary
    :param translations: The translations dictionary
    :param kwargs: Additional formatting arguments for the translated message
    """
    logging.info(translations.get(message, message).format(**kwargs))
