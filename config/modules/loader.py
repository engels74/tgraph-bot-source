# config/modules/loader.py

"""
Configuration file loading and saving for TGraph Bot.
Handles YAML file operations with support for comments and formatting preservation.
"""

from .constants import CONFIG_SECTIONS, get_category_keys, CONFIG_CATEGORIES
from .defaults import create_default_config
from .validator import validate_config
from .sanitizer import sanitize_config_value, ConfigurationError
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLError
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from typing import Optional, Any
import logging
import os

class ConfigLoadError(Exception):
    """Raised when there's an error loading the configuration."""
    pass

class ConfigSaveError(Exception):
    """Raised when there's an error saving the configuration."""
    pass

def setup_yaml() -> YAML:
    """Create and configure a YAML instance with proper settings."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096
    yaml.explicit_start = None
    yaml.version = None
    yaml.default_flow_style = False
    yaml.allow_unicode = True
    yaml.default_style = None
    yaml.preserve_comments = True
    return yaml

def get_section_for_key(key: str) -> Optional[str]:
    """Get the section name for a given key."""
    for section, data in CONFIG_SECTIONS.items():
        if key in data['keys']:
            return section
    return None

def organize_by_sections(config: CommentedMap, defaults: CommentedMap) -> CommentedMap:
    """
    Organize configuration values by sections while preserving comments and structure.
    
    Args:
        config: The current configuration
        defaults: The default configuration with all values
        
    Returns:
        Organized configuration with proper sections
    """
    new_config = CommentedMap()
    current_section = None

    # Process each category in order
    for category in CONFIG_CATEGORIES:
        category_keys = get_category_keys(category)

        for section, section_data in CONFIG_SECTIONS.items():
            if section_data['category'] == category:
                section_header = section_data['header']
                
                # Add section header if we have keys to add
                section_keys = [key for key in category_keys if key in config or key in defaults]
                if section_keys:
                    if current_section != section:
                        if new_config:  # Add newline before new section
                            new_config.yaml_set_comment_before_after_key(
                                section_keys[0], 
                                before="\n" + section_header
                            )
                        else:  # First section
                            new_config.yaml_set_comment_before_after_key(
                                section_keys[0],
                                before=section_header
                            )
                        current_section = section

                    # Add keys from current section
                    for key in section_keys:
                        if key in config:
                            new_config[key] = config[key]
                        elif key in defaults:
                            new_config[key] = defaults[key]

    # Add any remaining keys that aren't in sections
    for key in config:
        if key not in new_config:
            new_config[key] = config[key]

    return new_config

def load_yaml_config(config_path: str) -> CommentedMap:
    """
    Load and validate configuration from a YAML file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        The loaded configuration as a CommentedMap
        
    Raises:
        ConfigLoadError: If the configuration cannot be loaded or is invalid
    """
    try:
        yaml = setup_yaml()
        
        # If file doesn't exist, create it with defaults
        if not os.path.exists(config_path):
            logging.info(f"Configuration file not found at {config_path}, creating new one")
            config = create_default_config()
            save_yaml_config(config, config_path)
            return config
        
        # Load existing configuration
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.load(file)
                
                if config is None:
                    config = create_default_config()
                elif not isinstance(config, (dict, CommentedMap)):
                    raise ConfigLoadError(f"Invalid config file format: {config_path}")
                
                # Get defaults and validate
                defaults = create_default_config()
                
                # Track original keys
                original_keys = set(config.keys())
                
                # Organize and update config
                organized_config = organize_by_sections(config, defaults)
                
                # Validate final configuration
                is_valid, errors = validate_config(organized_config)
                if not is_valid:
                    error_msg = "Configuration validation failed:\n" + "\n".join(errors)
                    logging.error(error_msg)
                    raise ConfigLoadError(error_msg)
                
                # Save if we made any changes
                if set(organized_config.keys()) != original_keys:
                    save_yaml_config(organized_config, config_path)
                
                return organized_config
                
        except (OSError, YAMLError) as e:
            raise ConfigLoadError(f"Error reading config file: {str(e)}") from e
            
    except (OSError, YAMLError) as e:
        error_msg = f"Failed to load configuration: {str(e)}"
        logging.error(error_msg)
        raise ConfigLoadError(error_msg) from e

def save_yaml_config(config: CommentedMap, config_path: str) -> None:
    """
    Save configuration to a YAML file while preserving structure and comments.
    
    Args:
        config: The configuration to save
        config_path: Path where to save the configuration
        
    Raises:
        ConfigSaveError: If the save operation fails
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Save with preserved formatting
        yaml = setup_yaml()
        with open(config_path, 'w', encoding='utf-8') as file:
            yaml.dump(config, file)
        logging.info(f"Configuration saved to {config_path}")
    except (OSError, YAMLError) as e:
        error_msg = f"Error saving configuration to {config_path}: {str(e)}"
        logging.error(error_msg)
        raise ConfigSaveError(error_msg) from e

def update_config_value(config: CommentedMap, key: str, value: Any) -> None:
    """
    Update a single configuration value while preserving structure and comments.
    Uses sanitizer for secure value processing.
    
    Args:
        config: The configuration to update
        key: The key to update
        value: The new value
        
    Raises:
        KeyError: If key doesn't exist in config
        ConfigurationError: If value fails sanitization
    """
    if key not in config:
        logging.warning(f"Attempted to update non-existent key: {key}")
        raise KeyError(f"Configuration key not found: {key}")

    try:
        # Use sanitizer to process the value securely
        sanitized_value = sanitize_config_value(key, value)
        
        # Special handling for string values that need to be quoted
        if isinstance(sanitized_value, str) and (key.endswith("_COLOR") or key == "FIXED_UPDATE_TIME"):
            config[key] = DoubleQuotedScalarString(sanitized_value)
        else:
            config[key] = sanitized_value
            
    except ConfigurationError as e:
        logging.error(f"Failed to sanitize value for {key}: {str(e)}")
        raise

def get_config_path(config_dir: Optional[str] = None) -> str:
    """
    Get the configuration file path.
    
    Args:
        config_dir: Optional configuration directory override
        
    Returns:
        The full path to the configuration file
    """
    if config_dir is None:
        config_dir = os.environ.get("CONFIG_DIR", "/config")
    return os.path.join(config_dir, "config.yml")

# Export public interface
__all__ = [
    'load_yaml_config',
    'save_yaml_config',
    'update_config_value',
    'get_config_path',
    'ConfigLoadError',
    'ConfigSaveError',
]
