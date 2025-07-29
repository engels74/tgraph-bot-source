"""
Background task management system for the scheduling framework.

This module provides robust task lifecycle management, health monitoring,
graceful shutdown, and comprehensive error handling with retry logic.
"""

import asyncio
import logging
from collections.abc import Callable, Awaitable
from datetime import datetime, timedelta

from .types import (
    TaskStatus,
    ErrorType,
    RetryConfig,
    ErrorMetrics,
    CircuitState,
)
from .error_handling import ErrorClassifier, CircuitBreaker
from ...utils.time import get_system_now

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    Enhanced background task manager for handling multiple concurrent tasks.

    Provides task lifecycle management, health monitoring, graceful shutdown,
    and comprehensive error handling with retry logic and circuit breakers.
    """

    def __init__(
        self, restart_delay: float = 30.0, retry_config: RetryConfig | None = None
    ) -> None:
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
        restart_on_failure: bool = True,
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
        self._task_health[name] = get_system_now()

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
        self, name: str, coro: Callable[[], Awaitable[None]], restart_on_failure: bool
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
                    self._log_audit_event(
                        name,
                        "circuit_breaker_blocked",
                        "Circuit breaker is open, blocking task execution",
                    )
                    self._task_status[name] = TaskStatus.FAILED

                    # Wait for circuit breaker recovery timeout
                    await asyncio.sleep(min(self._retry_config.recovery_timeout, 60.0))
                    continue

                self._task_status[name] = TaskStatus.RUNNING
                self._task_health[name] = get_system_now()
                metrics.record_attempt()

                self._log_audit_event(name, "task_started", "Task execution started")

                # Execute the task with timeout protection
                # Special handling for scheduler loop - it needs to run indefinitely
                if name == "update_scheduler":
                    await coro()  # No timeout for scheduler loop
                else:
                    await asyncio.wait_for(
                        coro(), timeout=300.0
                    )  # 5 minute timeout for other tasks

                # Record successful execution
                self._task_status[name] = TaskStatus.IDLE
                circuit_breaker.record_success()
                metrics.record_success()

                self._log_audit_event(
                    name, "task_completed", "Task execution completed successfully"
                )
                logger.info(
                    f"Task {name} completed successfully (success rate: {metrics.get_success_rate():.2%})"
                )
                break

            except asyncio.CancelledError:
                logger.debug(f"Task {name} was cancelled")
                self._task_status[name] = TaskStatus.CANCELLED
                self._log_audit_event(name, "task_cancelled", "Task was cancelled")
                raise

            except asyncio.TimeoutError as e:
                error_type = ErrorClassifier.classify_error(e)
                self._handle_task_error(
                    name, e, error_type, circuit_breaker, metrics, restart_on_failure
                )

                if not restart_on_failure:
                    break

                # Apply exponential backoff for timeout errors
                delay = await self._calculate_retry_delay(metrics.consecutive_failures)
                await self._wait_with_shutdown_check(delay)

            except Exception as e:
                error_type = ErrorClassifier.classify_error(e)
                self._handle_task_error(
                    name, e, error_type, circuit_breaker, metrics, restart_on_failure
                )

                if not restart_on_failure or error_type == ErrorType.PERMANENT:
                    logger.error(
                        f"Task {name} failed with {error_type.value} error, not restarting"
                    )
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
        restart_on_failure: bool,  # pyright: ignore[reportUnusedParameter]
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
            name, "task_failed", f"{error_type.value} error: {str(error)[:200]}"
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
            _ = await asyncio.wait_for(self._shutdown_event.wait(), timeout=delay)
            # If we reach here, shutdown was requested
        except asyncio.TimeoutError:
            # Timeout is expected, continue
            pass

    def _log_audit_event(self, task_name: str, event_type: str, message: str) -> None:
        """Log audit events for task operations."""
        audit_entry: dict[str, str | datetime | None] = {
            "timestamp": get_system_now().isoformat(),
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

    def get_all_task_metrics(
        self,
    ) -> dict[str, dict[str, str | int | float | dict[str, int] | None]]:
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
        running_tasks = sum(
            1 for status in self._task_status.values() if status == TaskStatus.RUNNING
        )
        failed_tasks = sum(
            1 for status in self._task_status.values() if status == TaskStatus.FAILED
        )

        # Calculate overall success rate
        total_attempts = sum(
            metrics.total_attempts for metrics in self._task_metrics.values()
        )
        total_successes = sum(
            metrics.total_successes for metrics in self._task_metrics.values()
        )
        overall_success_rate = (
            total_successes / total_attempts if total_attempts > 0 else 0.0
        )

        # Count circuit breaker states
        open_circuits = sum(
            1
            for breaker in self._circuit_breakers.values()
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
                        self._shutdown_event.wait(), timeout=self._health_check_interval
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
        current_time = get_system_now()
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
        current_time = get_system_now()
        stale_threshold = timedelta(minutes=5)

        for _, last_health in self._task_health.items():
            if current_time - last_health > stale_threshold:
                return False

        return True
