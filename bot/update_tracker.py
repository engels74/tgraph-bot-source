"""
Update tracking and scheduling for TGraph Bot.

This module manages the scheduling and tracking of when server-wide graphs
should be automatically updated, based on configuration (UPDATE_DAYS, FIXED_UPDATE_TIME).
"""

import asyncio
import logging
import re
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING
from collections.abc import Callable
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from discord.ext import commands

logger = logging.getLogger(__name__)


@dataclass
class SchedulingConfig:
    """Configuration for scheduling automatic updates."""

    update_days: int
    fixed_update_time: str

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_update_days()
        self._validate_fixed_update_time()

    def _validate_update_days(self) -> None:
        """Validate update_days is within acceptable range."""
        if not (1 <= self.update_days <= 365):
            raise ValueError("UPDATE_DAYS must be between 1 and 365")

    def _validate_fixed_update_time(self) -> None:
        """Validate fixed_update_time format."""
        if self.fixed_update_time == "XX:XX":
            return  # Disabled fixed time is valid

        # Validate HH:MM format
        if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", self.fixed_update_time):
            raise ValueError(f"Invalid time format: {self.fixed_update_time}")

        # Additional validation by parsing
        try:
            hour, minute = map(int, self.fixed_update_time.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError(f"Invalid time format: {self.fixed_update_time}")
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid time format: {self.fixed_update_time}") from e

    def is_interval_based(self) -> bool:
        """Check if scheduling is interval-based (not fixed time)."""
        return self.fixed_update_time == "XX:XX"

    def is_fixed_time_based(self) -> bool:
        """Check if scheduling is fixed time-based."""
        return not self.is_interval_based()

    def get_fixed_time(self) -> time | None:
        """Get the fixed time as a time object, or None if disabled."""
        if self.is_interval_based():
            return None

        hour, minute = map(int, self.fixed_update_time.split(":"))
        return time(hour, minute)


@dataclass
class ScheduleState:
    """State tracking for the update scheduler."""

    last_update: datetime | None = None
    next_update: datetime | None = None
    is_running: bool = False
    consecutive_failures: int = 0
    last_failure: datetime | None = None
    last_error: Exception | None = field(default=None, repr=False)

    def record_successful_update(self, update_time: datetime) -> None:
        """Record a successful update."""
        self.last_update = update_time
        self.consecutive_failures = 0
        # Keep last_failure for historical tracking

    def record_failure(self, failure_time: datetime, error: Exception) -> None:
        """Record a failed update attempt."""
        self.consecutive_failures += 1
        self.last_failure = failure_time
        self.last_error = error

    def set_next_update(self, next_time: datetime) -> None:
        """Set the next scheduled update time."""
        self.next_update = next_time

    def start_scheduler(self) -> None:
        """Mark scheduler as running."""
        self.is_running = True

    def stop_scheduler(self) -> None:
        """Mark scheduler as stopped."""
        self.is_running = False


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

    def calculate_next_update(self, current_time: datetime) -> datetime:
        """
        Calculate the next update time based on configuration and state.

        Args:
            current_time: Current datetime for calculation reference

        Returns:
            Next scheduled update datetime
        """
        if self.config.is_fixed_time_based():
            return self._calculate_fixed_time_update(current_time)
        else:
            return self._calculate_interval_update(current_time)

    def _calculate_interval_update(self, current_time: datetime) -> datetime:
        """Calculate next update for interval-based scheduling."""
        if self.state.last_update:
            return self.state.last_update + timedelta(days=self.config.update_days)
        else:
            # First run - schedule for next interval
            return current_time + timedelta(days=self.config.update_days)

    def _calculate_fixed_time_update(self, current_time: datetime) -> datetime:
        """Calculate next update for fixed time scheduling."""
        fixed_time = self.config.get_fixed_time()
        if fixed_time is None:
            # Fallback to interval if fixed time is invalid
            return self._calculate_interval_update(current_time)

        # Calculate next occurrence of the fixed time
        next_update = datetime.combine(current_time.date(), fixed_time)

        # If time has passed today, schedule for tomorrow
        if next_update <= current_time:
            next_update += timedelta(days=1)

        # Respect the update_days interval if we have a last update
        if self.state.last_update:
            min_next_update = self.state.last_update + timedelta(days=self.config.update_days)
            if next_update < min_next_update:
                # Find next occurrence that respects the interval
                days_to_add = (min_next_update.date() - next_update.date()).days
                next_update += timedelta(days=days_to_add)

                # Ensure we still have the correct time after adding days
                next_update = datetime.combine(next_update.date(), fixed_time)

        return next_update

    def is_valid_schedule_time(self, schedule_time: datetime, current_time: datetime) -> bool:
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
        next_update = self.calculate_next_update(current_time)
        return next_update - current_time

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
                failure_count = min(self.state.consecutive_failures, 6)  # Cap at 64 hours
                backoff_hours = 1 << failure_count  # Bit shift for 2^failure_count
                backoff_until = self.state.last_failure + timedelta(hours=backoff_hours)
                return current_time < backoff_until

        return False


class UpdateTracker:
    """Manages scheduling and tracking of automatic graph updates."""

    def __init__(self, bot: "commands.Bot") -> None:
        """
        Initialize the update tracker.

        Args:
            bot: The Discord bot instance
        """
        self.bot: "commands.Bot" = bot
        self.update_task: asyncio.Task[None] | None = None
        self.update_callback: Callable[[], None] | None = None

        # Initialize scheduling components
        self._config: SchedulingConfig | None = None
        self._state: ScheduleState = ScheduleState()
        self._schedule: UpdateSchedule | None = None

    def set_update_callback(self, callback: Callable[[], None]) -> None:
        """
        Set the callback function to call when updates are triggered.

        Args:
            callback: Function to call for graph updates
        """
        self.update_callback = callback

    async def start_scheduler(
        self,
        update_days: int = 7,
        fixed_update_time: str | None = None
    ) -> None:
        """
        Start the automatic update scheduler.

        Args:
            update_days: Interval in days between updates
            fixed_update_time: Fixed time for updates (HH:MM format) or None
        """
        if self.update_task is not None:
            logger.warning("Update scheduler already running")
            return

        # Initialize scheduling configuration
        fixed_time_str = fixed_update_time if fixed_update_time else "XX:XX"
        self._config = SchedulingConfig(
            update_days=update_days,
            fixed_update_time=fixed_time_str
        )
        self._schedule = UpdateSchedule(self._config, self._state)

        logger.info(f"Starting update scheduler (every {update_days} days)")
        if fixed_update_time and fixed_update_time != "XX:XX":
            logger.info(f"Fixed update time: {fixed_update_time}")

        self._state.start_scheduler()
        self.update_task = asyncio.create_task(self._scheduler_loop())
        
    async def stop_scheduler(self) -> None:
        """Stop the automatic update scheduler."""
        if self.update_task is not None:
            _ = self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
            self.update_task = None
            self._state.stop_scheduler()
            logger.info("Update scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """
        Main scheduler loop for automatic updates.

        Uses the configured scheduling logic to determine when updates should occur.
        """
        try:
            while True:
                if self._schedule is None:
                    logger.error("Scheduler loop started without proper configuration")
                    break

                current_time = datetime.now()

                # Check if we should skip this update due to recent failures
                if self._schedule.should_skip_update(current_time):
                    logger.info("Skipping update due to recent failures (exponential backoff)")
                    # Wait a bit before checking again
                    await asyncio.sleep(300)  # 5 minutes
                    continue

                next_update = self._schedule.calculate_next_update(current_time)

                # Validate the calculated schedule time
                if not self._schedule.is_valid_schedule_time(next_update, current_time):
                    logger.error(f"Invalid schedule time calculated: {next_update}")
                    # Fallback to a simple interval
                    next_update = current_time + timedelta(hours=1)

                self._state.set_next_update(next_update)
                wait_seconds = (next_update - current_time).total_seconds()

                if wait_seconds > 0:
                    logger.info(f"Next update scheduled for: {next_update}")
                    await asyncio.sleep(wait_seconds)

                # Trigger update
                await self._trigger_update()

        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
            raise
        except Exception as e:
            logger.exception(f"Error in scheduler loop: {e}")
            # Record the failure
            if self._state:
                self._state.record_failure(datetime.now(), e)
            # Wait before retrying to avoid tight error loops
            await asyncio.sleep(60)  # 1 minute

    async def _trigger_update(self) -> None:
        """Trigger a graph update."""
        logger.info("Triggering scheduled graph update")

        try:
            if self.update_callback:
                await asyncio.to_thread(self.update_callback)
            else:
                logger.warning("No update callback set")

            # Record successful update in state
            update_time = datetime.now()
            self._state.record_successful_update(update_time)
            logger.info("Scheduled update completed successfully")

        except Exception as e:
            logger.exception(f"Error during scheduled update: {e}")
            # Record failure in state
            self._state.record_failure(datetime.now(), e)
            raise

    async def force_update(self) -> None:
        """Force an immediate update outside of the schedule."""
        logger.info("Forcing immediate graph update")
        await self._trigger_update()

    def get_next_update_time(self) -> datetime | None:
        """
        Get the next scheduled update time.

        Returns:
            The next update datetime or None if scheduler not running
        """
        if self.update_task is None or self._schedule is None:
            return None

        return self._state.next_update

    def get_last_update_time(self) -> datetime | None:
        """
        Get the last update time.

        Returns:
            The last update datetime or None if no updates have occurred
        """
        return self._state.last_update

    def get_scheduler_status(self) -> dict[str, str | int | datetime | None]:
        """
        Get comprehensive scheduler status information.

        Returns:
            Dictionary containing scheduler status details
        """
        return {
            "is_running": self._state.is_running,
            "last_update": self._state.last_update,
            "next_update": self._state.next_update,
            "consecutive_failures": self._state.consecutive_failures,
            "last_failure": self._state.last_failure,
            "config_update_days": self._config.update_days if self._config else None,
            "config_fixed_time": self._config.fixed_update_time if self._config else None,
        }

    # Test helper methods (for testing purposes only)
    def _get_state_for_testing(self) -> ScheduleState:
        """Get the internal state for testing purposes."""
        return self._state

    async def _trigger_update_for_testing(self) -> None:
        """Trigger update for testing purposes."""
        await self._trigger_update()
