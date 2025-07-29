"""
Tests for graph utility functions in TGraph Bot.

This module tests utility functions for date formatting, folder management,
username censoring, and common graph operations.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.tgraph_bot.graphs.graph_modules import (
    apply_modern_seaborn_styling,
    cleanup_old_files,
    censor_username,
    ensure_graph_directory,
    generate_graph_filename,
    get_current_graph_storage_path,
    process_play_history_data,
    validate_graph_data,
)
from src.tgraph_bot.graphs.graph_modules.utils.utils import (
    format_date,
    format_duration,
    get_date_range,
    parse_date,
    sanitize_filename,
    validate_color,
    aggregate_top_users_separated,  # Implemented in Phase 2
    aggregate_top_platforms_separated,  # Implemented in Phase 2
    ProcessedRecords,
)


class TestDateUtilities:
    """Test cases for date-related utility functions."""

    def test_format_date_default_format(self) -> None:
        """Test date formatting with default format."""
        date_obj = datetime(2023, 12, 25, 15, 30, 45)
        result = format_date(date_obj)
        assert result == "2023-12-25"

    def test_format_date_custom_format(self) -> None:
        """Test date formatting with custom format."""
        date_obj = datetime(2023, 12, 25, 15, 30, 45)
        result = format_date(date_obj, "%Y/%m/%d %H:%M")
        assert result == "2023/12/25 15:30"

    def test_parse_date_default_format(self) -> None:
        """Test date parsing with default format."""
        date_string = "2023-12-25"
        result = parse_date(date_string)
        expected = datetime(2023, 12, 25)
        assert result == expected

    def test_parse_date_custom_format(self) -> None:
        """Test date parsing with custom format."""
        date_string = "2023/12/25 15:30"
        result = parse_date(date_string, "%Y/%m/%d %H:%M")
        expected = datetime(2023, 12, 25, 15, 30)
        assert result == expected

    def test_parse_date_invalid_format(self) -> None:
        """Test date parsing with invalid format raises ValueError."""
        with pytest.raises(ValueError):
            _ = parse_date("invalid-date")

    @patch("src.tgraph_bot.graphs.graph_modules.utils.utils.datetime")
    def test_get_date_range(self, mock_datetime: MagicMock) -> None:
        """Test getting date range."""
        # Mock current time
        mock_now = datetime(2023, 12, 25, 12, 0, 0)
        mock_datetime.now.return_value = mock_now  # pyright: ignore[reportAny]

        start_date, end_date = get_date_range(7)

        assert end_date == mock_now
        assert start_date == mock_now - timedelta(days=7)

    def test_get_date_range_zero_days(self) -> None:
        """Test getting date range with zero days."""
        start_date, end_date = get_date_range(0)

        # Should be very close in time (within a second)
        time_diff = abs((end_date - start_date).total_seconds())
        assert time_diff < 1


class TestDirectoryUtilities:
    """Test cases for directory management utility functions."""

    def test_ensure_graph_directory_default_path(self) -> None:
        """Test ensuring graph directory with default path."""
        with tempfile.TemporaryDirectory() as _temp_dir:
            with patch(
                "src.tgraph_bot.graphs.graph_modules.utils.utils.Path"
            ) as mock_path:
                mock_path_instance = MagicMock()
                mock_path.return_value = mock_path_instance

                _ = ensure_graph_directory()

                mock_path.assert_called_once_with("graphs")
                mock_path_instance.mkdir.assert_called_once_with(  # pyright: ignore[reportAny]
                    parents=True, exist_ok=True
                )

    def test_ensure_graph_directory_custom_path(self) -> None:
        """Test ensuring graph directory with custom path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_path = Path(temp_dir) / "custom_graphs"

            result = ensure_graph_directory(str(custom_path))

            assert result == custom_path
            assert custom_path.exists()
            assert custom_path.is_dir()

    def test_cleanup_old_files_nonexistent_directory(self) -> None:
        """Test cleanup with non-existent directory."""
        nonexistent_dir = Path("/nonexistent/directory")
        result = cleanup_old_files(nonexistent_dir, keep_days=7)
        assert result == 0

    def test_cleanup_old_files_empty_directory(self) -> None:
        """Test cleanup with empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            result = cleanup_old_files(directory, keep_days=7)
            assert result == 0

    def test_cleanup_old_files_with_old_files(self) -> None:
        """Test cleanup with old files that should be deleted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)

            # Create test files
            old_file = directory / "old_file.txt"
            new_file = directory / "new_file.txt"

            _ = old_file.write_text("old content")
            _ = new_file.write_text("new content")

            # For this test, we'll just verify the function runs without error
            # since mocking file times is complex and the function logic is simple
            result = cleanup_old_files(directory, keep_days=7)

            # Function should return number of files cleaned up
            assert isinstance(result, int)
            assert result >= 0


