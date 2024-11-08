# config/modules/sanitizer.py

"""
Configuration value sanitization for TGraph Bot.
Handles type conversion, formatting, and validation of configuration values.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from .options import get_option_metadata
from .constants import CONFIG_SECTIONS
from .validator import _validate_color, ColorValidationResult

# Module-level constants
DEFAULT_COLOR = "#000000"
DEFAULT_TIME = "XX:XX"
DEFAULT_MIN_VALUE = 1
TIME_FORMATS = ["%H:%M", "%I:%M%p", "%H.%M", "%H:%M:%S"]

class ConfigurationError(Exception):
    """Raised when there are critical configuration issues."""
    pass

def sanitize_config_value(key: str, value: Any) -> Any:
    """
    Sanitize a configuration value based on its key's requirements.
    
    Args:
        key: The configuration key
        value: The value to sanitize
        
    Returns:
        The sanitized value
        
    Raises:
        ConfigurationError: For critical configuration issues
        ValueError: For invalid value formats
        TypeError: For invalid value types
    """
    try:
        if value is None:
            return _get_default_for_type(key)

        metadata = get_option_metadata(key)
        value_type = metadata["type"]

        # Handle empty strings
        if isinstance(value, str) and not value.strip():
            return _get_default_for_type(key)

        # Type-specific sanitization
        if value_type is bool:
            return _sanitize_boolean(value)
        elif value_type is int:
            return _sanitize_integer(value, metadata.get("min"), key)
        elif value_type is str:
            if "format" in metadata:
                if metadata["format"] == "hex":
                    return _sanitize_color(value)
                elif metadata["format"] == "HH:MM":
                    return _sanitize_time(value)
            return _sanitize_string(value)
        
        return value

    except ValueError as e:
        logging.error(f"Invalid value format for {key}: {str(e)}")
        return _get_default_for_type(key)
    except TypeError as e:
        logging.error(f"Invalid type for {key}: {str(e)}")
        return _get_default_for_type(key)
    except KeyError as e:
        logging.error(f"Missing metadata for {key}: {str(e)}")
        raise ConfigurationError(f"Missing configuration metadata for {key}")

def _sanitize_boolean(value: Any) -> bool:
    """Convert a value to boolean while preserving formatting."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ['true', '1', 'yes', 'on', 't', 'y']
    return bool(value)

def _sanitize_integer(value: Any, minimum: Optional[int] = None, key: str = None) -> int:
    """
    Convert a value to integer and apply minimum constraint.
    Special handling for cooldown values to allow zero/negative values.
    """
    try:
        value = int(float(value)) if isinstance(value, str) else int(value)
            
        # For cooldown settings, allow zero and negative values
        if key and (key.endswith('_COOLDOWN_MINUTES') or key.endswith('_COOLDOWN_SECONDS')):
            return value
            
        # For non-cooldown settings, apply minimum constraint
        if minimum is not None:
            value = max(minimum, value)
            
        return value
    except (ValueError, TypeError):
        # Return appropriate default based on whether it's a cooldown setting
        if key and (key.endswith('_COOLDOWN_MINUTES') or key.endswith('_COOLDOWN_SECONDS')):
            return 0  # Default to disabled for cooldowns
        return minimum if minimum is not None else DEFAULT_MIN_VALUE

def _sanitize_color(value: str) -> DoubleQuotedScalarString:
    """
    Sanitize a color value to proper hex format.
    Uses enhanced color validation from validator.py.
    """
    validation_result: ColorValidationResult = _validate_color(value)
    if not validation_result.is_valid:
        logging.warning(f"{validation_result.error_message}, using default: {DEFAULT_COLOR}")
        return DoubleQuotedScalarString(DEFAULT_COLOR)
        
    return DoubleQuotedScalarString(validation_result.normalized_color)

def _sanitize_time(value: str) -> DoubleQuotedScalarString:
    """
    Sanitize a time value to HH:MM format.
    Supports multiple common time formats.
    """
    time_str = str(value).strip().strip('"\'').upper()
    if time_str == "XX:XX":
        return DoubleQuotedScalarString(DEFAULT_TIME)
    
    try:
        # Try multiple common formats
        for fmt in TIME_FORMATS:
            try:
                parsed_time = datetime.strptime(time_str, fmt)
                # Validate hours and minutes are in reasonable range
                if 0 <= parsed_time.hour < 24 and 0 <= parsed_time.minute < 60:
                    return DoubleQuotedScalarString(parsed_time.strftime("%H:%M"))
            except ValueError:
                continue
        
        logging.warning(f"Could not parse time string: {time_str}, using default: {DEFAULT_TIME}")
        return DoubleQuotedScalarString(DEFAULT_TIME)
    except Exception as e:
        logging.error(f"Error processing time value: {str(e)}")
        return DoubleQuotedScalarString(DEFAULT_TIME)

def _sanitize_string(value: Any) -> str:
    """Convert a value to string and clean it up."""
    return str(value).strip().strip('"\'')
    
def _get_default_for_type(key: str) -> Any:
    """Get a safe default value based on the option's type."""
    metadata = get_option_metadata(key)
    value_type = metadata["type"]
    
    # Special handling for cooldown settings
    if key.endswith(('_COOLDOWN_MINUTES', '_COOLDOWN_SECONDS')):
        return 0
    
    if value_type is bool:
        return True
    elif value_type is int:
        return metadata.get("min", DEFAULT_MIN_VALUE)
    elif value_type is str:
        if "format" in metadata:
            if metadata["format"] == "hex":
                return DoubleQuotedScalarString(DEFAULT_COLOR)
            elif metadata["format"] == "HH:MM":
                return DoubleQuotedScalarString(DEFAULT_TIME)
        return ""

def format_value_for_display(key: str, value: Any) -> str:
    """
    Format a configuration value for display in Discord messages.
    Handles various types and edge cases.
    """
    if value is None:
        return "not set"
    if isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, list):
        if not value:
            return "empty list"
        return ', '.join(map(str, value))
    elif isinstance(value, dict):
        if not value:
            return "empty dict"
        return ', '.join(f"{k}: {v}" for k, v in value.items())
    elif isinstance(value, (DoubleQuotedScalarString, str)):
        return str(value).strip('"\'')
    elif hasattr(value, '__str__'):
        return str(value)
    return str(value)

def validate_and_sanitize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize an entire configuration dictionary.
    Includes enhanced error handling with section context.
    """
    sanitized = {}
    
    # Process sections in order
    for section in CONFIG_SECTIONS:
        section_data = CONFIG_SECTIONS[section]
        logging.debug(f"Processing section: {section}")
        for key in section_data['keys']:
            if key in config:
                try:
                    sanitized[key] = sanitize_config_value(key, config[key])
                except Exception as e:
                    logging.error(f"Error sanitizing {key} in section {section}: {str(e)}")
                    sanitized[key] = _get_default_for_type(key)
    
    # Handle any remaining keys not in sections
    logging.debug("Processing uncategorized keys")
    for key, value in config.items():
        if key not in sanitized:
            try:
                sanitized[key] = sanitize_config_value(key, value)
            except Exception as e:
                logging.error(f"Error sanitizing uncategorized key {key}: {str(e)}")
                sanitized[key] = _get_default_for_type(key)
                
    return sanitized
