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

    def get_config_value(self, key_path: str, default: object | None = None) -> object:
        """
        Get a specific configuration value using dot notation path with optional default.

        Args:
            key_path: Configuration key path using dot notation (e.g., "services.tautulli.api_key")
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default

        Raises:
            ConfigurationError: If key doesn't exist and no default provided
        """
        config = self.get_config()

        # Navigate nested configuration using dot notation
        keys = key_path.split(".")
        current: object = config

        try:
            for key in keys:
                if hasattr(current, key):
                    current = getattr(current, key)  # pyright: ignore[reportAny] # dynamic attribute access
                else:
                    if default is not None:
                        return default
                    raise ConfigurationError(
                        f"Configuration key '{key_path}' not found",
                        user_message=i18n.translate(
                            "Configuration setting `{key}` is not available.", key=key_path
                        ),
                    )
            return current
        except AttributeError:
            if default is not None:
                return default
            raise ConfigurationError(
                f"Configuration key '{key_path}' not found",
                user_message=i18n.translate(
                    "Configuration setting `{key}` is not available.", key=key_path
                ),
            )

    def validate_discord_channel(
        self, bot: discord.Client, channel_id: int | None = None
    ) -> discord.TextChannel:
        """
        Validate and retrieve a Discord text channel.

        Args:
            bot: Discord bot instance
            channel_id: Optional channel ID (uses config services.discord.channel_id if not provided)

        Returns:
            Discord TextChannel object

        Raises:
            ConfigurationError: If channel is invalid or not found
        """
        if channel_id is None:
            config = self.get_config()
            channel_id = config.services.discord.channel_id

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
            "time_range_days": config.data_collection.time_ranges.days,
            "keep_days": config.automation.data_retention.keep_days,
            "tv_color": config.graphs.appearance.colors.tv,
            "movie_color": config.graphs.appearance.colors.movie,
            "background_color": config.graphs.appearance.colors.background,
            "annotation_color": config.graphs.appearance.annotations.basic.color,
            "annotation_outline_color": config.graphs.appearance.annotations.basic.outline_color,
            "grid_enabled": config.graphs.appearance.grid.enabled,
            "enable_annotation_outline": config.graphs.appearance.annotations.basic.enable_outline,
            "censor_usernames": config.data_collection.privacy.censor_usernames,
        }

    def get_api_settings(self) -> dict[str, object]:
        """
        Get API-related configuration settings.

        Returns:
            Dictionary of API configuration settings
        """
        config = self.get_config()

        return {
            "tautulli_url": config.services.tautulli.url,
            "tautulli_api_key": config.services.tautulli.api_key,
            "discord_token": config.services.discord.token,
            "channel_id": config.services.discord.channel_id,
        }

    def is_graph_enabled(self, graph_type: str) -> bool:
        """
        Check if a specific graph type is enabled.

        Args:
            graph_type: Graph type to check (e.g., "daily_play_count", "top_10_users")

        Returns:
            True if graph type is enabled
        """
        # Map graph types to their nested configuration paths
        graph_type_mapping = {
            "DAILY_PLAY_COUNT": "graphs.features.enabled_types.daily_play_count",
            "PLAY_COUNT_BY_DAYOFWEEK": "graphs.features.enabled_types.play_count_by_dayofweek",
            "PLAY_COUNT_BY_HOUROFDAY": "graphs.features.enabled_types.play_count_by_hourofday",
            "TOP_10_PLATFORMS": "graphs.features.enabled_types.top_10_platforms",
            "TOP_10_USERS": "graphs.features.enabled_types.top_10_users",
            "PLAY_COUNT_BY_MONTH": "graphs.features.enabled_types.play_count_by_month",
        }

        config_path = graph_type_mapping.get(graph_type)
        if config_path is None:
            return False

        return bool(self.get_config_value(config_path, True))

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
