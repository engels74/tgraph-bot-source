"""
Centralized timestamp calculation for TGraph Bot.

This module provides a single source of truth for timestamp calculations,
ensuring consistency between the scheduler and Discord embed displays.
Following DRY and KISS principles to eliminate duplicate calculation logic.
"""

from datetime import datetime, timedelta

from .timezone import get_system_now, to_system_timezone
from .scheduling import parse_fixed_time, calculate_next_fixed_time, calculate_next_interval_time


class TimestampCalculator:
    """
    Centralized calculator for next update timestamps.
    
    This class ensures that both the scheduler and Discord embeds use exactly
    the same calculation logic, preventing discrepancies in displayed times.
    """

    def __init__(self) -> None:
        """Initialize the timestamp calculator."""
        pass

    def calculate_next_update(
        self,
        update_days: int,
        fixed_update_time: str,
        last_update: datetime | None = None,
        current_time: datetime | None = None,
    ) -> datetime:
        """
        Calculate the next update time based on configuration and state.

        This is the single source of truth for timestamp calculations used by
        both the scheduler system and Discord embed generation.

        Args:
            update_days: Number of days between updates (1-365)
            fixed_update_time: Fixed time string (HH:MM) or 'XX:XX' to disable
            last_update: Last successful update time (optional)
            current_time: Current datetime for calculation reference (defaults to system now)

        Returns:
            Next update datetime in system timezone

        Raises:
            ValueError: If fixed_update_time format is invalid

        Examples:
            >>> calculator = TimestampCalculator()
            >>> next_time = calculator.calculate_next_update(1, "23:59")
            >>> isinstance(next_time, datetime)
            True
            >>> next_time.tzinfo is not None
            True
        """
        if current_time is None:
            current_time = get_system_now()
        
        # Ensure current_time is in system timezone
        current_time = to_system_timezone(current_time)
        
        # Parse fixed time
        fixed_time = parse_fixed_time(fixed_update_time)
        
        if fixed_time is not None:
            # Fixed time scheduling
            return calculate_next_fixed_time(
                current_time, fixed_time, update_days, last_update
            )
        else:
            # Interval-based scheduling
            return calculate_next_interval_time(
                current_time, update_days, last_update
            )

    def calculate_time_until_next_update(
        self,
        update_days: int,
        fixed_update_time: str,
        last_update: datetime | None = None,
        current_time: datetime | None = None,
    ) -> timedelta:
        """
        Calculate the time remaining until the next update.

        Args:
            update_days: Number of days between updates
            fixed_update_time: Fixed time string (HH:MM) or 'XX:XX' to disable
            last_update: Last successful update time (optional)
            current_time: Current datetime for calculation reference (defaults to system now)

        Returns:
            Time remaining until next update
        """
        if current_time is None:
            current_time = get_system_now()
        
        next_update = self.calculate_next_update(
            update_days, fixed_update_time, last_update, current_time
        )
        return next_update - current_time

    def is_update_due(
        self,
        update_days: int,
        fixed_update_time: str,
        last_update: datetime | None = None,
        current_time: datetime | None = None,
    ) -> bool:
        """
        Check if an update is currently due.

        Args:
            update_days: Number of days between updates
            fixed_update_time: Fixed time string (HH:MM) or 'XX:XX' to disable
            last_update: Last successful update time (optional)
            current_time: Current datetime for calculation reference (defaults to system now)

        Returns:
            True if an update is due now, False otherwise
        """
        if current_time is None:
            current_time = get_system_now()
        
        next_update = self.calculate_next_update(
            update_days, fixed_update_time, last_update, current_time
        )
        return current_time >= next_update

    def validate_schedule_integrity(
        self,
        update_days: int,
        fixed_update_time: str,
        last_update: datetime | None = None,
        next_update: datetime | None = None,
        current_time: datetime | None = None,
    ) -> tuple[bool, list[str]]:
        """
        Validate schedule integrity and detect inconsistencies.

        Args:
            update_days: Number of days between updates
            fixed_update_time: Fixed time string (HH:MM) or 'XX:XX' to disable
            last_update: Last successful update time (optional)
            next_update: Stored next update time to validate (optional)
            current_time: Current datetime for validation reference (defaults to system now)

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        if current_time is None:
            current_time = get_system_now()
        
        issues: list[str] = []
        
        # Calculate what the next update should be
        calculated_next_update = self.calculate_next_update(
            update_days, fixed_update_time, last_update, current_time
        )
        
        # Check if stored next_update matches calculated value
        if next_update is not None:
            # Allow small tolerance for minor timing differences (1 second)
            time_diff = abs((next_update - calculated_next_update).total_seconds())
            if time_diff > 1.0:
                issues.append(
                    f"Stored next_update ({next_update}) doesn't match calculated "
                    + f"value ({calculated_next_update}). Difference: {time_diff:.1f}s"
                )
        
        # Check if next_update is reasonable
        if next_update and next_update <= current_time:
            issues.append(f"Next update time {next_update} is in the past")
        
        # Check if next_update is too far in the future
        if next_update:
            max_future = current_time + timedelta(days=update_days * 2)
            if next_update > max_future:
                issues.append(
                    f"Next update time {next_update} is too far in the future "
                    + f"(more than {update_days * 2} days)"
                )
        
        # Check if last_update and calculated next_update are consistent
        if last_update and calculated_next_update:
            expected_interval = timedelta(days=update_days)
            actual_interval = calculated_next_update - last_update
            
            # Allow some tolerance for fixed time scheduling (±1 day)
            tolerance = timedelta(days=1)
            if abs(actual_interval - expected_interval) > tolerance:
                issues.append(
                    f"Inconsistent interval: expected ~{expected_interval.days} days, "
                    + f"got {actual_interval.days} days"
                )
        
        is_valid = len(issues) == 0
        return is_valid, issues