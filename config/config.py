# config/config.py

"""
Main configuration interface for TGraph Bot.
Provides a clean API for configuration management while encapsulating implementation details.
"""

from functools import wraps
from threading import Lock
from time import time
from typing import Dict, Any, Optional, TypedDict, Literal, cast, Tuple
from .modules.constants import (
    CONFIG_SECTIONS,
    CONFIG_CATEGORIES,
    get_category_keys,
    get_category_display_name
)
from .modules.loader import (
    load_yaml_config,
    save_yaml_config,
    get_config_path,
    LoaderError,
)
from .modules.sanitizer import sanitize_config_value
from .modules.options import (
    CONFIGURABLE_OPTIONS,
    RESTART_REQUIRED_KEYS,
    get_option_metadata
)
from .modules.validator import (
    validate_config_value,
    _validate_color,
    ColorValidationResult,
)
import fcntl
import logging
import os
import tempfile

# Use environment variable or default path
CONFIG_PATH = get_config_path()

# Configuration Schema
class ConfigSchema(TypedDict):
    TAUTULLI_API_KEY: str
    TAUTULLI_URL: str
    DISCORD_TOKEN: str
    CHANNEL_ID: int
    UPDATE_DAYS: int
    FIXED_UPDATE_TIME: str
    KEEP_DAYS: int
    TIME_RANGE_DAYS: int
    LANGUAGE: Literal['en', 'da']
    CENSOR_USERNAMES: bool
    ENABLE_DAILY_PLAY_COUNT: bool
    ENABLE_PLAY_COUNT_BY_DAYOFWEEK: bool
    ENABLE_PLAY_COUNT_BY_HOUROFDAY: bool
    ENABLE_TOP_10_PLATFORMS: bool
    ENABLE_TOP_10_USERS: bool
    ENABLE_PLAY_COUNT_BY_MONTH: bool
    TV_COLOR: str
    MOVIE_COLOR: str
    GRAPH_BACKGROUND_COLOR: str
    ANNOTATION_COLOR: str
    ANNOTATION_OUTLINE_COLOR: str
    ENABLE_ANNOTATION_OUTLINE: bool
    CONFIG_COOLDOWN_MINUTES: int
    CONFIG_GLOBAL_COOLDOWN_SECONDS: int
    UPDATE_GRAPHS_COOLDOWN_MINUTES: int
    UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS: int
    MY_STATS_COOLDOWN_MINUTES: int
    MY_STATS_GLOBAL_COOLDOWN_SECONDS: int

# Error Classes
class ConfigError(Exception):
    """Base exception for configuration-related errors."""
    pass

class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""
    pass

class ConfigUpdateError(ConfigError):
    """Raised when configuration update fails."""
    pass

class ConfigKeyError(ConfigError):
    """Raised when accessing non-existent configuration keys."""
    pass

class ConfigCache:
    """Thread-safe configuration cache with exception handling."""
    
    def __init__(self, ttl: int = 300):
        """Initialize the cache.
        
        Args:
            ttl: Time-to-live in seconds for cache entries
        """
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._ttl = ttl
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache if it exists and hasn't expired."""
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time() - timestamp <= self._ttl:
                    return value
                else:
                    del self._cache[key]
            return None

    def set(self, key: str, value: Any) -> None:
        """Set a value in the cache."""
        if isinstance(value, Exception):
            return  # Don't cache exceptions
        with self._lock:
            self._cache[key] = (value, time())

    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()

# Create global cache instance
_config_cache = ConfigCache()

def cached_config(func):
    """Decorator for caching configuration values with exception handling."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
        cached_value = _config_cache.get(cache_key)
        
        if cached_value is not None:
            return cached_value
            
        try:
            result = func(*args, **kwargs)
            _config_cache.set(cache_key, result)
            return result
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {str(e)}")
            raise  # Re-raise the exception but don't cache it
            
    return wrapper

def get_categorized_config(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Organize configuration values by category.
    
    Args:
        config: The configuration dictionary
        
    Returns:
        Dictionary mapping categories to their configuration values
    """
    categorized = {}
    for category in CONFIG_CATEGORIES:
        keys = get_category_keys(category)
        category_config = {
            key: config[key] for key in keys 
            if key in config and key in CONFIGURABLE_OPTIONS
        }
        if category_config:  # Only include categories with configurable values
            categorized[category] = category_config
    return categorized

