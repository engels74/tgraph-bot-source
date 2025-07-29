"""
Tests for unified scheduling utilities.

This module tests the unified scheduling utilities that handle next update
calculations using the unified timezone system.
"""

import pytest
from datetime import datetime, time, timedelta
from unittest.mock import patch

from src.tgraph_bot.utils.time.scheduling import (
    calculate_next_update_time,
    parse_fixed_time,
    is_valid_fixed_time,
    calculate_next_fixed_time,
    calculate_next_interval_time,
)
from src.tgraph_bot.utils.time.timezone import get_system_timezone


class TestFixedTimeValidation:
    """Test fixed time validation and parsing."""

    def test_is_valid_fixed_time_valid_formats(self) -> None:
        """Test valid fixed time formats."""
        valid_times = [
            "00:00",
            "12:00",
            "23:59",
            "09:30",
            "15:45",
            "XX:XX",  # Special case for disabled
        ]

        for time_str in valid_times:
            assert is_valid_fixed_time(time_str), f"'{time_str}' should be valid"

    def test_is_valid_fixed_time_invalid_formats(self) -> None:
        """Test invalid fixed time formats."""
        invalid_times = [
            "24:00",
            "12:60",
            "25:30",
            "12",
            "12:00:00",
            "abc:def",
            "",
            "12:ab",
            "ab:30",
            "12:3",
        ]

        for time_str in invalid_times:
            assert not is_valid_fixed_time(time_str), f"'{time_str}' should be invalid"

    def test_parse_fixed_time_valid(self) -> None:
        """Test parsing valid fixed time strings."""
        test_cases = [
            ("00:00", time(0, 0)),
            ("12:00", time(12, 0)),
            ("23:59", time(23, 59)),
            ("09:30", time(9, 30)),
            ("15:45", time(15, 45)),
        ]

        for time_str, expected_time in test_cases:
            result = parse_fixed_time(time_str)
            assert result == expected_time, (
                f"'{time_str}' should parse to {expected_time}"
            )

    def test_parse_fixed_time_disabled(self) -> None:
        """Test parsing disabled fixed time."""
        result = parse_fixed_time("XX:XX")
        assert result is None

    def test_parse_fixed_time_invalid(self) -> None:
        """Test parsing invalid fixed time strings."""
        invalid_times = ["24:00", "12:60", "abc:def", ""]

        for time_str in invalid_times:
            with pytest.raises(ValueError, match="Invalid fixed time format"):
                _ = parse_fixed_time(time_str)


class TestNextFixedTimeCalculation:
    """Test next fixed time calculation."""

    def test_calculate_next_fixed_time_same_day(self) -> None:
        """Test calculating next fixed time with UPDATE_DAYS=1 (should be next day)."""
        # Current time: 10:00, fixed time: 15:00, UPDATE_DAYS=1 -> should be tomorrow at 15:00
        # This respects the UPDATE_DAYS=1 interval requirement (fix for date calculation bug)
        current_time = datetime(2025, 7, 25, 10, 0, 0, tzinfo=get_system_timezone())
        fixed_time = time(15, 0)
        update_days = 1

        result = calculate_next_fixed_time(current_time, fixed_time, update_days)

        expected = datetime(2025, 7, 26, 15, 0, 0, tzinfo=get_system_timezone())
        assert result == expected

    def test_calculate_next_fixed_time_next_day(self) -> None:
        """Test calculating next fixed time on the next day."""
        # Current time: 16:00, fixed time: 15:00 -> should be tomorrow at 15:00
        current_time = datetime(2025, 7, 25, 16, 0, 0, tzinfo=get_system_timezone())
        fixed_time = time(15, 0)
        update_days = 1

        result = calculate_next_fixed_time(current_time, fixed_time, update_days)

        expected = datetime(2025, 7, 26, 15, 0, 0, tzinfo=get_system_timezone())
        assert result == expected

    def test_calculate_next_fixed_time_multiple_days(self) -> None:
        """Test calculating next fixed time with multiple day interval."""
        # Current time: 10:00, fixed time: 15:00, update_days: 3
        current_time = datetime(2025, 7, 25, 10, 0, 0, tzinfo=get_system_timezone())
        fixed_time = time(15, 0)
        update_days = 3

        result = calculate_next_fixed_time(current_time, fixed_time, update_days)

        # Should be 3 days from now at 15:00
        expected = datetime(2025, 7, 28, 15, 0, 0, tzinfo=get_system_timezone())
        assert result == expected

    def test_calculate_next_fixed_time_with_last_update(self) -> None:
        """Test calculating next fixed time considering last update."""
        current_time = datetime(2025, 7, 25, 10, 0, 0, tzinfo=get_system_timezone())
        fixed_time = time(15, 0)
        update_days = 2
        last_update = datetime(2025, 7, 24, 15, 0, 0, tzinfo=get_system_timezone())

        result = calculate_next_fixed_time(
            current_time, fixed_time, update_days, last_update
        )

        # Should be 2 days after last update at 15:00
        expected = datetime(2025, 7, 26, 15, 0, 0, tzinfo=get_system_timezone())
        assert result == expected

    def test_calculate_next_fixed_time_respects_minimum_interval(self) -> None:
        """Test that next fixed time respects minimum interval from last update."""
        current_time = datetime(2025, 7, 25, 10, 0, 0, tzinfo=get_system_timezone())
        fixed_time = time(15, 0)
        update_days = 7  # Weekly updates
        last_update = datetime(
            2025, 7, 24, 15, 0, 0, tzinfo=get_system_timezone()
        )  # Yesterday

        result = calculate_next_fixed_time(
            current_time, fixed_time, update_days, last_update
        )

        # Should be 7 days after last update, not today
        expected = datetime(2025, 7, 31, 15, 0, 0, tzinfo=get_system_timezone())
        assert result == expected


