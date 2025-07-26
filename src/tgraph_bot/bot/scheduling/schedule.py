"""
Schedule calculation and timing logic for the update scheduling system.

This module handles the calculation of when updates should occur based on
configuration settings and current state.
"""

from datetime import datetime, timedelta

from .types import SchedulingConfig, ScheduleState
from ...utils.time import TimestampCalculator


class UpdateSchedule:
    """Handles calculation of update schedules based on configuration and state."""

    def __init__(self, config: SchedulingConfig, state: ScheduleState) -> None:
        """
        Initialize update schedule calculator.

        Args:
            config: Scheduling configuration
            state: Current schedule state
        """
        self.config: SchedulingConfig = config
        self.state: ScheduleState = state
        self._calculator: TimestampCalculator = TimestampCalculator()

    def calculate_next_update(self, current_time: datetime) -> datetime:
        """
        Calculate the next update time based on configuration and state.

        This method now uses the centralized TimestampCalculator to ensure
        consistency with Discord embed displays.

        Args:
            current_time: Current datetime for calculation reference

        Returns:
            Next scheduled update datetime (timezone-aware)
        """
        # Use centralized calculator for consistency
        return self._calculator.calculate_next_update(
            update_days=self.config.update_days,
            fixed_update_time=self.config.fixed_update_time,
            last_update=self.state.last_update,
            current_time=current_time,
        )

    def is_valid_schedule_time(
        self, schedule_time: datetime, current_time: datetime
    ) -> bool:
        """
        Validate that a scheduled time is reasonable.

        Args:
            schedule_time: The proposed schedule time
            current_time: Current time for reference

        Returns:
            True if the schedule time is valid
        """
        # Must be in the future
        if schedule_time <= current_time:
            return False

        # Must not be too far in the future (max 1 year)
        max_future = current_time + timedelta(days=365)
        if schedule_time > max_future:
            return False

        return True

    def calculate_time_until_next_update(self, current_time: datetime) -> timedelta:
        """
        Calculate the time remaining until the next update.

        Args:
            current_time: Current datetime for calculation reference

        Returns:
            Time remaining until next update
        """
        return self._calculator.calculate_time_until_next_update(
            update_days=self.config.update_days,
            fixed_update_time=self.config.fixed_update_time,
            last_update=self.state.last_update,
            current_time=current_time,
        )

    def should_skip_update(self, current_time: datetime) -> bool:
        """
        Determine if an update should be skipped due to recent failures.

        Args:
            current_time: Current datetime for calculation reference

        Returns:
            True if update should be skipped
        """
        # Skip if too many consecutive failures (exponential backoff)
        if self.state.consecutive_failures >= 3:
            if self.state.last_failure:
                # Exponential backoff: 2^failures hours
                failure_count = min(
                    self.state.consecutive_failures, 6
                )  # Cap at 64 hours
                backoff_hours = 1 << failure_count  # Bit shift for 2^failure_count
                backoff_until = self.state.last_failure + timedelta(hours=backoff_hours)
                return current_time < backoff_until

        return False