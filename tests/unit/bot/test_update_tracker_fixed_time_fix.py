"""
Tests for the fixed time scheduling bug fix.

This module specifically tests the fix for the scheduling logic bug where
UPDATE_DAYS was ignored on first run with fixed time scheduling.
"""

from datetime import datetime, timedelta, time

from src.tgraph_bot.bot.update_tracker import (
    SchedulingConfig,
    ScheduleState,
    UpdateSchedule,
    get_local_timezone,
)


class TestFixedTimeSchedulingBugFix:
    """Test the fix for the fixed time scheduling bug."""

    def test_first_run_respects_update_days_fixed_time(self) -> None:
        """Test that first run respects UPDATE_DAYS with fixed time scheduling."""
        # Setup: First run scenario (no last_update)
        config = SchedulingConfig(update_days=1, fixed_update_time="23:59")
        state = ScheduleState()  # No last_update (first run)
        schedule = UpdateSchedule(config, state)

        # Current time: 2025-07-16 21:28:00 (same as bug report)
        current_time = datetime(2025, 7, 16, 21, 28, 0, tzinfo=get_local_timezone())

        # Calculate next update
        next_update = schedule.calculate_next_update(current_time)

        # Expected: Should be 2025-07-17 23:59:00 (next day due to UPDATE_DAYS=1)
        expected_date = current_time.date() + timedelta(days=1)
        expected_time = time(23, 59)
        expected_next_update = datetime.combine(expected_date, expected_time).replace(
            tzinfo=get_local_timezone()
        )

        assert next_update == expected_next_update
        assert next_update.date() == (current_time.date() + timedelta(days=1))
        assert next_update.time() == time(23, 59)

    def test_first_run_respects_update_days_multiple_days(self) -> None:
        """Test that first run respects UPDATE_DAYS with multiple days."""
        # Setup: First run with UPDATE_DAYS=3
        config = SchedulingConfig(update_days=3, fixed_update_time="14:30")
        state = ScheduleState()  # No last_update (first run)
        schedule = UpdateSchedule(config, state)

        current_time = datetime(2025, 7, 16, 10, 0, 0, tzinfo=get_local_timezone())
        next_update = schedule.calculate_next_update(current_time)

        # Expected: Should be 3 days later at 14:30
        expected_date = current_time.date() + timedelta(days=3)
        expected_time = time(14, 30)
        expected_next_update = datetime.combine(expected_date, expected_time).replace(
            tzinfo=get_local_timezone()
        )

        assert next_update == expected_next_update
        assert next_update.date() == (current_time.date() + timedelta(days=3))
        assert next_update.time() == time(14, 30)

    def test_subsequent_run_respects_update_days_fixed_time(self) -> None:
        """Test that subsequent runs still respect UPDATE_DAYS with fixed time."""
        # Setup: Subsequent run scenario (has last_update)
        config = SchedulingConfig(update_days=2, fixed_update_time="12:00")
        state = ScheduleState()
        state.last_update = datetime(
            2025, 7, 14, 12, 0, 0, tzinfo=get_local_timezone()
        )  # 2 days ago
        schedule = UpdateSchedule(config, state)

        current_time = datetime(2025, 7, 16, 10, 0, 0, tzinfo=get_local_timezone())
        next_update = schedule.calculate_next_update(current_time)

        # Expected: Should be 2 days after last_update at 12:00
        expected_date = state.last_update.date() + timedelta(days=2)
        expected_time = time(12, 0)
        expected_next_update = datetime.combine(expected_date, expected_time).replace(
            tzinfo=get_local_timezone()
        )

        assert next_update == expected_next_update
        assert next_update.date() == (state.last_update.date() + timedelta(days=2))
        assert next_update.time() == time(12, 0)

    def test_bug_scenario_reproduction_and_fix(self) -> None:
        """Test the exact scenario from the bug report to verify the fix."""
        # Exact scenario from bug report
        config = SchedulingConfig(update_days=1, fixed_update_time="23:59")
        state = ScheduleState()  # First run, no last_update
        schedule = UpdateSchedule(config, state)

        # Bot started at 2025-07-16T21:28:00.798405
        current_time = datetime(
            2025, 7, 16, 21, 28, 0, 798405, tzinfo=get_local_timezone()
        )
        next_update = schedule.calculate_next_update(current_time)

        # Before fix: Would be 2025-07-16T23:59:00 (same day - BUG!)
        # After fix: Should be 2025-07-17T23:59:00 (next day - CORRECT!)
        expected_next_update = datetime(
            2025, 7, 17, 23, 59, 0, tzinfo=get_local_timezone()
        )

        assert next_update == expected_next_update
        assert next_update.date() > current_time.date()  # Must be future date
        assert next_update.time() == time(23, 59)  # Correct time

    def test_edge_case_time_already_passed_today(self) -> None:
        """Test when fixed time has already passed today."""
        config = SchedulingConfig(update_days=1, fixed_update_time="10:00")
        state = ScheduleState()  # First run
        schedule = UpdateSchedule(config, state)

        # Current time is after 10:00 today
        current_time = datetime(2025, 7, 16, 15, 30, 0, tzinfo=get_local_timezone())
        next_update = schedule.calculate_next_update(current_time)

        # Should be tomorrow at 10:00 (respecting UPDATE_DAYS=1)
        expected_next_update = datetime(
            2025, 7, 17, 10, 0, 0, tzinfo=get_local_timezone()
        )

        assert next_update == expected_next_update
        assert next_update.date() == (current_time.date() + timedelta(days=1))
        assert next_update.time() == time(10, 0)

    def test_edge_case_time_not_passed_today(self) -> None:
        """Test when fixed time has not passed today."""
        config = SchedulingConfig(update_days=1, fixed_update_time="18:00")
        state = ScheduleState()  # First run
        schedule = UpdateSchedule(config, state)

        # Current time is before 18:00 today
        current_time = datetime(2025, 7, 16, 12, 0, 0, tzinfo=get_local_timezone())
        next_update = schedule.calculate_next_update(current_time)

        # Should be tomorrow at 18:00 (respecting UPDATE_DAYS=1)
        expected_next_update = datetime(
            2025, 7, 17, 18, 0, 0, tzinfo=get_local_timezone()
        )

        assert next_update == expected_next_update
        assert next_update.date() == (current_time.date() + timedelta(days=1))
        assert next_update.time() == time(18, 0)

    def test_validation_error_for_invalid_schedule(self) -> None:
        """Test that validation catches invalid schedule times."""
        config = SchedulingConfig(update_days=1, fixed_update_time="23:59")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)

        # Create a scenario where calculated time would be in the past
        # (This shouldn't happen with our fix, but test the validation)
        current_time = datetime(2025, 7, 16, 21, 28, 0, tzinfo=get_local_timezone())

        # Mock the calculation to return a past time to test validation
        past_time = current_time - timedelta(hours=1)

        # Test that our validation would catch this
        assert not schedule.is_valid_schedule_time(past_time, current_time)

        # Test that a future time is valid
        future_time = current_time + timedelta(hours=1)
        assert schedule.is_valid_schedule_time(future_time, current_time)

    def test_consistency_between_first_and_subsequent_runs(self) -> None:
        """Test that scheduling behavior is consistent between first and subsequent runs."""
        config = SchedulingConfig(update_days=2, fixed_update_time="15:45")

        # First run scenario
        state_first = ScheduleState()
        schedule_first = UpdateSchedule(config, state_first)
        current_time = datetime(2025, 7, 16, 10, 0, 0, tzinfo=get_local_timezone())
        first_run_next = schedule_first.calculate_next_update(current_time)

        # Subsequent run scenario with same timing
        state_subsequent = ScheduleState()
        state_subsequent.last_update = current_time
        schedule_subsequent = UpdateSchedule(config, state_subsequent)
        subsequent_run_next = schedule_subsequent.calculate_next_update(current_time)

        # Both should respect UPDATE_DAYS=2 and schedule 2 days later
        expected_date = current_time.date() + timedelta(days=2)
        expected_time = time(15, 45)
        expected_next_update = datetime.combine(expected_date, expected_time).replace(
            tzinfo=get_local_timezone()
        )

        assert first_run_next == expected_next_update
        assert subsequent_run_next == expected_next_update
        assert first_run_next == subsequent_run_next  # Consistent behavior

    def test_interval_scheduling_unchanged(self) -> None:
        """Test that interval scheduling (non-fixed time) is unchanged by the fix."""
        config = SchedulingConfig(update_days=3, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)

        current_time = datetime(2025, 7, 16, 14, 30, 0, tzinfo=get_local_timezone())
        next_update = schedule.calculate_next_update(current_time)

        # Should be exactly 3 days later (interval scheduling)
        expected_next_update = current_time + timedelta(days=3)

        assert next_update == expected_next_update
        assert (next_update - current_time).days == 3
