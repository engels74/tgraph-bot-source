"""
Tests for unified timezone handling utilities.

This module tests the unified timezone utilities that provide consistent
timezone handling across the entire application.
"""
# pyright: reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportAny=false, reportUnusedVariable=false

from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock

from src.tgraph_bot.utils.time.timezone import (
    get_system_timezone,
    get_system_now,
    ensure_timezone_aware,
    to_system_timezone,
    format_for_discord,
)


class TestSystemTimezone:
    """Test system timezone detection and handling."""

    def test_get_system_timezone_returns_zoneinfo(self) -> None:
        """Test that get_system_timezone returns a ZoneInfo object."""
        tz = get_system_timezone()
        assert isinstance(tz, ZoneInfo)

    def test_get_system_timezone_consistency(self) -> None:
        """Test that get_system_timezone returns consistent results."""
        tz1 = get_system_timezone()
        tz2 = get_system_timezone()
        assert tz1.key == tz2.key

    def test_get_system_timezone_enhanced_detection_methods(self) -> None:
        """Test that the enhanced timezone detection works for the main use case."""
        # This test verifies that our enhanced detection works in practice
        # by testing the actual implementation without complex mocking
        tz = get_system_timezone()
        assert isinstance(tz, ZoneInfo)

        # The timezone should be detected consistently
        tz2 = get_system_timezone()
        assert tz.key == tz2.key

        # Should not be None or empty
        assert tz.key is not None
        assert len(tz.key) > 0


class TestSystemNow:
    """Test system-aware current time functions."""

    def test_get_system_now_returns_timezone_aware(self) -> None:
        """Test that get_system_now returns timezone-aware datetime."""
        now = get_system_now()
        assert now.tzinfo is not None
        assert isinstance(now.tzinfo, ZoneInfo)

    def test_get_system_now_uses_system_timezone(self) -> None:
        """Test that get_system_now uses the system timezone."""
        now = get_system_now()
        system_tz = get_system_timezone()
        assert now.tzinfo is not None
        assert system_tz is not None
        assert hasattr(now.tzinfo, "key") and hasattr(system_tz, "key")
        assert now.tzinfo.key == system_tz.key


class TestTimezoneAware:
    """Test timezone awareness utilities."""

    def test_ensure_timezone_aware_with_naive_datetime(self) -> None:
        """Test ensuring timezone awareness for naive datetime."""
        naive_dt = datetime(2025, 7, 25, 14, 30, 0)
        aware_dt = ensure_timezone_aware(naive_dt)

        assert aware_dt.tzinfo is not None
        assert isinstance(aware_dt.tzinfo, ZoneInfo)
        assert aware_dt.year == 2025
        assert aware_dt.month == 7
        assert aware_dt.day == 25
        assert aware_dt.hour == 14
        assert aware_dt.minute == 30

    def test_ensure_timezone_aware_with_aware_datetime(self) -> None:
        """Test ensuring timezone awareness for already aware datetime."""
        aware_dt = datetime(2025, 7, 25, 14, 30, 0, tzinfo=ZoneInfo("UTC"))
        result_dt = ensure_timezone_aware(aware_dt)

        # Should return the same datetime unchanged
        assert result_dt is aware_dt
        assert result_dt.tzinfo is not None
        assert hasattr(result_dt.tzinfo, "key")
        assert result_dt.tzinfo.key == "UTC"

    def test_ensure_timezone_aware_uses_system_timezone(self) -> None:
        """Test that ensure_timezone_aware uses system timezone for naive datetimes."""
        naive_dt = datetime(2025, 7, 25, 14, 30, 0)
        aware_dt = ensure_timezone_aware(naive_dt)
        system_tz = get_system_timezone()

        assert aware_dt.tzinfo is not None
        assert system_tz is not None and hasattr(system_tz, "key")
        assert hasattr(aware_dt.tzinfo, "key")
        assert aware_dt.tzinfo.key == system_tz.key


