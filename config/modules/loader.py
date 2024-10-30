# config/modules/loader.py

"""
Configuration file loading and saving for TGraph Bot.
Handles YAML file operations with support for comments and formatting preservation.
"""

import os
import logging
from typing import Optional, Any
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from .defaults import create_default_config
from .validator import validate_config
from .constants import CONFIG_SECTIONS

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

def add_missing_values(config: CommentedMap, defaults: CommentedMap) -> None:
    """
    Add missing values to config while maintaining section order and formatting.
    
    Args:
        config: The current configuration
        defaults: The default configuration with all values
    """
    new_config = CommentedMap()
    current_section = None

    # Process each section in order
    for section, section_data in CONFIG_SECTIONS.items():
        section_keys_added = False

        for key in section_data['keys']:
            # Add the key from either config or defaults
            if key in config:
                if not section_keys_added:
                    if current_section != section:
                        if new_config:  # Add newline before new section
                            new_config.yaml_set_comment_before_after_key(key, before="\n" + section_data['header'])
                        else:  # First section
                            new_config.yaml_set_comment_before_after_key(key, before=section_data['header'])
                        current_section = section
                    section_keys_added = True
                new_config[key] = config[key]
            elif key in defaults:
                if not section_keys_added:
                    if current_section != section:
                        if new_config:  # Add newline before new section
                            new_config.yaml_set_comment_before_after_key(key, before="\n" + section_data['header'])
                        else:  # First section
                            new_config.yaml_set_comment_before_after_key(key, before=section_data['header'])
                        current_section = section
                    section_keys_added = True
                new_config[key] = defaults[key]

    # Add any remaining keys that aren't in sections
    for key in config:
        if key not in new_config:
            new_config[key] = config[key]

    # Clear and update the original config
    config.clear()
    config.update(new_config)

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
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.load(file)
            
            if config is None:
                config = create_default_config()
            elif not isinstance(config, (dict, CommentedMap)):
                raise ConfigLoadError(f"Invalid config file format: {config_path}")
            
            # Get defaults
            defaults = create_default_config()
            
            # Track if we had missing values
            original_keys = set(config.keys())
            
            # Add any missing values while maintaining structure
            add_missing_values(config, defaults)
            
            # Validate configuration
            is_valid, errors = validate_config(config)
            if not is_valid:
                error_msg = "Configuration validation failed:\n" + "\n".join(errors)
                logging.error(error_msg)
                raise ConfigLoadError(error_msg)
            
            # Save if we added any missing values
            if set(config.keys()) != original_keys:
                save_yaml_config(config, config_path)
            
            return config
            
    except Exception as e:
        error_msg = f"Unexpected error loading configuration: {str(e)}"
        logging.error(error_msg)
        raise ConfigLoadError(error_msg) from e

def save_yaml_config(config: CommentedMap, config_path: str) -> None:
    """
    Save configuration to a YAML file while preserving structure and comments.
    
    Args:
        config: The configuration to save
        config_path: Path where to save the configuration
    """
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        yaml = setup_yaml()
        with open(config_path, 'w', encoding='utf-8') as file:
            yaml.dump(config, file)
        logging.info(f"Configuration saved to {config_path}")
    except Exception as e:
        error_msg = f"Error saving configuration to {config_path}: {str(e)}"
        logging.error(error_msg)
        raise ConfigSaveError(error_msg) from e

def update_config_value(config: CommentedMap, key: str, value: Any) -> None:
    """
    Update a single configuration value while preserving structure and comments.
    
    Args:
        config: The configuration to update
        key: The key to update
        value: The new value
    """
    if key in config:
        if isinstance(value, bool):
            config[key] = value
        elif isinstance(value, str) and (key.endswith("_COLOR") or key == "FIXED_UPDATE_TIME"):
            config[key] = DoubleQuotedScalarString(value.strip('"\''))
        else:
            config[key] = value
    else:
        logging.warning(f"Attempted to update non-existent key: {key}")

def get_config_path(config_dir: Optional[str] = None) -> str:
    """Get the configuration file path."""
    if config_dir is None:
        config_dir = os.environ.get("CONFIG_DIR", "/config")
    return os.path.join(config_dir, "config.yml")
