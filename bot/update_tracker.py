"""
Update tracking and scheduling for TGraph Bot.

This module manages the scheduling and tracking of when server-wide graphs
should be automatically updated, based on configuration (UPDATE_DAYS, FIXED_UPDATE_TIME).
"""

import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from discord.ext import commands

logger = logging.getLogger(__name__)


class UpdateTracker:
    """Manages scheduling and tracking of automatic graph updates."""
    
    def __init__(self, bot: "commands.Bot") -> None:
        """
        Initialize the update tracker.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.update_task: Optional[asyncio.Task[None]] = None
        self.last_update: Optional[datetime] = None
        self.update_callback: Optional[Callable[[], None]] = None
        
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
        fixed_update_time: Optional[str] = None
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
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
            self.update_task = None
            logger.info("Update scheduler stopped")
            
    async def _scheduler_loop(
        self, 
        update_days: int,
        fixed_update_time: Optional[str]
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
        fixed_update_time: Optional[str]
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
        fixed_update_time: Optional[str]
    ) -> Optional[datetime]:
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
