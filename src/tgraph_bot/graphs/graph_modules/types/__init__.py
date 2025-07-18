"""
Type definitions and constants for TGraph Bot graph modules.

This package contains type definitions, constants, enums, and other
type-related utilities used throughout the graph generation system.
"""

from .constants import (
    COLOR_PALETTES,
    CONFIG_KEYS,
    DATETIME_FORMATS,
    DAYS_OF_WEEK,
    DEFAULT_COLORS,
    FILE_EXTENSIONS,
    FILE_FORMATS,
    GRAPH_TITLES,
    GRAPH_TYPES,
    MEDIA_TYPES,
    MEDIA_TYPE_ALIASES,
    MEDIA_TYPE_DISPLAY_NAMES,
    PATH_PATTERNS,
    get_localized_day_names,
    get_localized_graph_titles,
    get_localized_media_type_names,
    validate_color,
    validate_day_of_week,
    validate_graph_type,
    validate_media_type,
)

__all__ = [
    "DAYS_OF_WEEK",
    "DATETIME_FORMATS",
    "MEDIA_TYPES",
    "MEDIA_TYPE_DISPLAY_NAMES",
    "MEDIA_TYPE_ALIASES",
    "GRAPH_TYPES",
    "GRAPH_TITLES",
    "DEFAULT_COLORS",
    "COLOR_PALETTES",
    "CONFIG_KEYS",
    "FILE_EXTENSIONS",
    "FILE_FORMATS",
    "PATH_PATTERNS",
    "validate_color",
    "validate_graph_type",
    "validate_media_type",
    "validate_day_of_week",
    "get_localized_day_names",
    "get_localized_media_type_names",
    "get_localized_graph_titles",
]
