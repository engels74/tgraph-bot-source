"""
Configuration utilities for TGraph Bot.

This module provides helper functions for configuration access, validation,
and common configuration-related operations to reduce code duplication
across the application.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeVar, final

import discord

from ... import i18n
from ...utils.core.exceptions import ConfigurationError

if TYPE_CHECKING:
    from ...config.manager import ConfigManager
    from ...config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


@final
class ConfigurationHelper:
    """
    Helper class for common configuration operations.

    Provides centralized configuration access patterns and validation
    to eliminate code duplication across command cogs and other modules.
    """

    def __init__(self, config_manager: "ConfigManager") -> None:
        """
        Initialize the configuration helper.

        Args:
            config_manager: The configuration manager instance
        """
        self.config_manager: "ConfigManager" = config_manager

    def get_config(self) -> "TGraphBotConfig":
        """
        Get the current configuration.

        Returns:
            Current configuration object
        """
        return self.config_manager.get_current_config()

    def get_config_value(self, key: str, default: object | None = None) -> object:
        """
        Get a specific configuration value with optional default.

        Args:
            key: Configuration key to retrieve
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default

        Raises:
            ConfigurationError: If key doesn't exist and no default provided
        """
        config = self.get_config()

        if hasattr(config, key):
            return getattr(config, key)  # pyright: ignore[reportAny]
        elif default is not None:
            return default
        else:
            raise ConfigurationError(
                f"Configuration key '{key}' not found",
                user_message=i18n.translate(
                    "Configuration setting `{key}` is not available.", key=key
                ),
            )

    def validate_discord_channel(
        self, bot: discord.Client, channel_id: int | None = None
    ) -> discord.TextChannel:
        """
        Validate and retrieve a Discord text channel.

        Args:
            bot: Discord bot instance
            channel_id: Optional channel ID (uses config CHANNEL_ID if not provided)

        Returns:
            Discord TextChannel object

        Raises:
            ConfigurationError: If channel is invalid or not found
        """
        if channel_id is None:
            config = self.get_config()
            channel_id = config.CHANNEL_ID

        channel = bot.get_channel(channel_id)

        if channel is None:
            raise ConfigurationError(
                f"Could not find Discord channel with ID: {channel_id}",
                user_message=i18n.translate(
                    "Could not find Discord channel with ID: {channel_id}. Please check the bot configuration.",
                    channel_id=channel_id,
                ),
            )

        if not isinstance(channel, discord.TextChannel):
            raise ConfigurationError(
                f"Channel {channel_id} is not a text channel",
                user_message=i18n.translate(
                    "Channel {channel_id} is not a text channel. Please configure a valid text channel.",
                    channel_id=channel_id,
                ),
            )

        return channel

    def get_cooldown_settings(self, command_prefix: str) -> tuple[int, int]:
        """
        Get cooldown settings for a specific command.

        Args:
            command_prefix: Command prefix (e.g., "UPDATE_GRAPHS", "MY_STATS")

        Returns:
            Tuple of (user_cooldown_seconds, global_cooldown_seconds)
        """
        config = self.get_config()

        # Get user cooldown (usually in minutes)
        user_cooldown_key = f"{command_prefix}_COOLDOWN_MINUTES"
        user_cooldown_minutes = getattr(config, user_cooldown_key, 0)
        user_cooldown_seconds = user_cooldown_minutes * 60

        # Get global cooldown (usually in seconds)
        global_cooldown_key = f"{command_prefix}_GLOBAL_COOLDOWN_SECONDS"
        global_cooldown_seconds = getattr(config, global_cooldown_key, 0)

        return user_cooldown_seconds, global_cooldown_seconds

    def validate_setting_exists(self, setting: str) -> bool:
        """
        Validate that a configuration setting exists.

        Args:
            setting: Setting name to validate

        Returns:
            True if setting exists

        Raises:
            ConfigurationError: If setting doesn't exist
        """
        config = self.get_config()

        if not hasattr(config, setting):
            raise ConfigurationError(
                f"Configuration setting '{setting}' does not exist",
                user_message=f"Configuration setting `{setting}` does not exist. Use `/config view` to see all available settings.",
            )

        return True

    def get_graph_settings(self) -> dict[str, object]:
        """
        Get all graph-related configuration settings.

        Returns:
            Dictionary of graph configuration settings
        """
        config = self.get_config()

        return {
            "time_range_days": config.TIME_RANGE_DAYS,
            "keep_days": config.KEEP_DAYS,
            "tv_color": config.TV_COLOR,
            "movie_color": config.MOVIE_COLOR,
            "background_color": config.GRAPH_BACKGROUND_COLOR,
            "annotation_color": config.ANNOTATION_COLOR,
            "annotation_outline_color": config.ANNOTATION_OUTLINE_COLOR,
            "grid_enabled": config.ENABLE_GRAPH_GRID,
            "enable_annotation_outline": config.ENABLE_ANNOTATION_OUTLINE,
            "censor_usernames": config.CENSOR_USERNAMES,
        }

    def get_api_settings(self) -> dict[str, object]:
        """
        Get API-related configuration settings.

        Returns:
            Dictionary of API configuration settings
        """
        config = self.get_config()

        return {
            "tautulli_url": config.TAUTULLI_URL,
            "tautulli_api_key": config.TAUTULLI_API_KEY,
            "discord_token": config.DISCORD_TOKEN,
            "channel_id": config.CHANNEL_ID,
        }

    def is_graph_enabled(self, graph_type: str) -> bool:
        """
        Check if a specific graph type is enabled.

        Args:
            graph_type: Graph type to check (e.g., "DAILY_PLAY_COUNT")

        Returns:
            True if graph type is enabled
        """
        config = self.get_config()
        enabled_key = f"{graph_type}_ENABLED"

        return getattr(config, enabled_key, False)

    def get_enabled_graphs(self) -> list[str]:
        """
        Get list of all enabled graph types.

        Returns:
            List of enabled graph type names
        """
        enabled_graphs: list[str] = []

        # List of all possible graph types
        graph_types = [
            "DAILY_PLAY_COUNT",
            "PLAY_COUNT_BY_DAYOFWEEK",
            "PLAY_COUNT_BY_HOUROFDAY",
            "TOP_10_PLATFORMS",
            "TOP_10_USERS",
            "PLAY_COUNT_BY_MONTH",
        ]

        for graph_type in graph_types:
            if self.is_graph_enabled(graph_type):
                enabled_graphs.append(graph_type)

        return enabled_graphs


def create_config_helper(config_manager: "ConfigManager") -> ConfigurationHelper:
    """
    Factory function to create a configuration helper.

    Args:
        config_manager: Configuration manager instance

    Returns:
        ConfigurationHelper instance
    """
    return ConfigurationHelper(config_manager)
