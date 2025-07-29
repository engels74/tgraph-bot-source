"""
Test for date calculation bug fix with UPDATE_DAYS=1.

This module contains comprehensive tests that reproduce and verify the fix
for the bug where both last_update and next_update timestamps are set to
the same date when UPDATE_DAYS=1 on first launch.

Following TDD principles:
1. Write failing tests that demonstrate the bug
2. Fix the implementation to make tests pass
3. Verify no regressions in existing functionality
"""

from datetime import datetime, time, timedelta

from src.tgraph_bot.utils.time.scheduling import calculate_next_fixed_time
from src.tgraph_bot.utils.time.timezone import get_system_timezone


class TestDateCalculationBugFix:
    """Test cases for the date calculation bug with UPDATE_DAYS=1."""

    def test_first_run_update_days_1_should_schedule_next_day(self) -> None:
        """
        Test that first run with UPDATE_DAYS=1 schedules for next day.

        This test reproduces the exact bug scenario:
        - UPDATE_DAYS=1 (daily updates)
        - Fixed time scheduling (23:59)
        - No last_update (first launch)
        - Current time before the fixed time

        Expected: next_update should be 1 day later, not same day.
        """
        # Scenario: Bot starts at 22:20, fixed time is 23:59, UPDATE_DAYS=1
        current_time = datetime(2025, 7, 25, 22, 20, 12, tzinfo=get_system_timezone())
        fixed_time = time(23, 59)
        update_days = 1
        last_update = None  # First run

        next_update = calculate_next_fixed_time(
            current_time, fixed_time, update_days, last_update
        )

        # Should be scheduled for tomorrow at 23:59, not today
        expected_date = current_time.date() + timedelta(days=1)
        expected_next_update = datetime.combine(expected_date, fixed_time).replace(
            tzinfo=get_system_timezone()
        )

        assert next_update == expected_next_update
        assert next_update.date() == (current_time.date() + timedelta(days=1))
        assert next_update.time() == fixed_time

    def test_first_run_update_days_1_different_times(self) -> None:
        """Test first run UPDATE_DAYS=1 with different current times."""
        test_cases = [
            # (current_hour, fixed_hour, fixed_minute)
            (1, 23, 59),  # Very early morning, late evening fixed time
            (10, 14, 30),  # Morning, afternoon fixed time
            (20, 8, 0),  # Evening, morning fixed time
            (12, 12, 0),  # Noon, same time fixed (edge case)
        ]

        for current_hour, fixed_hour, fixed_minute in test_cases:
            current_time = datetime(
                2025, 7, 25, current_hour, 0, 0, tzinfo=get_system_timezone()
            )
            fixed_time = time(fixed_hour, fixed_minute)
            update_days = 1
            last_update = None  # First run

            next_update = calculate_next_fixed_time(
                current_time, fixed_time, update_days, last_update
            )

            # Should always be scheduled for next day with UPDATE_DAYS=1
            expected_date = current_time.date() + timedelta(days=1)
            expected_next_update = datetime.combine(expected_date, fixed_time).replace(
                tzinfo=get_system_timezone()
            )

            assert next_update == expected_next_update, (
                f"Failed for current_time={current_hour}:00, "
                f"fixed_time={fixed_hour}:{fixed_minute:02d}"
            )

    def test_first_run_update_days_multiple_should_respect_interval(self) -> None:
        """Test first run with UPDATE_DAYS > 1 respects the interval."""
        test_cases = [2, 3, 7, 14]  # Different update intervals

        for update_days in test_cases:
            current_time = datetime(2025, 7, 25, 10, 0, 0, tzinfo=get_system_timezone())
            fixed_time = time(14, 30)
            last_update = None  # First run

            next_update = calculate_next_fixed_time(
                current_time, fixed_time, update_days, last_update
            )

            # Should be scheduled update_days from now
            expected_min_date = current_time.date() + timedelta(days=update_days)

            assert next_update.date() >= expected_min_date, (
                f"Failed for UPDATE_DAYS={update_days}: "
                f"expected >= {expected_min_date}, got {next_update.date()}"
            )
            assert next_update.time() == fixed_time

    def test_exact_bug_scenario_reproduction(self) -> None:
        """Reproduce the exact scenario from the bug report."""
        # Exact timestamps from the bug report
        current_time = datetime(
            2025, 7, 25, 22, 20, 12, 406078, tzinfo=get_system_timezone()
        )
        fixed_time = time(23, 59)
        update_days = 1
        last_update = None  # First launch

        next_update = calculate_next_fixed_time(
            current_time, fixed_time, update_days, last_update
        )

        # Expected correct behavior: next day at 23:59
        expected_next_update = datetime(
            2025, 7, 26, 23, 59, 0, tzinfo=get_system_timezone()
        )

        assert next_update == expected_next_update

        # Verify it's not the same date (the bug)
        assert next_update.date() != current_time.date()
        assert next_update.date() == current_time.date() + timedelta(days=1)

    def test_subsequent_runs_behavior_unchanged(self) -> None:
        """Test that subsequent runs (with last_update) are not affected."""
        current_time = datetime(2025, 7, 25, 10, 0, 0, tzinfo=get_system_timezone())
        fixed_time = time(23, 59)
        update_days = 1

        # Simulate a previous update
        last_update = datetime(2025, 7, 24, 23, 59, 0, tzinfo=get_system_timezone())

        next_update = calculate_next_fixed_time(
            current_time, fixed_time, update_days, last_update
        )

        # Should be 1 day after last_update
        expected_next_update = datetime(
            2025, 7, 25, 23, 59, 0, tzinfo=get_system_timezone()
        )

        assert next_update == expected_next_update
        assert (next_update.date() - last_update.date()).days == update_days

    def test_edge_case_exactly_at_fixed_time(self) -> None:
        """Test edge case when current time exactly matches fixed time."""
        # Current time is exactly the fixed time
        current_time = datetime(2025, 7, 25, 23, 59, 0, tzinfo=get_system_timezone())
        fixed_time = time(23, 59)
        update_days = 1
        last_update = None  # First run

        next_update = calculate_next_fixed_time(
            current_time, fixed_time, update_days, last_update
        )

        # Should still be scheduled for next day (not same moment)
        expected_next_update = datetime(
            2025, 7, 26, 23, 59, 0, tzinfo=get_system_timezone()
        )

        assert next_update == expected_next_update
        assert next_update.date() == current_time.date() + timedelta(days=1)

    def test_edge_case_past_fixed_time_same_day(self) -> None:
        """Test when current time is past the fixed time on same day."""
        # Current time is after the fixed time
        current_time = datetime(2025, 7, 25, 23, 59, 30, tzinfo=get_system_timezone())
        fixed_time = time(23, 59)  # 30 seconds ago
        update_days = 1
        last_update = None  # First run

        next_update = calculate_next_fixed_time(
            current_time, fixed_time, update_days, last_update
        )

        # Should be scheduled for next day
        expected_next_update = datetime(
            2025, 7, 26, 23, 59, 0, tzinfo=get_system_timezone()
        )

        assert next_update == expected_next_update
        assert next_update.date() == current_time.date() + timedelta(days=1)


