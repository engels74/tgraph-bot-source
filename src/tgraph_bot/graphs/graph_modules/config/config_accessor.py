"""
Configuration accessor utility for graph modules.

This module provides a centralized configuration access utility that handles
both dict and TGraphBotConfig objects, eliminating code duplication in
GraphFactory and other graph-related modules.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeVar, final, overload

from ....utils.core.exceptions import ConfigurationError

if TYPE_CHECKING:
    from ....config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


@final
class ConfigAccessor:
    """
    Centralized configuration access utility for graph modules.

    This class provides type-safe configuration access for both dict and
    TGraphBotConfig objects, eliminating the need for duplicated configuration
    access logic throughout the graph modules.
    """

    def __init__(self, config: "TGraphBotConfig | dict[str, object]") -> None:
        """
        Initialize the configuration accessor.

        Args:
            config: Configuration object (either TGraphBotConfig or dict)
        """
        self.config: "TGraphBotConfig | dict[str, object]" = config

    def _get_nested_value(self, key: str) -> object | None:
        """
        Get value from nested TGraphBotConfig structure using old flat key names.

        Args:
            key: Old flat configuration key

        Returns:
            Configuration value or None if not found
        """
        if isinstance(self.config, dict):
            return None

        if not hasattr(self.config, "services"):
            return None

        # Map old flat keys to nested paths - check for nested structure
        config = self.config
        if not (hasattr(config, "graphs") and hasattr(config.graphs, "appearance")):
            return None

        # Service configuration
        if key == "TAUTULLI_API_KEY":
            return config.services.tautulli.api_key
        elif key == "TAUTULLI_URL":
            return config.services.tautulli.url
        elif key == "DISCORD_TOKEN":
            return config.services.discord.token
        elif key == "CHANNEL_ID":
            return config.services.discord.channel_id

        # Automation configuration
        elif key == "UPDATE_DAYS":
            return config.automation.scheduling.update_days
        elif key == "FIXED_UPDATE_TIME":
            return config.automation.scheduling.fixed_update_time
        elif key == "KEEP_DAYS":
            return config.automation.data_retention.keep_days

        # Data collection configuration
        elif key == "TIME_RANGE_DAYS":
            return config.data_collection.time_ranges.days
        elif key == "TIME_RANGE_MONTHS":
            return config.data_collection.time_ranges.months
        elif key == "CENSOR_USERNAMES":
            return config.data_collection.privacy.censor_usernames

        # System configuration
        elif key == "LANGUAGE":
            return config.system.localization.language

        # Graph features configuration
        elif key == "ENABLE_DAILY_PLAY_COUNT":
            return config.graphs.features.enabled_types.daily_play_count
        elif key == "ENABLE_PLAY_COUNT_BY_DAYOFWEEK":
            return config.graphs.features.enabled_types.play_count_by_dayofweek
        elif key == "ENABLE_PLAY_COUNT_BY_HOUROFDAY":
            return config.graphs.features.enabled_types.play_count_by_hourofday
        elif key == "ENABLE_TOP_10_PLATFORMS":
            return config.graphs.features.enabled_types.top_10_platforms
        elif key == "ENABLE_TOP_10_USERS":
            return config.graphs.features.enabled_types.top_10_users
        elif key == "ENABLE_PLAY_COUNT_BY_MONTH":
            return config.graphs.features.enabled_types.play_count_by_month
        elif key == "ENABLE_MEDIA_TYPE_SEPARATION":
            return config.graphs.features.media_type_separation
        elif key == "ENABLE_STACKED_BAR_CHARTS":
            return config.graphs.features.stacked_bar_charts

        # Graph appearance configuration
        elif key == "GRAPH_WIDTH":
            return config.graphs.appearance.dimensions.width
        elif key == "GRAPH_HEIGHT":
            return config.graphs.appearance.dimensions.height
        elif key == "GRAPH_DPI":
            return config.graphs.appearance.dimensions.dpi
        elif key == "TV_COLOR":
            return config.graphs.appearance.colors.tv
        elif key == "MOVIE_COLOR":
            return config.graphs.appearance.colors.movie
        elif key == "GRAPH_BACKGROUND_COLOR":
            return config.graphs.appearance.colors.background
        elif key == "ENABLE_GRAPH_GRID":
            return config.graphs.appearance.grid.enabled

        # Annotation configuration
        elif key == "ANNOTATION_COLOR":
            return config.graphs.appearance.annotations.basic.color
        elif key == "ANNOTATION_OUTLINE_COLOR":
            return config.graphs.appearance.annotations.basic.outline_color
        elif key == "ENABLE_ANNOTATION_OUTLINE":
            return config.graphs.appearance.annotations.basic.enable_outline
        elif key == "ANNOTATE_DAILY_PLAY_COUNT":
            return config.graphs.appearance.annotations.enabled_on.daily_play_count
        elif key == "ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK":
            return config.graphs.appearance.annotations.enabled_on.play_count_by_dayofweek
        elif key == "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY":
            return config.graphs.appearance.annotations.enabled_on.play_count_by_hourofday
        elif key == "ANNOTATE_TOP_10_PLATFORMS":
            return config.graphs.appearance.annotations.enabled_on.top_10_platforms
        elif key == "ANNOTATE_TOP_10_USERS":
            return config.graphs.appearance.annotations.enabled_on.top_10_users
        elif key == "ANNOTATE_PLAY_COUNT_BY_MONTH":
            return config.graphs.appearance.annotations.enabled_on.play_count_by_month

        # Palette configuration
        elif key == "DAILY_PLAY_COUNT_PALETTE":
            return config.graphs.appearance.palettes.daily_play_count
        elif key == "PLAY_COUNT_BY_DAYOFWEEK_PALETTE":
            return config.graphs.appearance.palettes.play_count_by_dayofweek
        elif key == "PLAY_COUNT_BY_HOUROFDAY_PALETTE":
            return config.graphs.appearance.palettes.play_count_by_hourofday
        elif key == "TOP_10_PLATFORMS_PALETTE":
            return config.graphs.appearance.palettes.top_10_platforms
        elif key == "TOP_10_USERS_PALETTE":
            return config.graphs.appearance.palettes.top_10_users
        elif key == "PLAY_COUNT_BY_MONTH_PALETTE":
            return config.graphs.appearance.palettes.play_count_by_month

        return None

    @overload
    def get_value(self, key: str, default: T) -> T:
        """Get configuration value with typed default."""
        ...

    @overload
    def get_value(self, key: str) -> object:
        """Get configuration value without default."""
        ...

    def get_value(self, key: str, default: T | None = None) -> T | object:
        """
        Get a configuration value with optional default.

        Args:
            key: Configuration key to retrieve
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default

        Raises:
            ConfigurationError: If key doesn't exist and no default provided
        """
        if isinstance(self.config, dict):
            if default is not None:
                return self.config.get(key, default)
            elif key in self.config:
                return self.config[key]
            else:
                raise ConfigurationError(
                    f"Configuration key '{key}' not found in dict config",
                    user_message=f"Configuration setting `{key}` is not available.",
                )
        else:
            # TGraphBotConfig object - map old flat keys to nested paths
            nested_value = self._get_nested_value(key)
            if nested_value is not None:
                return nested_value
            elif default is not None:
                return default
            else:
                raise ConfigurationError(
                    f"Configuration key '{key}' not found in TGraphBotConfig",
                    user_message=f"Configuration setting `{key}` is not available.",
                )

    def get_bool_value(self, key: str, default: bool = True) -> bool:
        """
        Get a boolean configuration value.

        Args:
            key: Configuration key to retrieve
            default: Default boolean value if key doesn't exist

        Returns:
            Boolean configuration value
        """
        value = self.get_value(key, default)
        return bool(value)

    def get_int_value(self, key: str, default: int) -> int:
        """
        Get an integer configuration value with safe conversion.

        Args:
            key: Configuration key to retrieve
            default: Default integer value if key doesn't exist or conversion fails

        Returns:
            Integer configuration value
        """
        try:
            # Get the raw value without default to handle None case
            raw_value = self.get_value(key)
            if raw_value is None:
                return default
            return int(raw_value)  # pyright: ignore[reportArgumentType]
        except (ConfigurationError, ValueError, TypeError):
            # If key doesn't exist or conversion fails, use default
            logger.warning(
                f"Could not get or convert config value '{key}' to int, using default: {default}"
            )
            return default

    def get_graph_enable_value(self, graph_type: str, default: bool = True) -> bool:
        """
        Get the enable status for a specific graph type.

        Args:
            graph_type: Graph type key (e.g., "ENABLE_DAILY_PLAY_COUNT")
            default: Default value if key doesn't exist

        Returns:
            True if graph type is enabled, False otherwise
        """
        if isinstance(self.config, dict):
            return bool(self.config.get(graph_type, default))
        else:
            # Use direct attribute access for TGraphBotConfig objects
            # This handles the specific graph enable attributes
            if graph_type == "ENABLE_DAILY_PLAY_COUNT":
                return self.config.graphs.features.enabled_types.daily_play_count
            elif graph_type == "ENABLE_PLAY_COUNT_BY_DAYOFWEEK":
                return self.config.graphs.features.enabled_types.play_count_by_dayofweek
            elif graph_type == "ENABLE_PLAY_COUNT_BY_HOUROFDAY":
                return self.config.graphs.features.enabled_types.play_count_by_hourofday
            elif graph_type == "ENABLE_PLAY_COUNT_BY_MONTH":
                return self.config.graphs.features.enabled_types.play_count_by_month
            elif graph_type == "ENABLE_TOP_10_PLATFORMS":
                return self.config.graphs.features.enabled_types.top_10_platforms
            elif graph_type == "ENABLE_TOP_10_USERS":
                return self.config.graphs.features.enabled_types.top_10_users
            elif graph_type == "ENABLE_SAMPLE_GRAPH":
                # Sample graph is not in the main config schema, default to False
                return False
            else:
                # Fallback to generic attribute access
                return getattr(self.config, graph_type, default)

    def get_graph_dimensions(self) -> dict[str, int]:
        """
        Get graph dimension configuration values.

        Returns:
            Dictionary containing width, height, and dpi values
        """
        width = self.get_int_value("GRAPH_WIDTH", 12)
        height = self.get_int_value("GRAPH_HEIGHT", 8)
        dpi = self.get_int_value("GRAPH_DPI", 100)

        return {
            "width": width,
            "height": height,
            "dpi": dpi,
        }

    def is_dict_config(self) -> bool:
        """
        Check if the configuration is a dictionary.

        Returns:
            True if configuration is a dict, False if TGraphBotConfig
        """
        return isinstance(self.config, dict)

    def is_tgraph_config(self) -> bool:
        """
        Check if the configuration is a TGraphBotConfig object.

        Returns:
            True if configuration is TGraphBotConfig, False if dict
        """
        return not isinstance(self.config, dict)

    def validate_required_keys(self, keys: list[str]) -> None:
        """
        Validate that required configuration keys exist.

        Args:
            keys: List of required configuration keys

        Raises:
            ConfigurationError: If any required key is missing
        """
        missing_keys: list[str] = []

        for key in keys:
            try:
                _ = self.get_value(key)
            except ConfigurationError:
                missing_keys.append(key)

        if missing_keys:
            raise ConfigurationError(
                f"Missing required configuration keys: {missing_keys}",
                user_message=f"Required configuration settings are missing: {', '.join(missing_keys)}",
            )

    def get_all_graph_enable_keys(self) -> dict[str, bool]:
        """
        Get all graph enable configuration values.

        Returns:
            Dictionary mapping graph enable keys to their boolean values
        """
        graph_enable_keys = [
            "ENABLE_DAILY_PLAY_COUNT",
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK",
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY",
            "ENABLE_PLAY_COUNT_BY_MONTH",
            "ENABLE_TOP_10_PLATFORMS",
            "ENABLE_TOP_10_USERS",
            "ENABLE_SAMPLE_GRAPH",
        ]

        return {
            key: self.get_graph_enable_value(
                key, default=True if key != "ENABLE_SAMPLE_GRAPH" else False
            )
            for key in graph_enable_keys
        }