class TestNextIntervalTimeCalculation:
    """Test next interval time calculation."""

    def test_calculate_next_interval_time_basic(self) -> None:
        """Test basic interval time calculation."""
        current_time = datetime(2025, 7, 25, 14, 30, 0, tzinfo=get_system_timezone())
        update_days = 3

        result = calculate_next_interval_time(current_time, update_days)

        expected = current_time + timedelta(days=3)
        assert result == expected

    def test_calculate_next_interval_time_with_last_update(self) -> None:
        """Test interval time calculation with last update."""
        current_time = datetime(2025, 7, 25, 14, 30, 0, tzinfo=get_system_timezone())
        update_days = 2
        last_update = datetime(2025, 7, 23, 10, 0, 0, tzinfo=get_system_timezone())

        result = calculate_next_interval_time(current_time, update_days, last_update)

        # Should be 2 days after last update
        expected = datetime(2025, 7, 25, 10, 0, 0, tzinfo=get_system_timezone())
        assert result == expected

    def test_calculate_next_interval_time_past_due(self) -> None:
        """Test interval time calculation when update is past due."""
        current_time = datetime(2025, 7, 25, 14, 30, 0, tzinfo=get_system_timezone())
        update_days = 2
        last_update = datetime(
            2025, 7, 20, 10, 0, 0, tzinfo=get_system_timezone()
        )  # 5 days ago

        result = calculate_next_interval_time(current_time, update_days, last_update)

        # Should be 2 days after last update (even if in the past)
        expected = datetime(2025, 7, 22, 10, 0, 0, tzinfo=get_system_timezone())
        assert result == expected


class TestMainCalculateFunction:
    """Test the main calculate_next_update_time function."""

    def test_calculate_next_update_time_fixed_time_enabled(self) -> None:
        """Test calculation with fixed time enabled and UPDATE_DAYS=1."""
        # With UPDATE_DAYS=1, should schedule for next day to respect interval (bug fix)
        current_time = datetime(2025, 7, 25, 10, 0, 0, tzinfo=get_system_timezone())
        update_days = 1
        fixed_update_time = "23:59"

        result = calculate_next_update_time(
            update_days, fixed_update_time, current_time
        )

        expected = datetime(2025, 7, 26, 23, 59, 0, tzinfo=get_system_timezone())
        assert result == expected

    def test_calculate_next_update_time_fixed_time_disabled(self) -> None:
        """Test calculation with fixed time disabled."""
        current_time = datetime(2025, 7, 25, 14, 30, 0, tzinfo=get_system_timezone())
        update_days = 3
        fixed_update_time = "XX:XX"

        result = calculate_next_update_time(
            update_days, fixed_update_time, current_time
        )

        expected = current_time + timedelta(days=3)
        assert result == expected

    def test_calculate_next_update_time_with_last_update(self) -> None:
        """Test calculation with last update provided."""
        current_time = datetime(2025, 7, 25, 14, 30, 0, tzinfo=get_system_timezone())
        update_days = 2
        fixed_update_time = "12:00"
        last_update = datetime(2025, 7, 24, 12, 0, 0, tzinfo=get_system_timezone())

        result = calculate_next_update_time(
            update_days, fixed_update_time, current_time, last_update
        )

        expected = datetime(2025, 7, 26, 12, 0, 0, tzinfo=get_system_timezone())
        assert result == expected

    def test_calculate_next_update_time_invalid_fixed_time(self) -> None:
        """Test calculation with invalid fixed time."""
        current_time = datetime(2025, 7, 25, 14, 30, 0, tzinfo=get_system_timezone())
        update_days = 1
        fixed_update_time = "25:00"  # Invalid

        with pytest.raises(ValueError, match="Invalid fixed time format"):
            _ = calculate_next_update_time(update_days, fixed_update_time, current_time)

    def test_calculate_next_update_time_uses_system_now_by_default(self) -> None:
        """Test that function uses system now when current_time is not provided."""
        update_days = 1
        fixed_update_time = "XX:XX"

        with patch("src.tgraph_bot.utils.time.scheduling.get_system_now") as mock_now:
            mock_time = datetime(2025, 7, 25, 14, 30, 0, tzinfo=get_system_timezone())
            mock_now.return_value = mock_time

            result = calculate_next_update_time(update_days, fixed_update_time)

            mock_now.assert_called_once()
            expected = mock_time + timedelta(days=1)
            assert result == expected
