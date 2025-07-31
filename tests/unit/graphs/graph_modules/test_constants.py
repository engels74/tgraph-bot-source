"""
Unit tests for graph constants module.

This module tests the constants module to ensure all string constants,
validation functions, and localization support work correctly.
"""

from __future__ import annotations

import pytest

from src.tgraph_bot.graphs.graph_modules.types.constants import (
    DAYS_OF_WEEK,
    DATETIME_FORMATS,
    MEDIA_TYPES,
    MEDIA_TYPE_DISPLAY_NAMES,
    MEDIA_TYPE_ALIASES,
    GRAPH_TYPES,
    GRAPH_TITLES,
    DEFAULT_COLORS,
    COLOR_PALETTES,
    FILE_EXTENSIONS,
    FILE_FORMATS,
    PATH_PATTERNS,
    validate_color,
    validate_graph_type,
    validate_media_type,
    validate_day_of_week,
    get_localized_day_names,
    get_localized_media_type_names,
    get_localized_graph_titles,
)


class TestDaysOfWeek:
    """Test cases for days of week constants."""

    def test_day_constants(self) -> None:
        """Test that day constants are properly defined."""
        assert DAYS_OF_WEEK.MONDAY == "Monday"
        assert DAYS_OF_WEEK.TUESDAY == "Tuesday"
        assert DAYS_OF_WEEK.WEDNESDAY == "Wednesday"
        assert DAYS_OF_WEEK.THURSDAY == "Thursday"
        assert DAYS_OF_WEEK.FRIDAY == "Friday"
        assert DAYS_OF_WEEK.SATURDAY == "Saturday"
        assert DAYS_OF_WEEK.SUNDAY == "Sunday"

    def test_get_ordered_list(self) -> None:
        """Test getting ordered list of days."""
        ordered_days = DAYS_OF_WEEK.get_ordered_list()
        expected = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        assert ordered_days == expected
        assert len(ordered_days) == 7

    def test_get_weekend_days(self) -> None:
        """Test getting weekend days."""
        weekend_days = DAYS_OF_WEEK.get_weekend_days()
        assert weekend_days == ["Saturday", "Sunday"]
        assert len(weekend_days) == 2

    def test_get_weekday_days(self) -> None:
        """Test getting weekday days."""
        weekday_days = DAYS_OF_WEEK.get_weekday_days()
        expected = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        assert weekday_days == expected
        assert len(weekday_days) == 5


class TestDateTimeFormats:
    """Test cases for date/time format constants."""

    def test_format_constants(self) -> None:
        """Test that format constants are properly defined."""
        assert DATETIME_FORMATS.DATE_FORMAT == "%Y-%m-%d"
        assert DATETIME_FORMATS.DATETIME_FORMAT == "%Y-%m-%d %H:%M:%S"
        assert DATETIME_FORMATS.TIMESTAMP_FORMAT == "%Y%m%d_%H%M%S"
        assert DATETIME_FORMATS.MONTH_FORMAT == "%Y-%m"
        assert DATETIME_FORMATS.HOUR_FORMAT == "%H"
        assert DATETIME_FORMATS.DISPLAY_DATE_FORMAT == "%B %d, %Y"
        assert DATETIME_FORMATS.DISPLAY_DATETIME_FORMAT == "%B %d, %Y at %I:%M %p"


class TestMediaTypes:
    """Test cases for media type constants."""

    def test_media_type_constants(self) -> None:
        """Test that media type constants are properly defined."""
        assert MEDIA_TYPES.MOVIE == "movie"
        assert MEDIA_TYPES.TV == "tv"
        assert MEDIA_TYPES.EPISODE == "episode"
        assert MEDIA_TYPES.MUSIC == "music"
        assert MEDIA_TYPES.OTHER == "other"
        assert MEDIA_TYPES.UNKNOWN == "unknown"

    def test_get_all_types(self) -> None:
        """Test getting all media types."""
        all_types = MEDIA_TYPES.get_all_types()
        expected = ["movie", "tv", "episode", "music", "other", "unknown"]
        assert all_types == expected
        assert len(all_types) == 6

    def test_get_primary_types(self) -> None:
        """Test getting primary media types."""
        primary_types = MEDIA_TYPES.get_primary_types()
        assert primary_types == ["movie", "tv"]
        assert len(primary_types) == 2

    def test_display_names(self) -> None:
        """Test media type display names."""
        assert MEDIA_TYPE_DISPLAY_NAMES.MOVIE == "Movies"
        assert MEDIA_TYPE_DISPLAY_NAMES.TV == "TV Series"
        assert MEDIA_TYPE_DISPLAY_NAMES.EPISODE == "Episodes"
        assert MEDIA_TYPE_DISPLAY_NAMES.MUSIC == "Music"
        assert MEDIA_TYPE_DISPLAY_NAMES.OTHER == "Other"
        assert MEDIA_TYPE_DISPLAY_NAMES.UNKNOWN == "Unknown"

    def test_aliases(self) -> None:
        """Test media type aliases."""
        assert MEDIA_TYPE_ALIASES.MOVIE_ALIASES == ["movie", "film", "cinema"]
        assert MEDIA_TYPE_ALIASES.TV_ALIASES == ["tv", "episode", "show", "series"]
        assert MEDIA_TYPE_ALIASES.MUSIC_ALIASES == [
            "music",
            "track",
            "album",
            "artist",
            "song",
        ]
        assert MEDIA_TYPE_ALIASES.OTHER_ALIASES == ["other", "unknown"]


