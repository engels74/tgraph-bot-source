"""
Configuration accessor utility for graph modules.

This module provides a centralized configuration access utility that handles
TGraphBotConfig objects, providing direct access to nested configuration
values using the new nested structure.
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
        Get a configuration value using nested path.

        Args:
            key: Configuration nested path (e.g., "graphs.appearance.colors.tv")
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default

        Raises:
            ConfigurationError: If key doesn't exist and no default provided
        """
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

        # For graph types that are in the configuration schema, use True as default
        # For graph types not in the schema (like sample_graph), use False as default
        # This prevents test/demo graphs from being enabled by default
        schema_graph_types = {
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "top_10_platforms",
            "top_10_users",
            "play_count_by_month",
            "daily_play_count_by_stream_type",
            "daily_concurrent_stream_count_by_stream_type",
            "play_count_by_source_resolution",
            "play_count_by_stream_resolution",
            "play_count_by_platform_and_stream_type",
            "play_count_by_user_and_stream_type",
        }

        # Check if the value is explicitly set in the configuration
        # This allows non-schema graph types to be enabled if explicitly configured
        try:
            # Try to get the value directly from the config without a default
            # This will raise ConfigurationError if the path doesn't exist
            value = self.get_nested_value(path)
            return bool(value)
        except ConfigurationError:
            # If the path doesn't exist, use the default based on whether it's in the schema
            default_value = graph_type in schema_graph_types
            return default_value

    def get_color_value(self, color_type: str) -> str:
        """
        Get a color configuration value.

        Args:
            color_type: Color type name (e.g., "tv", "movie", "background")

        Returns:
            Color value as hex string
        """
        path = f"graphs.appearance.colors.{color_type}"
        defaults = {"tv": "#1f77b4", "movie": "#ff7f0e", "background": "#ffffff"}
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
            "graphs.appearance",
        ]

        for section in required_sections:
            try:
                _ = self.get_nested_value(section)
            except ConfigurationError as e:
                raise ConfigurationError(
                    f"Configuration missing required section: {section}",
                    user_message=f"Configuration section `{section}` is required but missing.",
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
            "top_10_users",
            "daily_play_count_by_stream_type",
            "daily_concurrent_stream_count_by_stream_type",
            "play_count_by_source_resolution",
            "play_count_by_stream_resolution",
            "play_count_by_platform_and_stream_type",
            "play_count_by_user_and_stream_type",
        ]

        return {
            graph_type: self.is_graph_type_enabled(graph_type)
            for graph_type in graph_types
        }

    def get_per_graph_media_type_separation(self, graph_type: str) -> bool:
        """
        Get media type separation setting for a specific graph type.

        Args:
            graph_type: Graph type name (e.g., "daily_play_count", "top_10_users")

        Returns:
            True if media type separation is enabled for this graph type, False otherwise
        """
        # Valid graph types that have per-graph configuration
        valid_graph_types = {
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "top_10_platforms",
            "top_10_users",
            "play_count_by_month",
        }

        # For valid graph types, try per-graph setting first
        if graph_type in valid_graph_types:
            per_graph_path = f"graphs.per_graph.{graph_type}.media_type_separation"
            try:
                value = self.get_nested_value(per_graph_path)
                return bool(value)
            except ConfigurationError:
                pass  # Fall through to global setting

        # Fall back to global setting for unknown/test graph types
        global_path = "graphs.features.media_type_separation"
        return self.get_bool_value(global_path, default=True)

    def get_resolution_grouping_strategy(self, graph_type: str) -> str:
        """
        Get resolution grouping strategy for a specific graph type.

        Args:
            graph_type: Graph type name (e.g., "play_count_by_source_resolution", "play_count_by_stream_resolution")

        Returns:
            Resolution grouping strategy ("standard", "detailed", "simplified")
        """
        # Valid resolution graph types that have resolution grouping configuration
        valid_graph_types = {
            "play_count_by_source_resolution",
            "play_count_by_stream_resolution",
        }

        # For valid graph types, try per-graph setting
        if graph_type in valid_graph_types:
            per_graph_path = f"graphs.per_graph.{graph_type}.resolution_grouping"
            try:
                value = self.get_nested_value(per_graph_path)
                return str(value)
            except ConfigurationError:
                pass  # Fall through to default

        # Default to "standard" grouping strategy
        return "standard"

    def get_per_graph_stacked_bar_charts(self, graph_type: str) -> bool:
        """
        Get stacked bar charts setting for a specific graph type.

        Args:
            graph_type: Graph type name (e.g., "daily_play_count", "top_10_users")

        Returns:
            True if stacked bar charts are enabled for this graph type, False otherwise
        """
        # Valid graph types that have per-graph configuration
        valid_graph_types = {
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "top_10_platforms",
            "top_10_users",
            "play_count_by_month",
        }

        # For valid graph types, try per-graph setting first
        if graph_type in valid_graph_types:
            per_graph_path = f"graphs.per_graph.{graph_type}.stacked_bar_charts"
            try:
                value = self.get_nested_value(per_graph_path)
                return bool(value)
            except ConfigurationError:
                pass  # Fall through to global setting

        # Fall back to global setting for unknown/test graph types
        global_path = "graphs.features.stacked_bar_charts"
        return self.get_bool_value(global_path, default=False)
