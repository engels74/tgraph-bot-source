# graphs/graph_modules/utils.py

"""
Utility functions for graph generation.
"""

from config.modules.validator import (
    _validate_color,
    validate_url,
    ColorValidationResult,
    validate_config_value
)
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
import os
import shutil

def format_date(date: datetime) -> str:
    """Format a datetime object to a string (YYYY-MM-DD).

    Args:
        date: The datetime object to format

    Returns:
        str: A formatted date string
    """
    return date.strftime("%Y-%m-%d")

def get_date_range(days: int) -> List[datetime]:
    """Get a list of datetime objects for the specified number of days up to today.
    
    Args:
        days: The number of days to generate
        
    Returns:
        List[datetime]: A list of datetime objects
        
    Raises:
        ValueError: If days is not a positive integer
    """
    if not isinstance(days, int) or days <= 0:
        raise ValueError("Days must be a positive integer")
        
    end_date = datetime.now().astimezone()
    start_date = end_date - timedelta(days=days - 1)
    return [start_date + timedelta(days=i) for i in range(days)]

def get_color(series_name: str, config: Dict[str, Any]) -> str:
    """Get the color for a given series name.
    
    Args:
        series_name: The name of the series
        config: The configuration dictionary
        
    Returns:
        str: The color code for the series. Returns default color '#1f77b4' if 
             no matching color is found in config.
    """
    color_map = {
        "TV": "TV_COLOR",
        "Movies": "MOVIE_COLOR"
    }
    
    series_key = series_name.strip()
    config_key = color_map.get(series_key)
    
    if config_key:
        color = config.get(config_key)
        if color:
            return color.strip('"\'')
            
    # Default color if no match or missing config
    return "#1f77b4"

def ensure_folder_exists(folder: str) -> None:
    """Ensure that the specified folder exists, creating it if necessary.
    
    Args:
        folder: The path to the folder
        
    Raises:
        OSError: If folder creation fails
    """
    try:
        if not os.path.exists(folder):
            os.makedirs(folder)
            logging.info(f"Created folder: {folder}")
        logging.debug(f"Ensured folder exists: {folder}")
    except OSError as e:
        logging.error(f"Failed to create folder {folder}: {e}")
        raise

def parse_folder_date(folder_name: str) -> Optional[datetime]:
    """Parse a folder name into a datetime object.
    
    Args:
        folder_name: The name of the folder in YYYY-MM-DD format
        
    Returns:
        Optional[datetime]: Parsed datetime or None if invalid
    """
    try:
        return datetime.strptime(folder_name, "%Y-%m-%d")
    except ValueError:
        return None

def cleanup_old_folders(base_folder: str, keep_days: int, translations: Dict[str, str]) -> None:
    """Clean up old folders, keeping only the specified number of most recent ones.
    
    Args:
        base_folder: The base folder containing dated subfolders
        keep_days: The number of recent folders to keep
        translations: The translations dictionary
    """
    if not os.path.exists(base_folder):
        return

    try:
        # Get all folders and parse dates
        folder_dates = []
        for folder in os.listdir(base_folder):
            folder_path = os.path.join(base_folder, folder)
            if os.path.isdir(folder_path):
                parsed_date = parse_folder_date(folder)
                if parsed_date:
                    folder_dates.append((folder, parsed_date))

        # Sort by date and get folders to delete
        folder_dates.sort(key=lambda x: x[1], reverse=True)
        folders_to_delete = [folder for folder, _ in folder_dates[keep_days:]]

        # Delete old folders
        for folder in folders_to_delete:
            folder_path = os.path.join(base_folder, folder)
            try:
                shutil.rmtree(folder_path)
                logging.debug(f"Deleted old folder: {folder}")
            except OSError as e:
                logging.error(
                    translations.get(
                        "error_deleting_folder",
                        "Error deleting folder {folder}: {error}"
                    ).format(folder=folder, error=str(e))
                )

        logging.info(
            translations.get(
                "log_cleaned_up_old_folders",
                "Cleaned up folders, keeping last {keep_days} days."
            ).format(keep_days=keep_days)
        )

    except Exception as e:
        logging.error(f"Error during folder cleanup: {str(e)}")