class TestGraphTypes:
    """Test cases for graph type constants."""

    def test_graph_type_constants(self) -> None:
        """Test that graph type constants are properly defined."""
        assert GRAPH_TYPES.DAILY_PLAY_COUNT == "daily_play_count"
        assert GRAPH_TYPES.PLAY_COUNT_BY_DAYOFWEEK == "play_count_by_dayofweek"
        assert GRAPH_TYPES.PLAY_COUNT_BY_HOUROFDAY == "play_count_by_hourofday"
        assert GRAPH_TYPES.PLAY_COUNT_BY_MONTH == "play_count_by_month"
        assert GRAPH_TYPES.TOP_10_PLATFORMS == "top_10_platforms"
        assert GRAPH_TYPES.TOP_10_USERS == "top_10_users"
        assert GRAPH_TYPES.SAMPLE_GRAPH == "sample_graph"

    def test_get_all_types(self) -> None:
        """Test getting all graph types."""
        all_types = GRAPH_TYPES.get_all_types()
        expected = [
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "play_count_by_month",
            "top_10_platforms",
            "top_10_users",
            "sample_graph",
        ]
        assert all_types == expected
        assert len(all_types) == 7

    def test_get_tautulli_types(self) -> None:
        """Test getting Tautulli-specific graph types."""
        tautulli_types = GRAPH_TYPES.get_tautulli_types()
        expected = [
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "play_count_by_month",
            "top_10_platforms",
            "top_10_users",
        ]
        assert tautulli_types == expected
        assert len(tautulli_types) == 6
        assert "sample_graph" not in tautulli_types

    def test_graph_titles(self) -> None:
        """Test graph title constants."""
        assert GRAPH_TITLES.DAILY_PLAY_COUNT == "Daily Play Count"
        assert GRAPH_TITLES.PLAY_COUNT_BY_DAYOFWEEK == "Play Count by Day of Week"
        assert GRAPH_TITLES.PLAY_COUNT_BY_HOUROFDAY == "Play Count by Hour of Day"
        assert GRAPH_TITLES.PLAY_COUNT_BY_MONTH == "Play Count by Month"
        assert GRAPH_TITLES.TOP_10_PLATFORMS == "Top 10 Platforms"
        assert GRAPH_TITLES.TOP_10_USERS == "Top 10 Users"
        assert GRAPH_TITLES.SAMPLE_GRAPH == "Sample Graph"


class TestDefaultColors:
    """Test cases for default color constants."""

    def test_primary_colors(self) -> None:
        """Test primary color constants."""
        assert DEFAULT_COLORS.TV_COLOR == "#1f77b4"
        assert DEFAULT_COLORS.MOVIE_COLOR == "#ff7f0e"
        assert DEFAULT_COLORS.MUSIC_COLOR == "#2ca02c"
        assert DEFAULT_COLORS.OTHER_COLOR == "#d62728"
        assert DEFAULT_COLORS.UNKNOWN_COLOR == "#666666"

    def test_background_colors(self) -> None:
        """Test background color constants."""
        assert DEFAULT_COLORS.GRAPH_BACKGROUND == "#ffffff"
        assert DEFAULT_COLORS.FIGURE_BACKGROUND == "#ffffff"

    def test_annotation_colors(self) -> None:
        """Test annotation color constants."""
        assert DEFAULT_COLORS.ANNOTATION_COLOR == "#ff0000"
        assert DEFAULT_COLORS.ANNOTATION_OUTLINE == "#000000"
        assert DEFAULT_COLORS.PEAK_ANNOTATION == "#ffcc00"
        assert DEFAULT_COLORS.PEAK_ANNOTATION_TEXT == "#000000"

    def test_grid_and_axis_colors(self) -> None:
        """Test grid and axis color constants."""
        assert DEFAULT_COLORS.GRID_COLOR == "#cccccc"
        assert DEFAULT_COLORS.AXIS_COLOR == "#333333"

    def test_get_media_type_colors(self) -> None:
        """Test getting media type color mapping."""
        color_mapping = DEFAULT_COLORS.get_media_type_colors()
        expected = {
            "tv": "#1f77b4",
            "movie": "#ff7f0e",
            "music": "#2ca02c",
            "other": "#d62728",
            "unknown": "#666666",
        }
        assert color_mapping == expected
        assert len(color_mapping) == 5


