# config/modules/validator.py

"""
Configuration validation for TGraph Bot.
Validates configuration values and structure against defined rules and constraints.
"""

from typing import Dict, Any, List, Tuple
import re
from urllib.parse import urlparse
from ipaddress import ip_address, IPv4Address
from .options import get_option_metadata, OPTION_METADATA
from .constants import CONFIG_CATEGORIES, get_category_keys, get_category_display_name

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
    Includes category-based validation and enhanced error messages.

    Args:
        config: The configuration dictionary to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check for required keys by category
    for category in CONFIG_CATEGORIES:
        category_name = get_category_display_name(category)
        for key in get_category_keys(category):
            metadata = OPTION_METADATA.get(key, {})
            if metadata.get("required", False) and (key not in config or config[key] is None):
                errors.append(f"Missing required configuration in {category_name}: {key}")
                continue

            if key in config and not validate_config_value(key, config[key]):
                errors.append(f"Invalid value for {key} in {category_name}: {config[key]}")

    # Check for unknown keys
    known_keys = set()
    for category in CONFIG_CATEGORIES:
        known_keys.update(get_category_keys(category))
    
    unknown_keys = set(config.keys()) - known_keys
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
