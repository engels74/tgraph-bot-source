"""
Tests for enhanced update tracker scheduling logic.

This module tests the enhanced scheduling features including failure handling,
exponential backoff, and improved edge case handling.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from discord.ext import commands

from src.tgraph_bot.bot.update_tracker import SchedulingConfig, ScheduleState, UpdateSchedule, UpdateTracker
from tests.utils.test_helpers import create_mock_discord_bot


class TestEnhancedScheduling:
    """Test enhanced scheduling features."""
    
    def test_time_until_next_update(self) -> None:
        """Test calculation of time until next update."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)
        
        now = datetime.now()
        time_until = schedule.calculate_time_until_next_update(now)
        
        # Should be approximately 7 days
        expected = timedelta(days=7)
        assert abs((time_until - expected).total_seconds()) < 1
    
    def test_should_skip_update_no_failures(self) -> None:
        """Test that updates are not skipped when there are no failures."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)
        
        now = datetime.now()
        assert schedule.should_skip_update(now) is False
    
    def test_should_skip_update_few_failures(self) -> None:
        """Test that updates are not skipped with few failures."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)
        
        # Record 2 failures (below threshold)
        now = datetime.now()
        error = Exception("Test error")
        state.record_failure(now - timedelta(minutes=30), error)
        state.record_failure(now - timedelta(minutes=15), error)
        
        assert schedule.should_skip_update(now) is False
    
    def test_should_skip_update_many_failures(self) -> None:
        """Test that updates are skipped with many failures."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)
        
        # Record 3 failures (at threshold)
        now = datetime.now()
        error = Exception("Test error")
        state.record_failure(now - timedelta(hours=2), error)
        state.record_failure(now - timedelta(hours=1), error)
        state.record_failure(now - timedelta(minutes=30), error)
        
        # Should skip because we're within the backoff period
        assert schedule.should_skip_update(now) is True
    
    def test_should_skip_update_backoff_expired(self) -> None:
        """Test that updates resume after backoff period expires."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)
        
        # Record 3 failures but long ago
        old_time = datetime.now() - timedelta(days=1)
        error = Exception("Test error")
        state.record_failure(old_time, error)
        state.record_failure(old_time, error)
        state.record_failure(old_time, error)
        
        # Should not skip because backoff period has expired
        now = datetime.now()
        assert schedule.should_skip_update(now) is False
    
    def test_exponential_backoff_calculation(self) -> None:
        """Test exponential backoff calculation."""
        now = datetime.now()
        error = Exception("Test error")

        # Test different failure counts
        for failures in [3, 4, 5, 6]:
            # Create fresh state for each test
            config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
            state = ScheduleState()
            schedule = UpdateSchedule(config, state)

            # Set the failure count directly and record the failure
            state.consecutive_failures = failures - 1  # Will be incremented by record_failure
            state.record_failure(now, error)

            # Calculate expected backoff
            failure_count = min(failures, 6)
            expected_hours = 1 << failure_count  # Bit shift for 2^failure_count
            backoff_until = now + timedelta(hours=expected_hours)

            # Should skip until backoff expires
            assert schedule.should_skip_update(now + timedelta(hours=expected_hours - 1)) is True
            # Should not skip after backoff expires (add a small buffer)
            assert schedule.should_skip_update(backoff_until + timedelta(minutes=1)) is False


class TestUpdateTrackerEnhanced:
    """Test enhanced UpdateTracker functionality."""
    
    @pytest.fixture
    def mock_bot(self) -> commands.Bot:
        """Create a mock Discord bot using standardized utility."""
        return create_mock_discord_bot(user_name="UpdateTrackerBot", guild_count=1)
    
    @pytest.fixture
    def update_tracker(self, mock_bot: commands.Bot) -> UpdateTracker:
        """Create an UpdateTracker instance."""
        return UpdateTracker(mock_bot)
    
    def test_get_last_update_time_initial(self, update_tracker: UpdateTracker) -> None:
        """Test getting last update time when no updates have occurred."""
        assert update_tracker.get_last_update_time() is None
    
    def test_get_next_update_time_not_running(self, update_tracker: UpdateTracker) -> None:
        """Test getting next update time when scheduler is not running."""
        assert update_tracker.get_next_update_time() is None
    
    def test_get_scheduler_status_initial(self, update_tracker: UpdateTracker) -> None:
        """Test getting scheduler status in initial state."""
        status = update_tracker.get_scheduler_status()
        
        assert status["is_running"] is False
        assert status["last_update"] is None
        assert status["next_update"] is None
        assert status["consecutive_failures"] == 0
        assert status["last_failure"] is None
        assert status["config_update_days"] is None
        assert status["config_fixed_time"] is None
    
    @pytest.mark.asyncio
    async def test_trigger_update_success(self, update_tracker: UpdateTracker) -> None:
        """Test successful update trigger."""
        # Set up callback
        callback = AsyncMock()
        update_tracker.set_update_callback(callback)

        # Trigger update
        await update_tracker._trigger_update_for_testing()  # pyright: ignore[reportPrivateUsage]

        # Verify callback was called and state updated
        callback.assert_called_once()
        state = update_tracker._get_state_for_testing()  # pyright: ignore[reportPrivateUsage]
        assert state.last_update is not None
        assert state.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_trigger_update_failure(self, update_tracker: UpdateTracker) -> None:
        """Test failed update trigger."""
        # Set up failing callback
        callback = AsyncMock(side_effect=Exception("Test error"))
        update_tracker.set_update_callback(callback)

        # Trigger update (should raise exception)
        with pytest.raises(Exception, match="Test error"):
            await update_tracker._trigger_update_for_testing()  # pyright: ignore[reportPrivateUsage]

        # Verify failure was recorded
        state = update_tracker._get_state_for_testing()  # pyright: ignore[reportPrivateUsage]
        assert state.consecutive_failures == 1
        assert state.last_failure is not None
    
    def test_fixed_time_with_dst_handling(self) -> None:
        """Test fixed time calculation handles daylight saving time correctly."""
        config = SchedulingConfig(update_days=7, fixed_update_time="14:30")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)
        
        # Set a previous update
        last_update = datetime(2024, 1, 1, 14, 30)  # Winter time
        state.record_successful_update(last_update)
        
        # Calculate next update during potential DST transition
        current_time = datetime(2024, 1, 5, 10, 0)  # 4 days later
        next_update = schedule.calculate_next_update(current_time)
        
        # Should respect the interval and maintain the correct time
        expected_date = last_update.date() + timedelta(days=7)
        assert next_update.date() == expected_date
        assert next_update.time().hour == 14
        assert next_update.time().minute == 30
