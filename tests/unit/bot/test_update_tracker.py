"""
Comprehensive tests for update tracker functionality.

This module consolidates all update tracker tests including:
- Scheduling configuration parsing and validation
- Schedule state management and tracking
- Enhanced scheduling features with failure handling
- Error handling, retry mechanisms, and circuit breakers
- Fixed time scheduling bug fixes
- Update tracker lifecycle and async operations

Consolidated from:
- test_update_tracker_config.py
- test_update_tracker_enhanced.py
- test_update_tracker_error_handling.py
- test_update_tracker_fixed_time_fix.py
"""

import pytest
from datetime import datetime, time, timedelta
from unittest.mock import AsyncMock

from discord.ext import commands

from src.tgraph_bot.bot.update_tracker import (
    SchedulingConfig,
    ScheduleState,
    UpdateSchedule,
    UpdateTracker,
    RetryConfig,
    ErrorType,
    ErrorClassifier,
    CircuitBreaker,
    CircuitState,
    get_local_timezone,
)
from tests.utils.test_helpers import create_mock_discord_bot


class TestSchedulingConfig:
    """Test scheduling configuration parsing and validation."""

    def test_interval_based_config(self) -> None:
        """Test interval-based scheduling configuration."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")

        assert config.update_days == 7
        assert config.fixed_update_time == "XX:XX"
        assert config.is_interval_based() is True
        assert config.is_fixed_time_based() is False
        assert config.get_fixed_time() is None

    def test_fixed_time_config(self) -> None:
        """Test fixed time scheduling configuration."""
        config = SchedulingConfig(update_days=7, fixed_update_time="14:30")

        assert config.update_days == 7
        assert config.fixed_update_time == "14:30"
        assert config.is_interval_based() is False
        assert config.is_fixed_time_based() is True

        fixed_time = config.get_fixed_time()
        assert fixed_time is not None
        assert fixed_time.hour == 14
        assert fixed_time.minute == 30

    def test_invalid_time_format(self) -> None:
        """Test invalid time format handling."""
        with pytest.raises(ValueError, match="Invalid time format"):
            _ = SchedulingConfig(
                update_days=7,
                fixed_update_time="25:00",  # Invalid hour
            )

        with pytest.raises(ValueError, match="Invalid time format"):
            _ = SchedulingConfig(
                update_days=7,
                fixed_update_time="12:60",  # Invalid minute
            )

        with pytest.raises(ValueError, match="Invalid time format"):
            _ = SchedulingConfig(update_days=7, fixed_update_time="invalid")

    def test_invalid_update_days(self) -> None:
        """Test invalid update days validation."""
        with pytest.raises(ValueError, match="UPDATE_DAYS must be between 1 and 365"):
            _ = SchedulingConfig(update_days=0, fixed_update_time="XX:XX")

        with pytest.raises(ValueError, match="UPDATE_DAYS must be between 1 and 365"):
            _ = SchedulingConfig(update_days=366, fixed_update_time="XX:XX")

    def test_config_equality(self) -> None:
        """Test configuration equality comparison."""
        config1 = SchedulingConfig(update_days=7, fixed_update_time="14:30")
        config2 = SchedulingConfig(update_days=7, fixed_update_time="14:30")
        config3 = SchedulingConfig(update_days=5, fixed_update_time="14:30")

        assert config1 == config2
        assert config1 != config3


class TestScheduleState:
    """Test schedule state management."""

    def test_initial_state(self) -> None:
        """Test initial schedule state."""
        state = ScheduleState()

        assert state.last_update is None
        assert state.next_update is None
        assert state.is_running is False
        assert state.consecutive_failures == 0
        assert state.last_failure is None

    def test_update_tracking(self) -> None:
        """Test update tracking functionality."""
        state = ScheduleState()
        now = datetime.now(get_local_timezone())

        # Record successful update
        state.record_successful_update(now)
        assert state.last_update == now
        assert state.consecutive_failures == 0
        assert state.last_failure is None

    def test_failure_tracking(self) -> None:
        """Test failure tracking functionality."""
        state = ScheduleState()
        now = datetime.now(get_local_timezone())
        error = Exception("Test error")

        # Record failure
        state.record_failure(now, error)
        assert state.consecutive_failures == 1
        assert state.last_failure == now

        # Record another failure
        state.record_failure(now + timedelta(minutes=1), error)
        assert state.consecutive_failures == 2

        # Record success - should reset failure count
        state.record_successful_update(now + timedelta(minutes=2))
        assert state.consecutive_failures == 0
        assert state.last_failure == now + timedelta(minutes=1)  # Preserved

    def test_schedule_management(self) -> None:
        """Test schedule management."""
        state = ScheduleState()
        next_time = datetime.now(get_local_timezone()) + timedelta(hours=1)

        state.set_next_update(next_time)
        assert state.next_update == next_time

        state.start_scheduler()
        assert state.is_running is True

        state.stop_scheduler()
        assert state.is_running is False


class TestUpdateSchedule:
    """Test update schedule calculation logic."""

    def test_interval_based_calculation(self) -> None:
        """Test interval-based schedule calculation."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)

        # First calculation (no previous update)
        now = datetime.now(get_local_timezone())
        next_update = schedule.calculate_next_update(now)

        expected = now + timedelta(days=7)
        # Allow small time difference due to execution time
        assert abs((next_update - expected).total_seconds()) < 1

    def test_interval_with_previous_update(self) -> None:
        """Test interval calculation with previous update."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()

        # Set previous update
        last_update = datetime.now(get_local_timezone()) - timedelta(days=3)
        state.record_successful_update(last_update)

        schedule = UpdateSchedule(config, state)
        next_update = schedule.calculate_next_update(datetime.now(get_local_timezone()))

        expected = last_update + timedelta(days=7)
        assert abs((next_update - expected).total_seconds()) < 1

    def test_fixed_time_calculation_today(self) -> None:
        """Test fixed time calculation respects UPDATE_DAYS on first run."""
        config = SchedulingConfig(update_days=1, fixed_update_time="23:59")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)

        # Test at early morning - should schedule for tomorrow (respects UPDATE_DAYS=1)
        test_time = datetime.now(get_local_timezone()).replace(
            hour=1, minute=0, second=0, microsecond=0
        )
        next_update = schedule.calculate_next_update(test_time)

        assert next_update.date() == test_time.date() + timedelta(days=1)
        assert next_update.time() == time(23, 59)

    def test_fixed_time_calculation_tomorrow(self) -> None:
        """Test fixed time calculation for tomorrow."""
        config = SchedulingConfig(update_days=1, fixed_update_time="08:00")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)

        # Test at late evening - should schedule for tomorrow
        test_time = datetime.now(get_local_timezone()).replace(
            hour=22, minute=0, second=0, microsecond=0
        )
        next_update = schedule.calculate_next_update(test_time)

        expected_date = test_time.date() + timedelta(days=1)
        assert next_update.date() == expected_date
        assert next_update.time() == time(8, 0)

    def test_fixed_time_with_interval_constraint(self) -> None:
        """Test fixed time with interval constraint."""
        config = SchedulingConfig(update_days=7, fixed_update_time="12:00")
        state = ScheduleState()

        # Set last update to 2 days ago with clean time
        base_time = datetime.now(get_local_timezone()).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        last_update = base_time - timedelta(days=2)
        state.record_successful_update(last_update)

        schedule = UpdateSchedule(config, state)
        test_time = base_time.replace(hour=10, minute=0)
        next_update = schedule.calculate_next_update(test_time)

        # Should respect the 7-day interval, not schedule for today
        min_next_update = last_update + timedelta(days=7)
        assert next_update >= min_next_update
        assert next_update.time() == time(12, 0)

    def test_schedule_validation(self) -> None:
        """Test schedule validation."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)

        now = datetime.now(get_local_timezone())

        # Valid future time
        future_time = now + timedelta(hours=1)
        assert schedule.is_valid_schedule_time(future_time, now) is True

        # Invalid past time
        past_time = now - timedelta(hours=1)
        assert schedule.is_valid_schedule_time(past_time, now) is False

        # Invalid too far future
        far_future = now + timedelta(days=400)
        assert schedule.is_valid_schedule_time(far_future, now) is False


