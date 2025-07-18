"""
Tests for MediaTypeProcessor utility in TGraph Bot.

This module tests the MediaTypeProcessor utility that consolidates
media type handling logic including classification, display information,
color management, and filtering options.
"""

from unittest.mock import MagicMock

import pytest

from src.tgraph_bot.graphs.graph_modules.media_type_processor import (
    MediaTypeProcessor,
    MediaTypeInfo,
    MediaTypeDisplayInfo,
)


class TestMediaTypeInfo:
    """Test cases for MediaTypeInfo dataclass."""
    
    def test_media_type_info_creation(self) -> None:
        """Test MediaTypeInfo creation with all fields."""
        info = MediaTypeInfo(
            type_name="movie",
            display_name="Movies",
            default_color="#ff7f0e",
            aliases=["film", "cinema"],
            description="Movie content type"
        )
        
        assert info.type_name == "movie"
        assert info.display_name == "Movies"
        assert info.default_color == "#ff7f0e"
        assert info.aliases == ["film", "cinema"]
        assert info.description == "Movie content type"
    
    def test_media_type_info_minimal(self) -> None:
        """Test MediaTypeInfo creation with minimal fields."""
        info = MediaTypeInfo(
            type_name="tv",
            display_name="TV Series",
            default_color="#1f77b4"
        )
        
        assert info.type_name == "tv"
        assert info.display_name == "TV Series"
        assert info.default_color == "#1f77b4"
        assert info.aliases == []
        assert info.description == ""


class TestMediaTypeDisplayInfo:
    """Test cases for MediaTypeDisplayInfo dataclass."""
    
    def test_display_info_creation(self) -> None:
        """Test MediaTypeDisplayInfo creation."""
        display_info = MediaTypeDisplayInfo(
            display_name="Movies",
            color="#ff7f0e"
        )
        
        assert display_info.display_name == "Movies"
        assert display_info.color == "#ff7f0e"


