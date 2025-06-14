"""
Test enhanced error handling, retry mechanisms, and logging for UpdateTracker.

This module tests the comprehensive error handling features added to the
UpdateTracker including circuit breakers, retry logic, and audit logging.
"""
# pyright: reportPrivateUsage=false, reportAny=false

import pytest
from unittest.mock import AsyncMock, Mock

from bot.update_tracker import (
    UpdateTracker,
    RetryConfig,
    ErrorType,
    ErrorClassifier,
    CircuitBreaker,
    CircuitState,
    ErrorMetrics,
)


class TestErrorClassifier:
    """Test error classification for retry logic."""
    
    def test_classify_transient_errors(self) -> None:
        """Test classification of transient errors."""
        # Network errors
        assert ErrorClassifier.classify_error(Exception("Connection timeout")) == ErrorType.TRANSIENT
        assert ErrorClassifier.classify_error(Exception("Network unavailable")) == ErrorType.TRANSIENT
        assert ErrorClassifier.classify_error(Exception("DNS resolution failed")) == ErrorType.TRANSIENT
        
        # Service errors
        assert ErrorClassifier.classify_error(Exception("Service temporarily unavailable")) == ErrorType.TRANSIENT
        assert ErrorClassifier.classify_error(Exception("Gateway timeout")) == ErrorType.TRANSIENT
    
    def test_classify_permanent_errors(self) -> None:
        """Test classification of permanent errors."""
        # Authentication errors
        assert ErrorClassifier.classify_error(Exception("Unauthorized access")) == ErrorType.PERMANENT
        assert ErrorClassifier.classify_error(Exception("Invalid API key")) == ErrorType.PERMANENT
        assert ErrorClassifier.classify_error(Exception("Forbidden")) == ErrorType.PERMANENT
        
        # Configuration errors
        assert ErrorClassifier.classify_error(Exception("Bad request")) == ErrorType.PERMANENT
        assert ErrorClassifier.classify_error(Exception("Not found")) == ErrorType.PERMANENT
    
    def test_classify_rate_limit_errors(self) -> None:
        """Test classification of rate limiting errors."""
        assert ErrorClassifier.classify_error(Exception("Rate limit exceeded")) == ErrorType.RATE_LIMITED
        assert ErrorClassifier.classify_error(Exception("Too many requests")) == ErrorType.RATE_LIMITED
        assert ErrorClassifier.classify_error(Exception("Quota exceeded")) == ErrorType.RATE_LIMITED
    
    def test_classify_unknown_errors(self) -> None:
        """Test classification of unknown errors."""
        assert ErrorClassifier.classify_error(Exception("Some random error")) == ErrorType.UNKNOWN
        assert ErrorClassifier.classify_error(ValueError("Invalid value")) == ErrorType.UNKNOWN


