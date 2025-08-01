"""
Update tracking and scheduling for TGraph Bot.

This module provides the main UpdateTracker class that orchestrates
the scheduling system using the refactored modular components.
"""

import asyncio
import logging
from collections.abc import Callable, Awaitable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .scheduling import (
    TaskStatus,
    ErrorType,
    CircuitState,
    RetryConfig,
    ErrorMetrics,
    SchedulingConfig,
    ScheduleState,
    ErrorClassifier,
    CircuitBreaker,
    BackgroundTaskManager,
    UpdateSchedule,
    StateManager,
    RecoveryManager,
)
from ..utils.time import get_system_now

if TYPE_CHECKING:
    from discord.ext import commands

logger = logging.getLogger(__name__)


class UpdateTracker:
    """
    Enhanced update tracker with background task management.

    Manages scheduling and tracking of automatic graph updates using
    the BackgroundTaskManager for robust task lifecycle management.
    """

    def __init__(
        self,
        bot: "commands.Bot",
        retry_config: RetryConfig | None = None,
        state_file_path: Path | None = None,
    ) -> None:
        """
        Initialize the update tracker with enhanced error handling and recovery.

        Args:
            bot: The Discord bot instance
            retry_config: Configuration for retry policies and circuit breakers
            state_file_path: Optional custom path for state persistence
        """
        self.bot: "commands.Bot" = bot
        self.update_callback: Callable[[], Awaitable[None]] | None = None

        # Initialize enhanced task manager with retry configuration
        self._retry_config: RetryConfig = retry_config or RetryConfig()
        self._task_manager: BackgroundTaskManager = BackgroundTaskManager(
            restart_delay=30.0, retry_config=self._retry_config
        )

        # Initialize scheduling components
        self._config: SchedulingConfig | None = None
        self._state: ScheduleState = ScheduleState()
        self._schedule: UpdateSchedule | None = None
        self._is_started: bool = False

        # Enhanced error tracking
        self._update_metrics: ErrorMetrics = ErrorMetrics()
        self._circuit_breaker: CircuitBreaker = CircuitBreaker(self._retry_config)

        # Recovery and persistence components
        self._state_manager: StateManager = StateManager(state_file_path)
        self._recovery_manager: RecoveryManager = RecoveryManager(self._state_manager)
        self._recovery_enabled: bool = True

    def set_update_callback(self, callback: Callable[[], Awaitable[None]]) -> None:
        """
        Set the callback function to call when updates are triggered.

        Args:
            callback: Async function to call for graph updates
        """
        self.update_callback = callback

    async def start_scheduler(
        self, update_days: int = 7, fixed_update_time: str | None = None
    ) -> None:
        """
        Start the automatic update scheduler with recovery and persistence.

        Args:
            update_days: Interval in days between updates
            fixed_update_time: Fixed time for updates (HH:MM format) or None
        """
        if self._is_started:
            logger.warning("Update scheduler already running")
            return

        # Initialize scheduling configuration
        fixed_time_str = fixed_update_time if fixed_update_time else "XX:XX"
        new_config = SchedulingConfig(
            update_days=update_days, fixed_update_time=fixed_time_str
        )

        # Attempt to load previous state and perform recovery
        if self._recovery_enabled:
            await self._perform_startup_recovery(new_config)
        else:
            self._config = new_config
            self._schedule = UpdateSchedule(self._config, self._state)

        logger.info(f"Starting update scheduler (every {update_days} days)")
        if fixed_update_time and fixed_update_time != "XX:XX":
            logger.info(f"Fixed update time: {fixed_update_time}")

        # Start the background task manager
        await self._task_manager.start()

        # Add the scheduler task
        self._task_manager.add_task(
            "update_scheduler", self._scheduler_loop, restart_on_failure=True
        )

        self._state.start_scheduler()
        self._is_started = True

        # Save initial state
        if self._recovery_enabled:
            try:
                self._state_manager.save_state(self._state, self._config)
                logger.debug("Initial state saved after scheduler start")
            except Exception as e:
                logger.error(f"Failed to save initial state: {e}")

    async def _perform_startup_recovery(self, new_config: SchedulingConfig) -> None:
        """
        Perform startup recovery by loading previous state and handling missed updates.

        Args:
            new_config: New configuration to apply
        """
        logger.info("Performing startup recovery")

        try:
            # Load previous state
            loaded_state, loaded_config = self._state_manager.load_state()

            # Use loaded state if available
            if loaded_state:
                self._state = loaded_state
                logger.info("Previous state loaded successfully")

                # Check if configuration changed
                config_changed = False
                if loaded_config:
                    if (
                        loaded_config.update_days != new_config.update_days
                        or loaded_config.fixed_update_time
                        != new_config.fixed_update_time
                    ):
                        config_changed = True
                        logger.info("Configuration changed since last run")

                # Use new configuration (may have changed)
                self._config = new_config

                # Perform recovery operations
                current_time = get_system_now()
                (
                    recovered_state,
                    missed_updates,
                ) = await self._recovery_manager.perform_recovery(
                    current_time=current_time,
                    state=self._state,
                    config=self._config,
                    update_callback=self.update_callback if config_changed else None,
                )

                self._state = recovered_state

                if missed_updates:
                    logger.info(
                        f"Recovery completed: processed {len(missed_updates)} missed updates"
                    )
                    for missed in missed_updates:
                        logger.info(
                            f"  - Processed missed update from {missed.scheduled_time} ({missed.reason})"
                        )

            else:
                # No previous state, use new configuration
                self._config = new_config
                logger.info("No previous state found, starting fresh")

            # Create schedule with current state and config
            self._schedule = UpdateSchedule(self._config, self._state)

        except Exception as e:
            logger.error(f"Recovery failed, starting with fresh state: {e}")
            # Fallback to fresh state
            self._config = new_config
            self._state = ScheduleState()
            self._schedule = UpdateSchedule(self._config, self._state)

    async def stop_scheduler(self) -> None:
        """Stop the automatic update scheduler and save state."""
        if not self._is_started:
            logger.debug("Update scheduler not running")
            return

        logger.info("Stopping update scheduler")

        # Save current state before stopping
        if self._recovery_enabled and self._config:
            try:
                self._state_manager.save_state(self._state, self._config)
                logger.debug("State saved before scheduler stop")
            except Exception as e:
                logger.error(f"Failed to save state during shutdown: {e}")

        # Stop the background task manager (this will cancel all tasks)
        await self._task_manager.stop()

        self._state.stop_scheduler()
        self._is_started = False
        logger.info("Update scheduler stopped")

    async def _wait_with_health_updates(
        self, total_wait_seconds: float, task_name: str = "update_scheduler"
    ) -> bool:
        """
        Wait for specified duration while periodically updating health status.

        This method breaks long waits into smaller chunks to prevent health check
        false positives during extended sleep periods.

        Args:
            total_wait_seconds: Total time to wait in seconds
            task_name: Name of the task for health updates

        Returns:
            True if wait completed normally, False if shutdown was requested
        """
        if total_wait_seconds <= 0:
            return True

        # Health update interval - keep it well below the 5-minute stale threshold
        health_update_interval = 120.0  # 2 minutes

        elapsed = 0.0

        while (
            elapsed < total_wait_seconds
            and not self._task_manager._shutdown_event.is_set()  # pyright: ignore[reportPrivateUsage]
        ):
            # Calculate how long to sleep this iteration
            remaining = total_wait_seconds - elapsed
            chunk_duration = min(health_update_interval, remaining)

            try:
                # Wait for this chunk duration or until shutdown requested
                _ = await asyncio.wait_for(
                    self._task_manager._shutdown_event.wait(),  # pyright: ignore[reportPrivateUsage]
                    timeout=chunk_duration,
                )
                # Shutdown was requested
                logger.debug(
                    f"Shutdown requested during scheduler wait (elapsed: {elapsed:.1f}s)"
                )
                return False

            except asyncio.TimeoutError:
                # Timeout is expected - this chunk completed normally
                elapsed += chunk_duration

                # Update health status to prevent stale detection
                if task_name in self._task_manager._task_health:  # pyright: ignore[reportPrivateUsage]
                    self._task_manager._task_health[task_name] = get_system_now()  # pyright: ignore[reportPrivateUsage]
                    logger.debug(
                        f"Updated health for {task_name} during long wait (elapsed: {elapsed:.1f}s/{total_wait_seconds:.1f}s)"
                    )

        return True

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

                current_time = get_system_now()

                # Check if we should skip this update due to recent failures
                if self._schedule.should_skip_update(current_time):
                    logger.info(
                        "Skipping update due to recent failures (exponential backoff)"
                    )
                    # Wait a bit before checking again
                    wait_completed = await self._wait_with_health_updates(
                        300.0
                    )  # 5 minutes
                    if not wait_completed:
                        logger.info(
                            "Scheduler loop terminated due to shutdown request during backoff"
                        )
                        break
                    continue

                next_update = self._schedule.calculate_next_update(current_time)

                # Validate the calculated schedule time
                if not self._schedule.is_valid_schedule_time(next_update, current_time):
                    logger.error(f"Invalid schedule time calculated: {next_update}")
                    # Fallback to a simple interval
                    from datetime import timedelta

                    next_update = current_time + timedelta(hours=1)

                self._state.set_next_update(next_update)
                wait_seconds = (next_update - current_time).total_seconds()

                if wait_seconds > 0:
                    logger.info(
                        f"Next update scheduled for: {next_update} (wait time: {wait_seconds:.1f}s)"
                    )
                    wait_completed = await self._wait_with_health_updates(wait_seconds)
                    if not wait_completed:
                        # Shutdown was requested during wait
                        logger.info("Scheduler loop terminated due to shutdown request")
                        break

                # Trigger update
                await self._trigger_update()

        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
            raise
        except Exception as e:
            logger.exception(f"Error in scheduler loop: {e}")
            # Record the failure
            if self._state:
                self._state.record_failure(get_system_now(), e)
            # Wait before retrying to avoid tight error loops
            wait_completed = await self._wait_with_health_updates(60.0)  # 1 minute
            if not wait_completed:
                logger.info(
                    "Scheduler loop terminated due to shutdown request during error recovery"
                )
                return

    async def _trigger_update(self) -> None:
        """
        Trigger a graph update with comprehensive error handling and retry logic.

        This method implements circuit breaker pattern, retry logic with exponential
        backoff, detailed error classification, and comprehensive audit logging.
        """
        # Check circuit breaker before attempting update
        if not self._circuit_breaker.should_allow_request():
            error_msg = "Update blocked by circuit breaker (too many recent failures)"
            logger.warning(error_msg)
            self._log_update_audit("update_blocked", error_msg)
            raise RuntimeError(error_msg)

        self._update_metrics.record_attempt()
        start_time = get_system_now()

        logger.info(
            f"Triggering scheduled graph update (attempt {self._update_metrics.total_attempts})"
        )
        self._log_update_audit(
            "update_started",
            f"Starting update attempt {self._update_metrics.total_attempts}",
        )

        # Retry logic with exponential backoff
        last_exception: Exception | None = None

        for attempt in range(self._retry_config.max_attempts):
            try:
                if attempt > 0:
                    # Calculate delay for retry
                    delay = self._retry_config.base_delay * (
                        self._retry_config.exponential_base ** (attempt - 1)
                    )
                    delay = min(delay, self._retry_config.max_delay)

                    # Add jitter if enabled
                    if self._retry_config.jitter:
                        import random

                        jitter_factor = 0.75 + (random.random() * 0.5)  # 0.75 to 1.25
                        delay *= jitter_factor

                    logger.info(
                        f"Retrying update after {delay:.1f}s delay (attempt {attempt + 1}/{self._retry_config.max_attempts})"
                    )
                    self._log_update_audit(
                        "update_retry",
                        f"Retrying after {delay:.1f}s (attempt {attempt + 1})",
                    )
                    await asyncio.sleep(delay)

                # Store the scheduled time before updating state
                scheduled_time = self._state.next_update
                logical_update_time = (
                    scheduled_time if scheduled_time else get_system_now()
                )

                # Record successful update using the scheduled time as the logical update time
                # This ensures consistent scheduling intervals regardless of execution delays
                # Update this BEFORE calculating next update so the calculator uses the correct last_update
                self._state.record_successful_update(logical_update_time)

                # Calculate and set next update time BEFORE executing update callback
                # This ensures Discord embeds created during the callback get the correct future timestamp
                if self._schedule:
                    next_update_time = self._schedule.calculate_next_update(
                        logical_update_time
                    )
                    self._state.set_next_update(next_update_time)
                    logger.info(f"Next update scheduled for: {next_update_time}")

                # Execute the update callback
                if self.update_callback:
                    # Add timeout protection
                    await asyncio.wait_for(
                        self.update_callback(), timeout=600.0
                    )  # 10 minute timeout
                else:
                    error_msg = "No update callback set"
                    logger.error(error_msg)
                    self._log_update_audit("update_error", error_msg)
                    raise RuntimeError(error_msg)

                # Record successful metrics
                update_time = get_system_now()
                duration = (update_time - start_time).total_seconds()
                self._update_metrics.record_success()
                self._circuit_breaker.record_success()

                success_msg = f"Scheduled update completed successfully in {duration:.1f}s (success rate: {self._update_metrics.get_success_rate():.2%})"
                logger.info(success_msg)
                self._log_update_audit("update_completed", success_msg)

                # Save state after successful update
                if self._recovery_enabled and self._config:
                    try:
                        self._state_manager.save_state(self._state, self._config)
                        logger.debug("State saved after successful update")
                    except Exception as e:
                        logger.error(f"Failed to save state after update: {e}")

                return

            except asyncio.TimeoutError as e:
                last_exception = e
                error_type = ErrorClassifier.classify_error(e)
                error_msg = f"Update attempt {attempt + 1} timed out after 10 minutes"
                logger.warning(error_msg)
                self._log_update_audit("update_timeout", error_msg)

                if attempt == self._retry_config.max_attempts - 1:
                    break  # Don't retry on last attempt

            except Exception as e:
                last_exception = e
                error_type = ErrorClassifier.classify_error(e)
                error_msg = f"Update attempt {attempt + 1} failed with {error_type.value} error: {str(e)[:200]}"
                logger.warning(error_msg)
                self._log_update_audit("update_attempt_failed", error_msg)

                # Don't retry permanent errors
                if error_type == ErrorType.PERMANENT:
                    logger.error(f"Permanent error detected, not retrying: {e}")
                    break

                if attempt == self._retry_config.max_attempts - 1:
                    break  # Don't retry on last attempt

        # All attempts failed
        failure_time = get_system_now()
        duration = (failure_time - start_time).total_seconds()

        if last_exception:
            error_type = ErrorClassifier.classify_error(last_exception)
            self._state.record_failure(failure_time, last_exception)
            self._update_metrics.record_failure(error_type)
            self._circuit_breaker.record_failure(last_exception)

            failure_msg = (
                f"All {self._retry_config.max_attempts} update attempts failed after {duration:.1f}s. "
                f"Last error ({error_type.value}): {last_exception}"
            )
            logger.exception(failure_msg)
            self._log_update_audit("update_failed", failure_msg)

            # Log circuit breaker state if it opened
            if self._circuit_breaker.get_state() == CircuitState.OPEN:
                logger.error("Circuit breaker opened due to repeated failures")
                self._log_update_audit(
                    "circuit_breaker_opened",
                    "Circuit breaker opened due to repeated failures",
                )

            raise last_exception
        else:
            # This shouldn't happen, but handle it gracefully
            error_msg = f"Update failed after {self._retry_config.max_attempts} attempts with no recorded exception"
            logger.error(error_msg)
            self._log_update_audit("update_failed", error_msg)
            raise RuntimeError(error_msg)

    def _log_update_audit(self, event_type: str, message: str) -> None:
        """Log audit events for update operations."""
        timestamp = get_system_now().isoformat()
        audit_msg = f"[UPDATE_AUDIT] {timestamp} - {event_type}: {message}"
        logger.info(audit_msg)

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
        if not self._is_started or self._schedule is None:
            return None

        return self._state.next_update

    def get_last_update_time(self) -> datetime | None:
        """
        Get the last update time.

        Returns:
            The last update datetime or None if no updates have occurred
        """
        return self._state.last_update

    def get_scheduler_status(self) -> dict[str, str | int | datetime | None | bool]:
        """
        Get comprehensive scheduler status information including task manager status.

        Returns:
            Dictionary containing scheduler status details
        """
        task_status = self._task_manager.get_all_task_status()
        scheduler_task_status = task_status.get("update_scheduler", {})

        return {
            "is_running": self._state.is_running,
            "is_started": self._is_started,
            "last_update": self._state.last_update,
            "next_update": self._state.next_update,
            "consecutive_failures": self._state.consecutive_failures,
            "last_failure": self._state.last_failure,
            "config_update_days": self._config.update_days if self._config else None,
            "config_fixed_time": self._config.fixed_update_time
            if self._config
            else None,
            "task_manager_healthy": self._task_manager.is_healthy(),
            "scheduler_task_status": scheduler_task_status.get("status"),
            "scheduler_task_health": scheduler_task_status.get("last_health"),
        }

    def is_scheduler_healthy(self) -> bool:
        """
        Check if the scheduler and its background tasks are healthy.

        Returns:
            True if scheduler is running and healthy, False otherwise
        """
        if not self._is_started:
            return False

        # Check if task manager is healthy
        if not self._task_manager.is_healthy():
            return False

        # Check if scheduler task is running
        task_status = self._task_manager.get_task_status("update_scheduler")
        if task_status != TaskStatus.RUNNING:
            return False

        return True

    async def restart_scheduler(self) -> None:
        """
        Restart the scheduler with current configuration.

        Useful for recovering from failures or applying configuration changes.
        """
        if not self._config:
            logger.error("Cannot restart scheduler: no configuration available")
            return

        logger.info("Restarting update scheduler")

        # Stop current scheduler
        await self.stop_scheduler()

        # Start with current configuration
        fixed_time = (
            None
            if self._config.fixed_update_time == "XX:XX"
            else self._config.fixed_update_time
        )
        await self.start_scheduler(
            update_days=self._config.update_days, fixed_update_time=fixed_time
        )

    def get_update_metrics(
        self,
    ) -> dict[str, str | int | float | dict[str, int] | None]:
        """Get comprehensive update metrics."""
        return self._update_metrics.to_dict()

    def get_circuit_breaker_status(self) -> dict[str, str | int | datetime | None]:
        """Get circuit breaker status for updates."""
        metrics = self._circuit_breaker.get_metrics()
        return {
            "state": self._circuit_breaker.get_state().value,
            "consecutive_failures": metrics.consecutive_failures,
            "consecutive_successes": metrics.consecutive_successes,
            "last_failure": metrics.last_failure,
            "last_success": metrics.last_success,
            "circuit_opened_at": metrics.circuit_opened_at,
        }

    def get_comprehensive_status(self) -> dict[str, object]:
        """Get comprehensive status including all metrics and health information."""
        base_status = self.get_scheduler_status()

        # Create comprehensive status dictionary
        comprehensive_status: dict[str, object] = dict(base_status)
        comprehensive_status.update(
            {
                "update_metrics": self.get_update_metrics(),
                "circuit_breaker": self.get_circuit_breaker_status(),
                "task_manager_metrics": self._task_manager.get_all_task_metrics(),
                "task_manager_health": self._task_manager.get_health_summary(),
                "circuit_breaker_states": self._task_manager.get_all_circuit_breaker_status(),
            }
        )

        return comprehensive_status

    def get_audit_log(self, limit: int = 50) -> list[dict[str, str | datetime | None]]:
        """Get recent audit log entries from task manager."""
        return self._task_manager.get_audit_log(limit)

    def reset_error_state(self) -> None:
        """Reset error state and circuit breakers (for recovery purposes)."""
        logger.info("Resetting error state and circuit breakers")

        # Reset update metrics
        self._update_metrics = ErrorMetrics()
        self._circuit_breaker = CircuitBreaker(self._retry_config)

        # Reset state consecutive failures
        self._state.consecutive_failures = 0
        self._state.last_error = None

        logger.info("Error state reset completed")

    # Test helper methods (for testing purposes only)
    def _get_state_for_testing(self) -> ScheduleState:
        """Get the internal state for testing purposes."""
        return self._state

    async def _trigger_update_for_testing(self) -> None:
        """Trigger update for testing purposes."""
        await self._trigger_update()

    # Recovery and persistence methods

    def enable_recovery(self) -> None:
        """Enable recovery and persistence features."""
        self._recovery_enabled = True
        logger.info("Recovery and persistence enabled")

    def disable_recovery(self) -> None:
        """Disable recovery and persistence features."""
        self._recovery_enabled = False
        logger.info("Recovery and persistence disabled")

    def is_recovery_enabled(self) -> bool:
        """Check if recovery is enabled."""
        return self._recovery_enabled

    async def force_recovery(self) -> dict[str, object]:
        """
        Force a recovery operation and return results.

        Returns:
            Dictionary with recovery results and statistics
        """
        if not self._config:
            raise RuntimeError("Cannot perform recovery: no configuration available")

        logger.info("Forcing recovery operation")
        current_time = get_system_now()

        # Perform recovery
        recovered_state, missed_updates = await self._recovery_manager.perform_recovery(
            current_time=current_time,
            state=self._state,
            config=self._config,
            update_callback=self.update_callback,
        )

        self._state = recovered_state

        # Save recovered state
        if self._recovery_enabled:
            try:
                self._state_manager.save_state(self._state, self._config)
            except Exception as e:
                logger.error(f"Failed to save recovered state: {e}")

        return {
            "recovery_time": current_time.isoformat(),
            "missed_updates_detected": len(missed_updates),
            "missed_updates": [update.to_dict() for update in missed_updates],
            "state_after_recovery": self._state.to_dict(),
        }

    def get_recovery_status(self) -> dict[str, object]:
        """
        Get comprehensive recovery and persistence status.

        Returns:
            Dictionary with recovery status information
        """
        status: dict[str, object] = {
            "recovery_enabled": self._recovery_enabled,
            "state_file_exists": self._state_manager.state_exists(),
            "state_file_path": str(self._state_manager.state_file_path),
        }

        # Add schedule integrity check if we have configuration
        if self._config:
            current_time = get_system_now()
            is_valid, issues = self._recovery_manager.validate_schedule_integrity(
                current_time, self._state, self._config
            )
            status["schedule_integrity_valid"] = is_valid
            status["schedule_integrity_issues"] = issues

        return status

    def clear_persistent_state(self) -> None:
        """Clear persistent state file (for testing or reset purposes)."""
        try:
            self._state_manager.delete_state()
            logger.info("Persistent state cleared")
        except Exception as e:
            logger.error(f"Failed to clear persistent state: {e}")
            raise

    async def validate_and_repair_schedule(self) -> dict[str, object]:
        """
        Validate schedule integrity and repair if necessary.

        Returns:
            Dictionary with validation and repair results
        """
        if not self._config:
            raise RuntimeError("Cannot validate schedule: no configuration available")

        current_time = get_system_now()

        # Validate current state
        is_valid, issues = self._recovery_manager.validate_schedule_integrity(
            current_time, self._state, self._config
        )

        result: dict[str, object] = {
            "validation_time": current_time.isoformat(),
            "was_valid": is_valid,
            "issues_found": issues,
            "repairs_performed": [],
        }

        # Repair if necessary
        if not is_valid:
            logger.info("Schedule integrity issues detected, performing repairs")
            original_state = self._state.to_dict()

            self._state = self._recovery_manager.repair_schedule_state(
                current_time, self._state, self._config
            )

            # Save repaired state
            if self._recovery_enabled:
                try:
                    self._state_manager.save_state(self._state, self._config)
                    result["state_saved"] = True
                except Exception as e:
                    logger.error(f"Failed to save repaired state: {e}")
                    result["state_saved"] = False
                    result["save_error"] = str(e)

            # Document what was repaired
            repaired_state = self._state.to_dict()
            repairs: list[dict[str, object]] = []
            for key, original_value in original_state.items():
                new_value = repaired_state.get(key)
                if original_value != new_value:
                    repairs.append(
                        {
                            "field": key,
                            "old_value": original_value,
                            "new_value": new_value,
                        }
                    )

            result["repairs_performed"] = repairs
            logger.info(f"Schedule repairs completed: {len(repairs)} fields modified")

        return result


__all__ = [
    "UpdateTracker",
]