def censor_username(username: str, should_censor: bool) -> str:
    """Censor a username if required.
    
    Args:
        username: The username to potentially censor
        should_censor: Whether censoring should be applied
        
    Returns:
        str: The censored or uncensored username
    """
    if not should_censor or not username:
        return username

    length = len(username)
    if length <= 2:
        return "*" * length

    half_length = length // 2
    return username[:half_length] + "*" * (length - half_length)

def is_valid_date_string(date_string: str) -> bool:
    """Check if a string is a valid date in the format YYYY-MM-DD.

    Args:
        date_string: The string to check

    Returns:
        bool: True if the string is a valid date, False otherwise
    """
    if not isinstance(date_string, str):
        return False

    try:
        if date_string.count('-') != 2:
            return False
            
        date = datetime.strptime(date_string, "%Y-%m-%d")
        
        # Ensure reasonable date range
        min_date = datetime(1970, 1, 1)
        max_date = datetime.now() + timedelta(days=365)
        
        return min_date <= date <= max_date
    except ValueError:
        return False

def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate configuration values with enhanced checks.
    
    Args:
        config: The configuration dictionary to validate
        
    Returns:
        List[str]: List of error messages, empty if validation passes
    """
    errors = []
    
    # Required configuration keys with type validation
    required_validations = {
        "TAUTULLI_API_KEY": (str, "API key must be a string"),
        "TAUTULLI_URL": (str, "URL must be a string"),
        "DISCORD_TOKEN": (str, "Discord token must be a string"),
        "CHANNEL_ID": ((int, str), "Channel ID must be a number or string that converts to a number")
    }

    # Check required fields
    for key, (expected_type, error_msg) in required_validations.items():
        if key not in config or not config[key]:
            errors.append(f"Missing or empty required configuration: {key}")
            continue

        value = config[key]
        if isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                try:
                    # For CHANNEL_ID, try converting string to int
                    if key == "CHANNEL_ID" and isinstance(value, str):
                        int(value)
                    else:
                        errors.append(f"{error_msg} (got {type(value).__name__})")
                except ValueError:
                    errors.append(f"{error_msg} (invalid format)")
        elif not isinstance(value, expected_type):
            errors.append(f"{error_msg} (got {type(value).__name__})")

    # Validate URL format and security
    if "TAUTULLI_URL" in config and config["TAUTULLI_URL"]:
        url = config["TAUTULLI_URL"]
        if not validate_url(url):
            errors.append(
                f"Invalid or insecure TAUTULLI_URL: {url}\n"
                "URL must start with http:// or https:// and be properly formatted"
            )

    # Validate numeric values
    numeric_validations = {
        "UPDATE_DAYS": (1, None, "UPDATE_DAYS must be a positive integer"),
        "KEEP_DAYS": (1, None, "KEEP_DAYS must be a positive integer"),
        "TIME_RANGE_DAYS": (1, 365, "TIME_RANGE_DAYS must be between 1 and 365")
    }

    for key, (min_val, max_val, error_msg) in numeric_validations.items():
        if key in config:
            try:
                value = int(config[key])
                if value < min_val:
                    errors.append(f"{error_msg} (got {value})")
                if max_val and value > max_val:
                    errors.append(f"{error_msg} (got {value})")
            except (ValueError, TypeError):
                errors.append(f"{key} must be a valid integer (got {config[key]})")

    # Validate color values using validator's color validation
    color_keys = ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR", "ANNOTATION_OUTLINE_COLOR"]
    for key in color_keys:
        if key in config:
            result: ColorValidationResult = _validate_color(config[key])
            if not result.is_valid:
                errors.append(f"Invalid color format for {key}: {result.error_message}")

    # Use validator's config_value validation for other fields
    for key, value in config.items():
        if key not in required_validations and key not in numeric_validations:
            try:
                if not validate_config_value(key, value):
                    errors.append(f"Invalid value for {key}: {value}")
            except KeyError:
                # Skip validation if key is not in validator's metadata
                continue

    return errors

def get_sorted_date_folders(base_folder: str) -> List[str]:
    """Get a sorted list of date folders in the base folder.

    Args:
        base_folder: The base folder containing date folders

    Returns:
        List[str]: List of folder names sorted by date in descending order
    """
    if not isinstance(base_folder, str):
        logging.error(f"Invalid base folder type: {type(base_folder)}")
        return []

    if not os.path.exists(base_folder):
        logging.warning(f"Base folder {base_folder} does not exist.")
        return []

    try:
        valid_folders = []
        for f in os.listdir(base_folder):
            folder_path = os.path.join(base_folder, f)
            if os.path.isdir(folder_path) and is_valid_date_string(f):
                valid_folders.append(f)

        try:
            valid_folders.sort(
                key=lambda x: datetime.strptime(x, "%Y-%m-%d"),
                reverse=True
            )
            logging.debug(f"Sorted {len(valid_folders)} valid date folders in {base_folder}")
            return valid_folders
        except ValueError as e:
            logging.error(f"Error parsing folder dates: {str(e)}")
            return []

    except OSError as e:
        logging.error(f"Error accessing folder {base_folder}: {str(e)}")
        return []

def format_delta_time(delta: timedelta) -> str:
    """Format a timedelta object into a human-readable string.

    Args:
        delta: The timedelta to format

    Returns:
        str: A formatted string representation of the time difference
        
    Raises:
        TypeError: If input is not a timedelta object
    """
    if not isinstance(delta, timedelta):
        raise TypeError("Input must be a timedelta object")

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

    return ", ".join(parts) if parts else "0 seconds"

def get_readable_file_size(size_in_bytes: int) -> str:
    """Convert file size in bytes to a human-readable format.

    Args:
        size_in_bytes: File size in bytes

    Returns:
        str: A string representation of the file size (e.g., "5.2 MB")

    Raises:
        ValueError: If size is negative or not a valid number
    """
    if not isinstance(size_in_bytes, (int, float)):
        raise ValueError("Size must be a number")

    if size_in_bytes < 0:
        raise ValueError("File size cannot be negative")
        
    if size_in_bytes == 0:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    base = 1024.0
    i = 0

    while size_in_bytes >= base and i < len(units) - 1:
        size_in_bytes /= base
        i += 1

    return f"{size_in_bytes:.1f} {units[i]}"

def validate_date_range(start_date: datetime, end_date: datetime) -> Tuple[bool, Optional[str]]:
    """
    Validate a date range for reasonableness.
    
    Args:
        start_date: The start date to validate
        end_date: The end date to validate
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
        return False, "Dates must be datetime objects"

    if start_date > end_date:
        return False, "Start date cannot be after end date"

    # Check for unreasonable date ranges
    min_date = datetime(1970, 1, 1)
    max_date = datetime.now() + timedelta(days=365)
    
    if start_date < min_date:
        return False, f"Start date cannot be before {min_date.date()}"
        
    if end_date > max_date:
        return False, f"End date cannot be after {max_date.date()}"

    # Check for unreasonably long date ranges
    max_range = timedelta(days=365 * 5)  # 5 years
    if end_date - start_date > max_range:
        return False, "Date range cannot exceed 5 years"

    return True, None

