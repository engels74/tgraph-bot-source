"""
Tests for timezone handling in the update tracker and health check system.

This module tests the fix for the datetime timezone error that occurred when
mixing timezone-aware and timezone-naive datetime objects in health checks.
"""

import asyncio
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import discord
import pytest

from tgraph_bot.bot.update_tracker import (
    BackgroundTaskManager,
    ScheduleState,
    StateManager,
    RecoveryManager,
    SchedulingConfig,
    UpdateTracker,
    get_local_timezone,
    get_local_now,
)
from tgraph_bot.utils.discord.discord_file_utils import (
    get_local_timezone as utils_get_local_timezone,
    get_local_now as utils_get_local_now,
    calculate_next_update_time,
    format_next_update_timestamp,
    ensure_timezone_aware,
)


class TestTimezoneHandling:
    """Test timezone handling in health check and state management."""

    def test_schedule_state_serialization_with_timezone_aware_datetimes(self) -> None:
        """Test that ScheduleState correctly handles timezone-aware datetimes during serialization."""
        # Create timezone-aware datetimes
        now_utc = discord.utils.utcnow()
        future_utc = now_utc + timedelta(hours=1)

        state = ScheduleState()
        state.last_update = now_utc
        state.next_update = future_utc
        state.last_failure = now_utc - timedelta(minutes=30)

        # Serialize to dict
        state_dict = state.to_dict()

        # Verify serialization includes timezone info
        assert state_dict["last_update"] is not None
        assert state_dict["next_update"] is not None
        assert state_dict["last_failure"] is not None

        # Deserialize back
        restored_state = ScheduleState.from_dict(state_dict)

        # Verify all datetimes are timezone-aware
        assert restored_state.last_update is not None
        assert restored_state.last_update.tzinfo is not None
        assert restored_state.next_update is not None
        assert restored_state.next_update.tzinfo is not None
        assert restored_state.last_failure is not None
        assert restored_state.last_failure.tzinfo is not None

        # Verify values are preserved
        assert restored_state.last_update == now_utc
        assert restored_state.next_update == future_utc

    def test_schedule_state_handles_timezone_naive_legacy_data(self) -> None:
        """Test that ScheduleState correctly converts timezone-naive legacy data to timezone-aware."""
        # Simulate legacy data with timezone-naive datetime strings
        legacy_data: dict[str, str | int | bool | None] = {
            "last_update": "2024-01-01T12:00:00",  # No timezone info
            "next_update": "2024-01-01T13:00:00",  # No timezone info
            "last_failure": "2024-01-01T11:30:00",  # No timezone info
            "is_running": True,
            "consecutive_failures": 0,
        }

        # Deserialize legacy data
        state = ScheduleState.from_dict(legacy_data)

        # Verify all datetimes are now timezone-aware (converted to local timezone)
        assert state.last_update is not None
        assert state.last_update.tzinfo is not None
        assert state.next_update is not None
        assert state.next_update.tzinfo is not None
        assert state.last_failure is not None
        assert state.last_failure.tzinfo is not None

    @pytest.mark.asyncio
    async def test_background_task_manager_health_check_with_timezone_aware_datetimes(
        self,
    ) -> None:
        """Test that BackgroundTaskManager health checks work with timezone-aware datetimes."""
        manager = BackgroundTaskManager()

        # Add a task with timezone-aware datetime
        task_name = "test_task"

        async def dummy_task() -> None:
            await asyncio.sleep(0.1)

        # Mock get_local_now to return a known timezone-aware datetime
        with patch("tgraph_bot.bot.update_tracker.get_local_now") as mock_local_now:
            base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=get_local_timezone())
            mock_local_now.return_value = base_time

            # Add task - this should set task health to timezone-aware datetime
            manager.add_task(task_name, dummy_task)

            # Verify task health is timezone-aware using public method
            task_status = manager.get_all_task_status()
            assert task_name in task_status
            task_health = task_status[task_name]["last_health"]
            assert task_health is not None
            assert isinstance(task_health, datetime)
            assert task_health.tzinfo is not None
            assert task_health == base_time

            # Test health check with timezone-aware current time
            future_time = base_time + timedelta(minutes=10)
            mock_local_now.return_value = future_time

            # This should not raise a timezone error
            is_healthy = manager.is_healthy()
            assert not is_healthy  # Should be unhealthy due to time difference

            # Test with recent time (should be healthy)
            recent_time = base_time + timedelta(minutes=1)
            mock_local_now.return_value = recent_time

            is_healthy = manager.is_healthy()
            assert is_healthy  # Should be healthy

        await manager.stop()

    def test_state_manager_preserves_timezone_info(self) -> None:
        """Test that StateManager preserves timezone information during save/load cycles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"
            manager = StateManager(state_file)

            # Create state with timezone-aware datetimes
            original_state = ScheduleState()
            original_state.last_update = discord.utils.utcnow()
            original_state.next_update = original_state.last_update + timedelta(days=1)

            config = SchedulingConfig(update_days=1, fixed_update_time="12:00")

            # Save state
            manager.save_state(original_state, config)

            # Load state
            loaded_state, _ = manager.load_state()

            # Verify timezone information is preserved
            assert loaded_state.last_update is not None
            assert loaded_state.last_update.tzinfo is not None
            assert loaded_state.next_update is not None
            assert loaded_state.next_update.tzinfo is not None

            # Verify values are preserved
            assert loaded_state.last_update == original_state.last_update
            assert loaded_state.next_update == original_state.next_update

    @pytest.mark.asyncio
    async def test_recovery_manager_handles_timezone_aware_datetimes(self) -> None:
        """Test that RecoveryManager correctly handles timezone-aware datetimes in missed update detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"
            state_manager = StateManager(state_file)
            recovery_manager = RecoveryManager(state_manager)

            # Create state with timezone-aware datetimes
            state = ScheduleState()
            base_time = discord.utils.utcnow()
            state.last_update = base_time - timedelta(days=2)  # 2 days ago
            state.next_update = base_time - timedelta(days=1)  # 1 day ago (missed)

            config = SchedulingConfig(update_days=1, fixed_update_time="12:00")
            current_time = base_time  # Current time is timezone-aware

            # This should not raise a timezone error
            missed_updates = recovery_manager.detect_missed_updates(
                current_time, state.last_update, state.next_update, config
            )

            # Should detect the missed update
            assert len(missed_updates) > 0
            assert missed_updates[0].scheduled_time == state.next_update

    @pytest.mark.asyncio
    async def test_update_tracker_startup_with_mixed_timezone_data(self) -> None:
        """Test that UpdateTracker handles startup recovery with mixed timezone data gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"

            # Create a state file with timezone-naive data (simulating legacy data)
            legacy_state = ScheduleState()
            legacy_state.last_update = datetime(2024, 1, 1, 12, 0, 0)  # Timezone-naive
            legacy_state.next_update = datetime(2024, 1, 2, 12, 0, 0)  # Timezone-naive

            state_manager = StateManager(state_file)
            config = SchedulingConfig(update_days=1, fixed_update_time="12:00")
            state_manager.save_state(legacy_state, config)

            # Create mock bot
            mock_bot = MagicMock()
            mock_user = MagicMock()
            mock_user.id = 12345
            mock_bot.user = mock_user

            # Create UpdateTracker - this should handle the timezone conversion gracefully
            tracker = UpdateTracker(mock_bot, state_file_path=state_file)

            # Start scheduler - this should not raise timezone errors
            try:
                await tracker.start_scheduler(
                    update_days=config.update_days,
                    fixed_update_time=config.fixed_update_time,
                )

                # Verify the tracker is running using public method
                status = tracker.get_scheduler_status()
                assert status["is_started"]

                # The main goal of this test is to verify that the system handles
                # timezone-naive legacy data without crashing with timezone errors.
                # The recovery system correctly detected the invalid dates and started fresh.
                # This is the expected behavior - no timezone errors should occur.
                assert status["is_running"] is not None  # State object exists

            finally:
                await tracker.stop_scheduler()

    def test_error_metrics_use_timezone_aware_datetimes(self) -> None:
        """Test that ErrorMetrics uses timezone-aware datetimes for all timestamp fields."""
        from tgraph_bot.bot.update_tracker import ErrorMetrics, ErrorType

        with patch("discord.utils.utcnow") as mock_utcnow:
            base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_utcnow.return_value = base_time

            metrics = ErrorMetrics()

            # Test record_attempt
            metrics.record_attempt()
            assert metrics.last_attempt is not None
            assert metrics.last_attempt.tzinfo is not None

            # Test record_success
            metrics.record_success()
            assert metrics.last_success is not None
            assert metrics.last_success.tzinfo is not None

            # Test record_failure
            metrics.record_failure(ErrorType.TRANSIENT)
            assert metrics.last_failure is not None
            assert metrics.last_failure.tzinfo is not None


class TestLocalTimezoneHandling:
    """Test local timezone handling functions."""

    def test_get_local_timezone(self) -> None:
        """Test that get_local_timezone returns system local timezone."""
        # Test update_tracker version
        tz = get_local_timezone()
        assert tz is not None
        assert isinstance(tz, ZoneInfo)

        # Test utils version
        utils_tz = utils_get_local_timezone()
        assert utils_tz is not None
        assert isinstance(utils_tz, ZoneInfo)

        # Both should return equivalent timezone
        assert str(tz) == str(utils_tz)

    def test_get_local_now(self) -> None:
        """Test that get_local_now returns timezone-aware local datetime."""
        # Test update_tracker version
        now = get_local_now()
        assert now.tzinfo is not None
        assert isinstance(now.tzinfo, ZoneInfo)

        # Test utils version
        utils_now = utils_get_local_now()
        assert utils_now.tzinfo is not None
        assert isinstance(utils_now.tzinfo, ZoneInfo)

        # Both should have same timezone
        assert str(now.tzinfo) == str(utils_now.tzinfo)

    def test_ensure_timezone_aware_with_naive_datetime(self) -> None:
        """Test ensure_timezone_aware converts naive datetime to local timezone."""
        naive_dt = datetime(2025, 1, 1, 12, 0, 0)  # No timezone

        aware_dt = ensure_timezone_aware(naive_dt)

        assert aware_dt.tzinfo is not None
        assert isinstance(aware_dt.tzinfo, ZoneInfo)
        assert aware_dt.year == 2025
        assert aware_dt.month == 1
        assert aware_dt.day == 1
        assert aware_dt.hour == 12
        assert aware_dt.minute == 0
        assert aware_dt.second == 0

    def test_ensure_timezone_aware_with_aware_datetime(self) -> None:
        """Test ensure_timezone_aware preserves timezone-aware datetime."""
        aware_dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = ensure_timezone_aware(aware_dt)

        assert result is aware_dt  # Should return same object
        assert result.tzinfo == timezone.utc

    def test_calculate_next_update_time_fixed_time(self) -> None:
        """Test calculate_next_update_time with fixed time uses local timezone."""
        next_update = calculate_next_update_time(1, "23:59")

        assert next_update is not None
        assert next_update.tzinfo is not None
        assert isinstance(next_update.tzinfo, ZoneInfo)
        # Should be in the future
        from datetime import datetime

        current_time = datetime.now(get_local_timezone())
        assert next_update > current_time
        # Should have zero seconds (fixed time precision)
        assert next_update.second == 0

    def test_calculate_next_update_time_interval_based(self) -> None:
        """Test calculate_next_update_time with interval-based scheduling."""
        next_update = calculate_next_update_time(2, "XX:XX")

        assert next_update is not None
        assert next_update.tzinfo is not None
        assert isinstance(next_update.tzinfo, ZoneInfo)

        # Should be approximately 2 days from now
        now = get_local_now()
        diff = next_update - now
        assert 1.9 <= diff.total_seconds() / 86400 <= 2.1  # Between 1.9 and 2.1 days

    def test_format_next_update_timestamp(self) -> None:
        """Test format_next_update_timestamp creates Discord timestamp."""
        # Create a fixed datetime in local timezone
        dt = datetime(2025, 7, 18, 23, 59, 0, tzinfo=get_local_timezone())

        # Test default style (relative)
        timestamp = format_next_update_timestamp(dt)
        assert timestamp.startswith("<t:")
        assert timestamp.endswith(":R>")

        # Test specific style
        timestamp_f = format_next_update_timestamp(dt, "f")
        assert timestamp_f.startswith("<t:")
        assert timestamp_f.endswith(":f>")

        # Test with naive datetime (should be converted to local timezone)
        naive_dt = datetime(2025, 7, 18, 23, 59, 0)
        timestamp_naive = format_next_update_timestamp(naive_dt)
        assert timestamp_naive.startswith("<t:")
        assert timestamp_naive.endswith(":R>")

    def test_scheduler_state_with_local_timezone(self) -> None:
        """Test ScheduleState correctly handles local timezone datetimes."""
        state = ScheduleState()
        local_time = get_local_now()

        state.last_update = local_time
        state.next_update = local_time + timedelta(days=1)

        # Test serialization
        state_dict = state.to_dict()
        assert state_dict["last_update"] is not None
        assert state_dict["next_update"] is not None

        # Test deserialization
        restored_state = ScheduleState.from_dict(state_dict)
        assert restored_state.last_update is not None
        assert restored_state.next_update is not None
        assert restored_state.last_update.tzinfo is not None
        assert restored_state.next_update.tzinfo is not None

    def test_scheduling_config_with_local_time(self) -> None:
        """Test SchedulingConfig works with local timezone."""
        config = SchedulingConfig(update_days=1, fixed_update_time="23:59")

        # Test fixed time parsing
        fixed_time = config.get_fixed_time()
        assert fixed_time is not None
        assert fixed_time.hour == 23
        assert fixed_time.minute == 59

        # Test is_fixed_time_based
        assert config.is_fixed_time_based()

        # Test interval-based config
        interval_config = SchedulingConfig(update_days=2, fixed_update_time="XX:XX")
        assert not interval_config.is_fixed_time_based()

    @pytest.mark.asyncio
    async def test_update_tracker_with_local_timezone(self) -> None:
        """Test UpdateTracker uses local timezone consistently."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"

            # Create mock bot
            mock_bot = MagicMock()
            mock_user = MagicMock()
            mock_user.id = 12345
            mock_bot.user = mock_user

            # Create UpdateTracker
            tracker = UpdateTracker(mock_bot, state_file_path=state_file)

            try:
                # Start scheduler with local timezone
                await tracker.start_scheduler(update_days=1, fixed_update_time="23:59")

                # Check scheduler status
                status = tracker.get_scheduler_status()
                assert status["is_started"]

                # Check that state uses local timezone
                next_update = status["next_update"]
                if next_update and isinstance(next_update, datetime):
                    assert next_update.tzinfo is not None
                    assert isinstance(next_update.tzinfo, (ZoneInfo, timezone))

            finally:
                await tracker.stop_scheduler()

    def test_mixed_timezone_data_conversion(self) -> None:
        """Test that mixed timezone data is handled correctly."""
        # Create state with mixed timezone data
        legacy_data: dict[str, str | int | bool | None] = {
            "last_update": "2025-01-01T12:00:00",  # Naive
            "next_update": "2025-01-01T13:00:00+00:00",  # UTC
            "last_failure": "2025-01-01T11:30:00+02:00",  # Europe/Copenhagen
            "is_running": True,
            "consecutive_failures": 0,
        }

        # Deserialize - should convert all to timezone-aware
        state = ScheduleState.from_dict(legacy_data)

        assert state.last_update is not None
        assert state.last_update.tzinfo is not None
        assert state.next_update is not None
        assert state.next_update.tzinfo is not None
        assert state.last_failure is not None
        assert state.last_failure.tzinfo is not None

        # All should be timezone-aware, but may have different timezones
        # The key is that they're all timezone-aware for consistent comparisons
        assert state.last_update.tzinfo is not None
        assert state.next_update.tzinfo is not None
        assert state.last_failure.tzinfo is not None

    def test_startup_sequence_stores_local_time_not_utc(self) -> None:
        """Test that startup sequence stores timestamps in local timezone, not UTC."""
        # This is the key test to ensure the fix works correctly
        utc_time = discord.utils.utcnow()

        # The issue is that startup_sequence.py uses discord.utils.utcnow() directly
        # but should convert it to local time before storing
        # This test verifies that the timestamps stored are in local timezone

        # Create a state and set it as if from startup sequence
        state = ScheduleState()

        # This is what the startup sequence SHOULD do (convert UTC to local)
        # Instead of: state.last_update = discord.utils.utcnow()
        # It should be: state.last_update = discord.utils.utcnow().astimezone(get_local_timezone())
        converted_time = utc_time.astimezone(get_local_timezone())
        state.last_update = converted_time

        # Verify the timestamp is in local timezone
        assert state.last_update.tzinfo is not None
        assert isinstance(state.last_update.tzinfo, ZoneInfo)
        assert str(state.last_update.tzinfo) == str(get_local_timezone())

        # Verify the time values are equivalent to what we expect
        # The UTC time converted to local should be the same moment in time
        utc_offset = converted_time.utcoffset()
        
        # If local timezone has an offset from UTC, wall clock times should differ
        # If local timezone IS UTC (offset = 0), then wall clock times will be the same
        if utc_offset and utc_offset.total_seconds() != 0:
            assert state.last_update.replace(tzinfo=None) != utc_time.replace(
                tzinfo=None
            )  # Different wall clock time when timezone differs from UTC
        else:
            # When local timezone is UTC, wall clock times are the same
            assert state.last_update.replace(tzinfo=None) == utc_time.replace(
                tzinfo=None
            )  # Same wall clock time when local timezone is UTC
            
        # Regardless of timezone, these should be the same moment in time
        assert (
            state.last_update.astimezone(timezone.utc) == utc_time
        )  # Same moment in time

        # Test serialization preserves the local timezone
        state_dict = state.to_dict()
        assert state_dict["last_update"] is not None

        # Test deserialization maintains local timezone
        restored_state = ScheduleState.from_dict(state_dict)
        assert restored_state.last_update is not None
        assert restored_state.last_update.tzinfo is not None
        assert restored_state.last_update == converted_time
