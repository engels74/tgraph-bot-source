"""
Test helper utilities for TGraph Bot tests.

This module provides reusable utility functions and context managers for
common testing patterns, including configuration management, temporary file
handling, and resource cleanup.

All utilities are designed with type safety and proper error handling in mind.
"""

from __future__ import annotations

import tempfile
import yaml
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config.manager import ConfigManager
    from config.schema import TGraphBotConfig


def create_config_manager_with_config(config: TGraphBotConfig) -> ConfigManager:
    """
    Create a ConfigManager instance with a pre-configured TGraphBotConfig.
    
    This utility function eliminates the common pattern of creating a ConfigManager
    and then setting its current configuration. It provides a clean, type-safe way
    to create a configured manager for testing.
    
    Args:
        config: The TGraphBotConfig instance to set as the current configuration
        
    Returns:
        ConfigManager: A configured ConfigManager instance
        
    Raises:
        ImportError: If ConfigManager cannot be imported
        AttributeError: If ConfigManager doesn't have expected methods
        
    Example:
        >>> from tests.conftest import base_config
        >>> from tests.utils import create_config_manager_with_config
        >>> 
        >>> config = base_config()
        >>> manager = create_config_manager_with_config(config)
        >>> assert manager.get_current_config() == config
    """
    try:
        from config.manager import ConfigManager
    except ImportError as e:
        msg = f"Failed to import ConfigManager: {e}"
        raise ImportError(msg) from e
    
    try:
        manager = ConfigManager()
        manager.set_current_config(config)
        return manager
    except AttributeError as e:
        msg = f"ConfigManager missing expected methods: {e}"
        raise AttributeError(msg) from e


@contextmanager
def create_temp_config_file(
    config_data: dict[str, object] | None = None,
    *,
    suffix: str = ".yml",
    encoding: str = "utf-8",
) -> Generator[Path, None, None]:
    """
    Create a temporary configuration file with YAML content.
    
    This context manager creates a temporary file with configuration data
    in YAML format, yields the file path, and ensures cleanup on exit.
    It standardizes the pattern of creating temporary config files for testing.
    
    Args:
        config_data: Dictionary of configuration data to write to file.
                    If None, creates a minimal valid configuration.
        suffix: File suffix for the temporary file (default: ".yml")
        encoding: File encoding (default: "utf-8")
        
    Yields:
        Path: Path to the created temporary configuration file
        
    Raises:
        OSError: If file creation or writing fails
        yaml.YAMLError: If YAML serialization fails
        
    Example:
        >>> config_data = {
        ...     'TAUTULLI_API_KEY': 'test_key',
        ...     'TAUTULLI_URL': 'http://localhost:8181/api/v2',
        ...     'DISCORD_TOKEN': 'test_token',
        ...     'CHANNEL_ID': 123456789,
        ... }
        >>> with create_temp_config_file(config_data) as config_path:
        ...     # Use config_path for testing
        ...     assert config_path.exists()
        ...     # File is automatically cleaned up after context
    """
    if config_data is None:
        # Provide minimal valid configuration data
        config_data = {
            'TAUTULLI_API_KEY': 'test_api_key',
            'TAUTULLI_URL': 'http://localhost:8181/api/v2',
            'DISCORD_TOKEN': 'test_discord_token',
            'CHANNEL_ID': 123456789012345678,
        }
    
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=suffix,
            encoding=encoding,
            delete=False,
        ) as temp_file:
            try:
                yaml.dump(config_data, temp_file, default_flow_style=False)
                temp_path = Path(temp_file.name)
            except yaml.YAMLError as e:
                msg = f"Failed to serialize configuration data to YAML: {e}"
                raise yaml.YAMLError(msg) from e
        
        try:
            yield temp_path
        finally:
            # Ensure cleanup even if an exception occurs
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                # Ignore cleanup errors - file might already be deleted
                pass
                
    except OSError as e:
        msg = f"Failed to create temporary configuration file: {e}"
        raise OSError(msg) from e


@contextmanager
def create_temp_directory(
    *,
    prefix: str | None = None,
    suffix: str | None = None,
) -> Generator[Path, None, None]:
    """
    Create a temporary directory with automatic cleanup.
    
    This context manager creates a temporary directory, yields its path,
    and ensures complete cleanup on exit. It standardizes temporary directory
    creation patterns used across tests.
    
    Args:
        prefix: Optional prefix for the directory name
        suffix: Optional suffix for the directory name
        
    Yields:
        Path: Path to the created temporary directory
        
    Raises:
        OSError: If directory creation fails
        
    Example:
        >>> with create_temp_directory(prefix="test_graphs_") as temp_dir:
        ...     # Use temp_dir for testing
        ...     assert temp_dir.exists()
        ...     assert temp_dir.is_dir()
        ...     # Directory is automatically cleaned up after context
    """
    try:
        with tempfile.TemporaryDirectory(
            prefix=prefix,
            suffix=suffix,
        ) as temp_dir_str:
            temp_dir_path = Path(temp_dir_str)
            yield temp_dir_path
    except OSError as e:
        msg = f"Failed to create temporary directory: {e}"
        raise OSError(msg) from e