class TestColorPalettes:
    """Test cases for color palette constants."""

    def test_seaborn_default_palette(self) -> None:
        """Test Seaborn default color palette."""
        palette = COLOR_PALETTES.SEABORN_DEFAULT
        expected = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
        assert palette == expected
        assert len(palette) == 6

    def test_named_palettes(self) -> None:
        """Test named color palettes."""
        assert COLOR_PALETTES.VIRIDIS == "viridis"
        assert COLOR_PALETTES.PLASMA == "plasma"
        assert COLOR_PALETTES.INFERNO == "inferno"
        assert COLOR_PALETTES.MAGMA == "magma"



class TestFileConstants:
    """Test cases for file and path constants."""

    def test_file_extensions(self) -> None:
        """Test file extension constants."""
        assert FILE_EXTENSIONS.PNG == ".png"
        assert FILE_EXTENSIONS.JPG == ".jpg"
        assert FILE_EXTENSIONS.JPEG == ".jpeg"
        assert FILE_EXTENSIONS.SVG == ".svg"
        assert FILE_EXTENSIONS.PDF == ".pdf"

    def test_get_image_extensions(self) -> None:
        """Test getting image extensions."""
        image_extensions = FILE_EXTENSIONS.get_image_extensions()
        expected = [".png", ".jpg", ".jpeg", ".svg"]
        assert image_extensions == expected
        assert len(image_extensions) == 4

    def test_file_formats(self) -> None:
        """Test file format constants."""
        assert FILE_FORMATS.PNG == "png"
        assert FILE_FORMATS.JPG == "jpg"
        assert FILE_FORMATS.JPEG == "jpeg"
        assert FILE_FORMATS.SVG == "svg"
        assert FILE_FORMATS.PDF == "pdf"

    def test_path_patterns(self) -> None:
        """Test path pattern constants."""
        assert PATH_PATTERNS.INVALID_FILENAME_CHARS == r'[<>:"/\\|?*]'
        assert PATH_PATTERNS.REPLACEMENT_CHAR == "_"
        assert PATH_PATTERNS.DEFAULT_FILENAME == "unnamed"
        assert PATH_PATTERNS.EMAIL_AT_REPLACEMENT == "_at_"
        assert PATH_PATTERNS.EMAIL_DOT_REPLACEMENT == "_"


class TestValidationFunctions:
    """Test cases for validation functions."""

    def test_validate_color(self) -> None:
        """Test color validation function."""
        # Valid colors
        assert validate_color("#1f77b4") is True
        assert validate_color("#FF7F0E") is True
        assert validate_color("#ffffff") is True
        assert validate_color("#000000") is True

        # Invalid colors
        assert validate_color("1f77b4") is False  # Missing #
        assert validate_color("#1f77b") is False  # Too short
        assert validate_color("#1f77b44") is False  # Too long
        assert validate_color("#gggggg") is False  # Invalid hex chars
        assert validate_color("blue") is False  # Named color
        assert validate_color("") is False  # Empty string
        assert validate_color(None) is False  # None
        assert validate_color(123) is False  # Number
        assert validate_color([]) is False  # List

    def test_validate_graph_type(self) -> None:
        """Test graph type validation function."""
        # Valid graph types
        assert validate_graph_type("daily_play_count") is True
        assert validate_graph_type("play_count_by_dayofweek") is True
        assert validate_graph_type("play_count_by_hourofday") is True
        assert validate_graph_type("play_count_by_month") is True
        assert validate_graph_type("top_10_platforms") is True
        assert validate_graph_type("top_10_users") is True
        assert validate_graph_type("sample_graph") is True

        # Invalid graph types
        assert validate_graph_type("invalid_graph") is False
        assert validate_graph_type("daily_play") is False
        assert validate_graph_type("") is False
        assert validate_graph_type(None) is False
        assert validate_graph_type(123) is False
        assert validate_graph_type([]) is False

    def test_validate_media_type(self) -> None:
        """Test media type validation function."""
        # Valid media types
        assert validate_media_type("movie") is True
        assert validate_media_type("tv") is True
        assert validate_media_type("episode") is True
        assert validate_media_type("music") is True
        assert validate_media_type("other") is True
        assert validate_media_type("unknown") is True

        # Invalid media types
        assert validate_media_type("film") is False  # Alias, not base type
        assert validate_media_type("show") is False  # Alias, not base type
        assert validate_media_type("invalid") is False
        assert validate_media_type("") is False
        assert validate_media_type(None) is False
        assert validate_media_type(123) is False
        assert validate_media_type([]) is False

    def test_validate_day_of_week(self) -> None:
        """Test day of week validation function."""
        # Valid days
        assert validate_day_of_week("Monday") is True
        assert validate_day_of_week("Tuesday") is True
        assert validate_day_of_week("Wednesday") is True
        assert validate_day_of_week("Thursday") is True
        assert validate_day_of_week("Friday") is True
        assert validate_day_of_week("Saturday") is True
        assert validate_day_of_week("Sunday") is True

        # Invalid days
        assert validate_day_of_week("monday") is False  # Wrong case
        assert validate_day_of_week("Mon") is False  # Abbreviated
        assert validate_day_of_week("Invalid") is False
        assert validate_day_of_week("") is False
        assert validate_day_of_week(None) is False
        assert validate_day_of_week(123) is False
        assert validate_day_of_week([]) is False