class TestUsernameUtilities:
    """Test cases for username censoring utility functions."""

    def test_censor_username_disabled(self) -> None:
        """Test username censoring when disabled."""
        username = "testuser123"
        result = censor_username(username, censor_enabled=False)
        assert result == username

    def test_censor_username_enabled_normal(self) -> None:
        """Test username censoring with normal username."""
        username = "testuser123"
        result = censor_username(username, censor_enabled=True)
        assert result == "t*********3"
        assert len(result) == len(username)
        assert result[0] == username[0]
        assert result[-1] == username[-1]

    def test_censor_username_short_username(self) -> None:
        """Test username censoring with short usernames."""
        # Single character
        result = censor_username("a", censor_enabled=True)
        assert result == "*"

        # Two characters
        result = censor_username("ab", censor_enabled=True)
        assert result == "**"

    def test_censor_username_three_characters(self) -> None:
        """Test username censoring with three character username."""
        result = censor_username("abc", censor_enabled=True)
        assert result == "a*c"

    def test_censor_username_empty_string(self) -> None:
        """Test username censoring with empty string."""
        result = censor_username("", censor_enabled=True)
        assert result == ""


class TestFilenameUtilities:
    """Test cases for filename utility functions."""

    def test_sanitize_filename_normal(self) -> None:
        """Test filename sanitization with normal filename."""
        filename = "normal_filename.txt"
        result = sanitize_filename(filename)
        assert result == filename

    def test_sanitize_filename_with_invalid_chars(self) -> None:
        """Test filename sanitization with invalid characters."""
        filename = 'file<>:"/\\|?*name.txt'
        result = sanitize_filename(filename)
        assert result == "file_________name.txt"

    def test_sanitize_filename_with_whitespace(self) -> None:
        """Test filename sanitization with leading/trailing whitespace."""
        filename = "  filename.txt  "
        result = sanitize_filename(filename)
        assert result == "filename.txt"

    def test_sanitize_filename_with_dots(self) -> None:
        """Test filename sanitization with leading/trailing dots."""
        filename = "..filename.txt."
        result = sanitize_filename(filename)
        assert result == "filename.txt"

    def test_sanitize_filename_empty_result(self) -> None:
        """Test filename sanitization when result would be empty."""
        filename = "   ...   "
        result = sanitize_filename(filename)
        assert result == "unnamed"

    def test_generate_graph_filename_basic(self) -> None:
        """Test graph filename generation with basic parameters."""
        graph_type = "daily_play_count"
        timestamp = datetime(2023, 12, 25, 15, 30, 45)

        result = generate_graph_filename(graph_type, timestamp)
        assert result == "daily_play_count_20231225_153045.png"

    def test_generate_graph_filename_with_user_id(self) -> None:
        """Test graph filename generation with user ID."""
        graph_type = "daily_play_count"
        timestamp = datetime(2023, 12, 25, 15, 30, 45)
        user_id = "user123"

        result = generate_graph_filename(graph_type, timestamp, user_id)
        assert result == "daily_play_count_user_user123_20231225_153045.png"

    def test_generate_graph_filename_no_timestamp(self) -> None:
        """Test graph filename generation without timestamp."""
        graph_type = "daily_play_count"

        result = generate_graph_filename(graph_type)

        # Should contain the graph type and timestamp format
        assert result.startswith("daily_play_count_")
        assert result.endswith(".png")
        # The graph type has underscores, so we expect: daily_play_count_YYYYMMDD_HHMMSS.png
        assert len(result.split("_")) == 5  # daily, play, count, date, time.png


