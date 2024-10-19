# config/config.py

"""
Main configuration interface for TGraph Bot.
Provides a clean API for configuration management while encapsulating implementation details.
"""

import os
import logging
import fcntl
import tempfile
from typing import Dict, Any, Optional, TypedDict, Literal, cast
from functools import lru_cache

from .modules.loader import (
    load_yaml_config,
    save_yaml_config,
    get_config_path,
    ConfigLoadError,
)
from .modules.validator import validate_config_value
from .modules.sanitizer import sanitize_config_value
from .modules.options import (
    CONFIGURABLE_OPTIONS,
    RESTART_REQUIRED_KEYS,
    get_option_metadata
)
from .modules.constants import (
    CONFIG_SECTIONS,
    CONFIG_CATEGORIES,
    get_category_keys,
    get_category_display_name
)

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

    # Validate values by category
    for category in CONFIG_CATEGORIES:
        for key in get_category_keys(category):
            if key in config and not validate_config_value(key, config[key]):
                raise ConfigValidationError(
                    f"Invalid value for {key} in category {get_category_display_name(category)}: {config[key]}"
                )

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
    except (ConfigLoadError, ConfigValidationError) as e:
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

@lru_cache(maxsize=128)
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
    get_config_value.cache_clear()

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
    'CONFIGURABLE_OPTIONS',
    'RESTART_REQUIRED_KEYS',
    'CONFIG_SECTIONS',
    'CONFIG_CATEGORIES',
    'CONFIG_PATH',
    'ConfigSchema',
    'ConfigError',
    'ConfigLoadError',
    'ConfigValidationError',
    'ConfigUpdateError',
    'ConfigKeyError',
]
