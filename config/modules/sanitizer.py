# config/modules/sanitizer.py

"""
Configuration value sanitization for TGraph Bot.
Handles type conversion, formatting, and validation of configuration values with enhanced error handling.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
import logging
import re

# Custom Exception Hierarchy
class SanitizerError(Exception):
    """Base exception for sanitizer errors."""
    pass

class ValidationError(SanitizerError):
    """Raised when value validation fails."""
    pass

class ConversionError(SanitizerError):
    """Raised when type conversion fails."""
    pass

class FormatError(SanitizerError):
    """Raised when format validation fails."""
    pass

class ResourceError(SanitizerError):
    """Raised when resource handling fails."""
    pass

class InvalidUserIdError(ValidationError):
    """Raised when user ID validation fails."""
    pass

# Module Constants
DEFAULT_COLOR: str = "#000000"
DEFAULT_TIME: str = "XX:XX"
DEFAULT_MIN_VALUE: int = 1
TIME_FORMATS: tuple[str, ...] = ("%H:%M", "%I:%M%p", "%H.%M", "%H:%M:%S")
MAX_USER_ID_LENGTH: int = 50

def sanitize_config_value(
    key: str,
    value: Any,
    translations: Optional[Dict[str, str]] = None
) -> Any:
    """
    Sanitize a configuration value based on its key's requirements.
    
    Args:
        key: The configuration key
        value: The value to sanitize
        translations: Optional translation dictionary
        
    Returns:
        The sanitized value
        
    Raises:
        SanitizerError: For sanitization failures
        ValidationError: For validation failures
        ConversionError: For type conversion failures
    """
    try:
        from .options import get_option_metadata

        if value is None:
            return _get_default_for_type(key)

        metadata = get_option_metadata(key)
        if metadata is None:
            error_msg = (translations or {}).get(
                'error_missing_metadata',
                'No metadata found for key: {key}'
            ).format(key=key)
            raise ValidationError(error_msg)

        value_type = metadata["type"]

        # Handle empty strings
        if isinstance(value, str) and not value.strip():
            return _get_default_for_type(key)

        try:
            # Type-specific sanitization with enhanced error handling
            if value_type is bool:
                return _sanitize_boolean(value, translations)
            elif value_type is int:
                return _sanitize_integer(value, metadata.get("min"), key, translations)
            elif value_type is str:
                if "format" in metadata:
                    if metadata["format"] == "hex":
                        return _sanitize_color(value, translations)
                    elif metadata["format"] == "HH:MM":
                        return _sanitize_time(value, translations)
                return _sanitize_string(value)
            
            return value

        except (ValueError, TypeError) as e:
            error_msg = (translations or {}).get(
                'error_sanitize_value',
                'Failed to sanitize value for {key}: {error}'
            ).format(key=key, error=str(e))
            raise ConversionError(error_msg) from e
            
    except Exception as e:
        if isinstance(e, (ValidationError, ConversionError)):
            raise
        error_msg = (translations or {}).get(
            'error_unexpected_sanitize',
            'Unexpected error sanitizing {key}: {error}'
        ).format(key=key, error=str(e))
        logging.error(error_msg)
        raise SanitizerError(error_msg) from e

def _sanitize_boolean(value: Any, translations: Optional[Dict[str, str]] = None) -> bool:
    """
    Convert a value to boolean with enhanced validation.
    
    Args:
        value: The value to convert
        translations: Optional translation dictionary
        
    Returns:
        The converted boolean value
        
    Raises:
        ConversionError: If conversion fails
    """
    try:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value = value.lower().strip()
            if value in ('true', '1', 'yes', 'on', 't', 'y'):
                return True
            if value in ('false', '0', 'no', 'off', 'f', 'n'):
                return False
            error_msg = (translations or {}).get(
                'error_invalid_boolean',
                'Invalid boolean string: {value}'
            ).format(value=value)
            raise ConversionError(error_msg)
        return bool(value)
        
    except (ValueError, TypeError) as e:
        error_msg = (translations or {}).get(
            'error_boolean_conversion',
            'Boolean conversion failed: {error}'
        ).format(error=str(e))
        raise ConversionError(error_msg) from e

def _sanitize_integer(
    value: Any,
    minimum: Optional[int] = None,
    key: Optional[str] = None,
    translations: Optional[Dict[str, str]] = None
) -> int:
    """
    Convert a value to integer with minimum constraint and cooldown handling.
    
    Args:
        value: The value to convert
        minimum: Optional minimum value
        key: Optional configuration key for context
        translations: Optional translation dictionary
        
    Returns:
        The sanitized integer value
        
    Raises:
        ConversionError: If conversion fails
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
        
    except (ValueError, TypeError) as e:
        if key and (key.endswith('_COOLDOWN_MINUTES') or key.endswith('_COOLDOWN_SECONDS')):
            return 0  # Default to disabled for cooldowns
            
        error_msg = (translations or {}).get(
            'error_integer_conversion',
            'Integer conversion failed: {error}'
        ).format(error=str(e))
        raise ConversionError(error_msg) from e