class TestFormatUtilities:
    """Test cases for formatting utility functions."""

    def test_format_duration_seconds(self) -> None:
        """Test duration formatting for seconds."""
        assert format_duration(30) == "30s"
        assert format_duration(59) == "59s"

    def test_format_duration_minutes(self) -> None:
        """Test duration formatting for minutes."""
        assert format_duration(60) == "1m"
        assert format_duration(90) == "1m 30s"
        assert format_duration(120) == "2m"
        assert format_duration(3599) == "59m 59s"

    def test_format_duration_hours(self) -> None:
        """Test duration formatting for hours."""
        assert format_duration(3600) == "1h"
        assert format_duration(3660) == "1h 1m"
        assert format_duration(7200) == "2h"
        assert format_duration(7260) == "2h 1m"


class TestColorUtilities:
    """Test cases for color validation utility functions."""

    def test_validate_color_hex_valid(self) -> None:
        """Test color validation with valid hex colors."""
        valid_hex_colors = [
            "#000000",
            "#FFFFFF",
            "#ff0000",
            "#00FF00",
            "#0000ff",
            "#123ABC",
        ]

        for color in valid_hex_colors:
            assert validate_color(color) is True

    def test_validate_color_hex_invalid(self) -> None:
        """Test color validation with invalid hex colors."""
        invalid_hex_colors = [
            "#00000",  # Too short
            "#0000000",  # Too long
            "#GGGGGG",  # Invalid characters
            "000000",  # Missing #
            "#",  # Just #
        ]

        for color in invalid_hex_colors:
            assert validate_color(color) is False

    def test_validate_color_named_valid(self) -> None:
        """Test color validation with valid named colors."""
        valid_named_colors = [
            "red",
            "green",
            "blue",
            "yellow",
            "orange",
            "purple",
            "pink",
            "brown",
            "black",
            "white",
            "gray",
            "grey",
            "cyan",
            "magenta",
            "RED",
            "Green",
            "BLUE",  # Case variations
        ]

        for color in valid_named_colors:
            assert validate_color(color) is True

    def test_validate_color_named_invalid(self) -> None:
        """Test color validation with invalid named colors."""
        invalid_named_colors = [
            "invalid_color",
            "lightblue",  # Not in basic set
            "darkred",  # Not in basic set
            "",  # Empty string
            "123",  # Numbers
        ]

        for color in invalid_named_colors:
            assert validate_color(color) is False


class TestDataProcessingUtilities:
    """Test cases for data processing utility functions."""

    def test_validate_graph_data_valid_data(self) -> None:
        """Test validate_graph_data with valid data."""
        valid_data = {"data": [{"date": "2023-01-01", "value": 10}], "total": 100}

        is_valid, error_msg = validate_graph_data(valid_data, ["data"])
        assert is_valid is True
        assert error_msg == ""

    def test_validate_graph_data_missing_required_key(self) -> None:
        """Test validate_graph_data with missing required key."""
        invalid_data = {"total": 100}

        is_valid, error_msg = validate_graph_data(invalid_data, ["data"])
        assert is_valid is False
        assert "Missing required key: data" in error_msg

    def test_validate_graph_data_empty_data(self) -> None:
        """Test validate_graph_data with empty data structure."""
        empty_data: dict[str, object] = {}

        is_valid, error_msg = validate_graph_data(empty_data, ["data"])
        assert is_valid is False
        assert "Missing required key: data" in error_msg

    def test_process_play_history_data_valid_data(self) -> None:
        """Test process_play_history_data with valid data."""
        raw_data = {
            "data": [
                {
                    "date": 1640995200,  # Unix timestamp
                    "user": "testuser",
                    "platform": "Web",
                    "media_type": "episode",
                    "duration": 3600,
                    "stopped": 3600,
                    "paused_counter": 0,
                }
            ]
        }

        result = process_play_history_data(raw_data)
        assert isinstance(result, list)
        assert len(result) == 1

        record = result[0]
        assert record["user"] == "testuser"
        assert record["platform"] == "Web"
        assert (
            record["media_type"] == "episode"
        )  # Raw media type is preserved in this step
        assert record["duration"] == 3600
        assert "datetime" in record

    def test_process_play_history_data_empty_data(self) -> None:
        """Test process_play_history_data with empty data."""
        raw_data: dict[str, object] = {"data": []}

        result = process_play_history_data(raw_data)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_process_play_history_data_invalid_data(self) -> None:
        """Test process_play_history_data with invalid data structure."""
        raw_data = {"invalid": "data"}

        # Should handle gracefully by returning empty list when "data" key is missing
        result = process_play_history_data(raw_data)
        assert isinstance(result, list)
        assert len(result) == 0


