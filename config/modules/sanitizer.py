# config/modules/sanitizer.py

"""
Configuration value sanitization for TGraph Bot.
Handles type conversion, formatting, and validation of configuration values.
"""

from datetime import datetime
from typing import Any, Dict, Optional
import logging
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from .options import get_option_metadata
from .constants import CONFIG_SECTIONS

def sanitize_config_value(key: str, value: Any) -> Any:
    """
    Sanitize a configuration value based on its key's requirements.
    
    Args:
        key: The configuration key
        value: The value to sanitize
        
    Returns:
        The sanitized value
        
    Raises:
        ValueError: If the value cannot be sanitized properly
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

    except Exception as e:
        logging.error(f"Error sanitizing config value for key {key}: {str(e)}")
        return _get_default_for_type(key)

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
        if isinstance(value, str):
            # Handle potential decimal strings
            value = int(float(value))
        else:
            value = int(value)
            
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
        return minimum if minimum is not None else 0

def _sanitize_color(value: str) -> DoubleQuotedScalarString:
    """Sanitize a color value to proper hex format."""
    color = str(value).strip().strip('"\'')
    if not color.startswith('#'):
        color = f'#{color}'
    # Ensure valid hex color
    if len(color) == 4:  # Convert #RGB to #RRGGBB
        color = f'#{color[1]*2}{color[2]*2}{color[3]*2}'
    elif len(color) != 7:  # Invalid length, return default
        color = '#000000'
    return DoubleQuotedScalarString(color)

def _sanitize_time(value: str) -> DoubleQuotedScalarString:
    """Sanitize a time value to HH:MM format."""
    time_str = str(value).strip().strip('"\'').upper()
    if time_str == "XX:XX":
        return DoubleQuotedScalarString("XX:XX")
    try:
        parsed_time = datetime.strptime(time_str, "%H:%M")
        return DoubleQuotedScalarString(parsed_time.strftime("%H:%M"))
    except ValueError:
        return DoubleQuotedScalarString("XX:XX")

def _sanitize_string(value: Any) -> str:
    """Convert a value to string and clean it up."""
    return str(value).strip().strip('"\'')

def _get_default_for_type(key: str) -> Any:
    """Get a safe default value based on the option's type."""
    metadata = get_option_metadata(key)
    value_type = metadata["type"]
    
    # Special handling for cooldown settings
    if key.endswith(('_COOLDOWN_MINUTES', '_COOLDOWN_SECONDS')):
        return 0  # Default to disabled for cooldowns
    
    if value_type is bool:
        return True
    elif value_type is int:
        return metadata.get("min", 1)
    elif value_type is str:
        if "format" in metadata:
            if metadata["format"] == "hex":
                return DoubleQuotedScalarString("#000000")
            elif metadata["format"] == "HH:MM":
                return DoubleQuotedScalarString("XX:XX")
        return ""

def validate_and_sanitize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize an entire configuration dictionary.
    
    Args:
        config: The configuration dictionary to process
        
    Returns:
        A new dictionary with all values sanitized
    """
    sanitized = {}
    
    # Process sections in order
    for section in CONFIG_SECTIONS:
        section_data = CONFIG_SECTIONS[section]
        for key in section_data['keys']:
            if key in config:
                try:
                    sanitized[key] = sanitize_config_value(key, config[key])
                except Exception as e:
                    logging.error(f"Error sanitizing {key}: {str(e)}")
                    sanitized[key] = _get_default_for_type(key)
    
    # Handle any remaining keys not in sections
    for key, value in config.items():
        if key not in sanitized:
            try:
                sanitized[key] = sanitize_config_value(key, value)
            except Exception as e:
                logging.error(f"Error sanitizing {key}: {str(e)}")
                sanitized[key] = _get_default_for_type(key)
                
    return sanitized

def format_value_for_display(key: str, value: Any) -> str:
    """
    Format a configuration value for display in Discord messages.
    
    Args:
        key: The configuration key
        value: The value to format
        
    Returns:
        A string representation of the value suitable for display
    """
    if isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, (DoubleQuotedScalarString, str)):
        return str(value).strip('"\'')
    return str(value)