class TestMediaTypeProcessor:
    """Test cases for MediaTypeProcessor class."""
    
    def test_processor_creation_without_config(self) -> None:
        """Test MediaTypeProcessor creation without configuration."""
        processor = MediaTypeProcessor()
        
        assert processor.config_accessor is None
        assert len(processor._media_types) > 0
    
    def test_processor_creation_with_config(self) -> None:
        """Test MediaTypeProcessor creation with configuration."""
        mock_config = MagicMock()
        processor = MediaTypeProcessor(config_accessor=mock_config)
        
        assert processor.config_accessor is mock_config
        assert len(processor._media_types) > 0
    
    def test_classify_media_type_movie(self) -> None:
        """Test media type classification for movies."""
        processor = MediaTypeProcessor()
        
        assert processor.classify_media_type("movie") == "movie"
        assert processor.classify_media_type("MOVIE") == "movie"
        assert processor.classify_media_type("film") == "movie"
    
    def test_classify_media_type_tv(self) -> None:
        """Test media type classification for TV content."""
        processor = MediaTypeProcessor()
        
        assert processor.classify_media_type("tv") == "tv"
        assert processor.classify_media_type("TV") == "tv"
        assert processor.classify_media_type("episode") == "tv"
        assert processor.classify_media_type("show") == "tv"
    
    def test_classify_media_type_music(self) -> None:
        """Test media type classification for music content."""
        processor = MediaTypeProcessor()
        
        assert processor.classify_media_type("music") == "music"
        assert processor.classify_media_type("track") == "music"
        assert processor.classify_media_type("album") == "music"
        assert processor.classify_media_type("artist") == "music"
    
    def test_classify_media_type_other(self) -> None:
        """Test media type classification for unknown content."""
        processor = MediaTypeProcessor()
        
        assert processor.classify_media_type("unknown") == "other"
        assert processor.classify_media_type("") == "other"
        assert processor.classify_media_type("book") == "other"
    
    def test_get_display_info_without_config(self) -> None:
        """Test getting display info without configuration."""
        processor = MediaTypeProcessor()
        
        info = processor.get_display_info("movie")
        assert info.display_name == "Movies"
        assert info.color == "#ff7f0e"
        
        info = processor.get_display_info("tv")
        assert info.display_name == "TV Series"
        assert info.color == "#1f77b4"
    
    def test_get_display_info_with_config_override(self) -> None:
        """Test getting display info with configuration color override."""
        mock_config = MagicMock()
        mock_config.get_value.side_effect = lambda key, default: {
            "TV_COLOR": "#custom_tv",
            "MOVIE_COLOR": "#custom_movie"
        }.get(key, default)

        processor = MediaTypeProcessor(config_accessor=mock_config)

        info = processor.get_display_info("tv")
        assert info.display_name == "TV Series"
        assert info.color == "#custom_tv"

        info = processor.get_display_info("movie")
        assert info.display_name == "Movies"
        assert info.color == "#custom_movie"
    
    def test_get_display_info_unknown_type(self) -> None:
        """Test getting display info for unknown media type."""
        processor = MediaTypeProcessor()
        
        info = processor.get_display_info("unknown")
        assert info.display_name == "Other"
        assert info.color == "#d62728"
    
    def test_get_color_for_type_without_config(self) -> None:
        """Test getting color for media type without configuration."""
        processor = MediaTypeProcessor()
        
        assert processor.get_color_for_type("movie") == "#ff7f0e"
        assert processor.get_color_for_type("tv") == "#1f77b4"
        assert processor.get_color_for_type("music") == "#2ca02c"
        assert processor.get_color_for_type("other") == "#d62728"
    
    def test_get_color_for_type_with_config_override(self) -> None:
        """Test getting color for media type with configuration override."""
        mock_config = MagicMock()
        mock_config.get_value.side_effect = lambda key, default: {
            "TV_COLOR": "#custom_tv",
            "MOVIE_COLOR": "#custom_movie"
        }.get(key, default)

        processor = MediaTypeProcessor(config_accessor=mock_config)

        assert processor.get_color_for_type("tv") == "#custom_tv"
        assert processor.get_color_for_type("movie") == "#custom_movie"
        assert processor.get_color_for_type("music") == "#2ca02c"  # No config override
    
    def test_get_all_display_info(self) -> None:
        """Test getting all display information."""
        processor = MediaTypeProcessor()
        
        all_info = processor.get_all_display_info()
        
        assert "movie" in all_info
        assert "tv" in all_info
        assert "music" in all_info
        assert "other" in all_info
        
        assert all_info["movie"]["display_name"] == "Movies"
        assert all_info["tv"]["display_name"] == "TV Series"
    
    def test_get_supported_types(self) -> None:
        """Test getting list of supported media types."""
        processor = MediaTypeProcessor()
        
        types = processor.get_supported_types()
        
        assert "movie" in types
        assert "tv" in types
        assert "music" in types
        assert "other" in types
        assert len(types) >= 4
    
    def test_is_valid_media_type(self) -> None:
        """Test media type validation."""
        processor = MediaTypeProcessor()
        
        assert processor.is_valid_media_type("movie") is True
        assert processor.is_valid_media_type("tv") is True
        assert processor.is_valid_media_type("music") is True
        assert processor.is_valid_media_type("other") is True
        assert processor.is_valid_media_type("invalid") is False
    
    def test_filter_by_media_type(self) -> None:
        """Test filtering records by media type."""
        processor = MediaTypeProcessor()
        
        records = [
            {"media_type": "movie", "title": "Movie 1"},
            {"media_type": "tv", "title": "TV Show 1"},
            {"media_type": "episode", "title": "Episode 1"},
            {"media_type": "music", "title": "Song 1"},
        ]
        
        # Filter for movies
        movie_records = processor.filter_by_media_type(records, ["movie"])
        assert len(movie_records) == 1
        assert movie_records[0]["title"] == "Movie 1"
        
        # Filter for TV content (should include both "tv" and "episode")
        tv_records = processor.filter_by_media_type(records, ["tv"])
        assert len(tv_records) == 2
        
        # Filter for multiple types
        multi_records = processor.filter_by_media_type(records, ["movie", "music"])
        assert len(multi_records) == 2
    
    def test_get_preferred_order(self) -> None:
        """Test getting preferred media type order."""
        processor = MediaTypeProcessor()
        
        order = processor.get_preferred_order()
        
        # Should start with movie, tv for consistent stacking
        assert order[0] == "movie"
        assert order[1] == "tv"
        assert "music" in order
        assert "other" in order
