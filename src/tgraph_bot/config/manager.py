"""Configuration manager for TGraph Bot.

This module provides functionality for loading, validating, and saving
YAML configuration files with Pydantic model validation and comment preservation.
"""

import logging
import tempfile
import threading
from pathlib import Path
from typing import Callable

import yaml
from pydantic import ValidationError

from ..config.schema import TGraphBotConfig


logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Configuration manager for handling YAML config files with Pydantic validation.

    Provides methods for loading, saving, and validating configuration files
    while preserving comments and ensuring atomic operations. Also supports
    live configuration management with change notifications.
    """

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        self._current_config: TGraphBotConfig | None = None
        self._config_lock: threading.RLock = threading.RLock()
        self._change_callbacks: list[
            Callable[[TGraphBotConfig, TGraphBotConfig], None]
        ] = []
        self._config_file_path: Path | None = None

    @staticmethod
    def load_config(config_path: Path) -> TGraphBotConfig:
        """
        Load and validate configuration from a YAML file.

        Args:
            config_path: Path to the YAML configuration file

        Returns:
            TGraphBotConfig: Validated configuration object

        Raises:
            FileNotFoundError: If the config file doesn't exist
            yaml.YAMLError: If the YAML syntax is invalid
            ValidationError: If the configuration fails Pydantic validation
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with config_path.open("r", encoding="utf-8") as f:
                raw_config_data: object = yaml.safe_load(f)  # pyright: ignore[reportAny]
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML syntax in {config_path}: {e}") from e

        if raw_config_data is None:
            config_data: dict[str, object] = {}
        elif isinstance(raw_config_data, dict):
            config_data = raw_config_data  # pyright: ignore[reportUnknownVariableType]
        else:
            raise ValueError(
                f"Configuration file must contain a YAML dictionary, got {type(raw_config_data).__name__}"
            )

        # Parse configuration using match statement for specific fields
        parsed_data = ConfigManager._parse_config_data(config_data)

        try:
            return TGraphBotConfig(**parsed_data)  # pyright: ignore[reportArgumentType]
        except ValidationError as e:
            # Re-raise the original ValidationError with additional context
            raise e

    @staticmethod
    def _parse_config_data(config_data: dict[str, object]) -> dict[str, object]:
        """
        Parse configuration data using match statements for specific fields.

        Args:
            config_data: Raw configuration data from YAML

        Returns:
            dict[str, Any]: Parsed configuration data
        """
        parsed_data = config_data.copy()

        # Parse specific fields using match statements as specified in requirements
        for key, value in config_data.items():
            match key:
                case "FIXED_UPDATE_TIME":
                    # Validate time format or XX:XX
                    match value:
                        case str() if value == "XX:XX":
                            parsed_data[key] = value
                        case str() if ":" in value:
                            # Let Pydantic handle time format validation
                            parsed_data[key] = value
                        case _:
                            parsed_data[key] = value

                case "LANGUAGE":
                    # Validate language code
                    match value:
                        case str() if len(value) == 2 and value.isalpha():
                            parsed_data[key] = value.lower()
                        case _:
                            parsed_data[key] = value

                case key if key.endswith("_COLOR"):
                    # Normalize color values to lowercase
                    match value:
                        case str() if value.startswith("#"):
                            parsed_data[key] = value.lower()
                        case _:
                            parsed_data[key] = value

                case _:
                    # No special parsing needed
                    parsed_data[key] = value

        return parsed_data

    @staticmethod
    def save_config(
        config: TGraphBotConfig, config_path: Path, preserve_comments: bool = True
    ) -> None:
        """
        Save configuration to a YAML file with atomic operation and comment preservation.

        Args:
            config: Configuration object to save
            config_path: Path where to save the configuration
            preserve_comments: Whether to preserve existing comments (default: True)

        Raises:
            OSError: If file operations fail
            yaml.YAMLError: If YAML serialization fails
        """
        config_dict = config.model_dump()

        if preserve_comments and config_path.exists():
            # Read original file to preserve comments
            original_content = config_path.read_text(encoding="utf-8")
            updated_content = ConfigManager._preserve_comments(
                original_content, config_dict
            )
            content_to_write = updated_content
        else:
            # Generate new YAML content without comment preservation
            content_to_write = yaml.dump(
                config_dict,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                indent=2,
            )

        # Atomic save operation using temporary file
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=config_path.parent,
                prefix=f".{config_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                _ = temp_file.write(content_to_write)
                temp_file.flush()
                temp_path = Path(temp_file.name)

            # Atomic move
            _ = temp_path.replace(config_path)

        except Exception as e:
            # Clean up temporary file if it exists
            if temp_file and Path(temp_file.name).exists():
                Path(temp_file.name).unlink(missing_ok=True)
            raise OSError(f"Failed to save configuration to {config_path}: {e}") from e

    @staticmethod
    def _preserve_comments(original_content: str, new_config: dict[str, object]) -> str:
        """
        Preserve comments from original YAML content while updating values.

        Args:
            original_content: Original YAML file content with comments
            new_config: New configuration values to update

        Returns:
            str: Updated YAML content with preserved comments
        """
        lines = original_content.split("\n")
        updated_lines: list[str] = []
        updated_keys: set[str] = set()

        for line in lines:
            stripped = line.strip()

            # Preserve comment-only lines and empty lines
            if not stripped or stripped.startswith("#"):
                updated_lines.append(line)
                continue

            # Check if line contains a configuration key
            if ":" in line:
                key_part = line.split(":")[0].strip()
                if key_part in new_config:
                    # Extract indentation and comment (only real comments, not values)
                    indent = line[: len(line) - len(line.lstrip())]
                    comment_part = ""

                    # Find actual comment (after the value, not within quotes)
                    colon_index = line.index(":")
                    value_part = line[colon_index + 1 :].strip()

                    # Look for comment that's not part of a quoted string
                    comment_index = -1
                    in_quotes = False
                    quote_char = None

                    for i, char in enumerate(value_part):
                        if char in ('"', "'") and (i == 0 or value_part[i - 1] != "\\"):
                            if not in_quotes:
                                in_quotes = True
                                quote_char = char
                            elif char == quote_char:
                                in_quotes = False
                                quote_char = None
                        elif char == "#" and not in_quotes:
                            comment_index = i
                            break

                    if comment_index >= 0:
                        comment_part = "  " + value_part[comment_index:]

                    # Format new value
                    new_value = new_config[key_part]
                    if new_value is None:
                        formatted_value = "null"
                    elif isinstance(new_value, str):
                        # Quote strings that start with # or contain spaces
                        if new_value.startswith("#") or " " in new_value:
                            formatted_value = f"'{new_value}'"
                        else:
                            formatted_value = new_value
                    elif isinstance(new_value, bool):
                        formatted_value = str(new_value).lower()
                    else:
                        formatted_value = str(new_value)

                    updated_line = (
                        f"{indent}{key_part}: {formatted_value}{comment_part}"
                    )
                    updated_lines.append(updated_line)
                    updated_keys.add(key_part)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        # Add any new keys that weren't in the original file
        for key, value in new_config.items():
            if key not in updated_keys:
                if value is None:
                    formatted_value = "null"
                elif isinstance(value, str):
                    # Quote strings that start with # or contain spaces
                    if value.startswith("#") or " " in value:
                        formatted_value = f"'{value}'"
                    else:
                        formatted_value = value
                elif isinstance(value, bool):
                    formatted_value = str(value).lower()
                else:
                    formatted_value = str(value)

                updated_lines.append(f"{key}: {formatted_value}")

        return "\n".join(updated_lines)

    @staticmethod
    def get_default_config() -> TGraphBotConfig:
        """
        Get a configuration object with default values.

        Returns:
            TGraphBotConfig: Configuration with default values

        Note:
            This creates a minimal config with placeholder values for required fields.
            Real configuration should be loaded from a proper config file.
        """
        default_data: dict[str, object] = {
            "TAUTULLI_API_KEY": "your_tautulli_api_key_here",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "your_discord_bot_token_here",
            "CHANNEL_ID": 123456789012345678,
        }

        return TGraphBotConfig(**default_data)  # pyright: ignore[reportArgumentType]

    @staticmethod
    def validate_config(config: TGraphBotConfig) -> bool:
        """
        Validate a configuration object.

        Args:
            config: Configuration object to validate

        Returns:
            bool: True if configuration is valid

        Raises:
            ValidationError: If configuration is invalid
        """
        # Re-validate the configuration by creating a new instance
        try:
            # model_dump() returns dict[str, Any] which is expected for Pydantic models
            _ = TGraphBotConfig(**config.model_dump())  # pyright: ignore[reportAny]
            return True
        except ValidationError:
            raise

    @staticmethod
    def create_sample_config(sample_path: Path) -> None:
        """
        Create a sample configuration file with all options and documentation.

        Args:
            sample_path: Path where to create the sample configuration file
        """
        sample_content = ConfigManager._generate_sample_content()

        _ = sample_path.parent.mkdir(parents=True, exist_ok=True)
        _ = sample_path.write_text(sample_content, encoding="utf-8")

    @staticmethod
    def _generate_sample_content() -> str:
        """
        Generate sample configuration file content with comprehensive documentation.

        Returns:
            str: Sample configuration file content
        """
        return """# TGraph Bot Configuration File
# This file contains all configuration options for the TGraph Discord bot.
# Copy this file to config.yml and modify the values as needed.

# ============================================================================
# Required Configuration (Set These First)
# ============================================================================

# Tautulli API key - Get this from Tautulli Settings > Web Interface > API
TAUTULLI_API_KEY: "your_tautulli_api_key_here"

# Tautulli base URL - Include the full URL with protocol and port
TAUTULLI_URL: "http://localhost:8181/api/v2"

# Discord bot token - Get this from Discord Developer Portal
DISCORD_TOKEN: "your_discord_bot_token_here"

# Discord channel ID where graphs will be posted
CHANNEL_ID: 123456789012345678

# ============================================================================
# Basic Bot Settings
# ============================================================================

# Number of days between automatic updates (1-365)
UPDATE_DAYS: 7

# Fixed time for updates in HH:MM format, or 'XX:XX' to disable
FIXED_UPDATE_TIME: 'XX:XX'

# Language code for internationalization (2-letter code)
LANGUAGE: en

# Number of days to keep generated graphs (1-365)
KEEP_DAYS: 7

# ============================================================================
# Data Collection Settings
# ============================================================================

# Time range in days for graph data (1-365)
TIME_RANGE_DAYS: 30

# Time range in months for monthly graph data (1-60)
TIME_RANGE_MONTHS: 12

# Whether to censor usernames in graphs
CENSOR_USERNAMES: true

# ============================================================================
# Graph Selection & Behavior
# ============================================================================

# Whether to separate Movies and TV Series in graphs
ENABLE_MEDIA_TYPE_SEPARATION: true

# Whether to use stacked bars when media type separation is enabled (applies to bar charts only)
ENABLE_STACKED_BAR_CHARTS: true

# Enable/disable specific graph types
ENABLE_DAILY_PLAY_COUNT: true
ENABLE_PLAY_COUNT_BY_DAYOFWEEK: true
ENABLE_PLAY_COUNT_BY_HOUROFDAY: true
ENABLE_TOP_10_PLATFORMS: true
ENABLE_TOP_10_USERS: true
ENABLE_PLAY_COUNT_BY_MONTH: true

# ============================================================================
# Visual Customization
# ============================================================================

# Base Graph Colors (Hex format: #RRGGBB)
# ----------------------------------------

# Color for TV shows in graphs
TV_COLOR: '#1f77b4'

# Color for movies in graphs
MOVIE_COLOR: '#ff7f0e'

# Background color for graphs
GRAPH_BACKGROUND_COLOR: '#ffffff'

# Whether to enable grid lines in graphs
ENABLE_GRAPH_GRID: false

# Annotation Settings (All Types)
# --------------------------------

# Basic annotation styling
ANNOTATION_COLOR: '#ff0000'
ANNOTATION_OUTLINE_COLOR: '#000000'
ENABLE_ANNOTATION_OUTLINE: true
ANNOTATION_FONT_SIZE: 10

# Enable/disable annotations on specific graph types
ANNOTATE_DAILY_PLAY_COUNT: true
ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK: true
ANNOTATE_PLAY_COUNT_BY_HOUROFDAY: true
ANNOTATE_TOP_10_PLATFORMS: true
ANNOTATE_TOP_10_USERS: true
ANNOTATE_PLAY_COUNT_BY_MONTH: true

# Peak annotation settings (separate from bar value annotations)
ENABLE_PEAK_ANNOTATIONS: true
PEAK_ANNOTATION_COLOR: '#ffcc00'
PEAK_ANNOTATION_TEXT_COLOR: '#000000'

# ============================================================================
# Performance & Rate Limiting
# ============================================================================

# Config Command Cooldowns
# -------------------------

# Per-user cooldown for config commands (0-1440 minutes)
CONFIG_COOLDOWN_MINUTES: 0

# Global cooldown for config commands (0-86400 seconds)
CONFIG_GLOBAL_COOLDOWN_SECONDS: 0

# Update Graphs Command Cooldowns
# --------------------------------

# Per-user cooldown for update graphs commands (0-1440 minutes)
UPDATE_GRAPHS_COOLDOWN_MINUTES: 0

# Global cooldown for update graphs commands (0-86400 seconds)
UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS: 0

# My Stats Command Cooldowns
# ---------------------------

# Per-user cooldown for my stats commands (0-1440 minutes)
MY_STATS_COOLDOWN_MINUTES: 5

# Global cooldown for my stats commands (0-86400 seconds)
MY_STATS_GLOBAL_COOLDOWN_SECONDS: 60
"""

    # Live Configuration Management Methods

    def set_current_config(self, config: TGraphBotConfig) -> None:
        """
        Set the current configuration.

        Args:
            config: Configuration object to set as current
        """
        with self._config_lock:
            old_config = self._current_config
            self._current_config = config

            # Notify callbacks of the change
            if old_config is not None:
                for callback in self._change_callbacks:
                    try:
                        callback(old_config, config)
                    except Exception as e:
                        logger.error(f"Error in config change callback: {e}")

    @property
    def config_file_path(self) -> Path | None:
        """
        Get the current config file path.

        Returns:
            Path to the current config file, or None if not set
        """
        return self._config_file_path

    @config_file_path.setter
    def config_file_path(self, path: Path | None) -> None:
        """
        Set the current config file path.

        Args:
            path: Path to the config file, or None to clear
        """
        self._config_file_path = path

    @config_file_path.deleter
    def config_file_path(self) -> None:
        """
        Clear the current config file path.
        """
        self._config_file_path = None

    def get_current_config(self) -> TGraphBotConfig:
        """
        Get the current configuration.

        Returns:
            TGraphBotConfig: The current configuration

        Raises:
            RuntimeError: If no configuration has been set
        """
        with self._config_lock:
            if self._current_config is None:
                raise RuntimeError(
                    "No configuration has been set. Call set_current_config() first."
                )
            return self._current_config

    def update_runtime_config(self, new_config: TGraphBotConfig) -> None:
        """
        Update the runtime configuration and notify callbacks.

        Args:
            new_config: The new configuration to apply
        """
        with self._config_lock:
            old_config = self._current_config
            self._current_config = new_config

            # Notify all registered callbacks
            if old_config is not None:
                for callback in self._change_callbacks:
                    try:
                        callback(old_config, new_config)
                    except Exception:
                        # Log error but don't let callback failures break config updates
                        pass

    def register_change_callback(
        self, callback: Callable[[TGraphBotConfig, TGraphBotConfig], None]
    ) -> None:
        """
        Register a callback to be called when configuration changes.

        Args:
            callback: Function to call with (old_config, new_config) when config changes
        """
        with self._config_lock:
            if callback not in self._change_callbacks:
                self._change_callbacks.append(callback)

    def unregister_change_callback(
        self, callback: Callable[[TGraphBotConfig, TGraphBotConfig], None]
    ) -> None:
        """
        Unregister a configuration change callback.

        Args:
            callback: The callback function to remove
        """
        with self._config_lock:
            if callback in self._change_callbacks:
                self._change_callbacks.remove(callback)
