"""
Configuration accessor utility for graph modules.

This module provides a centralized configuration access utility that handles
TGraphBotConfig objects, providing direct access to nested configuration
values without backwards compatibility.
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

    This class provides type-safe configuration access for TGraphBotConfig objects,
    working directly with the nested configuration structure.
    """

    def __init__(self, config: "TGraphBotConfig") -> None:
        """
        Initialize the configuration accessor.

        Args:
            config: TGraphBotConfig object with nested structure
        """
        self.config: "TGraphBotConfig" = config

    def _get_nested_path_for_flat_key(self, flat_key: str) -> str | None:
        """
        Map old flat configuration keys to new nested paths.

        Args:
            flat_key: Old flat configuration key

        Returns:
            Nested path for the key, or None if not found
        """
        # Map old flat keys to new nested paths
        path_mapping = {
            # Service configuration
            "TAUTULLI_API_KEY": "services.tautulli.api_key",
            "TAUTULLI_URL": "services.tautulli.url",
            "DISCORD_TOKEN": "services.discord.token",
            "CHANNEL_ID": "services.discord.channel_id",
            
            # Automation configuration
            "UPDATE_DAYS": "automation.scheduling.update_days",
            "FIXED_UPDATE_TIME": "automation.scheduling.fixed_update_time",
            "KEEP_DAYS": "automation.data_retention.keep_days",
            
            # Data collection configuration
            "TIME_RANGE_DAYS": "data_collection.time_ranges.days",
            "TIME_RANGE_MONTHS": "data_collection.time_ranges.months",
            "CENSOR_USERNAMES": "data_collection.privacy.censor_usernames",
            
            # System configuration
            "LANGUAGE": "system.localization.language",
            
            # Graph features configuration
            "ENABLE_DAILY_PLAY_COUNT": "graphs.features.enabled_types.daily_play_count",
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": "graphs.features.enabled_types.play_count_by_dayofweek",
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY": "graphs.features.enabled_types.play_count_by_hourofday",
            "ENABLE_TOP_10_PLATFORMS": "graphs.features.enabled_types.top_10_platforms",
            "ENABLE_TOP_10_USERS": "graphs.features.enabled_types.top_10_users",
            "ENABLE_PLAY_COUNT_BY_MONTH": "graphs.features.enabled_types.play_count_by_month",
            "ENABLE_MEDIA_TYPE_SEPARATION": "graphs.features.media_type_separation",
            "ENABLE_STACKED_BAR_CHARTS": "graphs.features.stacked_bar_charts",
            
            # Graph appearance configuration
            "GRAPH_WIDTH": "graphs.appearance.dimensions.width",
            "GRAPH_HEIGHT": "graphs.appearance.dimensions.height",
            "GRAPH_DPI": "graphs.appearance.dimensions.dpi",
            "TV_COLOR": "graphs.appearance.colors.tv",
            "MOVIE_COLOR": "graphs.appearance.colors.movie",
            "GRAPH_BACKGROUND_COLOR": "graphs.appearance.colors.background",
            "ENABLE_GRAPH_GRID": "graphs.appearance.grid.enabled",
            
            # Annotation configuration
            "ANNOTATION_COLOR": "graphs.appearance.annotations.basic.color",
            "ANNOTATION_OUTLINE_COLOR": "graphs.appearance.annotations.basic.outline_color",
            "ENABLE_ANNOTATION_OUTLINE": "graphs.appearance.annotations.basic.enable_outline",
            "ANNOTATION_FONT_SIZE": "graphs.appearance.annotations.basic.font_size",
            "ANNOTATE_DAILY_PLAY_COUNT": "graphs.appearance.annotations.enabled_on.daily_play_count",
            "ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK": "graphs.appearance.annotations.enabled_on.play_count_by_dayofweek",
            "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY": "graphs.appearance.annotations.enabled_on.play_count_by_hourofday",
            "ANNOTATE_TOP_10_PLATFORMS": "graphs.appearance.annotations.enabled_on.top_10_platforms",
            "ANNOTATE_TOP_10_USERS": "graphs.appearance.annotations.enabled_on.top_10_users",
            "ANNOTATE_PLAY_COUNT_BY_MONTH": "graphs.appearance.annotations.enabled_on.play_count_by_month",
            
            # Peak annotations (if they exist in schema)
            "ENABLE_PEAK_ANNOTATIONS": "graphs.appearance.annotations.peaks.enabled",
            "PEAK_ANNOTATION_COLOR": "graphs.appearance.annotations.peaks.color",
            "PEAK_ANNOTATION_TEXT_COLOR": "graphs.appearance.annotations.peaks.text_color",
            
            # Palette configuration
            "DAILY_PLAY_COUNT_PALETTE": "graphs.appearance.palettes.daily_play_count",
            "PLAY_COUNT_BY_DAYOFWEEK_PALETTE": "graphs.appearance.palettes.play_count_by_dayofweek",
            "PLAY_COUNT_BY_HOUROFDAY_PALETTE": "graphs.appearance.palettes.play_count_by_hourofday",
            "TOP_10_PLATFORMS_PALETTE": "graphs.appearance.palettes.top_10_platforms",
            "TOP_10_USERS_PALETTE": "graphs.appearance.palettes.top_10_users",
            "PLAY_COUNT_BY_MONTH_PALETTE": "graphs.appearance.palettes.play_count_by_month",
        }
        
        return path_mapping.get(flat_key)

    @overload
    def get_value(self, key: str, default: T) -> T:
        """Get configuration value with typed default (handles both flat keys and nested paths)."""
        ...

    @overload
    def get_value(self, key: str) -> object:
        """Get configuration value without default (handles both flat keys and nested paths)."""
        ...

    def get_value(self, key: str, default: T | None = None) -> T | object:
        """
        Get a configuration value using either flat key or nested path.

        This method provides backwards compatibility by accepting both old flat keys
        and new nested paths.

        Args:
            key: Configuration key (flat key like "TV_COLOR" or nested path like "graphs.appearance.colors.tv")
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default

        Raises:
            ConfigurationError: If key doesn't exist and no default provided
        """
        # First, try to map flat key to nested path
        nested_path = self._get_nested_path_for_flat_key(key)
        if nested_path is not None:
            # It's a flat key, use the mapped nested path
            return self.get_nested_value(nested_path, default)
        else:
            # Assume it's already a nested path
            return self.get_nested_value(key, default)

    @overload
    def get_nested_value(self, path: str, default: T) -> T:
        """Get nested configuration value with typed default."""
        ...

    @overload
    def get_nested_value(self, path: str) -> object:
        """Get nested configuration value without default."""
        ...

    def get_nested_value(self, path: str, default: T | None = None) -> T | object:
        """
        Get a nested configuration value using dot notation path.

        Args:
            path: Dot-separated path to configuration value (e.g., "graphs.appearance.colors.tv")
            default: Default value if path doesn't exist

        Returns:
            Configuration value or default

        Raises:
            ConfigurationError: If path doesn't exist and no default provided
        """
        try:
            current: object = self.config
            for part in path.split("."):
                current = getattr(current, part)  # pyright: ignore[reportAny]
            return current
        except AttributeError:
            if default is not None:
                return default
            else:
                raise ConfigurationError(
                    f"Configuration path '{path}' not found",
                    user_message=f"Configuration setting `{path}` is not available.",
                ) from None

    def get_bool_value(self, path: str, default: bool = True) -> bool:
        """
        Get a boolean configuration value.

        Args:
            path: Dot-separated path to configuration value
            default: Default boolean value if path doesn't exist

        Returns:
            Boolean configuration value
        """
        value = self.get_nested_value(path, default)
        return bool(value)

    def get_int_value(self, path: str, default: int) -> int:
        """
        Get an integer configuration value with safe conversion.

        Args:
            path: Dot-separated path to configuration value
            default: Default integer value if path doesn't exist or conversion fails

        Returns:
            Integer configuration value
        """
        try:
            raw_value = self.get_nested_value(path)
            if raw_value is None:
                return default
            return int(raw_value)  # pyright: ignore[reportArgumentType]
        except (ConfigurationError, ValueError, TypeError):
            logger.warning(
                f"Could not get or convert config value '{path}' to int, using default: {default}"
            )
            return default

    def get_str_value(self, path: str, default: str) -> str:
        """
        Get a string configuration value.

        Args:
            path: Dot-separated path to configuration value
            default: Default string value if path doesn't exist

        Returns:
            String configuration value
        """
        value = self.get_nested_value(path, default)
        return str(value)

    def get_graph_dimensions(self) -> dict[str, int]:
        """
        Get graph dimension configuration values.

        Returns:
            Dictionary containing width, height, and dpi values
        """
        width = self.get_int_value("graphs.appearance.dimensions.width", 12)
        height = self.get_int_value("graphs.appearance.dimensions.height", 8)
        dpi = self.get_int_value("graphs.appearance.dimensions.dpi", 100)

        return {
            "width": width,
            "height": height,
            "dpi": dpi,
        }

    def is_graph_type_enabled(self, graph_type: str) -> bool:
        """
        Check if a specific graph type is enabled.

        Args:
            graph_type: Graph type name (e.g., "daily_play_count", "top_10_users")

        Returns:
            True if graph type is enabled, False otherwise
        """
        path = f"graphs.features.enabled_types.{graph_type}"
        return self.get_bool_value(path, default=True)

    def get_color_value(self, color_type: str) -> str:
        """
        Get a color configuration value.

        Args:
            color_type: Color type name (e.g., "tv", "movie", "background")

        Returns:
            Color value as hex string
        """
        path = f"graphs.appearance.colors.{color_type}"
        defaults = {
            "tv": "#1f77b4",
            "movie": "#ff7f0e", 
            "background": "#ffffff"
        }
        return self.get_str_value(path, defaults.get(color_type, "#000000"))

    def get_palette_value(self, graph_type: str) -> str:
        """
        Get a palette configuration value for a specific graph type.

        Args:
            graph_type: Graph type name (e.g., "daily_play_count", "top_10_users")

        Returns:
            Palette name or empty string for default
        """
        path = f"graphs.appearance.palettes.{graph_type}"
        return self.get_str_value(path, "")

    def is_annotation_enabled(self, graph_type: str) -> bool:
        """
        Check if annotations are enabled for a specific graph type.

        Args:
            graph_type: Graph type name (e.g., "daily_play_count", "top_10_users")

        Returns:
            True if annotations are enabled, False otherwise
        """
        path = f"graphs.appearance.annotations.enabled_on.{graph_type}"
        return self.get_bool_value(path, default=True)

    def validate_config(self) -> None:
        """
        Validate that the configuration object has required nested structure.

        Raises:
            ConfigurationError: If configuration is missing required sections
        """
        required_sections = [
            "services.tautulli",
            "services.discord",
            "graphs.features",
            "graphs.appearance"
        ]
        
        for section in required_sections:
            try:
                _ = self.get_nested_value(section)
            except ConfigurationError as e:
                raise ConfigurationError(
                    f"Configuration missing required section: {section}",
                    user_message=f"Configuration section `{section}` is required but missing."
                ) from e

    def get_all_enabled_graph_types(self) -> dict[str, bool]:
        """
        Get all graph type enable states.

        Returns:
            Dictionary mapping graph type names to their enabled status
        """
        graph_types = [
            "daily_play_count",
            "play_count_by_dayofweek", 
            "play_count_by_hourofday",
            "play_count_by_month",
            "top_10_platforms",
            "top_10_users"
        ]
        
        return {
            graph_type: self.is_graph_type_enabled(graph_type)
            for graph_type in graph_types
        }

    def get_graph_enable_value(self, graph_type_key: str, default: bool = True) -> bool:
        """
        Get the enable status for a specific graph type using old flat key format.

        DEPRECATED: Use is_graph_type_enabled() with proper graph type names instead.

        Args:
            graph_type_key: Old flat graph enable key (e.g., "ENABLE_DAILY_PLAY_COUNT")
            default: Default value if key doesn't exist

        Returns:
            True if graph type is enabled, False otherwise
        """
        # Map old enable keys to new graph type names
        enable_key_mapping = {
            "ENABLE_DAILY_PLAY_COUNT": "daily_play_count",
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": "play_count_by_dayofweek",
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY": "play_count_by_hourofday",
            "ENABLE_PLAY_COUNT_BY_MONTH": "play_count_by_month",
            "ENABLE_TOP_10_PLATFORMS": "top_10_platforms",
            "ENABLE_TOP_10_USERS": "top_10_users",
            "ENABLE_SAMPLE_GRAPH": "sample_graph",  # Special case
        }
        
        graph_type = enable_key_mapping.get(graph_type_key)
        if graph_type is None:
            # Unknown key, return default
            return default
            
        if graph_type == "sample_graph":
            # Sample graph is not in main config, default to False
            return False
            
        return self.is_graph_type_enabled(graph_type)