def _sanitize_color(
    value: str,
    translations: Optional[Dict[str, str]] = None
) -> DoubleQuotedScalarString:
    """
    Sanitize a color value to proper hex format with validation.
    
    Args:
        value: The color value to sanitize
        translations: Optional translation dictionary
        
    Returns:
        The sanitized color value
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        from .validator import _validate_color
        
        validation_result = _validate_color(value)
        if not validation_result.is_valid:
            error_msg = (translations or {}).get(
                'error_invalid_color',
                'Invalid color value: {error}'
            ).format(error=validation_result.error_message)
            raise ValidationError(error_msg)
            
        return DoubleQuotedScalarString(validation_result.normalized_color or DEFAULT_COLOR)
        
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        error_msg = (translations or {}).get(
            'error_color_validation',
            'Color validation failed: {error}'
        ).format(error=str(e))
        raise ValidationError(error_msg) from e

def _sanitize_time(
    value: str,
    translations: Optional[Dict[str, str]] = None
) -> DoubleQuotedScalarString:
    """
    Sanitize a time value to HH:MM format with multi-format support.
    
    Args:
        value: The time value to sanitize
        translations: Optional translation dictionary
        
    Returns:
        The sanitized time value
        
    Raises:
        ValidationError: If validation fails
    """
    try:
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
        
        error_msg = (translations or {}).get(
            'error_invalid_time',
            'Invalid time format: {value}'
        ).format(value=time_str)
        raise ValidationError(error_msg)
        
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        error_msg = (translations or {}).get(
            'error_time_validation',
            'Time validation failed: {error}'
        ).format(error=str(e))
        raise ValidationError(error_msg) from e

def _sanitize_string(value: Any) -> str:
    """
    Convert a value to string and clean it.
    
    Args:
        value: The value to sanitize
        
    Returns:
        The sanitized string
        
    Raises:
        ConversionError: If conversion fails
    """
    try:
        return str(value).strip().strip('"\'')
    except (ValueError, TypeError) as e:
        raise ConversionError(f"String conversion failed: {str(e)}") from e

def _get_default_for_type(key: str) -> Any:
    """
    Get a safe default value based on the option's type.
    
    Args:
        key: The configuration key
        
    Returns:
        The default value for the type
        
    Raises:
        ValidationError: If metadata lookup fails
    """
    try:
        from .options import get_option_metadata
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
            
    except Exception as e:
        raise ValidationError(f"Failed to get default value for {key}: {str(e)}") from e

def format_value_for_display(key: str, value: Any) -> str:
    """
    Format a configuration value for display in Discord messages.
    
    Args:
        key: The configuration key
        value: The value to format
        
    Returns:
        The formatted value for display
        
    Raises:
        FormatError: If formatting fails
    """
    try:
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
        
    except Exception as e:
        raise FormatError(f"Failed to format value for display: {str(e)}") from e

def sanitize_user_id(user_id: Optional[str]) -> str:
    """
    Sanitize user ID for safe filename creation with enhanced security.
    
    Args:
        user_id: The user ID to sanitize
        
    Returns:
        A sanitized version of the user ID safe for filenames
        
    Raises:
        InvalidUserIdError: If user_id is invalid
    """
    if user_id is None:
        raise InvalidUserIdError("User ID cannot be None")
        
    try:
        # Convert to string and strip whitespace
        user_id_str = str(user_id).strip()
        
        # Basic validation
        if not user_id_str:
            raise InvalidUserIdError("User ID cannot be empty")
        
        if len(user_id_str) > MAX_USER_ID_LENGTH * 2:
            raise InvalidUserIdError(f"User ID exceeds maximum allowed length ({MAX_USER_ID_LENGTH * 2})")
            
        # Verify at least one alphanumeric character
        if not any(c.isalnum() for c in user_id_str):
            raise InvalidUserIdError("User ID must contain at least one alphanumeric character")
            
        # Enhanced sanitization
        sanitized = ""
        for c in user_id_str:
            if c.isalnum() or c in '_-':
                sanitized += c
            else:
                sanitized += '_'
                
        # Additional security measures
        sanitized = sanitized.strip('._-')  # Remove leading/trailing special chars
        if not sanitized:
            raise InvalidUserIdError("Sanitized user ID cannot be empty")
            
        # Limit length after sanitization
        sanitized = sanitized[:MAX_USER_ID_LENGTH]
        
        # Prevent hidden files
        if sanitized.startswith('.'):
            sanitized = f"_dot_{sanitized[1:]}"
            
        # Ensure the final ID is not just special characters
        if not any(c.isalnum() for c in sanitized):
            raise InvalidUserIdError("Sanitized user ID must contain at least one alphanumeric character")
            
        return sanitized
        
    except InvalidUserIdError:
        raise
    except Exception as e:
        raise InvalidUserIdError(f"Failed to sanitize user ID: {str(e)}") from e

def sanitize_language_code(language: str) -> str:
    """
    Sanitize language code to prevent path traversal and ensure valid format.
    
    Args:
        language: The language code to sanitize
        
    Returns:
        str: A sanitized language code
        
    Raises:
        ValidationError: If language code is invalid
    """
    if not language:
        raise ValidationError("Language code cannot be empty")
        
    try:
        # Strip any whitespace and quotes
        sanitized = str(language).strip().strip('"\'').lower()
        
        # Validate against common language code formats
        if not re.match(r'^[a-z]{2}(-[a-z]{2})?$', sanitized):
            raise ValidationError(f"Invalid language code format: {language}")
            
        # Limit length
        if len(sanitized) > 5:  # Most language codes are 2-5 characters
            raise ValidationError(f"Language code too long: {language}")
            
        return sanitized
        
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Failed to sanitize language code: {str(e)}") from e

# Export public interface
__all__ = [
    'sanitize_config_value',
    'format_value_for_display',
    'sanitize_user_id',
    'SanitizerError',
    'ValidationError',
    'ConversionError',
    'FormatError',
    'ResourceError',
    'InvalidUserIdError',
]