def validate_config_schema(config: Dict[str, Any]) -> None:
    """
    Validate configuration against schema.
    
    Args:
        config: Configuration dictionary to validate
        
    Raises:
        ConfigValidationError: If validation fails
    """
    if not isinstance(config, dict):
        raise ConfigValidationError("Configuration must be a dictionary")

    # Required fields and their types
    required_fields = {
        'TAUTULLI_API_KEY': str,
        'TAUTULLI_URL': str,
        'DISCORD_TOKEN': str,
        'CHANNEL_ID': int,
        'UPDATE_DAYS': int,
        'FIXED_UPDATE_TIME': str,
    }

    for field, expected_type in required_fields.items():
        if field not in config:
            raise ConfigValidationError(f"Missing required field: {field}")
        if not isinstance(config[field], expected_type):
            raise ConfigValidationError(
                f"Invalid type for {field}: expected {expected_type.__name__}, "
                f"got {type(config[field]).__name__}"
            )

    # Validate color fields separately
    color_fields = ['TV_COLOR', 'MOVIE_COLOR', 'ANNOTATION_COLOR', 'ANNOTATION_OUTLINE_COLOR']
    for field in color_fields:
        if field in config:
            result = _validate_color(config[field])
            if not result.is_valid:
                raise ConfigValidationError(f"Invalid color format for {field}: {result.error_message}")

    # Validate values by category
    for category in CONFIG_CATEGORIES:
        for key in get_category_keys(category):
            if key in config and not validate_config_value(key, config[key]):
                raise ConfigValidationError(
                    f"Invalid value for {key} in category {get_category_display_name(category)}: {config[key]}"
                )

async def validate_and_format_config_value(key: str, value: Any, translations: Dict[str, str]) -> Tuple[Optional[Any], Optional[str]]:
    """
    Validate and format a configuration value with enhanced error handling.
    
    Args:
        key: Configuration key
        value: Value to validate
        translations: Translation dictionary
        
    Returns:
        Tuple of (formatted_value, error_message)
    """
    try:
        if key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR", "ANNOTATION_OUTLINE_COLOR"]:
            result: ColorValidationResult = _validate_color(value)
            if not result.is_valid:
                return None, result.error_message
            return result.normalized_color, None

        # Handle other validations
        if not validate_config_value(key, value):
            return None, translations.get("config_invalid_value", "Invalid value provided")

        return sanitize_config_value(key, value), None

    except Exception as e:
        logging.error(f"Error validating config value: {str(e)}")
        return None, str(e)

@cached_config
def get_config_value(key: str) -> Any:
    """
    Get a specific configuration value with caching.
    
    Args:
        key: The configuration key to retrieve
        
    Returns:
        The configuration value
        
    Raises:
        ConfigKeyError: If the key doesn't exist
    """
    try:
        config = load_config()
        if key not in config:
            raise ConfigKeyError(f"Configuration key not found: {key}")
        return config[key]
    except ConfigError as e:
        logging.error(f"Failed to get configuration value: {str(e)}")
        raise

def load_config(config_path: Optional[str] = None, reload: bool = False) -> ConfigSchema:
    """
    Load and validate the bot configuration.
    
    Args:
        config_path: Optional path to config file
        reload: Whether to force reload from disk
        
    Returns:
        The loaded and validated configuration
        
    Raises:
        ConfigError: If configuration cannot be loaded or is invalid
    """
    try:
        path = config_path or CONFIG_PATH
        config = load_yaml_config(path)
        
        # Validate schema
        validate_config_schema(config)
        
        # Clear cache if reloading
        if reload:
            invalidate_config_cache()
        
        return cast(ConfigSchema, config)
    except (LoaderError, ConfigValidationError) as e:
        logging.error(f"Failed to load configuration: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error loading configuration: {str(e)}")
        raise ConfigError(f"Configuration load failed: {str(e)}") from e