class TestLocalizationFunctions:
    """Test cases for localization functions."""

    def test_get_localized_day_names(self) -> None:
        """Test getting localized day names."""
        # Default locale (English)
        day_names = get_localized_day_names()
        expected = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        assert day_names == expected

        # Explicit English locale
        day_names_en = get_localized_day_names("en")
        assert day_names_en == expected

        # Other locales (currently return English)
        day_names_es = get_localized_day_names("es")
        assert day_names_es == expected  # TODO: Will change when i18n is implemented

    def test_get_localized_media_type_names(self) -> None:
        """Test getting localized media type names."""
        # Default locale (English)
        media_names = get_localized_media_type_names()
        expected = {
            "movie": "Movies",
            "tv": "TV Series",
            "episode": "Episodes",
            "music": "Music",
            "other": "Other",
            "unknown": "Unknown",
        }
        assert media_names == expected

        # Explicit English locale
        media_names_en = get_localized_media_type_names("en")
        assert media_names_en == expected

        # Other locales (currently return English)
        media_names_es = get_localized_media_type_names("es")
        assert media_names_es == expected  # TODO: Will change when i18n is implemented

    def test_get_localized_graph_titles(self) -> None:
        """Test getting localized graph titles."""
        # Default locale (English)
        graph_titles = get_localized_graph_titles()
        expected = {
            "daily_play_count": "Daily Play Count",
            "play_count_by_dayofweek": "Play Count by Day of Week",
            "play_count_by_hourofday": "Play Count by Hour of Day",
            "play_count_by_month": "Play Count by Month",
            "top_10_platforms": "Top 10 Platforms",
            "top_10_users": "Top 10 Users",
            "sample_graph": "Sample Graph",
        }
        assert graph_titles == expected

        # Explicit English locale
        graph_titles_en = get_localized_graph_titles("en")
        assert graph_titles_en == expected

        # Other locales (currently return English)
        graph_titles_es = get_localized_graph_titles("es")
        assert graph_titles_es == expected  # TODO: Will change when i18n is implemented


class TestConstantImmutability:
    """Test cases for constant immutability."""

    def test_constants_are_immutable(self) -> None:
        """Test that constants cannot be modified."""
        # Test that dataclass instances are frozen
        with pytest.raises(AttributeError):
            setattr(DAYS_OF_WEEK, "MONDAY", "Modified")

        with pytest.raises(AttributeError):
            setattr(MEDIA_TYPES, "MOVIE", "modified")

        with pytest.raises(AttributeError):
            setattr(DEFAULT_COLORS, "TV_COLOR", "#modified")

    def test_list_methods_return_new_instances(self) -> None:
        """Test that list methods return new instances, not references."""
        days1 = DAYS_OF_WEEK.get_ordered_list()
        days2 = DAYS_OF_WEEK.get_ordered_list()

        # Should be equal but not the same object
        assert days1 == days2
        assert days1 is not days2

        # Modifying one should not affect the other
        days1.append("Modified")
        assert len(days2) == 7
        assert "Modified" not in days2
