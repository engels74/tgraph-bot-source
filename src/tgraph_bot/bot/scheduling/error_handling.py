"""
Error handling and circuit breaker components for the scheduling system.

This module contains error classification logic and circuit breaker implementation
to handle failures gracefully in the background task system.
"""

import logging
from datetime import timedelta

from .types import (
    ErrorType,
    CircuitState,
    RetryConfig,
    ErrorMetrics,
)
from ...utils.time import get_system_now

logger = logging.getLogger(__name__)


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
        if any(
            keyword in error_str
            for keyword in [
                "timeout",
                "connection",
                "network",
                "dns",
                "socket",
                "temporary",
                "unavailable",
                "service",
                "gateway",
            ]
        ):
            return ErrorType.TRANSIENT

        if any(
            keyword in error_type
            for keyword in ["timeout", "connection", "network", "http"]
        ):
            return ErrorType.TRANSIENT

        # Rate limiting errors
        if any(
            keyword in error_str
            for keyword in ["rate limit", "too many requests", "quota", "throttle"]
        ):
            return ErrorType.RATE_LIMITED

        # Authentication and configuration errors are permanent
        if any(
            keyword in error_str
            for keyword in [
                "unauthorized",
                "forbidden",
                "authentication",
                "permission",
                "invalid api",
                "bad request",
                "not found",
                "configuration",
            ]
        ):
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
        current_time = get_system_now()

        if self.metrics.circuit_state == CircuitState.CLOSED:
            return True
        elif self.metrics.circuit_state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if (
                self.metrics.circuit_opened_at
                and current_time - self.metrics.circuit_opened_at
                >= timedelta(seconds=self.config.recovery_timeout)
            ):
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
        self.metrics.circuit_opened_at = get_system_now()
        logger.warning(
            f"Circuit breaker opened after {self.metrics.consecutive_failures} failures"
        )

    def _transition_to_half_open(self) -> None:
        """Transition circuit to half-open state."""
        self.metrics.circuit_state = CircuitState.HALF_OPEN
        self.metrics.circuit_last_test = get_system_now()
        logger.info("Circuit breaker transitioning to half-open for testing")

    def _transition_to_closed(self) -> None:
        """Transition circuit to closed state."""
        self.metrics.circuit_state = CircuitState.CLOSED
        self.metrics.circuit_opened_at = None
        logger.info(
            f"Circuit breaker closed after {self.metrics.consecutive_successes} successes"
        )

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.metrics.circuit_state

    def get_metrics(self) -> ErrorMetrics:
        """Get current metrics."""
        return self.metrics