class TestEnhancedScheduling:
    """Test enhanced scheduling features."""

    def test_time_until_next_update(self) -> None:
        """Test calculation of time until next update."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)

        now = datetime.now(get_local_timezone())
        time_until = schedule.calculate_time_until_next_update(now)

        # Should be approximately 7 days
        expected = timedelta(days=7)
        assert abs((time_until - expected).total_seconds()) < 1

    def test_should_skip_update_no_failures(self) -> None:
        """Test that updates are not skipped when there are no failures."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)

        now = datetime.now(get_local_timezone())
        assert schedule.should_skip_update(now) is False

    def test_should_skip_update_few_failures(self) -> None:
        """Test that updates are not skipped with few failures."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)

        # Record 2 failures (below threshold)
        now = datetime.now(get_local_timezone())
        error = Exception("Test error")
        state.record_failure(now - timedelta(minutes=30), error)
        state.record_failure(now - timedelta(minutes=15), error)

        assert schedule.should_skip_update(now) is False

    def test_should_skip_update_many_failures(self) -> None:
        """Test that updates are skipped with many failures."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)

        # Record 3 failures (at threshold)
        now = datetime.now(get_local_timezone())
        error = Exception("Test error")
        state.record_failure(now - timedelta(hours=2), error)
        state.record_failure(now - timedelta(hours=1), error)
        state.record_failure(now - timedelta(minutes=30), error)

        # Should skip because we're within the backoff period
        assert schedule.should_skip_update(now) is True

    def test_should_skip_update_backoff_expired(self) -> None:
        """Test that updates resume after backoff period expires."""
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)

        # Record 3 failures but long ago
        old_time = datetime.now(get_local_timezone()) - timedelta(days=1)
        error = Exception("Test error")
        state.record_failure(old_time, error)
        state.record_failure(old_time, error)
        state.record_failure(old_time, error)

        # Should not skip because backoff period has expired
        now = datetime.now(get_local_timezone())
        assert schedule.should_skip_update(now) is False

    def test_exponential_backoff_calculation(self) -> None:
        """Test exponential backoff calculation."""
        now = datetime.now(get_local_timezone())
        error = Exception("Test error")

        # Test different failure counts
        for failures in [3, 4, 5, 6]:
            # Create fresh state for each test
            config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
            state = ScheduleState()
            schedule = UpdateSchedule(config, state)

            # Set the failure count directly and record the failure
            state.consecutive_failures = (
                failures - 1
            )  # Will be incremented by record_failure
            state.record_failure(now, error)

            # Calculate expected backoff
            failure_count = min(failures, 6)
            expected_hours = 1 << failure_count  # Bit shift for 2^failure_count
            backoff_until = now + timedelta(hours=expected_hours)

            # Should skip until backoff expires
            assert (
                schedule.should_skip_update(now + timedelta(hours=expected_hours - 1))
                is True
            )
            # Should not skip after backoff expires (add a small buffer)
            assert (
                schedule.should_skip_update(backoff_until + timedelta(minutes=1))
                is False
            )


