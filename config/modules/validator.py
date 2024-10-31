# config/modules/validator.py

"""
Configuration validation for TGraph Bot.
Validates configuration values and structure against defined rules and constraints.
"""

from typing import Dict, Any, List, Optional, Tuple
import re
from urllib.parse import urlparse
from ipaddress import ip_address, IPv4Address
from .options import get_option_metadata, OPTION_METADATA

def _normalize_string(value: str) -> str:
    """
    Normalize a string by stripping quotes, whitespace, and converting to lowercase.

    Args:
        value: The string to normalize

    Returns:
        The normalized string
    """
    return str(value).strip().strip('"\'').lower()

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

        # Handle None values
        if value is None:
            return not metadata.get("required", False)

        # Type-specific validation
        value_type = metadata["type"]

        # Handle string-to-number conversion for numeric types
        if value_type in (int, float):
            if isinstance(value, str):
                # Strip whitespace and validate non-empty
                value = value.strip()
                if not value:
                    return False
                try:
                    # Handle both integer and float formats
                    if value_type is int:
                        # First convert to float to handle scientific notation
                        value = int(float(value))
                    else:
                        value = float(value)
                except ValueError:
                    return False

            # Special handling for cooldown values - allow zero and negative
            if key.endswith(("_COOLDOWN_MINUTES", "_COOLDOWN_SECONDS")):
                return isinstance(value, (int, float))

            # Check minimum value constraint for non-cooldown values
            if "min" in metadata and value < metadata["min"]:
                return False

            # Check maximum value constraint
            if "max" in metadata and value > metadata["max"]:
                return False

            return True

        # Boolean validation with expanded formats
        if value_type is bool:
            if isinstance(value, str):
                return value.lower() in ['true', 'false', '1', '0', 'yes', 'no', 'on', 'off', 't', 'f']
            return isinstance(value, bool)

        # String validation with format checking
        if value_type is str:
            if not isinstance(value, (str, int, float, bool)):
                return False

            # Convert to string and check if empty
            str_value = _normalize_string(str(value))
            if not str_value and metadata.get("required", False):
                return False

            if "format" in metadata:
                if metadata["format"] == "hex":
                    return _validate_color(str_value)
                elif metadata["format"] == "HH:MM":
                    return _validate_time(str_value)

            # Check allowed values if specified
            if "allowed_values" in metadata:
                return str_value in metadata["allowed_values"]

            # Check max length if specified
            if "max_length" in metadata and len(str_value) > metadata["max_length"]:
                return False

            return True

        # Default type checking
        return isinstance(value, value_type)

    except (KeyError, TypeError, ValueError):
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
        if metadata.get("required", False) and (key not in config or config[key] is None):
            errors.append(f"Missing required configuration: {key}")
            continue

        if key in config and not validate_config_value(key, config[key]):
            errors.append(f"Invalid value for {key}: {config[key]}")

    # Check for unknown keys
    unknown_keys = set(config.keys()) - set(OPTION_METADATA.keys())
    if unknown_keys:
        errors.append(f"Unknown configuration keys: {', '.join(unknown_keys)}")

    return len(errors) == 0, errors

def _validate_color(value: str) -> bool:
    """
    Validate a color value in hex format.
    Supports RGB, RGBA, RRGGBB, and RRGGBBAA formats.

    Args:
        value: The color value to validate

    Returns:
        True if valid, False otherwise
    """
    if not value:
        return False

    # Normalize the value
    color = _normalize_string(value)

    # Check format
    if not color.startswith('#'):
        return False

    # Remove the # for pattern matching
    color = color[1:]

    # Valid formats: RGB, RGBA, RRGGBB, or RRGGBBAA
    return bool(re.match(r'^[0-9a-f]{3}([0-9a-f])?$|^[0-9a-f]{6}([0-9a-f]{2})?$', color, re.IGNORECASE))

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

    time_str = _normalize_string(value).upper()

    # Special case: XX:XX is valid
    if time_str == "XX:XX":
        return True

    # Check HH:MM format
    try:
        time_parts = time_str.split(':')
        if len(time_parts) != 2:
            return False
        
        hours, minutes = map(int, time_parts)
        return 0 <= hours < 24 and 0 <= minutes < 60
    except ValueError:
        return False

def _is_private_ip(ip_str: str) -> bool:
    """
    Check if an IP address is private.

    Args:
        ip_str: The IP address string to check

    Returns:
        True if private IP, False otherwise
    """
    try:
        ip = ip_address(ip_str)
        return (
            isinstance(ip, IPv4Address) and (
                ip.is_private or
                ip.is_loopback or
                ip.is_link_local or
                ip.is_multicast
            )
        )
    except ValueError:
        return False

def validate_url(url: str) -> bool:
    """
    Validate a URL format with enhanced security checks.

    Args:
        url: The URL to validate

    Returns:
        True if the URL is valid and secure, False otherwise
    """
    try:
        # Basic URL length check
        if not url or len(url) > 2048:  # Common URL length limit
            return False

        parsed = urlparse(url)

        # Check for required components
        if not all([
            parsed.scheme in ('http', 'https'),
            parsed.netloc,
            len(parsed.netloc) <= 253  # DNS name length limit
        ]):
            return False

        # Security checks
        hostname = parsed.hostname or ''
        return not any([
            hostname.startswith('localhost'),
            _is_private_ip(hostname),
            '..' in parsed.path,  # Path traversal check
            '%00' in url,  # Null byte injection check
            hostname.count('.') > 10  # Suspicious number of subdomains
        ])

    except Exception:
        return False

def validate_discord_token(token: str) -> bool:
    """
    Validate a Discord bot token format.

    Args:
        token: The token to validate

    Returns:
        True if the format is valid, False otherwise
    """
    if not token or len(token) > 100:  # Reasonable length limit
        return False
    # Basic format validation for Discord tokens
    # Real validation happens when the bot tries to connect
    return bool(re.match(r'^[A-Za-z0-9_\-]{24,}\.[A-Za-z0-9_\-]{6}\.[A-Za-z0-9_\-]{27}$', str(token)))

def validate_discord_channel_id(channel_id: str) -> bool:
    """
    Validate a Discord channel ID format.

    Args:
        channel_id: The channel ID to validate

    Returns:
        True if the format is valid, False otherwise
    """
    try:
        # Discord channel IDs are numeric and typically 17-19 digits
        channel_id_str = str(channel_id).strip()
        if not channel_id_str.isdigit() or not (17 <= len(channel_id_str) <= 19):
            return False
        
        # Additional sanity check - should be a positive number
        return int(channel_id_str) > 0
    except (ValueError, TypeError):
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
    try:
        # Handle string input
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return False
            value = int(float(value))

        if not isinstance(value, int):
            return False

        # Special handling for cooldown values
        if minimum == 0:  # This indicates it's a cooldown value
            return True  # Accept any integer for cooldowns

        if minimum is not None and value < minimum:
            return False

        if maximum is not None and value > maximum:
            return False

        return True

    except (ValueError, TypeError):
        return False

def validate_language(value: str) -> bool:
    """
    Validate a language code.

    Args:
        value: The language code to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        metadata = get_option_metadata("LANGUAGE")
        return value in metadata.get("allowed_values", [])
    except KeyError:
        return False

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