class TestIntervalConsistency:
    """Test that the fix maintains interval consistency."""

    def test_interval_consistency_between_runs(self) -> None:
        """Test that intervals are consistent between first and subsequent runs."""
        fixed_time = time(12, 0)
        update_days = 1
        base_date = datetime(2025, 7, 25, tzinfo=get_system_timezone())

        # First run
        first_run_time = base_date.replace(hour=10, minute=0)
        first_next_update = calculate_next_fixed_time(
            first_run_time, fixed_time, update_days, last_update=None
        )

        # Simulate the update happening
        simulated_last_update = first_next_update

        # Second run (after the update)
        second_run_time = first_next_update + timedelta(hours=1)
        second_next_update = calculate_next_fixed_time(
            second_run_time, fixed_time, update_days, last_update=simulated_last_update
        )

        # Verify consistent interval
        first_interval = (first_next_update.date() - first_run_time.date()).days
        second_interval = (
            second_next_update.date() - simulated_last_update.date()
        ).days

        assert first_interval == update_days
        assert second_interval == update_days
        assert first_interval == second_interval

    def test_no_regression_with_existing_logic(self) -> None:
        """Test that the fix doesn't break existing multi-day logic."""
        test_cases = [
            (7, "weekly updates"),
            (14, "bi-weekly updates"),
            (30, "monthly updates"),
        ]

        for update_days, description in test_cases:
            current_time = datetime(2025, 7, 25, 14, 0, 0, tzinfo=get_system_timezone())
            fixed_time = time(12, 0)
            last_update = None  # First run

            next_update = calculate_next_fixed_time(
                current_time, fixed_time, update_days, last_update
            )

            # Should respect the minimum interval
            min_expected_date = current_time.date() + timedelta(days=update_days)

            assert next_update.date() >= min_expected_date, (
                f"Failed for {description}: expected >= {min_expected_date}, "
                f"got {next_update.date()}"
            )
            assert next_update.time() == fixed_time
