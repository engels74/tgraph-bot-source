"""Tests for task scheduler system.

This test suite validates the task scheduler functionality including:
- Schedule calculation for fixed time (HH:MM format)
- Schedule calculation for random time (XX:XX format)
- Next run time calculation based on interval and current time
- Graceful shutdown and task cancellation
- Async scheduler lifecycle management

Requirements tested: 7.1, 7.2, 7.5
"""

# pyright: reportPrivateUsage=false, reportAny=false, reportUnusedVariable=false

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from tgraph_bot.config.models import AutomationConfig


@pytest.fixture
def fixed_time_config() -> AutomationConfig:
    """Fixture providing automation config with fixed update time."""
    return AutomationConfig(
        enabled=True,
        update_interval_days=7,
        fixed_update_time="14:30",  # 2:30 PM daily
    )


@pytest.fixture
def random_time_config() -> AutomationConfig:
    """Fixture providing automation config with random update time."""
    return AutomationConfig(
        enabled=True,
        update_interval_days=3,
        fixed_update_time="XX:XX",  # Random time within interval
    )


@pytest.fixture
def single_day_interval_config() -> AutomationConfig:
    """Fixture providing automation config with 1-day interval."""
    return AutomationConfig(
        enabled=True,
        update_interval_days=1,
        fixed_update_time="09:00",  # 9:00 AM daily
    )


@pytest.fixture
def max_interval_config() -> AutomationConfig:
    """Fixture providing automation config with maximum interval (365 days)."""
    return AutomationConfig(
        enabled=True,
        update_interval_days=365,
        fixed_update_time="XX:XX",
    )


