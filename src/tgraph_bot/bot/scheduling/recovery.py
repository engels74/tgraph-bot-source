"""
Recovery and schedule integrity management for the scheduling system.

This module handles missed update detection, schedule validation, and
automatic repair of inconsistent scheduler state.
"""

import logging
from collections.abc import Callable, Awaitable
from datetime import datetime, timedelta

from .types import (
    SchedulingConfig,
    ScheduleState,
    MissedUpdate,
)
from .schedule import UpdateSchedule
from .persistence import StateManager
from ...utils.time import get_system_now

logger = logging.getLogger(__name__)


class RecoveryManager:
    """Manages recovery operations for the scheduler."""

    def __init__(self, state_manager: StateManager) -> None:
        """
        Initialize recovery manager.

        Args:
            state_manager: State manager for persistence operations
        """
        self.state_manager: StateManager = state_manager

    def detect_missed_updates(
        self,
        current_time: datetime,
        last_update: datetime | None,
        next_update: datetime | None,
        config: SchedulingConfig,
    ) -> list[MissedUpdate]:
        """
        Detect missed updates based on current time and last known state.

        Args:
            current_time: Current datetime
            last_update: Last successful update time
            next_update: Last scheduled next update time
            config: Current scheduling configuration

        Returns:
            List of missed updates that should be processed
        """
        missed_updates: list[MissedUpdate] = []

        # If we have no update history, no missed updates to detect
        if last_update is None:
            logger.debug("No previous update history, no missed updates to detect")
            return missed_updates

        # Calculate what the next update should have been
        schedule = UpdateSchedule(config, ScheduleState())
        schedule.state.last_update = last_update

        # Check if we missed the scheduled next update
        if next_update and next_update < current_time:
            # We missed the scheduled update
            missed_updates.append(
                MissedUpdate(
                    scheduled_time=next_update,
                    detected_at=current_time,
                    reason="missed_scheduled_update",
                )
            )
            logger.warning(f"Detected missed scheduled update: {next_update}")

        # Check for additional missed updates based on interval
        if config.is_interval_based():
            # For interval-based scheduling, check how many intervals we missed
            time_since_last = current_time - last_update
            interval_days = config.update_days
            missed_intervals = int(time_since_last.days // interval_days)

            if missed_intervals > 1:  # More than one interval missed
                for i in range(1, missed_intervals):
                    missed_time = last_update + timedelta(days=interval_days * i)
                    if missed_time < current_time:
                        missed_updates.append(
                            MissedUpdate(
                                scheduled_time=missed_time,
                                detected_at=current_time,
                                reason="interval_based_missed_update",
                            )
                        )
                        logger.warning(
                            f"Detected missed interval update: {missed_time}"
                        )

        logger.info(f"Detected {len(missed_updates)} missed updates")
        return missed_updates

    def validate_schedule_integrity(
        self, current_time: datetime, state: ScheduleState, config: SchedulingConfig
    ) -> tuple[bool, list[str]]:
        """
        Validate schedule integrity and detect inconsistencies.

        Args:
            current_time: Current datetime
            state: Current schedule state
            config: Current scheduling configuration

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues: list[str] = []

        # Check if next_update is reasonable
        if state.next_update:
            if state.next_update <= current_time:
                issues.append(f"Next update time {state.next_update} is in the past")

            # Check if next_update is too far in the future
            max_future = current_time + timedelta(days=config.update_days * 2)
            if state.next_update > max_future:
                issues.append(
                    f"Next update time {state.next_update} is too far in the future"
                )

        # Check if last_update and next_update are consistent
        if state.last_update and state.next_update:
            expected_interval = timedelta(days=config.update_days)
            actual_interval = state.next_update - state.last_update

            # Allow some tolerance (±1 day)
            if abs((actual_interval - expected_interval).days) > 1:
                issues.append(
                    f"Inconsistent interval: expected {expected_interval.days} days, "
                    + f"got {actual_interval.days} days"
                )

        # Check for excessive consecutive failures
        if state.consecutive_failures > 10:
            issues.append(
                f"Excessive consecutive failures: {state.consecutive_failures}"
            )

        # Check if last_failure is too old compared to consecutive_failures
        if state.consecutive_failures > 0 and state.last_failure:
            time_since_failure = current_time - state.last_failure
            if time_since_failure.days > 7:  # More than a week old
                issues.append(
                    f"Last failure is {time_since_failure.days} days old but "
                    + f"consecutive_failures is {state.consecutive_failures}"
                )

        is_valid = len(issues) == 0
        if not is_valid:
            logger.warning(f"Schedule integrity validation failed: {issues}")
        else:
            logger.debug("Schedule integrity validation passed")

        return is_valid, issues

    def repair_schedule_state(
        self, current_time: datetime, state: ScheduleState, config: SchedulingConfig
    ) -> ScheduleState:
        """
        Attempt to repair inconsistent schedule state.

        Args:
            current_time: Current datetime
            state: Current schedule state (may be modified)
            config: Current scheduling configuration

        Returns:
            Repaired schedule state
        """
        logger.info("Attempting to repair schedule state")

        # Create a new schedule calculator for repairs
        schedule = UpdateSchedule(config, state)

        # Fix next_update if it's in the past or invalid
        if not state.next_update or state.next_update <= current_time:
            new_next_update = schedule.calculate_next_update(current_time)
            logger.info(
                f"Repairing next_update: {state.next_update} -> {new_next_update}"
            )
            state.set_next_update(new_next_update)

        # Reset excessive consecutive failures if last failure is old
        if state.consecutive_failures > 5 and state.last_failure:
            time_since_failure = current_time - state.last_failure
            if time_since_failure.days > 3:  # More than 3 days old
                logger.info(
                    f"Resetting consecutive failures from {state.consecutive_failures} to 0 (last failure was {time_since_failure.days} days ago)"
                )
                state.consecutive_failures = 0

        # Clear running state if we're not actually running
        if state.is_running:
            logger.info("Clearing running state during repair")
            state.stop_scheduler()

        logger.info("Schedule state repair completed")
        return state

    async def perform_recovery(
        self,
        current_time: datetime,
        state: ScheduleState,
        config: SchedulingConfig,
        update_callback: Callable[[], Awaitable[None]] | None = None,
    ) -> tuple[ScheduleState, list[MissedUpdate]]:
        """
        Perform comprehensive recovery operations.

        Args:
            current_time: Current datetime
            state: Current schedule state
            config: Current scheduling configuration
            update_callback: Optional callback to process missed updates

        Returns:
            Tuple of (recovered_state, processed_missed_updates)
        """
        logger.info("Starting comprehensive recovery process")

        # Detect missed updates
        missed_updates = self.detect_missed_updates(
            current_time, state.last_update, state.next_update, config
        )

        # Validate and repair schedule integrity
        is_valid, issues = self.validate_schedule_integrity(current_time, state, config)
        if not is_valid:
            logger.warning(f"Schedule integrity issues detected: {issues}")
            state = self.repair_schedule_state(current_time, state, config)

        # Process missed updates if callback is provided
        processed_updates: list[MissedUpdate] = []
        if update_callback and missed_updates:
            logger.info(f"Processing {len(missed_updates)} missed updates")

            for missed_update in missed_updates:
                try:
                    logger.info(
                        f"Processing missed update from {missed_update.scheduled_time}"
                    )
                    await update_callback()
                    processed_updates.append(missed_update)

                    # Update state to reflect processed update
                    state.record_successful_update(current_time)

                except Exception as e:
                    logger.error(
                        f"Failed to process missed update from {missed_update.scheduled_time}: {e}"
                    )
                    state.record_failure(current_time, e)
                    # Continue with other missed updates

        # Save recovered state
        try:
            self.state_manager.save_state(state, config)
            logger.info("Recovered state saved successfully")
        except Exception as e:
            logger.error(f"Failed to save recovered state: {e}")

        logger.info(
            f"Recovery process completed. Processed {len(processed_updates)} missed updates"
        )
        return state, processed_updates