# config/modules/validator.py

"""
Configuration validation for TGraph Bot.
Validates configuration values and structure against defined rules and constraints.
"""

from typing import Dict, Any, List, Optional, Tuple
import re
from datetime import datetime
from .options import get_option_metadata, OPTION_METADATA

def validate_config_value(key: str, value: Any) -> bool:
    """
    Validate a single configuration value against its metadata rules.
    
    Args:
        key: The configuration key
        value: The value to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        metadata = get_option_metadata(key)
        
        # Check required values
        if metadata.get("required", False) and value is None:
            return False
            
        # Type validation
        if not isinstance(value, metadata["type"]) and value is not None:
            # Special case for string-like values
            if metadata["type"] is str and not hasattr(value, "__str__"):
                return False
            # Special case for integer values that might be float
            if metadata["type"] is int and not isinstance(value, (int, float)):
                return False
        
        # Format-specific validation
        if "format" in metadata:
            if metadata["format"] == "hex":
                return _validate_color(value)
            elif metadata["format"] == "HH:MM":
                return _validate_time(value)
                
        # Range validation for numeric values
        if isinstance(value, (int, float)):
            if "min" in metadata and value < metadata["min"]:
                return False
            if "max" in metadata and value > metadata["max"]:
                return False
                
        # Allowed values validation
        if "allowed_values" in metadata and value not in metadata["allowed_values"]:
            return False
            
        return True
        
    except Exception:
        return False

def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate an entire configuration dictionary.
    
    Args:
        config: The configuration dictionary to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check for required keys
    for key, metadata in OPTION_METADATA.items():
        if metadata.get("required", False):
            if key not in config or config[key] is None:
                errors.append(f"Missing required configuration: {key}")
                continue
                
        if key in config:
            if not validate_config_value(key, config[key]):
                errors.append(f"Invalid value for {key}: {config[key]}")
    
    # Check for unknown keys
    unknown_keys = set(config.keys()) - set(OPTION_METADATA.keys())
    if unknown_keys:
        errors.append(f"Unknown configuration keys: {', '.join(unknown_keys)}")
    
    return len(errors) == 0, errors

def _validate_color(value: str) -> bool:
    """
    Validate a color value in hex format.
    
    Args:
        value: The color value to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not value:
        return False
        
    # Strip quotes and whitespace
    color = str(value).strip().strip('"\'')
    
    # Check format
    if not color.startswith('#'):
        return False
        
    # Remove the # for pattern matching
    color = color[1:]
    
    # Valid formats: RGB, RRGGBB
    return bool(re.match(r'^(?:[0-9a-fA-F]{3}){1,2}$', color))

def _validate_time(value: str) -> bool:
    """
    Validate a time value in HH:MM format.
    
    Args:
        value: The time value to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not value:
        return False
        
    time_str = str(value).strip().strip('"\'').upper()
    
    # Special case: XX:XX is valid
    if time_str == "XX:XX":
        return True
        
    # Check HH:MM format
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

def validate_integer_range(value: int, minimum: Optional[int] = None, maximum: Optional[int] = None) -> bool:
    """
    Validate an integer value against optional minimum and maximum constraints.
    
    Args:
        value: The value to validate
        minimum: Optional minimum value
        maximum: Optional maximum value
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(value, int):
        return False
        
    if minimum is not None and value < minimum:
        return False
        
    if maximum is not None and value > maximum:
        return False
        
    return True

def validate_language(value: str) -> bool:
    """
    Validate a language code.
    
    Args:
        value: The language code to validate
        
    Returns:
        True if valid, False otherwise
    """
    metadata = get_option_metadata("LANGUAGE")
    return value in metadata.get("allowed_values", [])

def get_validation_errors(config: Dict[str, Any]) -> List[str]:
    """
    Get a list of all validation errors in a configuration.
    
    Args:
        config: The configuration dictionary to validate
        
    Returns:
        List of error messages
    """
    is_valid, errors = validate_config(config)
    return errors

def validate_discord_token(token: str) -> bool:
    """
    Validate a Discord bot token format.
    
    Args:
        token: The token to validate
        
    Returns:
        True if the format is valid, False otherwise
    """
    # Basic format validation for Discord tokens
    # Real validation happens when the bot tries to connect
    return bool(re.match(r'^[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}$', str(token)))

def validate_url(url: str) -> bool:
    """
    Validate a URL format.
    
    Args:
        url: The URL to validate
        
    Returns:
        True if the format is valid, False otherwise
    """
    # Basic URL format validation
    pattern = r'^https?:\/\/(?:[\w-]+\.)+[\w-]+(?::\d+)?(?:\/[\w-./?%&=]*)?$'
    return bool(re.match(pattern, str(url)))

def validate_discord_channel_id(channel_id: str) -> bool:
    """
    Validate a Discord channel ID format.
    
    Args:
        channel_id: The channel ID to validate
        
    Returns:
        True if the format is valid, False otherwise
    """
    # Discord channel IDs are numeric and typically 17-19 digits
    return bool(re.match(r'^\d{17,19}$', str(channel_id)))
