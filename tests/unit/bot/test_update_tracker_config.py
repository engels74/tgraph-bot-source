"""
Tests for update tracker scheduling configuration and data structures.

This module tests the scheduling configuration parsing, validation,
and data structure management for the automated update system.
"""

import pytest
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from src.tgraph_bot.bot.update_tracker import SchedulingConfig, ScheduleState, UpdateSchedule, get_local_timezone


class TestSchedulingConfig:
    """Test scheduling configuration parsing and validation."""
    
    def test_interval_based_config(self) -> None:
        """Test interval-based scheduling configuration."""
        config = SchedulingConfig(
            update_days=7,
            fixed_update_time="XX:XX"
        )
        
        assert config.update_days == 7
        assert config.fixed_update_time == "XX:XX"
        assert config.is_interval_based() is True
        assert config.is_fixed_time_based() is False
        assert config.get_fixed_time() is None
    
    def test_fixed_time_config(self) -> None:
        """Test fixed time scheduling configuration."""
        config = SchedulingConfig(
            update_days=7,
            fixed_update_time="14:30"
        )
        
        assert config.update_days == 7
        assert config.fixed_update_time == "14:30"
        assert config.is_interval_based() is False
        assert config.is_fixed_time_based() is True
        
        fixed_time = config.get_fixed_time()
        assert fixed_time is not None
        assert fixed_time.hour == 14
        assert fixed_time.minute == 30
    
    def test_invalid_time_format(self) -> None:
        """Test invalid time format handling."""
        with pytest.raises(ValueError, match="Invalid time format"):
            _ = SchedulingConfig(
                update_days=7,
                fixed_update_time="25:00"  # Invalid hour
            )

        with pytest.raises(ValueError, match="Invalid time format"):
            _ = SchedulingConfig(
                update_days=7,
                fixed_update_time="12:60"  # Invalid minute
            )

        with pytest.raises(ValueError, match="Invalid time format"):
            _ = SchedulingConfig(
                update_days=7,
                fixed_update_time="invalid"
            )
    
    def test_invalid_update_days(self) -> None:
        """Test invalid update days validation."""
        with pytest.raises(ValueError, match="UPDATE_DAYS must be between 1 and 365"):
            _ = SchedulingConfig(
                update_days=0,
                fixed_update_time="XX:XX"
            )

        with pytest.raises(ValueError, match="UPDATE_DAYS must be between 1 and 365"):
            _ = SchedulingConfig(
                update_days=366,
                fixed_update_time="XX:XX"
            )
    
    def test_config_equality(self) -> None:
        """Test configuration equality comparison."""
        config1 = SchedulingConfig(update_days=7, fixed_update_time="14:30")
        config2 = SchedulingConfig(update_days=7, fixed_update_time="14:30")
        config3 = SchedulingConfig(update_days=5, fixed_update_time="14:30")
        
        assert config1 == config2
        assert config1 != config3


class TestScheduleState:
    """Test schedule state management."""
    
    def test_initial_state(self) -> None:
        """Test initial schedule state."""
        state = ScheduleState()
        
        assert state.last_update is None
        assert state.next_update is None
        assert state.is_running is False
        assert state.consecutive_failures == 0
        assert state.last_failure is None
    
    def test_update_tracking(self) -> None:
        """Test update tracking functionality."""
        state = ScheduleState()
        now = datetime.now(get_local_timezone())
        
        # Record successful update
        state.record_successful_update(now)
        assert state.last_update == now
        assert state.consecutive_failures == 0
        assert state.last_failure is None
    
    def test_failure_tracking(self) -> None:
        """Test failure tracking functionality."""
        state = ScheduleState()
        now = datetime.now(get_local_timezone())
        error = Exception("Test error")
        
        # Record failure
        state.record_failure(now, error)
        assert state.consecutive_failures == 1
        assert state.last_failure == now
        
        # Record another failure
        state.record_failure(now + timedelta(minutes=1), error)
        assert state.consecutive_failures == 2
        
        # Record success - should reset failure count
        state.record_successful_update(now + timedelta(minutes=2))
        assert state.consecutive_failures == 0
        assert state.last_failure == now + timedelta(minutes=1)  # Preserved
    
    def test_schedule_management(self) -> None:
        """Test schedule management."""
        state = ScheduleState()
        next_time = datetime.now(get_local_timezone()) + timedelta(hours=1)
        
        state.set_next_update(next_time)
        assert state.next_update == next_time
        
        state.start_scheduler()
        assert state.is_running is True
        
        state.stop_scheduler()
        assert state.is_running is False