def validate_series_data(
    series: List[Dict[str, Any]], 
    expected_length: Optional[int] = None,
    series_type: str = "series"
) -> List[str]:
    """
    Validate series data for completeness and consistency.
    
    Args:
        series: List of series data dictionaries
        expected_length: Expected number of data points per series (optional)
        series_type: Type of series for error messages (default: "series")
        
    Returns:
        List of validation error messages, empty if validation passes
    """
    errors = []
    
    if not isinstance(series, list):
        return [f"{series_type} must be a list"]
        
    for idx, serie in enumerate(series):
        # Validate dictionary type
        if not isinstance(serie, dict):
            errors.append(f"{series_type} {idx} is not a dictionary")
            continue
            
        # Check required keys
        if "name" not in serie or "data" not in serie:
            errors.append(f"{series_type} {idx} missing required keys (name, data)")
            continue
            
        # Validate data type and content
        data = serie["data"]
        if not isinstance(data, list):
            errors.append(f"{series_type} {idx} ({serie['name']}) data is not a list")
            continue
            
        # Validate length if specified
        if expected_length is not None and len(data) != expected_length:
            errors.append(
                f"{series_type} {idx} ({serie['name']}) data length mismatch: "
                f"expected {expected_length}, got {len(data)}"
            )
            
        # Validate numeric data
        if not all(isinstance(x, (int, float)) for x in data):
            errors.append(f"{series_type} {idx} ({serie['name']}) contains non-numeric data")
            
    return errors