class TestRetryConfig:
    """Test retry configuration validation."""
    
    def test_valid_config(self) -> None:
        """Test valid retry configuration."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            failure_threshold=5,
            recovery_timeout=30.0,
            success_threshold=2
        )
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
    
    def test_invalid_config_validation(self) -> None:
        """Test validation of invalid configurations."""
        with pytest.raises(ValueError, match="max_attempts must be at least 1"):
            _ = RetryConfig(max_attempts=0)

        with pytest.raises(ValueError, match="base_delay must be non-negative"):
            _ = RetryConfig(base_delay=-1.0)

        with pytest.raises(ValueError, match="max_delay must be >= base_delay"):
            _ = RetryConfig(base_delay=10.0, max_delay=5.0)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_closed_state(self) -> None:
        """Test circuit breaker in closed state."""
        config = RetryConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)
        
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.should_allow_request() is True
    
    def test_circuit_breaker_opens_after_failures(self) -> None:
        """Test circuit breaker opens after threshold failures."""
        config = RetryConfig(failure_threshold=2)
        breaker = CircuitBreaker(config)
        
        # Record failures
        breaker.record_failure(Exception("Error 1"))
        assert breaker.get_state() == CircuitState.CLOSED
        
        breaker.record_failure(Exception("Error 2"))
        assert breaker.get_state() == CircuitState.OPEN
        assert breaker.should_allow_request() is False
    
    def test_circuit_breaker_half_open_transition(self) -> None:
        """Test circuit breaker transitions to half-open after timeout."""
        config = RetryConfig(failure_threshold=1, recovery_timeout=0.1)
        breaker = CircuitBreaker(config)
        
        # Open the circuit
        breaker.record_failure(Exception("Error"))
        assert breaker.get_state() == CircuitState.OPEN
        
        # Wait for recovery timeout
        import time
        time.sleep(0.2)
        
        # Should transition to half-open
        assert breaker.should_allow_request() is True
        assert breaker.get_state() == CircuitState.HALF_OPEN
    
    def test_circuit_breaker_closes_after_successes(self) -> None:
        """Test circuit breaker closes after successful operations."""
        config = RetryConfig(failure_threshold=1, success_threshold=2)
        breaker = CircuitBreaker(config)
        
        # Open the circuit
        breaker.record_failure(Exception("Error"))
        # Manually transition to half-open for testing
        breaker.metrics.circuit_state = CircuitState.HALF_OPEN
        
        # Record successes
        breaker.record_success()
        assert breaker.get_state() == CircuitState.HALF_OPEN
        
        breaker.record_success()
        assert breaker.get_state() == CircuitState.CLOSED


class TestErrorMetrics:
    """Test error metrics tracking."""
    
    def test_metrics_initialization(self) -> None:
        """Test metrics are properly initialized."""
        metrics = ErrorMetrics()
        assert metrics.total_attempts == 0
        assert metrics.total_successes == 0
        assert metrics.total_failures == 0
        assert metrics.get_success_rate() == 0.0
        assert metrics.get_failure_rate() == 0.0
    
    def test_metrics_recording(self) -> None:
        """Test recording of attempts, successes, and failures."""
        metrics = ErrorMetrics()
        
        # Record attempts and successes
        metrics.record_attempt()
        metrics.record_success()
        
        assert metrics.total_attempts == 1
        assert metrics.total_successes == 1
        assert metrics.consecutive_successes == 1
        assert metrics.consecutive_failures == 0
        assert metrics.get_success_rate() == 1.0
        
        # Record failure
        metrics.record_attempt()
        metrics.record_failure(ErrorType.TRANSIENT)
        
        assert metrics.total_attempts == 2
        assert metrics.total_failures == 1
        assert metrics.consecutive_failures == 1
        assert metrics.consecutive_successes == 0
        assert metrics.transient_errors == 1
        assert metrics.get_success_rate() == 0.5
    
    def test_metrics_to_dict(self) -> None:
        """Test conversion of metrics to dictionary."""
        metrics = ErrorMetrics()
        metrics.record_attempt()
        metrics.record_success()
        
        data = metrics.to_dict()
        assert isinstance(data, dict)
        assert data["total_attempts"] == 1
        assert data["total_successes"] == 1
        assert data["success_rate"] == 1.0
        assert "error_breakdown" in data


@pytest.mark.asyncio
class TestEnhancedUpdateTracker:
    """Test enhanced UpdateTracker with error handling."""
    
    async def test_update_tracker_initialization(self) -> None:
        """Test UpdateTracker initializes with enhanced error handling."""
        mock_bot = Mock()
        retry_config = RetryConfig(max_attempts=2)

        tracker = UpdateTracker(mock_bot, retry_config)

        # Test that tracker initializes properly by checking public interface
        status = tracker.get_comprehensive_status()
        assert "update_metrics" in status
        assert "circuit_breaker" in status
    
    async def test_successful_update_with_metrics(self) -> None:
        """Test successful update records metrics correctly."""
        mock_bot = Mock()
        tracker = UpdateTracker(mock_bot)
        
        # Mock successful callback
        mock_callback = AsyncMock()
        tracker.set_update_callback(mock_callback)
        
        # Trigger update using public method
        await tracker.force_update()
        
        # Check metrics
        metrics = tracker.get_update_metrics()
        assert metrics["total_attempts"] == 1
        assert metrics["total_successes"] == 1
        assert metrics["success_rate"] == 1.0
        
        # Check circuit breaker
        cb_status = tracker.get_circuit_breaker_status()
        assert cb_status["state"] == "closed"
    
    async def test_failed_update_with_retry(self) -> None:
        """Test failed update triggers retry logic."""
        mock_bot = Mock()
        retry_config = RetryConfig(max_attempts=2, base_delay=0.01)  # Fast retry for testing
        tracker = UpdateTracker(mock_bot, retry_config)
        
        # Mock failing callback
        mock_callback = AsyncMock(side_effect=Exception("Test error"))
        tracker.set_update_callback(mock_callback)
        
        # Trigger update (should fail after retries)
        with pytest.raises(Exception, match="Test error"):
            await tracker.force_update()
        
        # Check that callback was called multiple times (retries)
        assert mock_callback.call_count == 2
        
        # Check metrics
        metrics = tracker.get_update_metrics()
        assert metrics["total_attempts"] == 1
        assert metrics["total_failures"] == 1
        assert metrics["success_rate"] == 0.0
    
    async def test_circuit_breaker_blocks_requests(self) -> None:
        """Test circuit breaker blocks requests after failures."""
        mock_bot = Mock()
        retry_config = RetryConfig(max_attempts=1, failure_threshold=1)
        tracker = UpdateTracker(mock_bot, retry_config)
        
        # Mock failing callback
        mock_callback = AsyncMock(side_effect=Exception("Test error"))
        tracker.set_update_callback(mock_callback)
        
        # First update should fail and open circuit
        with pytest.raises(Exception):
            await tracker.force_update()

        # Second update should be blocked by circuit breaker
        with pytest.raises(RuntimeError, match="circuit breaker"):
            await tracker.force_update()
        
        # Check circuit breaker status
        cb_status = tracker.get_circuit_breaker_status()
        assert cb_status["state"] == "open"
    
    async def test_comprehensive_status_reporting(self) -> None:
        """Test comprehensive status reporting includes all metrics."""
        mock_bot = Mock()
        tracker = UpdateTracker(mock_bot)
        
        status = tracker.get_comprehensive_status()
        
        # Check that all expected keys are present
        expected_keys = [
            "is_running", "update_metrics", "circuit_breaker",
            "task_manager_metrics", "task_manager_health"
        ]
        for key in expected_keys:
            assert key in status
    
    async def test_error_state_reset(self) -> None:
        """Test error state can be reset for recovery."""
        mock_bot = Mock()
        tracker = UpdateTracker(mock_bot)
        
        # Reset error state
        tracker.reset_error_state()

        # Check that state is reset by checking metrics
        reset_metrics = tracker.get_update_metrics()
        reset_cb_status = tracker.get_circuit_breaker_status()

        assert reset_metrics["total_failures"] == 0
        assert reset_cb_status["state"] == "closed"
