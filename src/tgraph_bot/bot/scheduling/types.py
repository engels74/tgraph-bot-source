"""
Core types, enums, and data classes for the scheduling system.

This module contains all the fundamental data structures used throughout
the scheduling system, extracted from the original update_tracker.py.
"""

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, time
from enum import Enum
from typing import TYPE_CHECKING

from ...utils.time import get_system_now, ensure_timezone_aware

if TYPE_CHECKING:
    pass


class TaskStatus(Enum):
    """Status of background tasks."""

    IDLE = "idle"
    RUNNING = "running"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ErrorType(Enum):
    """Classification of error types for retry logic."""

    TRANSIENT = "transient"  # Temporary errors that may resolve (network, timeout)
    PERMANENT = "permanent"  # Errors that won't resolve with retry (config, auth)
    RATE_LIMITED = "rate_limited"  # Rate limiting errors
    UNKNOWN = "unknown"  # Unclassified errors


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry policies."""

    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 300.0  # Maximum delay in seconds (5 minutes)
    exponential_base: float = 2.0  # Base for exponential backoff
    jitter: bool = True  # Add random jitter to delays

    # Circuit breaker settings
    failure_threshold: int = 5  # Failures before opening circuit
    recovery_timeout: float = 60.0  # Seconds before trying half-open
    success_threshold: int = 2  # Successes needed to close circuit

    def __post_init__(self) -> None:
        """Validate retry configuration."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if self.exponential_base < 1:
            raise ValueError("exponential_base must be >= 1")
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if self.recovery_timeout < 0:
            raise ValueError("recovery_timeout must be non-negative")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be at least 1")


@dataclass
class ErrorMetrics:
    """Metrics for error tracking and monitoring."""

    total_attempts: int = 0
    total_successes: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0

    # Error type counters
    transient_errors: int = 0
    permanent_errors: int = 0
    rate_limit_errors: int = 0
    unknown_errors: int = 0

    # Timing metrics
    last_success: datetime | None = None
    last_failure: datetime | None = None
    last_attempt: datetime | None = None

    # Circuit breaker state
    circuit_state: CircuitState = CircuitState.CLOSED
    circuit_opened_at: datetime | None = None
    circuit_last_test: datetime | None = None

    def record_attempt(self) -> None:
        """Record an attempt."""
        self.total_attempts += 1
        self.last_attempt = get_system_now()

    def record_success(self) -> None:
        """Record a successful operation."""
        self.total_successes += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_success = get_system_now()

    def record_failure(self, error_type: ErrorType) -> None:
        """Record a failed operation."""
        self.total_failures += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure = get_system_now()

        # Update error type counters
        if error_type == ErrorType.TRANSIENT:
            self.transient_errors += 1
        elif error_type == ErrorType.PERMANENT:
            self.permanent_errors += 1
        elif error_type == ErrorType.RATE_LIMITED:
            self.rate_limit_errors += 1
        else:
            self.unknown_errors += 1

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_attempts == 0:
            return 0.0
        return self.total_successes / self.total_attempts

    def get_failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_attempts == 0:
            return 0.0
        return self.total_failures / self.total_attempts

    def to_dict(self) -> dict[str, str | int | float | dict[str, int] | None]:
        """Convert metrics to dictionary for logging."""
        return {
            "total_attempts": self.total_attempts,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "success_rate": self.get_success_rate(),
            "failure_rate": self.get_failure_rate(),
            "error_breakdown": {
                "transient": self.transient_errors,
                "permanent": self.permanent_errors,
                "rate_limited": self.rate_limit_errors,
                "unknown": self.unknown_errors,
            },
            "circuit_state": self.circuit_state.value,
            "last_success": self.last_success.isoformat()
            if self.last_success
            else None,
            "last_failure": self.last_failure.isoformat()
            if self.last_failure
            else None,
            "last_attempt": self.last_attempt.isoformat()
            if self.last_attempt
            else None,
        }


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

    def to_dict(self) -> dict[str, str | int | bool | None]:
        """Convert state to dictionary for persistence."""
        return {
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "next_update": self.next_update.isoformat() if self.next_update else None,
            "is_running": self.is_running,
            "consecutive_failures": self.consecutive_failures,
            "last_failure": self.last_failure.isoformat()
            if self.last_failure
            else None,
            "last_error": str(self.last_error) if self.last_error else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | int | bool | None]) -> "ScheduleState":
        """Create state from dictionary for persistence."""
        state = cls()

        if data.get("last_update"):
            state.last_update = datetime.fromisoformat(str(data["last_update"]))
            # Ensure timezone-aware datetime using unified system
            state.last_update = ensure_timezone_aware(state.last_update)
        if data.get("next_update"):
            state.next_update = datetime.fromisoformat(str(data["next_update"]))
            # Ensure timezone-aware datetime using unified system
            state.next_update = ensure_timezone_aware(state.next_update)

        state.is_running = bool(data.get("is_running", False))
        consecutive_failures_value = data.get("consecutive_failures", 0)
        state.consecutive_failures = (
            int(consecutive_failures_value)
            if consecutive_failures_value is not None
            else 0
        )

        if data.get("last_failure"):
            state.last_failure = datetime.fromisoformat(str(data["last_failure"]))
            # Ensure timezone-aware datetime using unified system
            state.last_failure = ensure_timezone_aware(state.last_failure)
        if data.get("last_error"):
            state.last_error = Exception(str(data["last_error"]))

        return state


@dataclass
class PersistentScheduleData:
    """Persistent data structure for schedule state and configuration."""

    state: dict[str, str | int | bool | None]
    config: dict[str, str | int] | None = None
    version: str = "1.0"
    saved_at: str = field(default_factory=lambda: get_system_now().isoformat())

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PersistentScheduleData":
        """Create from dictionary for JSON deserialization."""
        return cls(
            state=data.get("state", {}),  # pyright: ignore[reportArgumentType]
            config=data.get("config"),  # pyright: ignore[reportArgumentType]
            version=str(data.get("version", "1.0")),
            saved_at=str(data.get("saved_at", get_system_now().isoformat())),
        )


@dataclass
class MissedUpdate:
    """Represents a missed update that needs to be processed."""

    scheduled_time: datetime
    detected_at: datetime
    reason: str = "system_downtime"

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for logging."""
        return {
            "scheduled_time": self.scheduled_time.isoformat(),
            "detected_at": self.detected_at.isoformat(),
            "reason": self.reason,
        }