def update_config(key: str, value: Any, translations: Dict[str, str]) -> str:
    """
    Update a configuration value with atomic file operations.
    
    Args:
        key: Configuration key to update
        value: New value to set
        translations: Translation strings
        
    Returns:
        Message indicating the result of the update
        
    Raises:
        ConfigUpdateError: If the update fails
    """
    try:
        # Create a temporary file in the same directory
        config_dir = os.path.dirname(CONFIG_PATH)
        with tempfile.NamedTemporaryFile(mode='w', dir=config_dir, delete=False) as temp_file:
            # Load and modify configuration
            with open(CONFIG_PATH, 'r') as config_file:
                # Acquire exclusive lock
                fcntl.flock(config_file.fileno(), fcntl.LOCK_EX)
                try:
                    config = load_yaml_config(CONFIG_PATH)
                    
                    # Special handling for color values
                    if key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR", "ANNOTATION_OUTLINE_COLOR"]:
                        result = _validate_color(value)
                        if not result.is_valid:
                            raise ValueError(result.error_message)
                        sanitized_value = sanitize_config_value(key, result.normalized_color)
                    else:
                        # Validate and sanitize
                        if not validate_config_value(key, value):
                            raise ValueError(f"Invalid value for {key}: {value}")
                        sanitized_value = sanitize_config_value(key, value)
                    
                    old_value = config.get(key)
                    config[key] = sanitized_value
                    
                    # Write to temp file
                    save_yaml_config(config, temp_file.name)
                    
                    # Atomic rename
                    os.replace(temp_file.name, CONFIG_PATH)
                    
                    # Clear cache
                    invalidate_config_cache()
                    
                    # Return appropriate message
                    if key == "FIXED_UPDATE_TIME" and str(sanitized_value).upper() == "XX:XX":
                        return translations["config_updated_fixed_time_disabled"].format(key=key)
                    
                    if key in RESTART_REQUIRED_KEYS:
                        return translations["config_updated_restart"].format(key=key)
                    
                    return translations["config_updated"].format(
                        key=key,
                        old_value=old_value,
                        new_value=sanitized_value
                    )
                finally:
                    # Release lock
                    fcntl.flock(config_file.fileno(), fcntl.LOCK_UN)
                    
    except Exception as e:
        logging.error(f"Failed to update configuration: {str(e)}")
        raise ConfigUpdateError(f"Configuration update failed: {str(e)}") from e

def get_config_metadata(key: str) -> Dict[str, Any]:
    """
    Get metadata for a configuration key.
    
    Args:
        key: The configuration key
        
    Returns:
        Dictionary containing option metadata
        
    Raises:
        ConfigKeyError: If the key doesn't exist
    """
    try:
        return get_option_metadata(key)
    except KeyError as e:
        raise ConfigKeyError(str(e)) from e

def invalidate_config_cache() -> None:
    """Invalidate the configuration cache."""
    _config_cache.clear()

def get_category_config(config: Dict[str, Any], category: str) -> Dict[str, Any]:
    """
    Get all configuration values for a specific category.
    
    Args:
        config: The configuration dictionary
        category: The category name
        
    Returns:
        Dictionary of configuration values for the category
    """
    return {
        key: config[key] 
        for key in get_category_keys(category) 
        if key in config
    }

def get_config_structure() -> Dict[str, Dict[str, Any]]:
    """
    Get the configuration structure organized by category.
    
    Returns:
        Dictionary mapping categories to their configuration metadata
    """
    return {
        category: {
            'display_name': get_category_display_name(category),
            'keys': get_category_keys(category)
        }
        for category in CONFIG_CATEGORIES
    }

# Export public interface
__all__ = [
    'load_config',
    'update_config',
    'get_config_value',
    'get_config_metadata',
    'get_categorized_config',
    'get_category_config',
    'get_config_structure',
    'invalidate_config_cache',
    'validate_and_format_config_value',
    'CONFIGURABLE_OPTIONS',
    'RESTART_REQUIRED_KEYS',
    'CONFIG_SECTIONS',
    'CONFIG_CATEGORIES',
    'CONFIG_PATH',
    'ConfigSchema',
    'ConfigError',
    'ConfigValidationError',
    'ConfigUpdateError',
    'ConfigKeyError',
]
