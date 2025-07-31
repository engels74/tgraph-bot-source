"""
Priority-based color and palette resolution system for TGraph Bot graphs.

This module provides centralized logic for resolving color schemes when both
media type separation and custom palette configurations are present, implementing
a priority system where custom palettes take precedence over media type colors.

The PaletteResolver eliminates configuration conflicts by providing:
- Priority-based color strategy resolution
- Centralized palette vs. separation decision logic
- Consistent color scheme application across all graph types
- Validation for palette and separation combinations

Priority System:
1. Highest Priority: Non-empty *_PALETTE configurations override everything
2. Medium Priority: ENABLE_MEDIA_TYPE_SEPARATION with MOVIE_COLOR/TV_COLOR
3. Lowest Priority: Default system colors

Usage Examples:
    Basic palette resolution:
        >>> resolver = PaletteResolver(config, config_accessor)
        >>> strategy = resolver.resolve_color_strategy("PlayCountByHourOfDayGraph")
        >>> if strategy.use_palette:
        ...     colors = strategy.palette_colors
        ... else:
        ...     colors = strategy.fallback_colors

    Check if palette should override separation:
        >>> if resolver.should_palette_override_separation("Top10UsersGraph"):
        ...     # Use palette instead of media type separation
        ...     pass

    Get effective color scheme:
        >>> colors = resolver.get_effective_colors("DailyPlayCountGraph")
        >>> # Returns either palette colors, separation colors, or defaults
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import TYPE_CHECKING, NamedTuple, final

from ..types.constants import DEFAULT_COLORS

if TYPE_CHECKING:
    from ....config.schema import TGraphBotConfig
    from ..config.config_accessor import ConfigAccessor


logger = logging.getLogger(__name__)


class ColorStrategy(Enum):
    """
    Available color strategy types for graph generation.
    """

    PALETTE = auto()  # Use custom seaborn palette
    SEPARATION = auto()  # Use media type separation colors
    DEFAULT = auto()  # Use default system colors


class ColorResolution(NamedTuple):
    """
    Result of color strategy resolution containing the strategy and color information.

    Attributes:
        strategy: The resolved color strategy to use
        use_palette: Whether to use a custom palette
        palette_name: Name of the palette if using palette strategy
        palette_colors: List of colors from the palette (if applicable)
        fallback_colors: Colors to use when palette is not available
        media_type_colors: Colors for media type separation (if applicable)
    """

    strategy: ColorStrategy
    use_palette: bool
    palette_name: str | None = None
    palette_colors: list[str] | None = None
    fallback_colors: list[str] | None = None
    media_type_colors: dict[str, str] | None = None


@final
class PaletteResolver:
    """
    Centralized resolver for color and palette priority decisions.

    This class implements the priority system where custom palettes take precedence
    over media type separation, providing consistent behavior across all graph types.
    """

    # Map graph class names to their corresponding palette configuration keys
    GRAPH_TYPE_TO_PALETTE_KEY: dict[str, str] = {
        "PlayCountByHourOfDayGraph": "graphs.appearance.palettes.play_count_by_hourofday",
        "Top10UsersGraph": "graphs.appearance.palettes.top_10_users",
        "DailyPlayCountGraph": "graphs.appearance.palettes.daily_play_count",
        "PlayCountByDayOfWeekGraph": "graphs.appearance.palettes.play_count_by_dayofweek",
        "Top10PlatformsGraph": "graphs.appearance.palettes.top_10_platforms",
        "PlayCountByMonthGraph": "graphs.appearance.palettes.play_count_by_month",
    }

    def __init__(
        self,
        config: "TGraphBotConfig | dict[str, object] | None" = None,
        config_accessor: "ConfigAccessor | None" = None,
    ) -> None:
        """
        Initialize the palette resolver.

        Args:
            config: Configuration object containing color and palette settings
            config_accessor: Accessor for configuration values
        """
        self.config: "TGraphBotConfig | dict[str, object] | None" = config
        self.config_accessor: "ConfigAccessor | None" = config_accessor

    def resolve_color_strategy(self, graph_type: str) -> ColorResolution:
        """
        Resolve the color strategy for a specific graph type.

        This is the main method that implements the priority system:
        1. Check if custom palette is configured and valid
        2. Check if media type separation is enabled
        3. Fall back to default colors

        Args:
            graph_type: The graph class name (e.g., "PlayCountByHourOfDayGraph")

        Returns:
            ColorResolution containing the strategy and color information
        """
        if self.config is None:
            return ColorResolution(
                strategy=ColorStrategy.DEFAULT,
                use_palette=False,
                fallback_colors=[DEFAULT_COLORS.TV_COLOR],
            )

        # Priority 1: Check for custom palette configuration
        palette_name = self._get_palette_for_graph_type(graph_type)
        if palette_name and self._is_valid_seaborn_palette(palette_name):
            palette_colors = self._get_palette_colors(palette_name)
            fallback_colors = self._get_fallback_colors()

            return ColorResolution(
                strategy=ColorStrategy.PALETTE,
                use_palette=True,
                palette_name=palette_name,
                palette_colors=palette_colors,
                fallback_colors=fallback_colors,
            )

        # Priority 2: Check for media type separation
        if self._is_media_type_separation_enabled():
            media_type_colors = self._get_media_type_colors()

            return ColorResolution(
                strategy=ColorStrategy.SEPARATION,
                use_palette=False,
                media_type_colors=media_type_colors,
                fallback_colors=list(media_type_colors.values())
                if media_type_colors
                else None,
            )

        # Priority 3: Default colors
        return ColorResolution(
            strategy=ColorStrategy.DEFAULT,
            use_palette=False,
            fallback_colors=[DEFAULT_COLORS.TV_COLOR],
        )

    def should_palette_override_separation(self, graph_type: str) -> bool:
        """
        Check if a custom palette should override media type separation for a graph type.

        Args:
            graph_type: The graph class name

        Returns:
            True if palette should take precedence over separation
        """
        palette_name = self._get_palette_for_graph_type(graph_type)
        return (
            palette_name is not None
            and palette_name.strip() != ""
            and self._is_valid_seaborn_palette(palette_name)
        )

    def get_effective_colors(self, graph_type: str) -> list[str]:
        """
        Get the effective color scheme to use for a graph type.

        This is a convenience method that resolves the strategy and returns
        the appropriate colors based on the priority system.

        Args:
            graph_type: The graph class name

        Returns:
            List of color strings to use for the graph
        """
        resolution = self.resolve_color_strategy(graph_type)

        if resolution.use_palette and resolution.palette_colors:
            return resolution.palette_colors
        elif resolution.media_type_colors:
            return list(resolution.media_type_colors.values())
        elif resolution.fallback_colors:
            return resolution.fallback_colors
        else:
            return [DEFAULT_COLORS.TV_COLOR]

    def _get_palette_for_graph_type(self, graph_type: str) -> str | None:
        """
        Get the configured palette name for a specific graph type.

        Args:
            graph_type: The graph class name

        Returns:
            Palette name if configured, None otherwise
        """
        palette_key = self.GRAPH_TYPE_TO_PALETTE_KEY.get(graph_type)
        if palette_key is None:
            return None

        # Get palette value from config using nested structure
        palette_value: object = None
        if self.config_accessor is not None:
            # Use the old flat key for ConfigAccessor compatibility
            old_key = self._get_old_palette_key(graph_type)
            if old_key:
                palette_value = self.config_accessor.get_value(old_key, "")
        elif isinstance(self.config, dict):
            # Navigate nested dict structure
            palette_value = self._get_nested_dict_value(self.config, palette_key)
        elif self.config is not None:
            # Navigate nested TGraphBotConfig structure
            palette_value = self._get_nested_config_value(self.config, palette_key)

        # Return palette if it's a non-empty string
        if palette_value and isinstance(palette_value, str) and palette_value.strip():
            return palette_value.strip()

        return None

    def _get_old_palette_key(self, graph_type: str) -> str | None:
        """
        Get the old flat palette key for ConfigAccessor compatibility.

        Args:
            graph_type: The graph class name

        Returns:
            Old flat key name or None if not found
        """
        old_key_mapping = {
            "PlayCountByHourOfDayGraph": "PLAY_COUNT_BY_HOUROFDAY_PALETTE",
            "Top10UsersGraph": "TOP_10_USERS_PALETTE",
            "DailyPlayCountGraph": "DAILY_PLAY_COUNT_PALETTE",
            "PlayCountByDayOfWeekGraph": "PLAY_COUNT_BY_DAYOFWEEK_PALETTE",
            "Top10PlatformsGraph": "TOP_10_PLATFORMS_PALETTE",
            "PlayCountByMonthGraph": "PLAY_COUNT_BY_MONTH_PALETTE",
        }
        return old_key_mapping.get(graph_type)

    def _get_nested_dict_value(self, config_dict: dict[str, object], key_path: str) -> object:
        """
        Get value from nested dictionary using dot notation path.

        Args:
            config_dict: The configuration dictionary
            key_path: Dot-separated path (e.g., "graphs.appearance.palettes.daily_play_count")

        Returns:
            The value at the path or None if not found
        """
        keys = key_path.split(".")
        current: object = config_dict

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]  # pyright: ignore[reportUnknownVariableType] # dynamic dict access
            else:
                return None

        return current  # pyright: ignore[reportUnknownVariableType] # dynamic dict navigation

    def _get_nested_config_value(self, config: "TGraphBotConfig", key_path: str) -> object:
        """
        Get value from nested TGraphBotConfig using dot notation path.

        Args:
            config: The TGraphBotConfig instance
            key_path: Dot-separated path (e.g., "graphs.appearance.palettes.daily_play_count")

        Returns:
            The value at the path or None if not found
        """
        keys = key_path.split(".")
        current: object = config

        for key in keys:
            if hasattr(current, key):
                current = getattr(current, key)  # pyright: ignore[reportAny] # dynamic attribute access
            else:
                return None

        return current

    def _is_media_type_separation_enabled(self) -> bool:
        """
        Check if media type separation is enabled in the configuration.

        Returns:
            True if media type separation is enabled
        """
        if self.config is None:
            return False

        # Use ConfigAccessor if available for compatibility
        if self.config_accessor is not None:
            return bool(self.config_accessor.get_value("ENABLE_MEDIA_TYPE_SEPARATION", True))
        elif isinstance(self.config, dict):
            # Navigate nested dict structure
            value = self._get_nested_dict_value(self.config, "graphs.features.media_type_separation")
            return bool(value if value is not None else True)
        else:
            # Navigate nested TGraphBotConfig structure
            value = self._get_nested_config_value(self.config, "graphs.features.media_type_separation")
            return bool(value if value is not None else True)

    def _get_media_type_colors(self) -> dict[str, str]:
        """
        Get the configured colors for media type separation.

        Returns:
            Dictionary mapping media types to their colors
        """
        if self.config is None:
            return {
                "tv": DEFAULT_COLORS.TV_COLOR,
                "movie": DEFAULT_COLORS.MOVIE_COLOR,
            }

        # Use ConfigAccessor if available for compatibility
        if self.config_accessor is not None:
            tv_color = self.config_accessor.get_value("TV_COLOR", DEFAULT_COLORS.TV_COLOR)
            movie_color = self.config_accessor.get_value("MOVIE_COLOR", DEFAULT_COLORS.MOVIE_COLOR)
        elif isinstance(self.config, dict):
            # Navigate nested dict structure
            tv_color = self._get_nested_dict_value(self.config, "graphs.appearance.colors.tv")
            movie_color = self._get_nested_dict_value(self.config, "graphs.appearance.colors.movie")
            tv_color = tv_color if tv_color is not None else DEFAULT_COLORS.TV_COLOR
            movie_color = movie_color if movie_color is not None else DEFAULT_COLORS.MOVIE_COLOR
        else:
            # Navigate nested TGraphBotConfig structure
            tv_color = self._get_nested_config_value(self.config, "graphs.appearance.colors.tv")
            movie_color = self._get_nested_config_value(self.config, "graphs.appearance.colors.movie")
            tv_color = tv_color if tv_color is not None else DEFAULT_COLORS.TV_COLOR
            movie_color = movie_color if movie_color is not None else DEFAULT_COLORS.MOVIE_COLOR

        return {
            "tv": str(tv_color),
            "movie": str(movie_color),
        }

    def _get_fallback_colors(self) -> list[str]:
        """
        Get appropriate fallback colors based on current configuration.

        Returns:
            List of fallback colors to use
        """
        if self._is_media_type_separation_enabled():
            media_colors = self._get_media_type_colors()
            return list(media_colors.values())
        else:
            return [DEFAULT_COLORS.TV_COLOR]

    def _get_palette_colors(self, palette_name: str, n_colors: int = 10) -> list[str]:
        """
        Get colors from a seaborn palette.

        Args:
            palette_name: Name of the seaborn palette
            n_colors: Number of colors to generate

        Returns:
            List of hex color strings
        """
        try:
            import seaborn as sns
            import matplotlib.colors as mcolors

            # Get palette colors
            palette_colors = sns.color_palette(palette_name, n_colors=n_colors)  # pyright: ignore[reportUnknownMemberType]

            # Convert to hex strings
            hex_colors = [mcolors.to_hex(color) for color in palette_colors]
            return hex_colors

        except Exception as e:
            logger.warning(
                f"Failed to generate colors from palette '{palette_name}': {e}"
            )
            return self._get_fallback_colors()

    def _is_valid_seaborn_palette(self, palette_name: str) -> bool:
        """
        Validate if palette name is supported by seaborn.

        Args:
            palette_name: Name of the palette to validate

        Returns:
            True if palette is valid, False otherwise
        """
        # Common seaborn palettes that are widely supported
        KNOWN_PALETTES = {
            "viridis",
            "plasma",
            "inferno",
            "magma",
            "cividis",
            "turbo",
            "hot",
            "cool",
            "spring",
            "summer",
            "autumn",
            "winter",
            "gray",
            "binary",
            "gist_gray",
            "gist_yarg",
            "bone",
            "pink",
            "jet",
            "rainbow",
            "nipy_spectral",
            "gist_ncar",
            "Set1",
            "Set2",
            "Set3",
            "tab10",
            "tab20",
            "tab20b",
            "tab20c",
            "Pastel1",
            "Pastel2",
            "Paired",
            "Accent",
            "Dark2",
            "husl",
            "hls",
            "deep",
            "muted",
            "bright",
            "pastel",
            "dark",
            "colorblind",
        }

        if palette_name in KNOWN_PALETTES:
            return True

        # Try to load the palette to verify it exists
        try:
            import seaborn as sns

            _ = sns.color_palette(palette_name, n_colors=1)  # pyright: ignore[reportUnknownMemberType]
            return True
        except Exception:
            logger.warning(f"Invalid or unsupported palette: '{palette_name}'")
            return False
