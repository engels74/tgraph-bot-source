# config/config.py

"""
Main configuration interface for TGraph Bot.
Provides a clean API for configuration management while encapsulating implementation details.
"""

import logging
from typing import Dict, Any, Optional

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

def load_config(config_path: Optional[str] = None, reload: bool = False) -> Dict[str, Any]:
    """
    Load the bot configuration.
    
    Args:
        config_path: Optional path to config file
        reload: Whether to force reload from disk
        
    Returns:
        The loaded configuration
        
    Raises:
        ConfigError: If configuration cannot be loaded
    """
    try:
        path = config_path or CONFIG_PATH
        return load_yaml_config(path)
    except ConfigLoadError as e:
        logging.error(f"Failed to load configuration: {str(e)}")
        raise

def update_config(key: str, value: Any, translations: Dict[str, str]) -> str:
    """
    Update a configuration value.
    
    Args:
        key: Configuration key to update
        value: New value to set
        translations: Translation strings
        
    Returns:
        Message indicating the result of the update
    """
    try:
        config = load_config(reload=True)
        
        # Validate and sanitize the new value
        if not validate_config_value(key, value):
            raise ValueError(f"Invalid value for {key}: {value}")
            
        sanitized_value = sanitize_config_value(key, value)
        old_value = config.get(key)
        config[key] = sanitized_value
        
        # Save the updated configuration
        save_yaml_config(config, CONFIG_PATH)
        
        # Return appropriate message based on the type of update
        if key == "FIXED_UPDATE_TIME" and str(sanitized_value).upper() == "XX:XX":
            return translations["config_updated_fixed_time_disabled"].format(key=key)
            
        if key in RESTART_REQUIRED_KEYS:
            return translations["config_updated_restart"].format(key=key)
            
        return translations["config_updated"].format(
            key=key,
            old_value=old_value,
            new_value=sanitized_value
        )
        
    except Exception as e:
        logging.error(f"Failed to update configuration: {str(e)}")
        raise

def get_config_value(key: str) -> Any:
    """
    Get a specific configuration value.
    
    Args:
        key: The configuration key to retrieve
        
    Returns:
        The configuration value
    """
    config = load_config()
    if key not in config:
        raise KeyError(f"Configuration key not found: {key}")
    return config[key]

def get_section_keys(section: str) -> list:
    """
    Get all configuration keys in a section.
    
    Args:
        section: Name of the configuration section
        
    Returns:
        List of keys in the section
    """
    if section not in CONFIG_SECTIONS:
        raise KeyError(f"Configuration section not found: {section}")
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
    """
    return get_option_metadata(key)

class ConfigError(Exception):
    """Base exception for configuration-related errors."""
    pass

# Export public interface
__all__ = [
    'load_config',
    'update_config',
    'get_config_value',
    'get_section_keys',
    'is_configurable',
    'requires_restart',
    'get_config_metadata',
    'CONFIGURABLE_OPTIONS',
    'RESTART_REQUIRED_KEYS',
    'CONFIG_SECTIONS',
    'CONFIG_PATH',
    'validate_config_value',
    'sanitize_config_value',
    'ConfigError',
]
