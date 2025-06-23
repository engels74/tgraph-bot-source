"""
Update tracking and scheduling for TGraph Bot.

This module manages the scheduling and tracking of when server-wide graphs
should be automatically updated, based on configuration (UPDATE_DAYS, FIXED_UPDATE_TIME).
"""

import asyncio
import json
import logging
import re
import tempfile

from datetime import datetime, time, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from collections.abc import Callable, Awaitable
from dataclasses import dataclass, field, asdict
from enum import Enum

if TYPE_CHECKING:
    from discord.ext import commands

logger = logging.getLogger(__name__)


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
        self.last_attempt = datetime.now()

    def record_success(self) -> None:
        """Record a successful operation."""
        self.total_successes += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_success = datetime.now()

    def record_failure(self, error_type: ErrorType) -> None:
        """Record a failed operation."""
        self.total_failures += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure = datetime.now()

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
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
        }


class ErrorClassifier:
    """Classifies errors for appropriate retry handling."""

    @staticmethod
    def classify_error(error: Exception) -> ErrorType:
        """
        Classify an error to determine retry strategy.

        Args:
            error: The exception to classify

        Returns:
            ErrorType indicating how to handle the error
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Network and timeout errors are usually transient
        if any(keyword in error_str for keyword in [
            "timeout", "connection", "network", "dns", "socket",
            "temporary", "unavailable", "service", "gateway"
        ]):
            return ErrorType.TRANSIENT

        if any(keyword in error_type for keyword in [
            "timeout", "connection", "network", "http"
        ]):
            return ErrorType.TRANSIENT

        # Rate limiting errors
        if any(keyword in error_str for keyword in [
            "rate limit", "too many requests", "quota", "throttle"
        ]):
            return ErrorType.RATE_LIMITED

        # Authentication and configuration errors are permanent
        if any(keyword in error_str for keyword in [
            "unauthorized", "forbidden", "authentication", "permission",
            "invalid api", "bad request", "not found", "configuration"
        ]):
            return ErrorType.PERMANENT

        # Default to unknown for unclassified errors
        return ErrorType.UNKNOWN


class CircuitBreaker:
    """Circuit breaker implementation for preventing cascading failures."""

    def __init__(self, config: RetryConfig) -> None:
        """Initialize circuit breaker with configuration."""
        self.config: RetryConfig = config
        self.metrics: ErrorMetrics = ErrorMetrics()

    def should_allow_request(self) -> bool:
        """Check if a request should be allowed through the circuit."""
        current_time = datetime.now()

        if self.metrics.circuit_state == CircuitState.CLOSED:
            return True
        elif self.metrics.circuit_state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if (self.metrics.circuit_opened_at and
                current_time - self.metrics.circuit_opened_at >=
                timedelta(seconds=self.config.recovery_timeout)):
                self._transition_to_half_open()
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self) -> None:
        """Record a successful operation."""
        self.metrics.record_success()

        if self.metrics.circuit_state == CircuitState.HALF_OPEN:
            if self.metrics.consecutive_successes >= self.config.success_threshold:
                self._transition_to_closed()

    def record_failure(self, error: Exception) -> None:
        """Record a failed operation."""
        error_type = ErrorClassifier.classify_error(error)
        self.metrics.record_failure(error_type)

        if self.metrics.circuit_state == CircuitState.CLOSED:
            if self.metrics.consecutive_failures >= self.config.failure_threshold:
                self._transition_to_open()
        elif self.metrics.circuit_state == CircuitState.HALF_OPEN:
            self._transition_to_open()

    def _transition_to_open(self) -> None:
        """Transition circuit to open state."""
        self.metrics.circuit_state = CircuitState.OPEN
        self.metrics.circuit_opened_at = datetime.now()
        logger.warning(f"Circuit breaker opened after {self.metrics.consecutive_failures} failures")

    def _transition_to_half_open(self) -> None:
        """Transition circuit to half-open state."""
        self.metrics.circuit_state = CircuitState.HALF_OPEN
        self.metrics.circuit_last_test = datetime.now()
        logger.info("Circuit breaker transitioning to half-open for testing")

    def _transition_to_closed(self) -> None:
        """Transition circuit to closed state."""
        self.metrics.circuit_state = CircuitState.CLOSED
        self.metrics.circuit_opened_at = None
        logger.info(f"Circuit breaker closed after {self.metrics.consecutive_successes} successes")

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.metrics.circuit_state

    def get_metrics(self) -> ErrorMetrics:
        """Get current metrics."""
        return self.metrics


class BackgroundTaskManager:
    """
    Enhanced background task manager for handling multiple concurrent tasks.

    Provides task lifecycle management, health monitoring, graceful shutdown,
    and comprehensive error handling with retry logic and circuit breakers.
    """

    def __init__(self, restart_delay: float = 30.0, retry_config: RetryConfig | None = None) -> None:
        """Initialize the background task manager."""
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._task_status: dict[str, TaskStatus] = {}
        self._task_health: dict[str, datetime] = {}
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._health_check_task: asyncio.Task[None] | None = None
        self._health_check_interval: float = 60.0  # 1 minute
        self._restart_delay: float = restart_delay

        # Enhanced error handling and retry components
        self._retry_config: RetryConfig = retry_config or RetryConfig()
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._task_metrics: dict[str, ErrorMetrics] = {}
        self._audit_log: list[dict[str, str | datetime | None]] = []

    async def start(self) -> None:
        """Start the background task manager."""
        logger.info("Starting background task manager")
        self._shutdown_event.clear()

        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop(self) -> None:
        """Stop the background task manager and all managed tasks."""
        logger.info("Stopping background task manager")
        self._shutdown_event.set()

        # Cancel health check task
        if self._health_check_task:
            _ = self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        # Cancel all managed tasks
        for task_name, task in self._tasks.items():
            logger.debug(f"Cancelling task: {task_name}")
            _ = task.cancel()

        # Wait for all tasks to complete
        if self._tasks:
            _ = await asyncio.gather(*self._tasks.values(), return_exceptions=True)

        self._tasks.clear()
        self._task_status.clear()
        self._task_health.clear()

    def add_task(
        self,
        name: str,
        coro: Callable[[], Awaitable[None]],
        restart_on_failure: bool = True
    ) -> None:
        """
        Add a new background task.

        Args:
            name: Unique name for the task
            coro: Coroutine function to run as background task
            restart_on_failure: Whether to restart the task if it fails
        """
        if name in self._tasks:
            logger.warning(f"Task {name} already exists, replacing it")
            self.remove_task(name)

        logger.info(f"Adding background task: {name}")
        task = asyncio.create_task(self._task_wrapper(name, coro, restart_on_failure))
        self._tasks[name] = task
        self._task_status[name] = TaskStatus.RUNNING
        self._task_health[name] = datetime.now()

    def remove_task(self, name: str) -> None:
        """
        Remove and cancel a background task.

        Args:
            name: Name of the task to remove
        """
        if name not in self._tasks:
            logger.warning(f"Task {name} not found")
            return

        logger.info(f"Removing background task: {name}")
        task = self._tasks[name]
        _ = task.cancel()

        del self._tasks[name]
        _ = self._task_status.pop(name, None)
        _ = self._task_health.pop(name, None)

    async def _task_wrapper(
        self,
        name: str,
        coro: Callable[[], Awaitable[None]],
        restart_on_failure: bool
    ) -> None:
        """
        Enhanced wrapper for background tasks with comprehensive error handling,
        retry logic, circuit breaker protection, and audit logging.

        Args:
            name: Task name
            coro: Coroutine function to run
            restart_on_failure: Whether to restart on failure
        """
        # Initialize circuit breaker and metrics for this task
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = CircuitBreaker(self._retry_config)
            self._task_metrics[name] = ErrorMetrics()

        circuit_breaker = self._circuit_breakers[name]
        metrics = self._task_metrics[name]

        while not self._shutdown_event.is_set():
            try:
                # Check circuit breaker before attempting operation
                if not circuit_breaker.should_allow_request():
                    self._log_audit_event(name, "circuit_breaker_blocked",
                                         f"Circuit breaker is open, blocking task execution")
                    self._task_status[name] = TaskStatus.FAILED

                    # Wait for circuit breaker recovery timeout
                    await asyncio.sleep(min(self._retry_config.recovery_timeout, 60.0))
                    continue

                self._task_status[name] = TaskStatus.RUNNING
                self._task_health[name] = datetime.now()
                metrics.record_attempt()

                self._log_audit_event(name, "task_started", "Task execution started")

                # Execute the task with timeout protection
                # Special handling for scheduler loop - it needs to run indefinitely
                if name == "update_scheduler":
                    await coro()  # No timeout for scheduler loop
                else:
                    await asyncio.wait_for(coro(), timeout=300.0)  # 5 minute timeout for other tasks

                # Record successful execution
                self._task_status[name] = TaskStatus.IDLE
                circuit_breaker.record_success()
                metrics.record_success()

                self._log_audit_event(name, "task_completed", "Task execution completed successfully")
                logger.info(f"Task {name} completed successfully (success rate: {metrics.get_success_rate():.2%})")
                break

            except asyncio.CancelledError:
                logger.debug(f"Task {name} was cancelled")
                self._task_status[name] = TaskStatus.CANCELLED
                self._log_audit_event(name, "task_cancelled", "Task was cancelled")
                raise

            except asyncio.TimeoutError as e:
                error_type = ErrorClassifier.classify_error(e)
                self._handle_task_error(name, e, error_type, circuit_breaker, metrics, restart_on_failure)

                if not restart_on_failure:
                    break

                # Apply exponential backoff for timeout errors
                delay = await self._calculate_retry_delay(metrics.consecutive_failures)
                await self._wait_with_shutdown_check(delay)

            except Exception as e:
                error_type = ErrorClassifier.classify_error(e)
                self._handle_task_error(name, e, error_type, circuit_breaker, metrics, restart_on_failure)

                if not restart_on_failure or error_type == ErrorType.PERMANENT:
                    logger.error(f"Task {name} failed with {error_type.value} error, not restarting")
                    break

                # Apply retry logic based on error type and configuration
                delay = await self._calculate_retry_delay(metrics.consecutive_failures)
                await self._wait_with_shutdown_check(delay)

    def _handle_task_error(
        self,
        name: str,
        error: Exception,
        error_type: ErrorType,
        circuit_breaker: CircuitBreaker,
        metrics: ErrorMetrics,
        restart_on_failure: bool  # pyright: ignore[reportUnusedParameter]
    ) -> None:
        """Handle task errors with comprehensive logging and metrics."""
        self._task_status[name] = TaskStatus.FAILED
        circuit_breaker.record_failure(error)
        metrics.record_failure(error_type)

        # Log error with context
        error_msg = (
            f"Task {name} failed with {error_type.value} error "
            f"(attempt {metrics.total_attempts}, "
            f"consecutive failures: {metrics.consecutive_failures}): {error}"
        )
        logger.exception(error_msg)

        # Log audit event
        self._log_audit_event(
            name,
            "task_failed",
            f"{error_type.value} error: {str(error)[:200]}"
        )

        # Log circuit breaker state changes
        if circuit_breaker.get_state() == CircuitState.OPEN:
            logger.warning(f"Circuit breaker opened for task {name}")

    async def _calculate_retry_delay(self, consecutive_failures: int) -> float:
        """Calculate retry delay with exponential backoff and jitter."""
        if consecutive_failures == 0:
            return 0.0

        # Exponential backoff: base_delay * (exponential_base ^ failures)
        delay = self._retry_config.base_delay * (
            self._retry_config.exponential_base ** (consecutive_failures - 1)
        )

        # Cap at maximum delay
        delay = min(delay, self._retry_config.max_delay)

        # Add jitter if enabled (±25% random variation)
        if self._retry_config.jitter:
            import random
            jitter_factor = 0.75 + (random.random() * 0.5)  # 0.75 to 1.25
            delay *= jitter_factor

        return delay

    async def _wait_with_shutdown_check(self, delay: float) -> None:
        """Wait for specified delay while checking for shutdown."""
        if delay <= 0:
            return

        try:
            _ = await asyncio.wait_for(
                self._shutdown_event.wait(),
                timeout=delay
            )
            # If we reach here, shutdown was requested
        except asyncio.TimeoutError:
            # Timeout is expected, continue
            pass

    def _log_audit_event(self, task_name: str, event_type: str, message: str) -> None:
        """Log audit events for task operations."""
        audit_entry: dict[str, str | datetime | None] = {
            "timestamp": datetime.now().isoformat(),
            "task_name": task_name,
            "event_type": event_type,
            "message": message,
        }

        # Add to audit log (keep last 1000 entries)
        self._audit_log.append(audit_entry)
        if len(self._audit_log) > 1000:
            _ = self._audit_log.pop(0)

        # Log to standard logger as well
        logger.info(f"[AUDIT] {task_name}: {event_type} - {message}")

    def get_task_metrics(self, name: str) -> ErrorMetrics | None:
        """Get metrics for a specific task."""
        return self._task_metrics.get(name)

    def get_all_task_metrics(self) -> dict[str, dict[str, str | int | float | dict[str, int] | None]]:
        """Get metrics for all tasks."""
        return {name: metrics.to_dict() for name, metrics in self._task_metrics.items()}

    def get_circuit_breaker_status(self, name: str) -> CircuitState | None:
        """Get circuit breaker status for a specific task."""
        circuit_breaker = self._circuit_breakers.get(name)
        return circuit_breaker.get_state() if circuit_breaker else None

    def get_all_circuit_breaker_status(self) -> dict[str, str]:
        """Get circuit breaker status for all tasks."""
        return {
            name: breaker.get_state().value
            for name, breaker in self._circuit_breakers.items()
        }

    def get_audit_log(self, limit: int = 100) -> list[dict[str, str | datetime | None]]:
        """Get recent audit log entries."""
        return self._audit_log[-limit:] if self._audit_log else []

    def get_health_summary(self) -> dict[str, str | int | float | bool]:
        """Get comprehensive health summary of all tasks."""
        total_tasks = len(self._tasks)
        running_tasks = sum(1 for status in self._task_status.values() if status == TaskStatus.RUNNING)
        failed_tasks = sum(1 for status in self._task_status.values() if status == TaskStatus.FAILED)

        # Calculate overall success rate
        total_attempts = sum(metrics.total_attempts for metrics in self._task_metrics.values())
        total_successes = sum(metrics.total_successes for metrics in self._task_metrics.values())
        overall_success_rate = total_successes / total_attempts if total_attempts > 0 else 0.0

        # Count circuit breaker states
        open_circuits = sum(
            1 for breaker in self._circuit_breakers.values()
            if breaker.get_state() == CircuitState.OPEN
        )

        return {
            "total_tasks": total_tasks,
            "running_tasks": running_tasks,
            "failed_tasks": failed_tasks,
            "healthy_tasks": total_tasks - failed_tasks,
            "overall_success_rate": overall_success_rate,
            "total_attempts": total_attempts,
            "total_successes": total_successes,
            "open_circuits": open_circuits,
            "is_healthy": self.is_healthy() and open_circuits == 0,
            "audit_log_entries": len(self._audit_log),
        }

    async def _health_check_loop(self) -> None:
        """Periodic health check for all managed tasks."""
        try:
            while not self._shutdown_event.is_set():
                await self._perform_health_check()

                try:
                    _ = await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self._health_check_interval
                    )
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    continue  # Continue health checks

        except asyncio.CancelledError:
            logger.debug("Health check loop cancelled")
            raise
        except Exception as e:
            logger.exception(f"Error in health check loop: {e}")

    async def _perform_health_check(self) -> None:
        """Perform health check on all tasks."""
        current_time = datetime.now()
        stale_threshold = timedelta(minutes=5)  # 5 minutes

        for task_name, last_health in self._task_health.items():
            if current_time - last_health > stale_threshold:
                status = self._task_status.get(task_name, TaskStatus.FAILED)
                logger.warning(
                    f"Task {task_name} appears stale (last health: {last_health}, "
                    + f"status: {status.value})"
                )

    def get_task_status(self, name: str) -> TaskStatus | None:
        """Get the status of a specific task."""
        return self._task_status.get(name)

    def get_all_task_status(self) -> dict[str, dict[str, str | datetime | bool | None]]:
        """Get status of all managed tasks."""
        result: dict[str, dict[str, str | datetime | bool | None]] = {}
        for name in self._tasks:
            status = self._task_status.get(name, TaskStatus.FAILED)
            health = self._task_health.get(name)
            result[name] = {
                "status": status.value,
                "last_health": health,
                "is_done": self._tasks[name].done(),
                "is_cancelled": self._tasks[name].cancelled(),
            }
        return result

    def is_healthy(self) -> bool:
        """Check if all tasks are healthy."""
        current_time = datetime.now()
        stale_threshold = timedelta(minutes=5)

        for _, last_health in self._task_health.items():
            if current_time - last_health > stale_threshold:
                return False

        return True


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
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "last_error": str(self.last_error) if self.last_error else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | int | bool | None]) -> "ScheduleState":
        """Create state from dictionary for persistence."""
        state = cls()

        if data.get("last_update"):
            state.last_update = datetime.fromisoformat(str(data["last_update"]))
        if data.get("next_update"):
            state.next_update = datetime.fromisoformat(str(data["next_update"]))

        state.is_running = bool(data.get("is_running", False))
        consecutive_failures_value = data.get("consecutive_failures", 0)
        state.consecutive_failures = int(consecutive_failures_value) if consecutive_failures_value is not None else 0

        if data.get("last_failure"):
            state.last_failure = datetime.fromisoformat(str(data["last_failure"]))
        if data.get("last_error"):
            state.last_error = Exception(str(data["last_error"]))

        return state


@dataclass
class PersistentScheduleData:
    """Persistent data structure for schedule state and configuration."""

    state: dict[str, str | int | bool | None]
    config: dict[str, str | int] | None = None
    version: str = "1.0"
    saved_at: str = field(default_factory=lambda: datetime.now().isoformat())

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
            saved_at=str(data.get("saved_at", datetime.now().isoformat()))
        )


class StateManager:
    """Manages persistent state storage and recovery for the scheduler."""

    def __init__(self, state_file_path: Path | None = None) -> None:
        """
        Initialize state manager.

        Args:
            state_file_path: Path to state file, defaults to data/scheduler_state.json
        """
        if state_file_path is None:
            # Default to data directory in current working directory
            data_dir = Path.cwd() / "data"
            data_dir.mkdir(exist_ok=True)
            self.state_file_path: Path = data_dir / "scheduler_state.json"
        else:
            self.state_file_path = state_file_path

        # Ensure parent directory exists
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(f"StateManager initialized with state file: {self.state_file_path}")

    def save_state(self, state: ScheduleState, config: SchedulingConfig | None = None) -> None:
        """
        Save scheduler state to persistent storage with atomic operation.

        Args:
            state: Current scheduler state
            config: Current scheduling configuration
        """
        try:
            # Prepare data for persistence
            config_dict = None
            if config:
                config_dict = {
                    "update_days": config.update_days,
                    "fixed_update_time": config.fixed_update_time
                }

            persistent_data = PersistentScheduleData(
                state=state.to_dict(),
                config=config_dict
            )

            # Atomic save using temporary file
            temp_file = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    encoding='utf-8',
                    dir=self.state_file_path.parent,
                    prefix=f'.{self.state_file_path.name}.',
                    suffix='.tmp',
                    delete=False,
                ) as temp_file:
                    json.dump(persistent_data.to_dict(), temp_file, indent=2, ensure_ascii=False)
                    temp_file.flush()
                    temp_path = Path(temp_file.name)

                # Atomic move
                _ = temp_path.replace(self.state_file_path)
                logger.debug(f"State saved successfully to {self.state_file_path}")

            except Exception as e:
                # Clean up temporary file if it exists
                if temp_file and Path(temp_file.name).exists():
                    Path(temp_file.name).unlink(missing_ok=True)
                raise OSError(f"Failed to save state to {self.state_file_path}: {e}") from e

        except Exception as e:
            logger.error(f"Failed to save scheduler state: {e}")
            raise

    def load_state(self) -> tuple[ScheduleState, SchedulingConfig | None]:
        """
        Load scheduler state from persistent storage.

        Returns:
            Tuple of (state, config) or (default_state, None) if no valid state found
        """
        try:
            if not self.state_file_path.exists():
                logger.debug("No state file found, returning default state")
                return ScheduleState(), None

            with self.state_file_path.open('r', encoding='utf-8') as f:
                data: dict[str, object] = json.load(f)  # pyright: ignore[reportAny]

            persistent_data = PersistentScheduleData.from_dict(data)

            # Validate version compatibility
            if persistent_data.version != "1.0":
                logger.warning(f"State file version {persistent_data.version} may not be compatible")

            # Restore state
            state = ScheduleState.from_dict(persistent_data.state)

            # Restore configuration if available
            config = None
            if persistent_data.config:
                config = SchedulingConfig(
                    update_days=int(persistent_data.config["update_days"]),
                    fixed_update_time=str(persistent_data.config["fixed_update_time"])
                )

            logger.info(f"State loaded successfully from {self.state_file_path}")
            logger.debug(f"Loaded state: last_update={state.last_update}, next_update={state.next_update}")

            return state, config

        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to load state file (corrupted): {e}")
            logger.info("Creating backup of corrupted state file and returning default state")
            self._backup_corrupted_state()
            return ScheduleState(), None

        except Exception as e:
            logger.error(f"Unexpected error loading state: {e}")
            return ScheduleState(), None

    def _backup_corrupted_state(self) -> None:
        """Create a backup of corrupted state file for debugging."""
        try:
            if self.state_file_path.exists():
                backup_path = self.state_file_path.with_suffix(f".corrupted.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                _ = self.state_file_path.rename(backup_path)
                logger.info(f"Corrupted state file backed up to: {backup_path}")
        except Exception as e:
            logger.error(f"Failed to backup corrupted state file: {e}")

    def delete_state(self) -> None:
        """Delete the persistent state file."""
        try:
            if self.state_file_path.exists():
                self.state_file_path.unlink()
                logger.info(f"State file deleted: {self.state_file_path}")
        except Exception as e:
            logger.error(f"Failed to delete state file: {e}")

    def state_exists(self) -> bool:
        """Check if a state file exists."""
        return self.state_file_path.exists()


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
            "reason": self.reason
        }


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
        config: SchedulingConfig
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
            missed_updates.append(MissedUpdate(
                scheduled_time=next_update,
                detected_at=current_time,
                reason="missed_scheduled_update"
            ))
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
                        missed_updates.append(MissedUpdate(
                            scheduled_time=missed_time,
                            detected_at=current_time,
                            reason="interval_based_missed_update"
                        ))
                        logger.warning(f"Detected missed interval update: {missed_time}")

        logger.info(f"Detected {len(missed_updates)} missed updates")
        return missed_updates

    def validate_schedule_integrity(
        self,
        current_time: datetime,
        state: ScheduleState,
        config: SchedulingConfig
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
                issues.append(f"Next update time {state.next_update} is too far in the future")

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
            issues.append(f"Excessive consecutive failures: {state.consecutive_failures}")

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
        self,
        current_time: datetime,
        state: ScheduleState,
        config: SchedulingConfig
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
            logger.info(f"Repairing next_update: {state.next_update} -> {new_next_update}")
            state.set_next_update(new_next_update)

        # Reset excessive consecutive failures if last failure is old
        if state.consecutive_failures > 5 and state.last_failure:
            time_since_failure = current_time - state.last_failure
            if time_since_failure.days > 3:  # More than 3 days old
                logger.info(f"Resetting consecutive failures from {state.consecutive_failures} to 0 (last failure was {time_since_failure.days} days ago)")
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
        update_callback: Callable[[], Awaitable[None]] | None = None
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
                    logger.info(f"Processing missed update from {missed_update.scheduled_time}")
                    await update_callback()
                    processed_updates.append(missed_update)

                    # Update state to reflect processed update
                    state.record_successful_update(current_time)

                except Exception as e:
                    logger.error(f"Failed to process missed update from {missed_update.scheduled_time}: {e}")
                    state.record_failure(current_time, e)
                    # Continue with other missed updates

        # Save recovered state
        try:
            self.state_manager.save_state(state, config)
            logger.info("Recovered state saved successfully")
        except Exception as e:
            logger.error(f"Failed to save recovered state: {e}")

        logger.info(f"Recovery process completed. Processed {len(processed_updates)} missed updates")
        return state, processed_updates


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
    """
    Enhanced update tracker with background task management.

    Manages scheduling and tracking of automatic graph updates using
    the BackgroundTaskManager for robust task lifecycle management.
    """

    def __init__(self, bot: "commands.Bot", retry_config: RetryConfig | None = None, state_file_path: Path | None = None) -> None:
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
            restart_delay=30.0,
            retry_config=self._retry_config
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
        self,
        update_days: int = 7,
        fixed_update_time: str | None = None
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
            update_days=update_days,
            fixed_update_time=fixed_time_str
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
            "update_scheduler",
            self._scheduler_loop,
            restart_on_failure=True
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
                    if (loaded_config.update_days != new_config.update_days or
                        loaded_config.fixed_update_time != new_config.fixed_update_time):
                        config_changed = True
                        logger.info("Configuration changed since last run")

                # Use new configuration (may have changed)
                self._config = new_config

                # Perform recovery operations
                current_time = datetime.now()
                recovered_state, missed_updates = await self._recovery_manager.perform_recovery(
                    current_time=current_time,
                    state=self._state,
                    config=self._config,
                    update_callback=self.update_callback if config_changed else None
                )

                self._state = recovered_state

                if missed_updates:
                    logger.info(f"Recovery completed: processed {len(missed_updates)} missed updates")
                    for missed in missed_updates:
                        logger.info(f"  - Processed missed update from {missed.scheduled_time} ({missed.reason})")

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
        start_time = datetime.now()

        logger.info(f"Triggering scheduled graph update (attempt {self._update_metrics.total_attempts})")
        self._log_update_audit("update_started", f"Starting update attempt {self._update_metrics.total_attempts}")

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

                    logger.info(f"Retrying update after {delay:.1f}s delay (attempt {attempt + 1}/{self._retry_config.max_attempts})")
                    self._log_update_audit("update_retry", f"Retrying after {delay:.1f}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)

                # Execute the update callback
                if self.update_callback:
                    # Add timeout protection
                    await asyncio.wait_for(self.update_callback(), timeout=600.0)  # 10 minute timeout
                else:
                    error_msg = "No update callback set"
                    logger.error(error_msg)
                    self._log_update_audit("update_error", error_msg)
                    raise RuntimeError(error_msg)

                # Record successful update
                update_time = datetime.now()
                duration = (update_time - start_time).total_seconds()

                self._state.record_successful_update(update_time)
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
        failure_time = datetime.now()
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
                self._log_update_audit("circuit_breaker_opened", "Circuit breaker opened due to repeated failures")

            raise last_exception
        else:
            # This shouldn't happen, but handle it gracefully
            error_msg = f"Update failed after {self._retry_config.max_attempts} attempts with no recorded exception"
            logger.error(error_msg)
            self._log_update_audit("update_failed", error_msg)
            raise RuntimeError(error_msg)

    def _log_update_audit(self, event_type: str, message: str) -> None:
        """Log audit events for update operations."""
        timestamp = datetime.now().isoformat()
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
            "config_fixed_time": self._config.fixed_update_time if self._config else None,
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
        fixed_time = None if self._config.fixed_update_time == "XX:XX" else self._config.fixed_update_time
        await self.start_scheduler(
            update_days=self._config.update_days,
            fixed_update_time=fixed_time
        )

    def get_update_metrics(self) -> dict[str, str | int | float | dict[str, int] | None]:
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
        comprehensive_status.update({
            "update_metrics": self.get_update_metrics(),
            "circuit_breaker": self.get_circuit_breaker_status(),
            "task_manager_metrics": self._task_manager.get_all_task_metrics(),
            "task_manager_health": self._task_manager.get_health_summary(),
            "circuit_breaker_states": self._task_manager.get_all_circuit_breaker_status(),
        })

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
        current_time = datetime.now()

        # Perform recovery
        recovered_state, missed_updates = await self._recovery_manager.perform_recovery(
            current_time=current_time,
            state=self._state,
            config=self._config,
            update_callback=self.update_callback
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
            current_time = datetime.now()
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

        current_time = datetime.now()

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
                    repairs.append({
                        "field": key,
                        "old_value": original_value,
                        "new_value": new_value,
                    })

            result["repairs_performed"] = repairs
            logger.info(f"Schedule repairs completed: {len(repairs)} fields modified")

        return result
