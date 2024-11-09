# config/modules/sanitizer.py

"""
Configuration value sanitization for TGraph Bot.
Handles type conversion, formatting, and validation of configuration values.
"""

from .constants import CONFIG_SECTIONS
from .options import get_option_metadata
from .validator import _validate_color, ColorValidationResult
from datetime import datetime
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from typing import Any, Dict, Optional
import logging

# Module-level constants with explicit types
DEFAULT_COLOR: str = "#000000"
DEFAULT_TIME: str = "XX:XX"
DEFAULT_MIN_VALUE: int = 1
TIME_FORMATS: tuple[str, ...] = ("%H:%M", "%I:%M%p", "%H.%M", "%H:%M:%S")

class ConfigurationError(Exception):
    """Base exception for critical configuration issues."""
    pass

class ValidationError(ConfigurationError):
    """Raised when configuration value validation fails."""
    pass

class SanitizationError(ConfigurationError):
    """Raised when value sanitization fails."""
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
        ValidationError: For invalid value formats
        SanitizationError: For sanitization failures
    """
    try:
        if value is None:
            return _get_default_for_type(key)

        metadata = get_option_metadata(key)
        if metadata is None:
            raise ConfigurationError(f"No metadata found for key: {key}")

        value_type = metadata["type"]

        # Handle empty strings
        if isinstance(value, str) and not value.strip():
            return _get_default_for_type(key)

        # Type-specific sanitization with error handling
        try:
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

        except (ValueError, TypeError) as e:
            raise SanitizationError(f"Failed to sanitize value for {key}: {value}") from e
            
    except KeyError as e:
        logging.error(f"Missing metadata for {key}: {str(e)}")
        raise ConfigurationError(f"Missing configuration metadata for {key}") from e
    except Exception as e:
        logging.error(f"Unexpected error sanitizing {key}: {str(e)}")
        raise ConfigurationError(f"Failed to sanitize configuration value for {key}") from e

def _sanitize_boolean(value: Any) -> bool:
    """
    Convert a value to boolean with improved validation.
    
    Args:
        value: The value to convert
        
    Returns:
        bool: The converted boolean value
        
    Raises:
        ValueError: If the value cannot be converted to boolean
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        value = value.lower().strip()
        if value in ('true', '1', 'yes', 'on', 't', 'y'):
            return True
        if value in ('false', '0', 'no', 'off', 'f', 'n'):
            return False
        raise ValueError(f"Invalid boolean string: {value}")
    return bool(value)

def _sanitize_integer(
    value: Any, 
    minimum: Optional[int] = None, 
    key: Optional[str] = None
) -> int:
    """
    Convert a value to integer with minimum constraint and cooldown handling.
    
    Args:
        value: The value to convert
        minimum: Optional minimum value
        key: Optional configuration key for context
        
    Returns:
        int: The sanitized integer value
        
    Raises:
        ValueError: If the value cannot be converted to integer
    """
    try:
        converted_value = int(float(str(value).strip()))
            
        # For cooldown settings, allow zero/negative values
        if key and (key.endswith('_COOLDOWN_MINUTES') or key.endswith('_COOLDOWN_SECONDS')):
            return converted_value
            
        # For non-cooldown settings, apply minimum constraint
        if minimum is not None:
            return max(minimum, converted_value)
            
        return converted_value
    except (ValueError, TypeError):
        if key and (key.endswith('_COOLDOWN_MINUTES') or key.endswith('_COOLDOWN_SECONDS')):
            return 0  # Default to disabled for cooldowns
        return minimum if minimum is not None else DEFAULT_MIN_VALUE

def _sanitize_color(value: str) -> DoubleQuotedScalarString:
    """
    Sanitize a color value to proper hex format with validation.
    
    Args:
        value: The color value to sanitize
        
    Returns:
        DoubleQuotedScalarString: The sanitized color value
        
    Raises:
        ValidationError: If color validation fails
    """
    validation_result: ColorValidationResult = _validate_color(value)
    if not validation_result.is_valid:
        logging.warning(f"Invalid color value: {validation_result.error_message}")
        return DoubleQuotedScalarString(DEFAULT_COLOR)
        
    return DoubleQuotedScalarString(validation_result.normalized_color)

def _sanitize_time(value: str) -> DoubleQuotedScalarString:
    """
    Sanitize a time value to HH:MM format with multi-format support.
    
    Args:
        value: The time value to sanitize
        
    Returns:
        DoubleQuotedScalarString: The sanitized time value
        
    Raises:
        ValidationError: If time format is invalid
    """
    time_str = str(value).strip().strip('"\'').upper()
    if time_str == "XX:XX":
        return DoubleQuotedScalarString(DEFAULT_TIME)
    
    for fmt in TIME_FORMATS:
        try:
            parsed_time = datetime.strptime(time_str, fmt)
            if 0 <= parsed_time.hour < 24 and 0 <= parsed_time.minute < 60:
                return DoubleQuotedScalarString(parsed_time.strftime("%H:%M"))
        except ValueError:
            continue
    
    logging.warning(f"Invalid time format: {time_str}, using default")
    return DoubleQuotedScalarString(DEFAULT_TIME)

def _sanitize_string(value: Any) -> str:
    """
    Convert a value to string and clean it.
    
    Args:
        value: The value to sanitize
        
    Returns:
        str: The sanitized string
    """
    return str(value).strip().strip('"\'')

def _get_default_for_type(key: str) -> Any:
    """
    Get a safe default value based on the option's type.
    
    Args:
        key: The configuration key
        
    Returns:
        The default value for the type
        
    Raises:
        KeyError: If the key doesn't exist in metadata
    """
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
    
    Args:
        key: The configuration key
        value: The value to format
        
    Returns:
        str: The formatted value for display
    """
    if value is None:
        return "not set"
    if isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, (list, tuple)):
        return ', '.join(map(str, value)) if value else "empty list"
    elif isinstance(value, dict):
        return ', '.join(f"{k}: {v}" for k, v in value.items()) if value else "empty dict"
    elif isinstance(value, (DoubleQuotedScalarString, str)):
        return str(value).strip('"\'')
    return str(value)

def validate_and_sanitize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize an entire configuration dictionary.
    
    Args:
        config: The configuration dictionary to process
        
    Returns:
        Dict[str, Any]: The sanitized configuration
        
    Raises:
        ConfigurationError: If validation or sanitization fails
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
                except (ValidationError, SanitizationError) as e:
                    logging.error(f"Error in section {section}, key {key}: {str(e)}")
                    sanitized[key] = _get_default_for_type(key)
                except Exception as e:
                    logging.error(f"Unexpected error processing {key}: {str(e)}")
                    raise ConfigurationError(f"Failed to process configuration key: {key}") from e
    
    # Handle remaining keys
    for key, value in config.items():
        if key not in sanitized:
            try:
                sanitized[key] = sanitize_config_value(key, value)
            except Exception as e:
                logging.error(f"Error processing uncategorized key {key}: {str(e)}")
                sanitized[key] = _get_default_for_type(key)
                
    return sanitized
