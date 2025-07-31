"""
Media type processor for TGraph Bot graph generation.

This module provides utilities for handling media type classification,
display information, color management, and filtering options.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from collections.abc import Sequence, Mapping

if TYPE_CHECKING:
    from ..config.config_accessor import ConfigAccessor


@dataclass
class MediaTypeInfo:
    """Information about a media type."""

    type_name: str
    display_name: str
    default_color: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class MediaTypeDisplayInfo:
    """Display information for a media type."""

    display_name: str
    color: str


class MediaTypeProcessor:
    """Processor for media type classification and display utilities."""

    def __init__(self, config_accessor: ConfigAccessor | None = None) -> None:
        """Initialize MediaTypeProcessor with optional configuration."""
        self.config_accessor: ConfigAccessor | None = config_accessor
        self._media_types: dict[str, MediaTypeInfo] = self._initialize_media_types()

    def _initialize_media_types(self) -> dict[str, MediaTypeInfo]:
        """Initialize default media type definitions."""
        return {
            "movie": MediaTypeInfo(
                type_name="movie",
                display_name="Movies",
                default_color="#ff7f0e",
                aliases=["film", "cinema"],
                description="Movie content type",
            ),
            "tv": MediaTypeInfo(
                type_name="tv",
                display_name="TV Series",
                default_color="#1f77b4",
                aliases=["episode", "show", "series"],
                description="TV show/series content type",
            ),
            "music": MediaTypeInfo(
                type_name="music",
                display_name="Music",
                default_color="#2ca02c",
                aliases=["track", "album", "artist", "audio"],
                description="Music content type",
            ),
            "other": MediaTypeInfo(
                type_name="other",
                display_name="Other",
                default_color="#d62728",
                aliases=["unknown"],
                description="Other/unknown content type",
            ),
        }

    def classify_media_type(self, media_type: str) -> str:
        """
        Classify a media type string into a standard category.

        Args:
            media_type: Media type string to classify

        Returns:
            Classified media type ("movie", "tv", "music", "other")
        """
        if not media_type:
            return "other"

        media_type_lower = media_type.lower().strip()

        # Check direct matches first
        if media_type_lower in self._media_types:
            return media_type_lower

        # Check aliases
        for type_name, info in self._media_types.items():
            if media_type_lower in [alias.lower() for alias in info.aliases]:
                return type_name

        return "other"

    def _get_configured_color(self, media_type: str, default_color: str) -> str:
        """
        Get configured color for media type, falling back to default.

        Args:
            media_type: The classified media type
            default_color: Default color if no config available

        Returns:
            Color hex string from config or default
        """
        if self.config_accessor is None:
            return default_color

        # Map media types to configuration paths
        config_key_map = {
            "tv": "graphs.appearance.colors.tv",
            "movie": "graphs.appearance.colors.movie",
        }

        config_key = config_key_map.get(media_type)
        if config_key is None:
            return default_color

        try:
            configured_color = self.config_accessor.get_value(config_key, default_color)
            return str(configured_color)
        except Exception:
            return default_color

    def get_display_info(self, media_type: str) -> MediaTypeDisplayInfo:
        """
        Get display information for a media type.

        Args:
            media_type: Media type to get display info for

        Returns:
            MediaTypeDisplayInfo with display name and color
        """
        classified_type = self.classify_media_type(media_type)
        info = self._media_types.get(classified_type, self._media_types["other"])

        # Use configuration color if available, otherwise use default
        color = self._get_configured_color(classified_type, info.default_color)

        return MediaTypeDisplayInfo(
            display_name=info.display_name,
            color=color,
        )

    def get_color_for_type(self, media_type: str) -> str:
        """
        Get the color for a media type.

        Args:
            media_type: Media type to get color for

        Returns:
            Color hex string
        """
        return self.get_display_info(media_type).color

    def is_valid_media_type(self, media_type: str) -> bool:
        """
        Check if a media type is valid (known).

        Args:
            media_type: Media type to validate

        Returns:
            True if valid, False otherwise
        """
        return self.classify_media_type(media_type) != "other"

    def filter_by_media_type(
        self, records: Sequence[Mapping[str, object]], media_type: str | list[str]
    ) -> Sequence[Mapping[str, object]]:
        """
        Filter records by media type.

        Args:
            records: List of records to filter
            media_type: Media type(s) to filter by (single string or list of strings)

        Returns:
            Filtered list of records
        """
        if not records:
            return []

        # Normalize media_type to a list
        if isinstance(media_type, str):
            target_types = [media_type]
        else:
            target_types = media_type

        filtered_records: list[Mapping[str, object]] = []
        for record in records:
            if isinstance(record, dict):
                record_media_type = record.get("media_type", "")
                if isinstance(record_media_type, str):
                    classified_type = self.classify_media_type(record_media_type)
                    if classified_type in target_types:
                        filtered_records.append(record)

        return filtered_records

    def get_preferred_order(self) -> list[str]:
        """
        Get the preferred display order for media types.

        Returns:
            List of media type names in preferred order
        """
        return ["movie", "tv", "music", "other"]

    def get_all_display_names(self) -> dict[str, str]:
        """
        Get all media type display names.

        Returns:
            Dictionary mapping type names to display names
        """
        return {
            type_name: info.display_name
            for type_name, info in self._media_types.items()
        }

    def get_all_colors(self) -> dict[str, str]:
        """
        Get all media type colors.

        Returns:
            Dictionary mapping type names to colors
        """
        return {
            type_name: info.default_color
            for type_name, info in self._media_types.items()
        }

    def get_all_display_info(self) -> dict[str, dict[str, str]]:
        """
        Get all media type display information.

        Returns:
            Dictionary mapping type names to display info dict
        """
        return {
            type_name: {
                "display_name": info.display_name,
                "color": info.default_color,
            }
            for type_name, info in self._media_types.items()
        }

    def get_supported_types(self) -> list[str]:
        """
        Get list of all supported media types.

        Returns:
            List of supported media type names
        """
        return list(self._media_types.keys())
