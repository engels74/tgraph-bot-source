# config/modules/loader.py

"""
Configuration file loading and saving for TGraph Bot.
Handles YAML file operations with support for comments and formatting preservation.
Uses atomic file operations to prevent configuration corruption.
"""

from .constants import CONFIG_SECTIONS, get_category_keys, CONFIG_CATEGORIES
from .defaults import create_default_config
from .validator import validate_config
from .sanitizer import sanitize_config_value, SanitizerError
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLError
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from typing import Optional, Any
import logging
import os
import tempfile

class LoaderError(Exception):
    """Base exception for configuration loader errors."""
    pass

class ConfigFileError(LoaderError):
    """Raised when there are file operation errors."""
    pass

class ConfigFormatError(LoaderError):
    """Raised when there are YAML formatting or parsing errors."""
    pass

class ConfigValidationError(LoaderError):
    """Raised when configuration validation fails."""
    pass

class ConfigUpdateError(LoaderError):
    """Raised when configuration update operations fail."""
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
        
    Raises:
        ConfigFormatError: If configuration organization fails
    """
    try:
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
        
    except Exception as e:
        error_msg = f"Failed to organize configuration sections: {e}"
        logging.error(error_msg)
        raise ConfigFormatError(error_msg) from e

def load_yaml_config(config_path: str) -> CommentedMap:
    """
    Load and validate configuration from a YAML file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        The loaded configuration as a CommentedMap
        
    Raises:
        ConfigFileError: If file operations fail
        ConfigFormatError: If YAML parsing fails
        ConfigValidationError: If configuration validation fails
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
                    raise ConfigFormatError(f"Invalid config file format: {config_path}")
                
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
                    raise ConfigValidationError(error_msg)
                
                # Save if we made any changes
                if set(organized_config.keys()) != original_keys:
                    save_yaml_config(organized_config, config_path)
                
                return organized_config
                
        except (OSError, IOError) as e:
            raise ConfigFileError(f"Error reading config file: {str(e)}") from e
        except YAMLError as e:
            raise ConfigFormatError(f"Error parsing YAML: {str(e)}") from e
            
    except Exception as e:
        if isinstance(e, (ConfigFileError, ConfigFormatError, ConfigValidationError)):
            raise
        error_msg = f"Unexpected error loading configuration: {str(e)}"
        logging.error(error_msg)
        raise LoaderError(error_msg) from e

def save_yaml_config(config: CommentedMap, config_path: str) -> None:
    """
    Save configuration to a YAML file while preserving structure and comments.
    Uses atomic write operations with proper error handling.
    
    Args:
        config: The configuration to save
        config_path: Path where to save the configuration
        
    Raises:
        ConfigFileError: If file operations fail
        ConfigFormatError: If YAML formatting fails
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Create temporary file in same directory for atomic write
        config_dir = os.path.dirname(config_path)
        with tempfile.NamedTemporaryFile(mode='w', dir=config_dir, delete=False) as temp_file:
            try:
                # Save config to temporary file
                yaml = setup_yaml()
                yaml.dump(config, temp_file)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                
                # Atomic rename
                os.replace(temp_file.name, config_path)
                logging.info(f"Configuration saved to {config_path}")
                
            except YAMLError as e:
                os.unlink(temp_file.name)
                raise ConfigFormatError(f"Error formatting YAML: {str(e)}") from e
            except OSError as e:
                os.unlink(temp_file.name)
                raise ConfigFileError(f"Error during atomic save: {str(e)}") from e
            except Exception as e:
                os.unlink(temp_file.name)
                raise LoaderError(f"Unexpected error saving configuration: {str(e)}") from e
                
    except Exception as e:
        if isinstance(e, (ConfigFileError, ConfigFormatError)):
            raise
        error_msg = f"Failed to save configuration: {str(e)}"
        logging.error(error_msg)
        raise LoaderError(error_msg) from e

def update_config_value(config: CommentedMap, key: str, value: Any) -> None:
    """
    Update a single configuration value while preserving structure and comments.
    Uses sanitizer for secure value processing.
    
    Args:
        config: The configuration to update
        key: The key to update
        value: The new value
        
    Raises:
        ConfigUpdateError: If update operation fails
        ConfigValidationError: If new value fails validation
    """
    if key not in config:
        error_msg = f"Configuration key not found: {key}"
        logging.error(error_msg)
        raise ConfigUpdateError(error_msg)

    try:
        # Use sanitizer to process the value securely
        sanitized_value = sanitize_config_value(key, value)
        
        # Special handling for string values that need to be quoted
        if isinstance(sanitized_value, str) and (key.endswith("_COLOR") or key == "FIXED_UPDATE_TIME"):
            config[key] = DoubleQuotedScalarString(sanitized_value)
        else:
            config[key] = sanitized_value
            
    except SanitizerError as e:
        error_msg = f"Failed to sanitize value for {key}: {str(e)}"
        logging.error(error_msg)
        raise ConfigValidationError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error updating configuration value: {str(e)}"
        logging.error(error_msg)
        raise ConfigUpdateError(error_msg) from e

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
    'LoaderError',
    'ConfigFileError', 
    'ConfigFormatError',
    'ConfigValidationError',
    'ConfigUpdateError',
]