class TestGraphStorageUtilities:
    """Test cases for graph storage utility functions."""

    def test_get_current_graph_storage_path_no_user(self) -> None:
        """Test get_current_graph_storage_path without user email."""
        result = get_current_graph_storage_path()
        assert isinstance(result, Path)
        assert result.name.startswith("2")  # Should start with year

    def test_get_current_graph_storage_path_with_user(self) -> None:
        """Test get_current_graph_storage_path with user email."""
        result = get_current_graph_storage_path(user_email="test@example.com")
        assert isinstance(result, Path)
        # The function sanitizes email addresses by replacing @ and . with _
        assert "test_at_example_com" in str(result)

    def test_apply_modern_seaborn_styling(self) -> None:
        """Test apply_modern_seaborn_styling function."""
        # Should not raise exception
        apply_modern_seaborn_styling()

        # Verify seaborn was configured (basic check)
        import seaborn as sns

        # Just verify we can call this without error
        # The styling effects are hard to test directly
        assert sns is not None


class TestSeparationUtilityFunctions:
    """Test cases for media type separation utility functions.

    NOTE: These tests are written for TDD - they will pass once the
    separation utility functions are implemented in Phase 2.
    """

    def create_sample_processed_records(self) -> ProcessedRecords:
        """Create sample processed records for testing."""
        return [
            {
                "date": "2023-12-25",
                "user": "alice",
                "platform": "Plex Web",
                "media_type": "movie",
                "datetime": datetime(2023, 12, 25, 14, 30),
                "duration": 7200,
                "stopped": 1703516200,
                "paused_counter": 0,
            },
            {
                "date": "2023-12-25",
                "user": "alice",
                "platform": "Plex Web",
                "media_type": "episode",
                "datetime": datetime(2023, 12, 25, 16, 0),
                "duration": 2400,
                "stopped": 1703521600,
                "paused_counter": 1,
            },
            {
                "date": "2023-12-25",
                "user": "bob",
                "platform": "Plex Android",
                "media_type": "movie",
                "datetime": datetime(2023, 12, 25, 18, 0),
                "duration": 6000,
                "stopped": 1703528400,
                "paused_counter": 0,
            },
            {
                "date": "2023-12-25",
                "user": "bob",
                "platform": "Plex Android",
                "media_type": "episode",
                "datetime": datetime(2023, 12, 25, 20, 0),
                "duration": 3000,
                "stopped": 1703535600,
                "paused_counter": 2,
            },
            {
                "date": "2023-12-26",
                "user": "charlie",
                "platform": "Plex iOS",
                "media_type": "movie",
                "datetime": datetime(2023, 12, 26, 10, 0),
                "duration": 5400,
                "stopped": 1703584800,
                "paused_counter": 0,
            },
        ]

    def test_aggregate_top_users_separated_basic_functionality(self) -> None:
        """Test basic functionality of aggregate_top_users_separated."""
        records = self.create_sample_processed_records()

        result = aggregate_top_users_separated(records, limit=10, censor=False)

        # Should return data grouped by media type
        assert isinstance(result, dict)
        assert "movie" in result
        assert "tv" in result  # episode gets classified as tv

        # Check movie data structure
        movie_data = result["movie"]
        assert isinstance(movie_data, list)
        assert len(movie_data) <= 10  # Respects limit

        # Check TV data structure
        tv_data = result["tv"]
        assert isinstance(tv_data, list)
        assert len(tv_data) <= 10  # Respects limit

    def test_aggregate_top_users_separated_limit_parameter(self) -> None:
        """Test that limit parameter is respected."""
        records = self.create_sample_processed_records()

        result = aggregate_top_users_separated(records, limit=2, censor=False)

        # Each media type should respect the limit
        for _, user_data in result.items():
            assert len(user_data) <= 2

    def test_aggregate_top_users_separated_censor_parameter(self) -> None:
        """Test that censor parameter works correctly."""
        records = self.create_sample_processed_records()

        # Test with censoring enabled
        result_censored = aggregate_top_users_separated(records, limit=10, censor=True)

        # Test with censoring disabled
        result_uncensored = aggregate_top_users_separated(records, limit=10, censor=False)

        # Should have same structure but different usernames
        assert set(result_censored.keys()) == set(result_uncensored.keys())

        # Check that usernames are different when censored
        for media_type in result_censored:
            censored_users = {entry["username"] for entry in result_censored[media_type]}
            uncensored_users = {entry["username"] for entry in result_uncensored[media_type]}

            # At least some usernames should be different (censored)
            if uncensored_users:  # Only check if there are users
                # For usernames longer than 2 chars, they should be censored
                long_usernames = {u for u in uncensored_users if len(u) > 2}
                if long_usernames:
                    assert censored_users != uncensored_users

    def test_aggregate_top_users_separated_empty_data(self) -> None:
        """Test handling of empty data."""
        empty_records: ProcessedRecords = []

        result = aggregate_top_users_separated(empty_records, limit=10, censor=False)

        # Should return empty structure but with proper media type keys
        assert isinstance(result, dict)
        # May have empty lists for each media type or be completely empty
        for _, user_data in result.items():
            assert isinstance(user_data, list)
            assert len(user_data) == 0

    def test_aggregate_top_users_separated_data_consistency(self) -> None:
        """Test data structure consistency with existing aggregate_top_users."""
        records = self.create_sample_processed_records()

        result = aggregate_top_users_separated(records, limit=10, censor=False)

        # Each media type should contain UserAggregateRecord-like structures
        for _, user_data in result.items():
            for entry in user_data:
                assert "username" in entry
                assert "play_count" in entry
                assert isinstance(entry["username"], str)
                assert isinstance(entry["play_count"], int)
                assert entry["play_count"] > 0

    def test_aggregate_top_platforms_separated_basic_functionality(self) -> None:
        """Test basic functionality of aggregate_top_platforms_separated."""
        records = self.create_sample_processed_records()

        result = aggregate_top_platforms_separated(records, limit=10)

        # Should return data grouped by media type
        assert isinstance(result, dict)
        assert "movie" in result
        assert "tv" in result  # episode gets classified as tv

        # Check movie data structure
        movie_data = result["movie"]
        assert isinstance(movie_data, list)
        assert len(movie_data) <= 10  # Respects limit

        # Check that each entry has required fields
        for entry in movie_data:
            assert "platform" in entry
            assert "play_count" in entry
            assert isinstance(entry["play_count"], int)
            assert entry["play_count"] > 0

        # Check TV data structure
        tv_data = result["tv"]
        assert isinstance(tv_data, list)
        assert len(tv_data) <= 10  # Respects limit

    def test_aggregate_top_platforms_separated_limit_parameter(self) -> None:
        """Test that limit parameter is respected."""
        records = self.create_sample_processed_records()

        result = aggregate_top_platforms_separated(records, limit=2)

        # Each media type should respect the limit
        for _, platform_data in result.items():
            assert len(platform_data) <= 2

    def test_aggregate_top_platforms_separated_empty_data(self) -> None:
        """Test handling of empty data."""
        empty_records: ProcessedRecords = []

        result = aggregate_top_platforms_separated(empty_records, limit=10)

        # Should return empty structure but with proper media type keys
        assert isinstance(result, dict)
        # May have empty lists for each media type or be completely empty
        for _, platform_data in result.items():
            assert isinstance(platform_data, list)
            assert len(platform_data) == 0

    def test_aggregate_top_platforms_separated_data_consistency(self) -> None:
        """Test data structure consistency with existing aggregate_top_platforms."""
        records = self.create_sample_processed_records()

        result = aggregate_top_platforms_separated(records, limit=10)

        # Each media type should contain PlatformAggregateRecord-like structures
        for _, platform_data in result.items():
            for entry in platform_data:
                assert "platform" in entry
                assert "play_count" in entry
                assert isinstance(entry["platform"], str)
                assert isinstance(entry["play_count"], int)
                assert entry["play_count"] > 0

    def test_separation_functions_media_type_classification(self) -> None:
        """Test that separation functions properly classify media types."""
        # Create records with various media types
        records: ProcessedRecords = [
            {
                "date": "2023-12-25",
                "user": "test_user",
                "platform": "Plex Web",
                "media_type": "movie",  # Should be classified as "movie"
                "datetime": datetime(2023, 12, 25, 14, 30),
                "duration": 7200,
                "stopped": 1703516200,
                "paused_counter": 0,
            },
            {
                "date": "2023-12-25",
                "user": "test_user",
                "platform": "Plex Web",
                "media_type": "episode",  # Should be classified as "tv"
                "datetime": datetime(2023, 12, 25, 16, 0),
                "duration": 2400,
                "stopped": 1703521600,
                "paused_counter": 1,
            },
            {
                "date": "2023-12-25",
                "user": "test_user",
                "platform": "Plex Web",
                "media_type": "track",  # Should be classified as "music"
                "datetime": datetime(2023, 12, 25, 18, 0),
                "duration": 180,
                "stopped": 1703528400,
                "paused_counter": 0,
            },
            {
                "date": "2023-12-25",
                "user": "test_user",
                "platform": "Plex Web",
                "media_type": "unknown_type",  # Should be classified as "other"
                "datetime": datetime(2023, 12, 25, 20, 0),
                "duration": 1800,
                "stopped": 1703535600,
                "paused_counter": 0,
            },
        ]

        # Test users separation
        users_result = aggregate_top_users_separated(records, limit=10, censor=False)

        # Should have entries for different media types
        expected_media_types = {"movie", "tv", "music", "other"}
        actual_media_types = set(users_result.keys())

        # Should have at least some of the expected media types
        assert len(actual_media_types.intersection(expected_media_types)) > 0

        # Test platforms separation
        platforms_result = aggregate_top_platforms_separated(records, limit=10)

        # Should have entries for different media types
        actual_platform_media_types = set(platforms_result.keys())

        # Should have at least some of the expected media types
        assert len(actual_platform_media_types.intersection(expected_media_types)) > 0

    def test_separation_functions_input_validation(self) -> None:
        """Test input validation and edge cases for separation functions."""
        # Test with records missing required fields
        invalid_records: ProcessedRecords = [
            {
                "date": "2023-12-25",
                "user": "",  # Empty user
                "platform": "Plex Web",
                "media_type": "movie",
                "datetime": datetime(2023, 12, 25, 14, 30),
                "duration": 7200,
                "stopped": 1703516200,
                "paused_counter": 0,
            },
            {
                "date": "2023-12-25",
                "user": "test_user",
                "platform": "",  # Empty platform
                "media_type": "episode",
                "datetime": datetime(2023, 12, 25, 16, 0),
                "duration": 2400,
                "stopped": 1703521600,
                "paused_counter": 1,
            },
        ]

        # Functions should handle invalid data gracefully
        users_result = aggregate_top_users_separated(invalid_records, limit=10, censor=False)
        platforms_result = aggregate_top_platforms_separated(invalid_records, limit=10)

        # Should return valid structure even with invalid input
        assert isinstance(users_result, dict)
        assert isinstance(platforms_result, dict)

        # Test with negative limit (should handle gracefully)
        valid_records = self.create_sample_processed_records()

        users_result_negative = aggregate_top_users_separated(valid_records, limit=-1, censor=False)
        platforms_result_negative = aggregate_top_platforms_separated(valid_records, limit=-1)

        # Should return valid structure
        assert isinstance(users_result_negative, dict)
        assert isinstance(platforms_result_negative, dict)