class TestErrorClassifier:
    """Test error classification for retry logic."""

    def test_classify_transient_errors(self) -> None:
        """Test classification of transient errors."""
        # Network errors
        assert (
            ErrorClassifier.classify_error(Exception("Connection timeout"))
            == ErrorType.TRANSIENT
        )
        assert (
            ErrorClassifier.classify_error(Exception("Network unavailable"))
            == ErrorType.TRANSIENT
        )
        assert (
            ErrorClassifier.classify_error(Exception("DNS resolution failed"))
            == ErrorType.TRANSIENT
        )

        # Service errors
        assert (
            ErrorClassifier.classify_error(Exception("Service temporarily unavailable"))
            == ErrorType.TRANSIENT
        )
        assert (
            ErrorClassifier.classify_error(Exception("Gateway timeout"))
            == ErrorType.TRANSIENT
        )

    def test_classify_permanent_errors(self) -> None:
        """Test classification of permanent errors."""
        # Authentication errors
        assert (
            ErrorClassifier.classify_error(Exception("Unauthorized access"))
            == ErrorType.PERMANENT
        )
        assert (
            ErrorClassifier.classify_error(Exception("Invalid API key"))
            == ErrorType.PERMANENT
        )
        assert (
            ErrorClassifier.classify_error(Exception("Forbidden"))
            == ErrorType.PERMANENT
        )

        # Configuration errors
        assert (
            ErrorClassifier.classify_error(Exception("Bad request"))
            == ErrorType.PERMANENT
        )
        assert (
            ErrorClassifier.classify_error(Exception("Not found"))
            == ErrorType.PERMANENT
        )

    def test_classify_rate_limit_errors(self) -> None:
        """Test classification of rate limiting errors."""
        assert (
            ErrorClassifier.classify_error(Exception("Rate limit exceeded"))
            == ErrorType.RATE_LIMITED
        )
        assert (
            ErrorClassifier.classify_error(Exception("Too many requests"))
            == ErrorType.RATE_LIMITED
        )
        assert (
            ErrorClassifier.classify_error(Exception("Quota exceeded"))
            == ErrorType.RATE_LIMITED
        )

    def test_classify_unknown_errors(self) -> None:
        """Test classification of unknown errors."""
        assert (
            ErrorClassifier.classify_error(Exception("Some random error"))
            == ErrorType.UNKNOWN
        )
        assert (
            ErrorClassifier.classify_error(ValueError("Invalid value"))
            == ErrorType.UNKNOWN
        )


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_initial_state(self) -> None:
        """Test circuit breaker initial state."""
        config = RetryConfig(failure_threshold=3, recovery_timeout=60)
        breaker = CircuitBreaker(config)

        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.should_allow_request() is True

    def test_circuit_breaker_failure_tracking(self) -> None:
        """Test circuit breaker failure tracking."""
        config = RetryConfig(failure_threshold=3, recovery_timeout=60)
        breaker = CircuitBreaker(config)

        # Record failures
        breaker.record_failure(Exception("Error 1"))
        assert breaker.get_state() == CircuitState.CLOSED

        breaker.record_failure(Exception("Error 2"))
        assert breaker.get_state() == CircuitState.CLOSED

        # Third failure should open circuit
        breaker.record_failure(Exception("Error 3"))
        assert breaker.get_state() == CircuitState.OPEN

    def test_circuit_breaker_success_reset(self) -> None:
        """Test circuit breaker success resets failure count."""
        config = RetryConfig(failure_threshold=3, recovery_timeout=60)
        breaker = CircuitBreaker(config)

        # Record some failures
        breaker.record_failure(Exception("Error 1"))
        breaker.record_failure(Exception("Error 2"))
        assert breaker.get_state() == CircuitState.CLOSED

        # Record success - should reset consecutive failures
        breaker.record_success()
        metrics = breaker.get_metrics()
        assert metrics.consecutive_failures == 0
        assert breaker.get_state() == CircuitState.CLOSED

    def test_circuit_breaker_half_open_transition(self) -> None:
        """Test circuit breaker half-open state transition."""
        config = RetryConfig(
            failure_threshold=2, recovery_timeout=0.1
        )  # 0.1 second timeout
        breaker = CircuitBreaker(config)

        # Open the circuit
        breaker.record_failure(Exception("Error 1"))
        breaker.record_failure(Exception("Error 2"))
        assert breaker.get_state() == CircuitState.OPEN

        # Wait for recovery timeout
        import time

        time.sleep(0.2)

        # Should transition to half-open on next request
        assert breaker.should_allow_request() is True
        assert breaker.get_state() == CircuitState.HALF_OPEN

    def test_circuit_breaker_request_blocking(self) -> None:
        """Test circuit breaker blocks requests when open."""
        config = RetryConfig(failure_threshold=2, recovery_timeout=60)
        breaker = CircuitBreaker(config)

        # Initially should allow requests
        assert breaker.should_allow_request() is True

        # Open the circuit
        breaker.record_failure(Exception("Error 1"))
        breaker.record_failure(Exception("Error 2"))
        assert breaker.get_state() == CircuitState.OPEN

        # Should not allow requests when open
        assert breaker.should_allow_request() is False