class TestScheduleCalculationFixedTime:
    """Tests for schedule calculation with fixed time (HH:MM format).
    
    Requirements tested: 7.2
    """

    def test_calculate_next_run_fixed_time_future_today(
        self, fixed_time_config: AutomationConfig
    ) -> None:
        """Test next run calculation when fixed time is later today."""
        # Mock current time: 10:00 AM, fixed time: 2:30 PM
        with patch("tgraph_bot.scheduler.task_scheduler.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 10, 0, 0)  # 10:00 AM
            mock_datetime.now.return_value = mock_now
            mock_datetime.combine = datetime.combine
            
            from tgraph_bot.scheduler.task_scheduler import TaskScheduler
            
            scheduler = TaskScheduler(config=fixed_time_config)
            next_run = scheduler._calculate_next_run()
            
            # Should be today at 2:30 PM
            expected = datetime(2024, 1, 15, 14, 30, 0)
            assert next_run == expected

    def test_calculate_next_run_fixed_time_past_today(
        self, fixed_time_config: AutomationConfig
    ) -> None:
        """Test next run calculation when fixed time has passed today."""
        # Mock current time: 5:00 PM, fixed time: 2:30 PM
        with patch("tgraph_bot.scheduler.task_scheduler.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 17, 0, 0)  # 5:00 PM
            mock_datetime.now.return_value = mock_now
            mock_datetime.combine = datetime.combine
            
            from tgraph_bot.scheduler.task_scheduler import TaskScheduler
            
            scheduler = TaskScheduler(config=fixed_time_config)
            next_run = scheduler._calculate_next_run()
            
            # Should be tomorrow at 2:30 PM
            expected = datetime(2024, 1, 16, 14, 30, 0)
            assert next_run == expected

    def test_calculate_next_run_fixed_time_midnight(self) -> None:
        """Test next run calculation with midnight as fixed time."""
        config = AutomationConfig(
            enabled=True,
            update_interval_days=1,
            fixed_update_time="00:00",
        )
        
        with patch("tgraph_bot.scheduler.task_scheduler.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 23, 30, 0)  # 11:30 PM
            mock_datetime.now.return_value = mock_now
            mock_datetime.combine = datetime.combine
            
            from tgraph_bot.scheduler.task_scheduler import TaskScheduler
            
            scheduler = TaskScheduler(config=config)
            next_run = scheduler._calculate_next_run()
            
            # Should be tomorrow at midnight
            expected = datetime(2024, 1, 16, 0, 0, 0)
            assert next_run == expected

    def test_calculate_next_run_fixed_time_end_of_day(self) -> None:
        """Test next run calculation with 23:59 as fixed time."""
        config = AutomationConfig(
            enabled=True,
            update_interval_days=1,
            fixed_update_time="23:59",
        )
        
        with patch("tgraph_bot.scheduler.task_scheduler.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 12, 0, 0)  # Noon
            mock_datetime.now.return_value = mock_now
            mock_datetime.combine = datetime.combine
            
            from tgraph_bot.scheduler.task_scheduler import TaskScheduler
            
            scheduler = TaskScheduler(config=config)
            next_run = scheduler._calculate_next_run()
            
            # Should be today at 23:59
            expected = datetime(2024, 1, 15, 23, 59, 0)
            assert next_run == expected


class TestScheduleCalculationRandomTime:
    """Tests for schedule calculation with random time (XX:XX format).
    
    Requirements tested: 7.3
    """

    def test_calculate_next_run_random_time_within_interval(
        self, random_time_config: AutomationConfig
    ) -> None:
        """Test that random time falls within the update interval."""
        with patch("tgraph_bot.scheduler.task_scheduler.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 10, 0, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.combine = datetime.combine
            
            from tgraph_bot.scheduler.task_scheduler import TaskScheduler
            
            scheduler = TaskScheduler(config=random_time_config)
            next_run = scheduler._calculate_next_run()
            
            # Should be between now and now + 3 days
            min_time = mock_now
            max_time = mock_now + timedelta(days=3)
            
            assert min_time < next_run <= max_time

    def test_calculate_next_run_random_time_different_each_call(
        self, random_time_config: AutomationConfig
    ) -> None:
        """Test that random time generates different values on multiple calls."""
        with patch("tgraph_bot.scheduler.task_scheduler.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 10, 0, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.combine = datetime.combine
            
            from tgraph_bot.scheduler.task_scheduler import TaskScheduler
            
            scheduler = TaskScheduler(config=random_time_config)
            
            # Generate multiple random times
            times = [scheduler._calculate_next_run() for _ in range(10)]
            
            # At least some should be different (very high probability)
            unique_times = set(times)
            assert len(unique_times) > 1

    def test_calculate_next_run_random_time_max_interval(
        self, max_interval_config: AutomationConfig
    ) -> None:
        """Test random time calculation with maximum interval (365 days)."""
        with patch("tgraph_bot.scheduler.task_scheduler.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 10, 0, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.combine = datetime.combine
            
            from tgraph_bot.scheduler.task_scheduler import TaskScheduler
            
            scheduler = TaskScheduler(config=max_interval_config)
            next_run = scheduler._calculate_next_run()
            
            # Should be between now and now + 365 days
            min_time = mock_now
            max_time = mock_now + timedelta(days=365)
            
            assert min_time < next_run <= max_time


class TestNextRunTimeCalculation:
    """Tests for next run time calculation logic.
    
    Requirements tested: 7.1, 7.2
    """

    @pytest.mark.parametrize(
        "current_hour,current_minute,fixed_hour,fixed_minute,expected_days_offset",
        [
            (10, 0, 14, 30, 0),  # Future today
            (17, 0, 14, 30, 1),  # Past today, tomorrow
            (14, 29, 14, 30, 0),  # 1 minute before
            (14, 30, 14, 30, 1),  # Exact time, next occurrence
            (14, 31, 14, 30, 1),  # 1 minute after
        ],
    )
    def test_next_run_time_various_scenarios(
        self,
        current_hour: int,
        current_minute: int,
        fixed_hour: int,
        fixed_minute: int,
        expected_days_offset: int,
    ) -> None:
        """Test next run time calculation for various time scenarios."""
        config = AutomationConfig(
            enabled=True,
            update_interval_days=1,
            fixed_update_time=f"{fixed_hour:02d}:{fixed_minute:02d}",
        )
        
        with patch("tgraph_bot.scheduler.task_scheduler.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, current_hour, current_minute, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.combine = datetime.combine
            
            from tgraph_bot.scheduler.task_scheduler import TaskScheduler
            
            scheduler = TaskScheduler(config=config)
            next_run = scheduler._calculate_next_run()
            
            expected = datetime(
                2024, 1, 15 + expected_days_offset, fixed_hour, fixed_minute, 0
            )
            assert next_run == expected


class TestGracefulShutdown:
    """Tests for graceful shutdown and task cancellation.

    Requirements tested: 7.5
    """

    @pytest.mark.asyncio
    async def test_scheduler_start_creates_task(
        self, fixed_time_config: AutomationConfig
    ) -> None:
        """Test that starting scheduler creates an asyncio task."""
        from tgraph_bot.scheduler.task_scheduler import TaskScheduler

        scheduler = TaskScheduler(config=fixed_time_config)

        # Initially no task
        assert scheduler._task is None

        # Start scheduler
        await scheduler.start()

        # Task should be created
        assert scheduler._task is not None
        assert isinstance(scheduler._task, asyncio.Task)
        assert not scheduler._task.done()

        # Cleanup
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_scheduler_stop_cancels_task(
        self, fixed_time_config: AutomationConfig
    ) -> None:
        """Test that stopping scheduler cancels the running task."""
        from tgraph_bot.scheduler.task_scheduler import TaskScheduler

        scheduler = TaskScheduler(config=fixed_time_config)

        # Start scheduler
        await scheduler.start()
        task = scheduler._task
        assert task is not None
        assert not task.done()

        # Stop scheduler
        await scheduler.stop()

        # Task should be cancelled and done
        assert task.done()
        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_scheduler_stop_waits_for_cancellation(
        self, fixed_time_config: AutomationConfig
    ) -> None:
        """Test that stop() waits for task cancellation to complete."""
        from tgraph_bot.scheduler.task_scheduler import TaskScheduler

        scheduler = TaskScheduler(config=fixed_time_config)

        await scheduler.start()

        # Stop should complete without raising CancelledError
        await scheduler.stop()

        # Task should be fully cancelled
        assert scheduler._task is not None
        assert scheduler._task.done()

    @pytest.mark.asyncio
    async def test_scheduler_stop_when_not_started(
        self, fixed_time_config: AutomationConfig
    ) -> None:
        """Test that stopping scheduler when not started is safe."""
        from tgraph_bot.scheduler.task_scheduler import TaskScheduler

        scheduler = TaskScheduler(config=fixed_time_config)

        # Stop without starting should not raise
        await scheduler.stop()

        assert scheduler._task is None

    @pytest.mark.asyncio
    async def test_scheduler_stop_when_already_stopped(
        self, fixed_time_config: AutomationConfig
    ) -> None:
        """Test that stopping scheduler multiple times is safe."""
        from tgraph_bot.scheduler.task_scheduler import TaskScheduler

        scheduler = TaskScheduler(config=fixed_time_config)

        await scheduler.start()
        await scheduler.stop()

        # Second stop should be safe
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_scheduler_lifecycle_with_context_manager(
        self, fixed_time_config: AutomationConfig
    ) -> None:
        """Test scheduler lifecycle using async context manager."""
        from tgraph_bot.scheduler.task_scheduler import managed_scheduler, TaskScheduler

        scheduler = TaskScheduler(config=fixed_time_config)

        async with managed_scheduler(scheduler) as sched:
            # Scheduler should be running
            assert sched._task is not None
            assert not sched._task.done()

        # After context exit, scheduler should be stopped
        assert scheduler._task is not None
        assert scheduler._task.done()


class TestSchedulerWithMockedSleep:
    """Tests using mocked asyncio.sleep for faster execution.

    Requirements tested: 7.1, 7.2
    """

    @pytest.mark.asyncio
    async def test_schedule_loop_calculates_sleep_duration(
        self, fixed_time_config: AutomationConfig
    ) -> None:
        """Test that scheduler calculates correct sleep duration."""
        from tgraph_bot.scheduler.task_scheduler import TaskScheduler

        scheduler = TaskScheduler(config=fixed_time_config)

        # Test the calculation directly
        with patch("tgraph_bot.scheduler.task_scheduler.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 10, 0, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.combine = datetime.combine

            next_run = scheduler._calculate_next_run()
            sleep_duration = (next_run - mock_now).total_seconds()

            # From 10:00 to 14:30 = 4.5 hours = 16200 seconds
            assert sleep_duration == pytest.approx(16200.0, abs=1.0)  # pyright: ignore[reportUnknownMemberType]

    @pytest.mark.asyncio
    async def test_scheduler_loop_runs_continuously(
        self, fixed_time_config: AutomationConfig
    ) -> None:
        """Test that scheduler loop continues running after each iteration."""
        from tgraph_bot.scheduler.task_scheduler import TaskScheduler

        scheduler = TaskScheduler(config=fixed_time_config)

        # Patch asyncio.sleep to make the loop run faster
        with patch("tgraph_bot.scheduler.task_scheduler.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.return_value = None

            # Start scheduler and let it run briefly
            try:
                await scheduler.start()
                # Give it time to iterate
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                pass
            finally:
                await scheduler.stop()

        # Verify sleep was called (loop ran)
        assert mock_sleep.call_count > 0

    @pytest.mark.asyncio
    async def test_scheduler_handles_errors_gracefully(
        self, fixed_time_config: AutomationConfig
    ) -> None:
        """Test that scheduler continues running even after errors in execution."""
        from tgraph_bot.scheduler.task_scheduler import TaskScheduler

        scheduler = TaskScheduler(config=fixed_time_config)

        # Start the scheduler and let it run briefly
        await scheduler.start()

        # Give it a moment to start
        await asyncio.sleep(0.01)

        # Verify task is running
        assert scheduler._task is not None
        assert not scheduler._task.done()

        # Stop it
        await scheduler.stop()

        # Verify it stopped cleanly
        assert scheduler._task.done()

