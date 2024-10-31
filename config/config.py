# config/config.py

"""
Main configuration interface for TGraph Bot.
Provides a clean API for configuration management while encapsulating implementation details.
"""

import logging
import os
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
    CONFIG_SECTIONS,
    get_option_metadata
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

    # Validate specific field constraints
    if config['UPDATE_DAYS'] <= 0:
        raise ConfigValidationError("UPDATE_DAYS must be a positive integer")

    if not config['FIXED_UPDATE_TIME'].upper() == 'XX:XX' and not validate_config_value('FIXED_UPDATE_TIME', config['FIXED_UPDATE_TIME']):
        raise ConfigValidationError("Invalid FIXED_UPDATE_TIME format")

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

def invalidate_config_cache() -> None:
    """Invalidate the configuration cache."""
    get_config_value.cache_clear()

def get_section_keys(section: str) -> list:
    """
    Get all configuration keys in a section.
    
    Args:
        section: Name of the configuration section
        
    Returns:
        List of keys in the section
        
    Raises:
        ConfigKeyError: If the section doesn't exist
    """
    if section not in CONFIG_SECTIONS:
        raise ConfigKeyError(f"Configuration section not found: {section}")
    return CONFIG_SECTIONS[section]["keys"]

def is_configurable(key: str) -> bool:
    """
    Check if a configuration key can be modified via Discord commands.
    
    Args:
        key: The configuration key to check
        
    Returns:
        True if the key is configurable via Discord
    """
    return key in CONFIGURABLE_OPTIONS

def requires_restart(key: str) -> bool:
    """
    Check if changing a configuration key requires a bot restart.
    
    Args:
        key: The configuration key to check
        
    Returns:
        True if changing the key requires a restart
    """
    return key in RESTART_REQUIRED_KEYS

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

# Export public interface
__all__ = [
    'load_config',
    'update_config',
    'get_config_value',
    'get_section_keys',
    'is_configurable',
    'requires_restart',
    'get_config_metadata',
    'invalidate_config_cache',
    'CONFIGURABLE_OPTIONS',
    'RESTART_REQUIRED_KEYS',
    'CONFIG_SECTIONS',
    'CONFIG_PATH',
    'ConfigSchema',
    'ConfigError',
    'ConfigLoadError',
    'ConfigValidationError',
    'ConfigUpdateError',
    'ConfigKeyError',
]
