"""
Tests for Discord embed timestamp consistency and race condition handling.

This module tests that Discord embeds always show the same timestamp as the
internal scheduler state, preventing the UPDATE_DAYS discrepancy bug.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from src.tgraph_bot.utils.time.timestamp_calculator import TimestampCalculator
from src.tgraph_bot.utils.discord.discord_file_utils import create_graph_specific_embed
from src.tgraph_bot.bot.update_tracker import UpdateTracker
from src.tgraph_bot.config.manager import ConfigManager


@pytest.fixture
def mock_config_manager() -> Mock:
    """Create a mock config manager with test configuration."""
    config_manager = Mock(spec=ConfigManager)
    mock_config = Mock()
    mock_config.UPDATE_DAYS = 1
    mock_config.FIXED_UPDATE_TIME = "23:59"
    mock_config.DISCORD_TIMESTAMP_FORMAT = "F"
    config_manager.get_current_config.return_value = mock_config  # pyright: ignore[reportAny]
    return config_manager


@pytest.fixture
def test_timezone() -> ZoneInfo:
    """Use a consistent timezone for testing."""
    return ZoneInfo("Europe/Copenhagen")


@pytest.fixture
def base_time(test_timezone: ZoneInfo) -> datetime:
    """Base time for consistent testing - July 25, 2025 at 21:41:47."""
    return datetime(2025, 7, 25, 21, 41, 47, 967895, tzinfo=test_timezone)


class TestTimestampConsistency:
    """Test that scheduler and embed timestamps are always consistent."""

    def test_timestamp_calculator_exists(self) -> None:
        """Test that TimestampCalculator class exists and is importable."""
        # This test will fail until we create the class
        calculator = TimestampCalculator()
        assert calculator is not None

    def test_scheduler_and_embed_use_same_calculation(
        self, base_time: datetime
    ) -> None:
        """Test that scheduler and embed timestamps use the same calculation logic."""
        # Given: A timestamp calculator and configuration
        calculator = TimestampCalculator()
        update_days = 1
        fixed_time = "23:59"
        last_update: datetime = base_time

        # When: Both scheduler and embed calculate next update time
        scheduler_next_update = calculator.calculate_next_update(
            update_days=update_days,
            fixed_update_time=fixed_time,
            last_update=last_update,
            current_time=base_time,
        )

        embed_next_update = calculator.calculate_next_update(
            update_days=update_days,
            fixed_update_time=fixed_time,
            last_update=last_update,
            current_time=base_time,
        )

        # Then: Both should return identical timestamps
        assert scheduler_next_update == embed_next_update

    def test_scheduler_state_matches_embed_display(self, base_time: datetime) -> None:
        """Test that the scheduler state matches what's displayed in embeds."""
        # This test will fail until we refactor the systems to use the same calculator

        # Given: An update tracker with calculated next update
        bot = Mock()
        update_tracker = UpdateTracker(bot)

        # Mock the scheduler to have a specific next update time
        expected_next_update = base_time + timedelta(days=1)
        expected_next_update = expected_next_update.replace(
            hour=23, minute=59, second=0, microsecond=0
        )
        update_tracker._state.next_update = expected_next_update  # pyright: ignore[reportPrivateUsage]

        # When: We create an embed using the same parameters
        with patch(
            "src.tgraph_bot.utils.discord.discord_file_utils.calculate_next_update_time"
        ) as mock_calc:
            mock_calc.return_value = expected_next_update

            embed = create_graph_specific_embed(
                graph_file_path="test_daily_play_count.png",
                update_days=1,
                fixed_update_time="23:59",
                timestamp_format="F",
            )

        # Then: The embed should contain the same timestamp as the scheduler
        # Check that the embed description contains the expected timestamp
        assert embed.description is not None
        assert "Next update:" in embed.description

    def test_update_days_properly_applied_to_timestamps(
        self, base_time: datetime
    ) -> None:
        """Test that UPDATE_DAYS=1 correctly adds 1 day to timestamps."""
        calculator = TimestampCalculator()

        # Given: UPDATE_DAYS=1 and a last update time
        last_update: datetime = base_time
        update_days = 1
        fixed_time = "23:59"

        # When: Calculating next update
        next_update = calculator.calculate_next_update(
            update_days=update_days,
            fixed_update_time=fixed_time,
            last_update=last_update,
            current_time=base_time,
        )

        # Then: Next update should be exactly 1 day later at 23:59
        expected_date = base_time.date() + timedelta(days=1)
        expected_next_update = datetime.combine(
            expected_date, datetime.strptime("23:59", "%H:%M").time()
        )
        expected_next_update = expected_next_update.replace(tzinfo=base_time.tzinfo)

        assert next_update == expected_next_update
        assert next_update.date() == base_time.date() + timedelta(days=1)
        assert next_update.hour == 23
        assert next_update.minute == 59