class TestUpdateSchedule:
    """Test update schedule calculation logic."""
    
    def test_interval_based_calculation(self) -> None:
        """Test interval-based schedule calculation."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)
        
        # First calculation (no previous update)
        now = datetime.now(get_local_timezone())
        next_update = schedule.calculate_next_update(now)
        
        expected = now + timedelta(days=7)
        # Allow small time difference due to execution time
        assert abs((next_update - expected).total_seconds()) < 1
    
    def test_interval_with_previous_update(self) -> None:
        """Test interval calculation with previous update."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        
        # Set previous update
        last_update = datetime.now(get_local_timezone()) - timedelta(days=3)
        state.record_successful_update(last_update)
        
        schedule = UpdateSchedule(config, state)
        next_update = schedule.calculate_next_update(datetime.now(get_local_timezone()))
        
        expected = last_update + timedelta(days=7)
        assert abs((next_update - expected).total_seconds()) < 1
    
    def test_fixed_time_calculation_today(self) -> None:
        """Test fixed time calculation respects UPDATE_DAYS on first run."""
        config = SchedulingConfig(update_days=1, fixed_update_time="23:59")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)
        
        # Test at early morning - should schedule for tomorrow (respects UPDATE_DAYS=1)
        test_time = datetime.now(get_local_timezone()).replace(hour=1, minute=0, second=0, microsecond=0)
        next_update = schedule.calculate_next_update(test_time)

        assert next_update.date() == test_time.date() + timedelta(days=1)
        assert next_update.time() == time(23, 59)
    
    def test_fixed_time_calculation_tomorrow(self) -> None:
        """Test fixed time calculation for tomorrow."""
        config = SchedulingConfig(update_days=1, fixed_update_time="08:00")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)
        
        # Test at late evening - should schedule for tomorrow
        test_time = datetime.now(get_local_timezone()).replace(hour=22, minute=0, second=0, microsecond=0)
        next_update = schedule.calculate_next_update(test_time)
        
        expected_date = test_time.date() + timedelta(days=1)
        assert next_update.date() == expected_date
        assert next_update.time() == time(8, 0)
    
    def test_fixed_time_with_interval_constraint(self) -> None:
        """Test fixed time with interval constraint."""
        config = SchedulingConfig(update_days=7, fixed_update_time="12:00")
        state = ScheduleState()

        # Set last update to 2 days ago with clean time
        base_time = datetime.now(get_local_timezone()).replace(hour=12, minute=0, second=0, microsecond=0)
        last_update = base_time - timedelta(days=2)
        state.record_successful_update(last_update)

        schedule = UpdateSchedule(config, state)
        test_time = base_time.replace(hour=10, minute=0)
        next_update = schedule.calculate_next_update(test_time)

        # Should respect the 7-day interval, not schedule for today
        min_next_update = last_update + timedelta(days=7)
        assert next_update >= min_next_update
        assert next_update.time() == time(12, 0)
    
    def test_schedule_validation(self) -> None:
        """Test schedule validation."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)
        
        now = datetime.now(get_local_timezone())
        
        # Valid future time
        future_time = now + timedelta(hours=1)
        assert schedule.is_valid_schedule_time(future_time, now) is True
        
        # Invalid past time
        past_time = now - timedelta(hours=1)
        assert schedule.is_valid_schedule_time(past_time, now) is False
        
        # Invalid too far future
        far_future = now + timedelta(days=400)
        assert schedule.is_valid_schedule_time(far_future, now) is False