class TestFixedTimeSchedulingBugFix:
    """Test the fix for the fixed time scheduling bug."""

    def test_first_run_respects_update_days_fixed_time(self) -> None:
        """Test that first run respects UPDATE_DAYS with fixed time scheduling."""
        # Setup: First run scenario (no last_update)
        config = SchedulingConfig(update_days=1, fixed_update_time="23:59")
        state = ScheduleState()  # No last_update (first run)
        schedule = UpdateSchedule(config, state)

        # Current time: 2025-07-16 21:28:00 (same as bug report)
        current_time = datetime(2025, 7, 16, 21, 28, 0, tzinfo=get_local_timezone())

        # Calculate next update
        next_update = schedule.calculate_next_update(current_time)

        # Expected: Should be 2025-07-17 23:59:00 (next day due to UPDATE_DAYS=1)
        expected_date = current_time.date() + timedelta(days=1)
        expected_time = time(23, 59)
        expected_next_update = datetime.combine(expected_date, expected_time).replace(
            tzinfo=get_local_timezone()
        )

        assert next_update == expected_next_update
        assert next_update.date() == (current_time.date() + timedelta(days=1))
        assert next_update.time() == time(23, 59)

    def test_first_run_respects_update_days_multiple_days(self) -> None:
        """Test that first run respects UPDATE_DAYS with multiple days."""
        # Setup: First run with UPDATE_DAYS=3
        config = SchedulingConfig(update_days=3, fixed_update_time="14:30")
        state = ScheduleState()  # No last_update (first run)
        schedule = UpdateSchedule(config, state)

        current_time = datetime(2025, 7, 16, 10, 0, 0, tzinfo=get_local_timezone())
        next_update = schedule.calculate_next_update(current_time)

        # Expected: Should be 3 days later at 14:30
        expected_date = current_time.date() + timedelta(days=3)
        expected_time = time(14, 30)
        expected_next_update = datetime.combine(expected_date, expected_time).replace(
            tzinfo=get_local_timezone()
        )

        assert next_update == expected_next_update
        assert next_update.date() == (current_time.date() + timedelta(days=3))
        assert next_update.time() == time(14, 30)

    def test_subsequent_run_respects_update_days_fixed_time(self) -> None:
        """Test that subsequent runs still respect UPDATE_DAYS with fixed time."""
        # Setup: Subsequent run scenario (has last_update)
        config = SchedulingConfig(update_days=2, fixed_update_time="12:00")
        state = ScheduleState()
        state.last_update = datetime(
            2025, 7, 14, 12, 0, 0, tzinfo=get_local_timezone()
        )  # 2 days ago
        schedule = UpdateSchedule(config, state)

        current_time = datetime(2025, 7, 16, 10, 0, 0, tzinfo=get_local_timezone())
        next_update = schedule.calculate_next_update(current_time)

        # Expected: Should be 2 days after last_update at 12:00
        expected_date = state.last_update.date() + timedelta(days=2)
        expected_time = time(12, 0)
        expected_next_update = datetime.combine(expected_date, expected_time).replace(
            tzinfo=get_local_timezone()
        )

        assert next_update == expected_next_update
        assert next_update.date() == (state.last_update.date() + timedelta(days=2))
        assert next_update.time() == time(12, 0)

    def test_bug_scenario_reproduction_and_fix(self) -> None:
        """Test the exact scenario from the bug report to verify the fix."""
        # Exact scenario from bug report
        config = SchedulingConfig(update_days=1, fixed_update_time="23:59")
        state = ScheduleState()  # First run, no last_update
        schedule = UpdateSchedule(config, state)

        # Bot started at 2025-07-16T21:28:00.798405
        current_time = datetime(
            2025, 7, 16, 21, 28, 0, 798405, tzinfo=get_local_timezone()
        )
        next_update = schedule.calculate_next_update(current_time)

        # Before fix: Would be 2025-07-16T23:59:00 (same day - BUG!)
        # After fix: Should be 2025-07-17T23:59:00 (next day - CORRECT!)
        expected_next_update = datetime(
            2025, 7, 17, 23, 59, 0, tzinfo=get_local_timezone()
        )

        assert next_update == expected_next_update
        assert next_update.date() == datetime(2025, 7, 17).date()
        assert next_update.time() == time(23, 59)

    def test_fixed_time_with_dst_handling(self) -> None:
        """Test fixed time calculation handles daylight saving time correctly."""
        config = SchedulingConfig(update_days=7, fixed_update_time="14:30")
        state = ScheduleState()
        schedule = UpdateSchedule(config, state)

        # Set a previous update
        last_update = datetime(
            2024, 1, 1, 14, 30, tzinfo=get_local_timezone()
        )  # Winter time
        state.record_successful_update(last_update)

        # Calculate next update during potential DST transition
        current_time = datetime(
            2024, 1, 5, 10, 0, tzinfo=get_local_timezone()
        )  # 4 days later
        next_update = schedule.calculate_next_update(current_time)

        # Should respect the interval and maintain the correct time
        expected_date = last_update.date() + timedelta(days=7)
        assert next_update.date() == expected_date
        assert next_update.time().hour == 14
        assert next_update.time().minute == 30


