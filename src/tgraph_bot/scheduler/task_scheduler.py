"""Task scheduler for automated graph updates.

This module provides the TaskScheduler class that manages scheduled graph
generation and posting based on configured intervals and times.

Requirements implemented: 7.1, 7.2, 7.3, 7.4, 7.5, 22.1, 22.2, 22.4
"""

from __future__ import annotations

import asyncio
import logging
import random
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from tgraph_bot.config.models import AutomationConfig

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TaskScheduler:
    """Manages scheduled graph updates.

    This class handles the scheduling of automated graph generation and posting
    based on the configured update interval and fixed time settings.

    Attributes:
        config: Automation configuration containing scheduling parameters
        _task: The asyncio task running the schedule loop (None when not started)

    Requirements:
        - 7.1: Schedule automatic graph updates based on configured interval
        - 7.2: Generate and post graphs at specific time daily (HH:MM format)
        - 7.3: Generate and post graphs at random time (XX:XX format)
        - 7.5: Support graceful shutdown with task cancellation
        - 22.1: Use asyncio.TaskGroup for structured concurrency (in _execute_update)
        - 22.2: Automatic task cancellation on failure
        - 22.4: Use asynccontextmanager for resource lifecycle
    """

    config: AutomationConfig
    _task: asyncio.Task[None] | None = field(default=None, init=False)

    async def start(self) -> None:
        """Start the scheduler task.

        Creates and starts the background task that runs the scheduling loop.
        If a task is already running, this method does nothing.

        Requirements: 7.1, 7.5
        """
        if self._task is not None and not self._task.done():
            logger.warning("Scheduler task already running")
            return

        self._task = asyncio.create_task(self._schedule_loop())
        logger.info("Task scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler task.

        Cancels the running scheduler task and waits for it to complete.
        Safe to call multiple times or when no task is running.

        Requirements: 7.5
        """
        if self._task is None:
            return

        if not self._task.done():
            _ = self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass  # Expected when cancelling

        logger.info("Task scheduler stopped")

    async def _schedule_loop(self) -> None:
        """Main scheduling loop.

        Continuously calculates the next run time, sleeps until that time,
        and executes the update. Handles errors during execution to ensure
        the loop continues running.

        Requirements: 7.1, 7.2, 7.3
        """
        while True:
            try:
                next_run = self._calculate_next_run()
                now = datetime.now()
                sleep_seconds = (next_run - now).total_seconds()

                if sleep_seconds > 0:
                    logger.info(
                        "Next scheduled update at %s (in %.0f seconds)",
                        next_run.isoformat(),
                        sleep_seconds,
                    )
                    await asyncio.sleep(sleep_seconds)

                # Execute the scheduled update
                await self._execute_update()

            except asyncio.CancelledError:
                # Graceful shutdown requested
                logger.info("Scheduler loop cancelled")
                raise
            except Exception as e:
                # Log error but continue running
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                # Wait a bit before retrying to avoid tight error loops
                await asyncio.sleep(60)

    def _calculate_next_run(self) -> datetime:
        """Calculate the next scheduled run time.

        Returns:
            The datetime when the next update should run

        Requirements:
            - 7.2: Fixed time (HH:MM) - daily at that specific time
            - 7.3: Random time (XX:XX) - random time within update interval
        """
        now = datetime.now()
        fixed_time_str = self.config.fixed_update_time

        if fixed_time_str == "XX:XX":
            # Random time within the update interval
            return self._calculate_random_next_run(now)
        else:
            # Fixed time daily
            return self._calculate_fixed_next_run(now, fixed_time_str)

    def _calculate_fixed_next_run(self, now: datetime, time_str: str) -> datetime:
        """Calculate next run time for fixed time schedule.

        Args:
            now: Current datetime
            time_str: Time string in HH:MM format

        Returns:
            Next scheduled run datetime

        Requirements: 7.2
        """
        # Parse the time string
        hour, minute = map(int, time_str.split(":"))
        target_time = time(hour=hour, minute=minute)

        # Combine with today's date
        next_run = datetime.combine(now.date(), target_time)

        # If the time has already passed today, schedule for tomorrow
        if next_run <= now:
            next_run += timedelta(days=1)

        return next_run

    def _calculate_random_next_run(self, now: datetime) -> datetime:
        """Calculate next run time for random time schedule.

        Generates a random datetime within the configured update interval
        from the current time.

        Args:
            now: Current datetime

        Returns:
            Random datetime within the update interval

        Requirements: 7.3
        """
        interval_days = self.config.update_interval_days

        # Generate random offset in seconds within the interval
        # Use full interval range: 0 to interval_days * 86400 seconds
        max_seconds = interval_days * 86400
        random_seconds = random.uniform(0, max_seconds)

        next_run = now + timedelta(seconds=random_seconds)
        return next_run

    async def _execute_update(self) -> None:
        """Execute the scheduled graph update.

        This method will be implemented to trigger graph generation and posting.
        For now, it's a placeholder that logs the execution.

        Requirements: 7.4
        """
        logger.info("Executing scheduled graph update")
        # TODO: Implement graph generation and posting
        # This will be implemented in task 14 when integrating with graph generation
        # Will use TaskGroup for concurrent graph generation (Requirement 22.1)


@asynccontextmanager
async def managed_scheduler(
    scheduler: TaskScheduler,
) -> AsyncGenerator[TaskScheduler, None]:
    """Context manager for scheduler lifecycle.

    Automatically starts the scheduler on entry and stops it on exit,
    ensuring proper cleanup even if exceptions occur.

    Args:
        scheduler: The TaskScheduler instance to manage

    Yields:
        The running scheduler instance

    Requirements: 22.4 (asynccontextmanager for resource lifecycle)

    Example:
        >>> async with managed_scheduler(scheduler) as sched:
        ...     # Scheduler is running
        ...     await asyncio.sleep(10)
        ... # Scheduler is automatically stopped
    """
    await scheduler.start()
    try:
        yield scheduler
    finally:
        await scheduler.stop()

