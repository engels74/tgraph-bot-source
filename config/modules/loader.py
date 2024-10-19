# config/modules/loader.py

"""
Configuration file loading and saving for TGraph Bot.
Handles YAML file operations with support for comments and formatting preservation.
"""

import os
import logging
from typing import Optional
from ruamel.yaml import YAML, YAMLError
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from .defaults import create_default_config, merge_with_defaults
from .validator import validate_config

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
    yaml.explicit_start = False
    return yaml

def load_yaml_config(config_path: str) -> CommentedMap:
    """
    Load and validate configuration from a YAML file.
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
                    logging.warning(f"Empty config file: {config_path}")
                    config = create_default_config()
                elif not isinstance(config, (dict, CommentedMap)):
                    raise ConfigLoadError(f"Invalid config file format: {config_path}")
                
                # Merge with defaults while preserving structure
                config = merge_with_defaults(config)
                
                # Validate configuration
                is_valid, errors = validate_config(config)
                if not is_valid:
                    error_msg = "Configuration validation failed:\n" + "\n".join(errors)
                    logging.error(error_msg)
                    raise ConfigLoadError(error_msg)
                
                # Update values while preserving structure
                update_config_values(config)
                
                return config
                
        except YAMLError as e:
            error_msg = f"Error parsing YAML configuration: {str(e)}"
            logging.error(error_msg)
            raise ConfigLoadError(error_msg)
            
    except Exception as e:
        error_msg = f"Unexpected error loading configuration: {str(e)}"
        logging.error(error_msg)
        raise ConfigLoadError(error_msg)

def update_config_values(config: CommentedMap) -> None:
    """
    Update configuration values while preserving structure.
    
    Args:
        config: Configuration to update
    """
    for key, value in config.items():
        if isinstance(value, bool):
            config[key] = value  # ruamel.yaml will handle lowercase conversion
        elif key.endswith("_COLOR") or key == "FIXED_UPDATE_TIME":
            if isinstance(value, str):
                config[key] = DoubleQuotedScalarString(value.strip('"\''))
        elif key == "CHANNEL_ID":
            if isinstance(value, str):
                config[key] = value.strip('"\'')

def save_yaml_config(config: CommentedMap, config_path: str) -> None:
    """Save configuration to a YAML file."""
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        yaml = setup_yaml()
        
        with open(config_path, 'w', encoding='utf-8') as file:
            yaml.dump(config, file)
            
        logging.info(f"Configuration saved to {config_path}")
        
    except Exception as e:
        error_msg = f"Error saving configuration to {config_path}: {str(e)}"
        logging.error(error_msg)
        raise ConfigSaveError(error_msg)

def get_config_path(config_dir: Optional[str] = None) -> str:
    """Get the configuration file path."""
    if config_dir is None:
        config_dir = os.environ.get("CONFIG_DIR", "/config")
    return os.path.join(config_dir, "config.yml")
