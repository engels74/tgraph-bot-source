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
        self.last_update: datetime | None = None
        self.update_callback: Callable[[], None] | None = None

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
            
        logger.info(f"Starting update scheduler (every {update_days} days)")
        if fixed_update_time and fixed_update_time != "XX:XX":
            logger.info(f"Fixed update time: {fixed_update_time}")
            
        self.update_task = asyncio.create_task(
            self._scheduler_loop(update_days, fixed_update_time)
        )
        
    async def stop_scheduler(self) -> None:
        """Stop the automatic update scheduler."""
        if self.update_task is not None:
            _ = self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
            self.update_task = None
            logger.info("Update scheduler stopped")

    async def _scheduler_loop(
        self,
        update_days: int,
        fixed_update_time: str | None
    ) -> None:
        """
        Main scheduler loop for automatic updates.
        
        Args:
            update_days: Interval in days between updates
            fixed_update_time: Fixed time for updates (HH:MM format) or None
        """
        try:
            while True:
                next_update = self._calculate_next_update(update_days, fixed_update_time)
                wait_seconds = (next_update - datetime.now()).total_seconds()
                
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
            
    def _calculate_next_update(
        self,
        update_days: int,
        fixed_update_time: str | None
    ) -> datetime:
        """
        Calculate the next update time.
        
        Args:
            update_days: Interval in days between updates
            fixed_update_time: Fixed time for updates (HH:MM format) or None
            
        Returns:
            The next update datetime
        """
        now = datetime.now()
        
        if fixed_update_time and fixed_update_time != "XX:XX":
            # Parse fixed time
            try:
                hour, minute = map(int, fixed_update_time.split(":"))
                update_time = time(hour, minute)
                
                # Calculate next occurrence of this time
                next_update = datetime.combine(now.date(), update_time)
                
                # If time has passed today, schedule for tomorrow
                if next_update <= now:
                    next_update += timedelta(days=1)
                    
                # If we have a last update, ensure we respect the update_days interval
                if self.last_update:
                    min_next_update = self.last_update + timedelta(days=update_days)
                    if next_update < min_next_update:
                        # Find next occurrence that respects the interval
                        days_to_add = (min_next_update.date() - next_update.date()).days
                        next_update += timedelta(days=days_to_add)
                        
                return next_update
                
            except ValueError:
                logger.error(f"Invalid fixed update time format: {fixed_update_time}")
                
        # Fallback to interval-based scheduling
        if self.last_update:
            return self.last_update + timedelta(days=update_days)
        else:
            # First run - schedule for next interval
            return now + timedelta(days=update_days)
            
    async def _trigger_update(self) -> None:
        """Trigger a graph update."""
        logger.info("Triggering scheduled graph update")
        
        try:
            if self.update_callback:
                await asyncio.to_thread(self.update_callback)
            else:
                logger.warning("No update callback set")
                
            self.last_update = datetime.now()
            logger.info("Scheduled update completed successfully")
            
        except Exception as e:
            logger.exception(f"Error during scheduled update: {e}")
            
    async def force_update(self) -> None:
        """Force an immediate update outside of the schedule."""
        logger.info("Forcing immediate graph update")
        await self._trigger_update()
        
    def get_next_update_time(
        self,
        update_days: int,
        fixed_update_time: str | None
    ) -> datetime | None:
        """
        Get the next scheduled update time.
        
        Args:
            update_days: Interval in days between updates
            fixed_update_time: Fixed time for updates (HH:MM format) or None
            
        Returns:
            The next update datetime or None if scheduler not running
        """
        if self.update_task is None:
            return None
            
        return self._calculate_next_update(update_days, fixed_update_time)
