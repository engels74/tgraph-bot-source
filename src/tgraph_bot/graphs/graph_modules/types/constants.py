"""
Constants module for TGraph Bot graph modules.

This module centralizes all string constants, literals, and repeated values
used across the graph modules to eliminate DRY violations and improve
maintainability. It provides typed constant definitions, localization support,
and constant validation.

Usage Examples:
    Basic usage:
        >>> from .constants import DAYS_OF_WEEK, MEDIA_TYPES, GRAPH_TYPES
        >>> print(DAYS_OF_WEEK.MONDAY)  # "Monday"
        >>> print(MEDIA_TYPES.MOVIE)    # "movie"

    With validation:
        >>> from .constants import validate_color, validate_graph_type
        >>> validate_color("#1f77b4")  # True
        >>> validate_graph_type("daily_play_count")  # True

    Localized constants:
        >>> from .constants import get_localized_day_names
        >>> day_names = get_localized_day_names("en")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, final

if TYPE_CHECKING:
    pass


# =============================================================================
# Day and Time Constants
# =============================================================================


@final
@dataclass(frozen=True)
class DaysOfWeek:
    """Constants for days of the week."""

    MONDAY: Final[str] = "Monday"
    TUESDAY: Final[str] = "Tuesday"
    WEDNESDAY: Final[str] = "Wednesday"
    THURSDAY: Final[str] = "Thursday"
    FRIDAY: Final[str] = "Friday"
    SATURDAY: Final[str] = "Saturday"
    SUNDAY: Final[str] = "Sunday"

    @classmethod
    def get_ordered_list(cls) -> list[str]:
        """Get days of week in order starting from Monday."""
        return [
            cls.MONDAY,
            cls.TUESDAY,
            cls.WEDNESDAY,
            cls.THURSDAY,
            cls.FRIDAY,
            cls.SATURDAY,
            cls.SUNDAY,
        ]

    @classmethod
    def get_weekend_days(cls) -> list[str]:
        """Get weekend days."""
        return [cls.SATURDAY, cls.SUNDAY]

    @classmethod
    def get_weekday_days(cls) -> list[str]:
        """Get weekday days."""
        return [
            cls.MONDAY,
            cls.TUESDAY,
            cls.WEDNESDAY,
            cls.THURSDAY,
            cls.FRIDAY,
        ]


@final
@dataclass(frozen=True)
class DateTimeFormats:
    """Constants for date and time formatting."""

    DATE_FORMAT: Final[str] = "%Y-%m-%d"
    DATETIME_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
    TIMESTAMP_FORMAT: Final[str] = "%Y%m%d_%H%M%S"
    MONTH_FORMAT: Final[str] = "%Y-%m"
    HOUR_FORMAT: Final[str] = "%H"

    # Display formats
    DISPLAY_DATE_FORMAT: Final[str] = "%B %d, %Y"
    DISPLAY_DATETIME_FORMAT: Final[str] = "%B %d, %Y at %I:%M %p"


# =============================================================================
# Media Type Constants
# =============================================================================


@final
@dataclass(frozen=True)
class MediaTypes:
    """Constants for media types."""

    MOVIE: Final[str] = "movie"
    TV: Final[str] = "tv"
    EPISODE: Final[str] = "episode"
    MUSIC: Final[str] = "music"
    OTHER: Final[str] = "other"
    UNKNOWN: Final[str] = "unknown"

    @classmethod
    def get_all_types(cls) -> list[str]:
        """Get all media types."""
        return [cls.MOVIE, cls.TV, cls.EPISODE, cls.MUSIC, cls.OTHER, cls.UNKNOWN]

    @classmethod
    def get_primary_types(cls) -> list[str]:
        """Get primary media types (movie, tv)."""
        return [cls.MOVIE, cls.TV]


@final
@dataclass(frozen=True)
class MediaTypeDisplayNames:
    """Display names for media types."""

    MOVIE: Final[str] = "Movies"
    TV: Final[str] = "TV Series"
    EPISODE: Final[str] = "Episodes"
    MUSIC: Final[str] = "Music"
    OTHER: Final[str] = "Other"
    UNKNOWN: Final[str] = "Unknown"


@final
@dataclass(frozen=True)
class MediaTypeAliases:
    """Aliases for media type classification."""

    @property
    def MOVIE_ALIASES(self) -> list[str]:
        """Get movie aliases."""
        return ["movie", "film", "cinema"]

    @property
    def TV_ALIASES(self) -> list[str]:
        """Get TV aliases."""
        return ["tv", "episode", "show", "series"]

    @property
    def MUSIC_ALIASES(self) -> list[str]:
        """Get music aliases."""
        return ["music", "track", "album", "artist", "song"]

    @property
    def OTHER_ALIASES(self) -> list[str]:
        """Get other aliases."""
        return ["other", "unknown"]


# =============================================================================
# Graph Type Constants
# =============================================================================


@final
@dataclass(frozen=True)
class GraphTypes:
    """Constants for graph types."""

    DAILY_PLAY_COUNT: Final[str] = "daily_play_count"
    PLAY_COUNT_BY_DAYOFWEEK: Final[str] = "play_count_by_dayofweek"
    PLAY_COUNT_BY_HOUROFDAY: Final[str] = "play_count_by_hourofday"
    PLAY_COUNT_BY_MONTH: Final[str] = "play_count_by_month"
    TOP_10_PLATFORMS: Final[str] = "top_10_platforms"
    TOP_10_USERS: Final[str] = "top_10_users"
    SAMPLE_GRAPH: Final[str] = "sample_graph"

    @classmethod
    def get_all_types(cls) -> list[str]:
        """Get all graph types."""
        return [
            cls.DAILY_PLAY_COUNT,
            cls.PLAY_COUNT_BY_DAYOFWEEK,
            cls.PLAY_COUNT_BY_HOUROFDAY,
            cls.PLAY_COUNT_BY_MONTH,
            cls.TOP_10_PLATFORMS,
            cls.TOP_10_USERS,
            cls.SAMPLE_GRAPH,
        ]

    @classmethod
    def get_tautulli_types(cls) -> list[str]:
        """Get Tautulli-specific graph types."""
        return [
            cls.DAILY_PLAY_COUNT,
            cls.PLAY_COUNT_BY_DAYOFWEEK,
            cls.PLAY_COUNT_BY_HOUROFDAY,
            cls.PLAY_COUNT_BY_MONTH,
            cls.TOP_10_PLATFORMS,
            cls.TOP_10_USERS,
        ]


@final
@dataclass(frozen=True)
class GraphTitles:
    """Default titles for graph types."""

    DAILY_PLAY_COUNT: Final[str] = "Daily Play Count"
    PLAY_COUNT_BY_DAYOFWEEK: Final[str] = "Play Count by Day of Week"
    PLAY_COUNT_BY_HOUROFDAY: Final[str] = "Play Count by Hour of Day"
    PLAY_COUNT_BY_MONTH: Final[str] = "Play Count by Month"
    TOP_10_PLATFORMS: Final[str] = "Top 10 Platforms"
    TOP_10_USERS: Final[str] = "Top 10 Users"
    SAMPLE_GRAPH: Final[str] = "Sample Graph"


# =============================================================================
# Color Constants
# =============================================================================


@final
@dataclass(frozen=True)
class DefaultColors:
    """Default color constants."""

    # Primary colors
    TV_COLOR: Final[str] = "#1f77b4"  # Blue
    MOVIE_COLOR: Final[str] = "#ff7f0e"  # Orange
    MUSIC_COLOR: Final[str] = "#2ca02c"  # Green
    OTHER_COLOR: Final[str] = "#d62728"  # Red
    UNKNOWN_COLOR: Final[str] = "#666666"  # Gray

    # Background colors
    GRAPH_BACKGROUND: Final[str] = "#ffffff"  # White
    FIGURE_BACKGROUND: Final[str] = "#ffffff"  # White

    # Annotation colors
    ANNOTATION_COLOR: Final[str] = "#ff0000"  # Red
    ANNOTATION_OUTLINE: Final[str] = "#000000"  # Black
    PEAK_ANNOTATION: Final[str] = "#ffcc00"  # Yellow
    PEAK_ANNOTATION_TEXT: Final[str] = "#000000"  # Black

    # Grid and axis colors
    GRID_COLOR: Final[str] = "#cccccc"  # Light gray
    AXIS_COLOR: Final[str] = "#333333"  # Dark gray

    @classmethod
    def get_media_type_colors(cls) -> dict[str, str]:
        """Get color mapping for media types."""
        return {
            MediaTypes.TV: cls.TV_COLOR,
            MediaTypes.MOVIE: cls.MOVIE_COLOR,
            MediaTypes.MUSIC: cls.MUSIC_COLOR,
            MediaTypes.OTHER: cls.OTHER_COLOR,
            MediaTypes.UNKNOWN: cls.UNKNOWN_COLOR,
        }


@final
@dataclass(frozen=True)
class ColorPalettes:
    """Color palettes for graphs."""

    VIRIDIS: Final[str] = "viridis"
    PLASMA: Final[str] = "plasma"
    INFERNO: Final[str] = "inferno"
    MAGMA: Final[str] = "magma"

    @property
    def SEABORN_DEFAULT(self) -> list[str]:
        """Get Seaborn default color palette."""
        return ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]


# =============================================================================
# Configuration Key Constants
# =============================================================================


@final
@dataclass(frozen=True)
class ConfigKeys:
    """Configuration key constants."""

    # Graph enable/disable keys
    ENABLE_DAILY_PLAY_COUNT: Final[str] = "ENABLE_DAILY_PLAY_COUNT"
    ENABLE_PLAY_COUNT_BY_DAYOFWEEK: Final[str] = "ENABLE_PLAY_COUNT_BY_DAYOFWEEK"
    ENABLE_PLAY_COUNT_BY_HOUROFDAY: Final[str] = "ENABLE_PLAY_COUNT_BY_HOUROFDAY"
    ENABLE_PLAY_COUNT_BY_MONTH: Final[str] = "ENABLE_PLAY_COUNT_BY_MONTH"
    ENABLE_TOP_10_PLATFORMS: Final[str] = "ENABLE_TOP_10_PLATFORMS"
    ENABLE_TOP_10_USERS: Final[str] = "ENABLE_TOP_10_USERS"

    # Color configuration keys
    TV_COLOR: Final[str] = "TV_COLOR"
    MOVIE_COLOR: Final[str] = "MOVIE_COLOR"
    GRAPH_BACKGROUND_COLOR: Final[str] = "GRAPH_BACKGROUND_COLOR"
    ANNOTATION_COLOR: Final[str] = "ANNOTATION_COLOR"
    ANNOTATION_OUTLINE_COLOR: Final[str] = "ANNOTATION_OUTLINE_COLOR"
    PEAK_ANNOTATION_COLOR: Final[str] = "PEAK_ANNOTATION_COLOR"
    PEAK_ANNOTATION_TEXT_COLOR: Final[str] = "PEAK_ANNOTATION_TEXT_COLOR"

    # Annotation enable/disable keys
    ANNOTATE_DAILY_PLAY_COUNT: Final[str] = "ANNOTATE_DAILY_PLAY_COUNT"
    ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK: Final[str] = "ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK"
    ANNOTATE_PLAY_COUNT_BY_HOUROFDAY: Final[str] = "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY"
    ANNOTATE_PLAY_COUNT_BY_MONTH: Final[str] = "ANNOTATE_PLAY_COUNT_BY_MONTH"
    ANNOTATE_TOP_10_PLATFORMS: Final[str] = "ANNOTATE_TOP_10_PLATFORMS"
    ANNOTATE_TOP_10_USERS: Final[str] = "ANNOTATE_TOP_10_USERS"

    # Other configuration keys
    TIME_RANGE_DAYS: Final[str] = "TIME_RANGE_DAYS"
    TIME_RANGE_MONTHS: Final[str] = "TIME_RANGE_MONTHS"
    ENABLE_GRAPH_GRID: Final[str] = "ENABLE_GRAPH_GRID"
    ENABLE_STACKED_BAR_CHARTS: Final[str] = "ENABLE_STACKED_BAR_CHARTS"
    ENABLE_MEDIA_TYPE_SEPARATION: Final[str] = "ENABLE_MEDIA_TYPE_SEPARATION"
    CENSOR_USERNAMES: Final[str] = "CENSOR_USERNAMES"


# =============================================================================
# File and Path Constants
# =============================================================================


@final
@dataclass(frozen=True)
class FileExtensions:
    """File extension constants."""

    PNG: Final[str] = ".png"
    JPG: Final[str] = ".jpg"
    JPEG: Final[str] = ".jpeg"
    SVG: Final[str] = ".svg"
    PDF: Final[str] = ".pdf"

    @classmethod
    def get_image_extensions(cls) -> list[str]:
        """Get supported image extensions."""
        return [cls.PNG, cls.JPG, cls.JPEG, cls.SVG]


@final
@dataclass(frozen=True)
class FileFormats:
    """File format constants."""

    PNG: Final[str] = "png"
    JPG: Final[str] = "jpg"
    JPEG: Final[str] = "jpeg"
    SVG: Final[str] = "svg"
    PDF: Final[str] = "pdf"


@final
@dataclass(frozen=True)
class PathPatterns:
    """Path pattern constants."""

    INVALID_FILENAME_CHARS: Final[str] = r'[<>:"/\\|?*]'
    REPLACEMENT_CHAR: Final[str] = "_"
    DEFAULT_FILENAME: Final[str] = "unnamed"
    EMAIL_AT_REPLACEMENT: Final[str] = "_at_"
    EMAIL_DOT_REPLACEMENT: Final[str] = "_"


# =============================================================================
# Create singleton instances
# =============================================================================

# =============================================================================
# Validation Functions
# =============================================================================


def validate_color(color: object) -> bool:
    """
    Validate that a color string is in valid hex format.

    Args:
        color: Color value to validate

    Returns:
        True if valid hex color, False otherwise
    """
    if not isinstance(color, str):
        return False
    return bool(re.match(r"^#[0-9a-fA-F]{6}$", color))


def validate_graph_type(graph_type: object) -> bool:
    """
    Validate that a graph type is supported.

    Args:
        graph_type: Graph type value to validate

    Returns:
        True if valid graph type, False otherwise
    """
    if not isinstance(graph_type, str):
        return False
    return graph_type in GRAPH_TYPES.get_all_types()


def validate_media_type(media_type: object) -> bool:
    """
    Validate that a media type is supported.

    Args:
        media_type: Media type value to validate

    Returns:
        True if valid media type, False otherwise
    """
    if not isinstance(media_type, str):
        return False
    return media_type in MEDIA_TYPES.get_all_types()


def validate_day_of_week(day: object) -> bool:
    """
    Validate that a day string is a valid day of the week.

    Args:
        day: Day value to validate

    Returns:
        True if valid day of week, False otherwise
    """
    if not isinstance(day, str):
        return False
    return day in DAYS_OF_WEEK.get_ordered_list()


# =============================================================================
# Localization Support
# =============================================================================


def get_localized_day_names(locale: str = "en") -> list[str]:  # pyright: ignore[reportUnusedParameter]
    """
    Get localized day names for the specified locale.

    Args:
        locale: Locale code (e.g., "en", "es", "fr")

    Returns:
        List of localized day names starting from Monday

    Note:
        Currently only supports English. Future versions will support
        additional locales through the i18n system.
    """
    # For now, return English names
    # TODO: Integrate with i18n system for proper localization
    return DAYS_OF_WEEK.get_ordered_list()


def get_localized_media_type_names(locale: str = "en") -> dict[str, str]:  # pyright: ignore[reportUnusedParameter]
    """
    Get localized media type display names for the specified locale.

    Args:
        locale: Locale code (e.g., "en", "es", "fr")

    Returns:
        Dictionary mapping media type keys to localized display names

    Note:
        Currently only supports English. Future versions will support
        additional locales through the i18n system.
    """
    # For now, return English names
    # TODO: Integrate with i18n system for proper localization
    return {
        MEDIA_TYPES.MOVIE: MEDIA_TYPE_DISPLAY_NAMES.MOVIE,
        MEDIA_TYPES.TV: MEDIA_TYPE_DISPLAY_NAMES.TV,
        MEDIA_TYPES.EPISODE: MEDIA_TYPE_DISPLAY_NAMES.EPISODE,
        MEDIA_TYPES.MUSIC: MEDIA_TYPE_DISPLAY_NAMES.MUSIC,
        MEDIA_TYPES.OTHER: MEDIA_TYPE_DISPLAY_NAMES.OTHER,
        MEDIA_TYPES.UNKNOWN: MEDIA_TYPE_DISPLAY_NAMES.UNKNOWN,
    }


def get_localized_graph_titles(locale: str = "en") -> dict[str, str]:  # pyright: ignore[reportUnusedParameter]
    """
    Get localized graph titles for the specified locale.

    Args:
        locale: Locale code (e.g., "en", "es", "fr")

    Returns:
        Dictionary mapping graph type keys to localized titles

    Note:
        Currently only supports English. Future versions will support
        additional locales through the i18n system.
    """
    # For now, return English titles
    # TODO: Integrate with i18n system for proper localization
    return {
        GRAPH_TYPES.DAILY_PLAY_COUNT: GRAPH_TITLES.DAILY_PLAY_COUNT,
        GRAPH_TYPES.PLAY_COUNT_BY_DAYOFWEEK: GRAPH_TITLES.PLAY_COUNT_BY_DAYOFWEEK,
        GRAPH_TYPES.PLAY_COUNT_BY_HOUROFDAY: GRAPH_TITLES.PLAY_COUNT_BY_HOUROFDAY,
        GRAPH_TYPES.PLAY_COUNT_BY_MONTH: GRAPH_TITLES.PLAY_COUNT_BY_MONTH,
        GRAPH_TYPES.TOP_10_PLATFORMS: GRAPH_TITLES.TOP_10_PLATFORMS,
        GRAPH_TYPES.TOP_10_USERS: GRAPH_TITLES.TOP_10_USERS,
        GRAPH_TYPES.SAMPLE_GRAPH: GRAPH_TITLES.SAMPLE_GRAPH,
    }


# =============================================================================
# Create singleton instances
# =============================================================================

# Create singleton instances for easy access
DAYS_OF_WEEK: Final[DaysOfWeek] = DaysOfWeek()
DATETIME_FORMATS: Final[DateTimeFormats] = DateTimeFormats()
MEDIA_TYPES: Final[MediaTypes] = MediaTypes()
MEDIA_TYPE_DISPLAY_NAMES: Final[MediaTypeDisplayNames] = MediaTypeDisplayNames()
MEDIA_TYPE_ALIASES: Final[MediaTypeAliases] = MediaTypeAliases()
GRAPH_TYPES: Final[GraphTypes] = GraphTypes()
GRAPH_TITLES: Final[GraphTitles] = GraphTitles()
DEFAULT_COLORS: Final[DefaultColors] = DefaultColors()
COLOR_PALETTES: Final[ColorPalettes] = ColorPalettes()
CONFIG_KEYS: Final[ConfigKeys] = ConfigKeys()
FILE_EXTENSIONS: Final[FileExtensions] = FileExtensions()
FILE_FORMATS: Final[FileFormats] = FileFormats()
PATH_PATTERNS: Final[PathPatterns] = PathPatterns()
