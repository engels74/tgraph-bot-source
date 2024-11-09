# config/__init__.py

from .modules.constants import CONFIG_SECTIONS
from .modules.defaults import create_default_config
from .modules.loader import load_yaml_config, save_yaml_config
from .modules.options import (
    CONFIGURABLE_OPTIONS,
    RESTART_REQUIRED_KEYS
)
from .modules.sanitizer import sanitize_config_value
from .modules.validator import validate_config_value
from ruamel.yaml import YAML, YAMLError
from typing import Dict, Any, Optional, List
import logging
import os
import threading

# Get the CONFIG_DIR from environment variable, default to '/config' if not set
CONFIG_DIR = os.environ.get("CONFIG_DIR", "/config")

class ConfigError(Exception):
    """Base exception for configuration-related errors."""
    pass

class ConfigManager:
    """
    Thread-safe configuration manager for TGraph Bot.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file
            
        Raises:
            ValueError: If config_path is empty or None
        """
        if not config_path:
            raise ValueError("Configuration path cannot be empty")
            
        self.config_path = config_path
        self._config = None
        self._lock = threading.RLock()  # Use RLock for reentrant locking
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.width = 4096

    @property
    def config(self) -> Dict[str, Any]:
        """
        Get the current configuration. Loads it if not already loaded.
        Thread-safe access to configuration.
        
        Returns:
            The current configuration dictionary
            
        Raises:
            ConfigError: If configuration cannot be loaded
        """
        with self._lock:
            if self._config is None:
                self._config = self.load_config()
            return self._config

    def load_config(self, reload: bool = False) -> Dict[str, Any]:
        """
        Thread-safe loading of configuration from file.
        
        Args:
            reload: Force reload from disk if True
            
        Returns:
            The loaded configuration dictionary
            
        Raises:
            ConfigError: If configuration cannot be loaded or is invalid
        """
        with self._lock:
            try:
                if self._config is not None and not reload:
                    return self._config

                if not os.path.exists(self.config_path):
                    logging.info(f"Configuration file not found at {self.config_path}, creating new one")
                    self.create_default_config_file(self.config_path)

                self._config = load_yaml_config(self.config_path)
                return self._config
            except (FileNotFoundError, YAMLError) as e:
                logging.error(f"Failed to load configuration: {str(e)}")
                raise ConfigError(f"Configuration load failed: {str(e)}") from e

    def save_config(self) -> None:
        """
        Thread-safe saving of configuration to file.
        
        Raises:
            ConfigError: If configuration cannot be saved
        """
        with self._lock:
            try:
                if self._config is None:
                    raise ConfigError("Cannot save None configuration")
                save_yaml_config(self._config, self.config_path)
            except (IOError, YAMLError) as e:
                logging.error(f"Failed to save configuration: {str(e)}")
                raise ConfigError(f"Configuration save failed: {str(e)}") from e

    def update_value(self, key: str, value: Any, translations: Dict[str, str]) -> str:
        """
        Thread-safe update of a single configuration value.
        
        Args:
            key: The configuration key to update
            value: The new value to set
            translations: Translation dictionary for messages
            
        Returns:
            A message indicating the result of the update
            
        Raises:
            ConfigError: If the update fails
            ValueError: If key or translations are invalid
        """
        if not key or not translations:
            raise ValueError("Key and translations must not be empty")
            
        with self._lock:
            try:
                if key not in CONFIGURABLE_OPTIONS:
                    raise ConfigError(f"Invalid configuration key: {key}")

                old_value = self.config.get(key)  # Use get() to safely handle missing keys
                sanitized_value = sanitize_config_value(key, value)
                
                if not validate_config_value(key, sanitized_value):
                    raise ConfigError(f"Invalid value for {key}: {value}")
                    
                self.config[key] = sanitized_value
                self.save_config()
                
                if key == "FIXED_UPDATE_TIME" and str(sanitized_value).upper() == "XX:XX":
                    return translations.get("config_updated_fixed_time_disabled", "Configuration updated").format(key=key)
                    
                if key in RESTART_REQUIRED_KEYS:
                    return translations.get("config_updated_restart", "Configuration updated").format(key=key)
                    
                return translations.get("config_updated", "Configuration updated").format(
                    key=key,
                    old_value=old_value if old_value is not None else "N/A",
                    new_value=sanitized_value
                )
            except (ConfigError, ValueError, TypeError) as e:
                logging.error(f"Error updating config value: {str(e)}")
                raise ConfigError(f"Configuration update failed: {str(e)}") from e

    def get_configurable_options(self) -> List[str]:
        """
        Get list of configurable options. Thread-safe.
        
        Returns:
            List of configuration keys that can be modified via Discord
        """
        return list(CONFIGURABLE_OPTIONS)  # Return a copy to prevent modification

    @staticmethod
    def create_default_config_file(config_path: str) -> None:
        """
        Create a new configuration file with default values.
        Thread-safe as it's a static method operating on a new file.
        
        Args:
            config_path: Path where the configuration file should be created
            
        Raises:
            ConfigError: If default configuration cannot be created
            ValueError: If config_path is empty or None
        """
        if not config_path:
            raise ValueError("Configuration path cannot be empty")
            
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            config = create_default_config()
            save_yaml_config(config, config_path)
        except (IOError, YAMLError) as e:
            logging.error(f"Failed to create default configuration: {str(e)}")
            raise ConfigError(f"Default configuration creation failed: {str(e)}") from e

def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """
    Get or create a ConfigManager instance.
    
    Args:
        config_path: Optional path to configuration file. If not provided,
                     uses default path based on CONFIG_DIR
                     
    Returns:
        A ConfigManager instance
        
    Raises:
        ValueError: If CONFIG_DIR environment variable is not set and no config_path provided
    """
    if config_path is None:
        if not CONFIG_DIR:
            raise ValueError("CONFIG_DIR environment variable not set and no config_path provided")
        config_path = os.path.join(CONFIG_DIR, "config.yml")
    
    return ConfigManager(config_path)

# Export public interface
__all__ = [
    'load_yaml_config',
    'save_yaml_config',
    'validate_config_value',
    'sanitize_config_value',
    'create_default_config',
    'CONFIGURABLE_OPTIONS',
    'RESTART_REQUIRED_KEYS',
    'CONFIG_SECTIONS',
    'CONFIG_DIR',
    'ConfigError',
    'ConfigManager',
    'get_config_manager',
]