class TestUpdateTrackerEnhanced:
    """Test enhanced UpdateTracker functionality."""

    @pytest.fixture
    def mock_bot(self) -> commands.Bot:
        """Create a mock Discord bot using standardized utility."""
        return create_mock_discord_bot(user_name="UpdateTrackerBot", guild_count=1)

    @pytest.fixture
    def update_tracker(self, mock_bot: commands.Bot) -> UpdateTracker:
        """Create an UpdateTracker instance."""
        return UpdateTracker(mock_bot)

    def test_get_last_update_time_initial(self, update_tracker: UpdateTracker) -> None:
        """Test getting last update time when no updates have occurred."""
        assert update_tracker.get_last_update_time() is None

    def test_get_next_update_time_not_running(
        self, update_tracker: UpdateTracker
    ) -> None:
        """Test getting next update time when scheduler is not running."""
        assert update_tracker.get_next_update_time() is None

    def test_get_scheduler_status_initial(self, update_tracker: UpdateTracker) -> None:
        """Test getting scheduler status in initial state."""
        status = update_tracker.get_scheduler_status()

        assert status["is_running"] is False
        assert status["last_update"] is None
        assert status["next_update"] is None
        assert status["consecutive_failures"] == 0
        assert status["last_failure"] is None
        assert status["config_update_days"] is None
        assert status["config_fixed_time"] is None

    @pytest.mark.asyncio
    async def test_trigger_update_success(self, update_tracker: UpdateTracker) -> None:
        """Test successful update trigger."""
        # Set up callback
        callback = AsyncMock()
        update_tracker.set_update_callback(callback)

        # Trigger update
        await update_tracker._trigger_update_for_testing()  # pyright: ignore[reportPrivateUsage]

        # Verify callback was called and state updated
        callback.assert_called_once()
        state = update_tracker._get_state_for_testing()  # pyright: ignore[reportPrivateUsage]
        assert state.last_update is not None
        assert state.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_trigger_update_failure(self, update_tracker: UpdateTracker) -> None:
        """Test failed update trigger."""
        # Set up failing callback
        callback = AsyncMock(side_effect=Exception("Test error"))
        update_tracker.set_update_callback(callback)

        # Trigger update (should raise exception)
        with pytest.raises(Exception, match="Test error"):
            await update_tracker._trigger_update_for_testing()  # pyright: ignore[reportPrivateUsage]

        # Verify failure was recorded
        state = update_tracker._get_state_for_testing()  # pyright: ignore[reportPrivateUsage]
        assert state.consecutive_failures == 1
        assert state.last_failure is not None