class TestTimezoneConversion:
    """Test timezone conversion utilities."""

    def test_to_system_timezone_from_utc(self) -> None:
        """Test converting UTC datetime to system timezone."""
        utc_dt = datetime(2025, 7, 25, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
        system_dt = to_system_timezone(utc_dt)

        assert isinstance(system_dt.tzinfo, ZoneInfo)
        system_tz = get_system_timezone()
        assert system_dt.tzinfo.key == system_tz.key

    def test_to_system_timezone_from_different_timezone(self) -> None:
        """Test converting from different timezone to system timezone."""
        ny_dt = datetime(2025, 7, 25, 8, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        system_dt = to_system_timezone(ny_dt)

        assert isinstance(system_dt.tzinfo, ZoneInfo)
        system_tz = get_system_timezone()
        assert system_dt.tzinfo.key == system_tz.key

    def test_to_system_timezone_with_naive_datetime(self) -> None:
        """Test converting naive datetime to system timezone."""
        naive_dt = datetime(2025, 7, 25, 14, 30, 0)
        system_dt = to_system_timezone(naive_dt)

        assert isinstance(system_dt.tzinfo, ZoneInfo)
        system_tz = get_system_timezone()
        assert system_dt.tzinfo.key == system_tz.key

    def test_to_system_timezone_preserves_time_value(self) -> None:
        """Test that timezone conversion preserves the actual time value."""
        # Create a UTC datetime
        utc_dt = datetime(2025, 7, 25, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

        # Convert to system timezone
        system_dt = to_system_timezone(utc_dt)

        # The UTC timestamp should be the same
        assert utc_dt.timestamp() == system_dt.timestamp()


class TestDiscordFormatting:
    """Test Discord timestamp formatting utilities."""

    @patch("src.tgraph_bot.utils.time.timezone.discord.utils.format_dt")
    def test_format_for_discord_with_timezone_aware(
        self, mock_format_dt: MagicMock
    ) -> None:
        """Test Discord formatting with timezone-aware datetime."""
        mock_format_dt.return_value = "<t:1737027000:F>"

        aware_dt = datetime(2025, 7, 25, 23, 59, 0, tzinfo=get_system_timezone())
        result = format_for_discord(aware_dt)

        mock_format_dt.assert_called_once()
        call_args = mock_format_dt.call_args
        assert call_args is not None
        args, kwargs = call_args
        assert len(args) == 1
        assert args[0].tzinfo is not None
        assert kwargs.get("style") == "F"
        assert result == "<t:1737027000:F>"

    @patch("src.tgraph_bot.utils.time.timezone.discord.utils.format_dt")
    def test_format_for_discord_with_naive_datetime(
        self, mock_format_dt: MagicMock
    ) -> None:
        """Test Discord formatting with naive datetime."""
        mock_format_dt.return_value = "<t:1737027000:F>"

        naive_dt = datetime(2025, 7, 25, 23, 59, 0)
        result = format_for_discord(naive_dt, style="F")

        mock_format_dt.assert_called_once()
        call_args = mock_format_dt.call_args
        assert call_args is not None
        args, kwargs = call_args
        assert len(args) == 1
        # Should be converted to timezone-aware
        assert args[0].tzinfo is not None
        assert isinstance(args[0].tzinfo, ZoneInfo)
        assert kwargs.get("style") == "F"
        assert result == "<t:1737027000:F>"

    @patch("src.tgraph_bot.utils.time.timezone.discord.utils.format_dt")
    def test_format_for_discord_default_style(self, mock_format_dt: MagicMock) -> None:
        """Test Discord formatting with default style."""
        mock_format_dt.return_value = "<t:1737027000:F>"

        dt = datetime(2025, 7, 25, 23, 59, 0, tzinfo=get_system_timezone())
        result = format_for_discord(dt)

        mock_format_dt.assert_called_once()
        call_args = mock_format_dt.call_args
        assert call_args is not None
        args, kwargs = call_args
        assert kwargs.get("style") == "F"  # Default style
        assert result == "<t:1737027000:F>"