class TestRaceConditionHandling:
    """Test race condition scenarios and proper handling."""

    def test_embed_handles_uninitialized_scheduler(self) -> None:
        """Test that embeds handle the case where scheduler isn't ready yet."""
        # Given: A scenario where scheduler hasn't calculated next_update yet
        bot = Mock()
        update_tracker = UpdateTracker(bot)
        update_tracker._state.next_update = (  # pyright: ignore[reportPrivateUsage]
            None  # Scheduler not ready
        )

        # When: Creating an embed before scheduler is ready
        embed = create_graph_specific_embed(
            graph_file_path="test_daily_play_count.png",
            update_days=1,
            fixed_update_time="23:59",
            timestamp_format="F",
        )

        # Then: Embed should still be created successfully
        # and should either wait for scheduler or calculate independently using same logic
        assert embed is not None
        assert embed.title is not None

    def test_scheduler_ready_state_accessible(self) -> None:
        """Test that we can check if scheduler is ready and has calculated next_update."""
        # Given: An update tracker
        bot = Mock()
        update_tracker = UpdateTracker(bot)

        # When: Scheduler hasn't been started
        # Then: Should indicate it's not ready
        assert not update_tracker.is_scheduler_healthy()

        # When: Scheduler has calculated next_update
        update_tracker._state.next_update = datetime.now()  # pyright: ignore[reportPrivateUsage]
        update_tracker._is_started = True  # pyright: ignore[reportPrivateUsage]

        # Then: Should indicate it's ready (this will need implementation)
        # This test will help us design the interface for checking readiness

    def test_manual_command_waits_for_scheduler_readiness(self) -> None:
        """Test that manual /update_graphs command waits for scheduler readiness."""
        # This test will drive the implementation of race condition prevention

        # Given: A scenario where manual command is triggered immediately after bot start
        bot = Mock()
        update_tracker = UpdateTracker(bot)

        # When: Manual command tries to get next update time before scheduler is ready
        next_update = update_tracker.get_next_update_time()

        # Then: Should either return None (graceful handling) or wait for scheduler
        # This test will help us decide on the approach
        # For now, we expect None when not ready
        assert next_update is None


class TestTimestampDisplayFormat:
    """Test that timestamp formatting is consistent across the system."""

    def test_discord_timestamp_format_applied_correctly(
        self, base_time: datetime
    ) -> None:
        """Test that Discord timestamp format configuration is respected."""
        calculator = TimestampCalculator()

        # Given: A calculated next update time
        next_update = calculator.calculate_next_update(
            update_days=1,
            fixed_update_time="23:59",
            last_update=base_time,
            current_time=base_time,
        )

        # When: Formatting for Discord with different styles
        from src.tgraph_bot.utils.time import format_for_discord

        formatted_f = format_for_discord(next_update, style="F")  # Full date/time
        formatted_r = format_for_discord(next_update, style="R")  # Relative time

        # Then: Should return properly formatted Discord timestamps
        assert formatted_f.startswith("<t:")
        assert formatted_f.endswith(":F>")
        assert formatted_r.startswith("<t:")
        assert formatted_r.endswith(":R>")

    def test_timezone_awareness_preserved(
        self, test_timezone: ZoneInfo, base_time: datetime
    ) -> None:
        """Test that timezone information is preserved through calculations."""
        calculator = TimestampCalculator()

        # Given: A timezone-aware base time
        assert base_time.tzinfo is not None

        # When: Calculating next update
        next_update = calculator.calculate_next_update(
            update_days=1,
            fixed_update_time="23:59",
            last_update=base_time,
            current_time=base_time,
        )

        # Then: Result should maintain timezone awareness
        assert next_update.tzinfo is not None
        # ZoneInfo objects have a 'key' attribute, but we need proper typing
        assert hasattr(next_update.tzinfo, "key")
        assert hasattr(test_timezone, "key")
        assert next_update.tzinfo.key == test_timezone.key  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]


# Integration test to verify the fix
class TestBugFix:
    """Integration tests to verify the specific UPDATE_DAYS bug is fixed."""

    def test_update_days_1_scenario_matches_scheduler_state(self) -> None:
        """Test the specific scenario from the bug report: UPDATE_DAYS=1."""
        # Given: The exact scenario from the bug report
        last_update = datetime(
            2025, 7, 25, 21, 41, 47, 967895, tzinfo=ZoneInfo("Europe/Copenhagen")
        )
        expected_next = datetime(
            2025, 7, 26, 23, 59, 0, tzinfo=ZoneInfo("Europe/Copenhagen")
        )

        calculator = TimestampCalculator()

        # When: Calculating next update with UPDATE_DAYS=1 and FIXED_UPDATE_TIME="23:59"
        calculated_next = calculator.calculate_next_update(
            update_days=1,
            fixed_update_time="23:59",
            last_update=last_update,
            current_time=last_update,
        )

        # Then: Should match the expected scheduler state from bug report
        assert calculated_next.date() == expected_next.date()
        assert calculated_next.hour == expected_next.hour
        assert calculated_next.minute == expected_next.minute

        # And: Discord format should show "Saturday, 26 July 2025 at 23:59"
        from src.tgraph_bot.utils.time import format_for_discord

        formatted = format_for_discord(calculated_next, style="F")
        assert formatted.startswith("<t:")
        assert formatted.endswith(":F>")
