"""
Media Type Processor for TGraph Bot.

This module provides a centralized utility for handling media type classification,
display information, color management, and filtering operations. It consolidates
media type handling logic that was previously scattered across multiple graph
implementations.
"""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config_accessor import ConfigAccessor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MediaTypeInfo:
    """
    Information about a media type including display properties and classification rules.
    
    This dataclass encapsulates all the information needed to handle a specific
    media type, including its canonical name, display properties, and aliases
    for classification.
    """
    
    type_name: str
    display_name: str
    default_color: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""


@dataclass(frozen=True)
class MediaTypeDisplayInfo:
    """
    Display information for a media type.
    
    This dataclass provides the display properties needed for rendering
    media types in graphs, including the human-readable name and color.
    """
    
    display_name: str
    color: str


class MediaTypeProcessor:
    """
    Centralized processor for media type operations.

    This class consolidates all media type handling logic including:
    - Classification of raw media type strings into standardized categories
    - Retrieval of display information (names, colors) with configuration overrides
    - Filtering of records by media type
    - Management of media type ordering for consistent visualization

    The processor supports configuration-based color overrides for TV and movie
    content types while providing sensible defaults for all media types.
    """

    config_accessor: "ConfigAccessor | None"
    _media_types: dict[str, MediaTypeInfo]

    def __init__(self, config_accessor: "ConfigAccessor | None" = None) -> None:
        """
        Initialize the MediaTypeProcessor.

        Args:
            config_accessor: Optional configuration accessor for color overrides
        """
        self.config_accessor = config_accessor
        self._media_types = self._initialize_media_types()
    
    def _initialize_media_types(self) -> dict[str, MediaTypeInfo]:
        """
        Initialize the media type registry with default types and their properties.
        
        Returns:
            Dictionary mapping media type names to their information
        """
        return {
            "movie": MediaTypeInfo(
                type_name="movie",
                display_name="Movies",
                default_color="#ff7f0e",  # Orange - matches MOVIE_COLOR default
                aliases=["movie", "film", "cinema"],
                description="Movie content type"
            ),
            "tv": MediaTypeInfo(
                type_name="tv",
                display_name="TV Series",
                default_color="#1f77b4",  # Blue - matches TV_COLOR default
                aliases=["tv", "episode", "show", "series"],
                description="Television content type"
            ),
            "music": MediaTypeInfo(
                type_name="music",
                display_name="Music",
                default_color="#2ca02c",  # Green
                aliases=["music", "track", "album", "artist", "song"],
                description="Music content type"
            ),
            "other": MediaTypeInfo(
                type_name="other",
                display_name="Other",
                default_color="#d62728",  # Red
                aliases=["other", "unknown"],
                description="Other or unknown content type"
            ),
        }
    
    def classify_media_type(self, media_type: str) -> str:
        """
        Classify a raw media type string into a standardized category.
        
        This method implements the classification logic that was previously
        duplicated across multiple graph implementations. It normalizes
        various media type strings from the Tautulli API into consistent
        categories.
        
        Args:
            media_type: The raw media type from Tautulli API
            
        Returns:
            Standardized media type ('movie', 'tv', 'music', 'other')
        """
        if not media_type:
            return "other"
        
        media_type_lower = media_type.lower().strip()
        
        # Check each media type's aliases
        for type_name, type_info in self._media_types.items():
            if media_type_lower in type_info.aliases:
                return type_name
        
        # Default to 'other' if no match found
        return "other"
    
    def get_display_info(self, media_type: str) -> MediaTypeDisplayInfo:
        """
        Get display information for a media type with configuration overrides.
        
        This method retrieves the display name and color for a media type,
        applying configuration-based color overrides when available. This
        consolidates the display info logic that was repeated across graph
        implementations.
        
        Args:
            media_type: The media type to get display info for
            
        Returns:
            MediaTypeDisplayInfo with display name and color
        """
        # Ensure we have a valid media type
        normalized_type = self.classify_media_type(media_type)
        
        if normalized_type not in self._media_types:
            # Fallback for unknown types
            return MediaTypeDisplayInfo(
                display_name="Other",
                color="#d62728"
            )
        
        type_info = self._media_types[normalized_type]
        color = self.get_color_for_type(normalized_type)
        
        return MediaTypeDisplayInfo(
            display_name=type_info.display_name,
            color=color
        )
    
    def get_color_for_type(self, media_type: str) -> str:
        """
        Get the color for a media type with configuration overrides.
        
        This method applies configuration-based color overrides for TV and
        movie types while using default colors for other types. This
        consolidates the color retrieval logic from BaseGraph.
        
        Args:
            media_type: The media type to get color for
            
        Returns:
            Hex color string for the media type
        """
        # Ensure we have a valid media type
        normalized_type = self.classify_media_type(media_type)
        
        if normalized_type not in self._media_types:
            return "#d62728"  # Default gray for unknown types
        
        type_info = self._media_types[normalized_type]
        
        # Apply configuration overrides for TV and movie types
        if self.config_accessor is not None:
            if normalized_type == "tv":
                return str(self.config_accessor.get_value("TV_COLOR", type_info.default_color))
            elif normalized_type == "movie":
                return str(self.config_accessor.get_value("MOVIE_COLOR", type_info.default_color))
        
        return type_info.default_color
    
    def get_all_display_info(self) -> dict[str, dict[str, str]]:
        """
        Get display information for all media types.
        
        This method returns a dictionary mapping media type names to their
        display information, compatible with the existing get_media_type_display_info
        function format.
        
        Returns:
            Dictionary mapping media type to display info (name, color)
        """
        result: dict[str, dict[str, str]] = {}
        
        for type_name in self._media_types:
            display_info = self.get_display_info(type_name)
            result[type_name] = {
                "display_name": display_info.display_name,
                "color": display_info.color
            }
        
        return result
    
    def get_supported_types(self) -> list[str]:
        """
        Get a list of all supported media types.
        
        Returns:
            List of supported media type names
        """
        return list(self._media_types.keys())
    
    def is_valid_media_type(self, media_type: str) -> bool:
        """
        Check if a media type is valid/supported.
        
        Args:
            media_type: The media type to validate
            
        Returns:
            True if the media type is supported, False otherwise
        """
        return media_type in self._media_types
    
    def filter_by_media_type(
        self,
        records: Sequence[Mapping[str, object]],
        allowed_types: Sequence[str]
    ) -> list[dict[str, object]]:
        """
        Filter records by media type.

        This method filters a list of records to include only those with
        media types that classify to the allowed types. This provides
        centralized filtering logic for graph implementations.

        Args:
            records: List of records to filter
            allowed_types: List of allowed media types

        Returns:
            Filtered list of records
        """
        filtered_records: list[dict[str, object]] = []

        for record in records:
            if not isinstance(record, dict):
                continue

            record_media_type = record.get("media_type", "")
            classified_type = self.classify_media_type(str(record_media_type))

            if classified_type in allowed_types:
                filtered_records.append(dict(record))

        return filtered_records
    
    def get_preferred_order(self) -> list[str]:
        """
        Get the preferred order for media types in visualizations.
        
        This method returns the preferred order for displaying media types
        in stacked charts and legends, ensuring consistent visualization
        across all graph implementations.
        
        Returns:
            List of media types in preferred display order
        """
        # Movies at bottom, TV series on top for stacked bars
        # This matches the existing pattern in graph implementations
        return ["movie", "tv", "music", "other"]
