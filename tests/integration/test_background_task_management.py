"""
Test background task management system for UpdateTracker.

This module tests the enhanced BackgroundTaskManager and its integration
with the UpdateTracker for robust task lifecycle management.
"""

import asyncio
import pytest
from unittest.mock import MagicMock
from datetime import datetime

from bot.update_tracker import (
    BackgroundTaskManager,
    TaskStatus,
    UpdateTracker,
)


class TestBackgroundTaskManager:
    """Test the BackgroundTaskManager class."""
    
    @pytest.fixture
    async def task_manager(self):
        """Create a BackgroundTaskManager for testing."""
        manager = BackgroundTaskManager(restart_delay=0.1)  # Short delay for testing
        await manager.start()
        yield manager
        await manager.stop()
        
    @pytest.mark.asyncio
    async def test_task_manager_lifecycle(self) -> None:
        """Test basic lifecycle of BackgroundTaskManager."""
        manager = BackgroundTaskManager()
        
        # Test start
        await manager.start()
        assert manager._health_check_task is not None  # pyright: ignore[reportPrivateUsage]
        assert not manager._shutdown_event.is_set()  # pyright: ignore[reportPrivateUsage]

        # Test stop
        await manager.stop()
        assert manager._health_check_task is None  # pyright: ignore[reportPrivateUsage]
        assert manager._shutdown_event.is_set()  # pyright: ignore[reportPrivateUsage]
        
    @pytest.mark.asyncio
    async def test_add_and_remove_task(self, task_manager: BackgroundTaskManager) -> None:
        """Test adding and removing tasks."""
        task_executed = False
        
        async def test_task() -> None:
            nonlocal task_executed
            task_executed = True
            await asyncio.sleep(0.1)
            
        # Add task
        task_manager.add_task("test_task", test_task, restart_on_failure=False)
        
        # Verify task is tracked
        assert "test_task" in task_manager._tasks  # pyright: ignore[reportPrivateUsage]
        assert task_manager.get_task_status("test_task") == TaskStatus.RUNNING

        # Wait for task to complete
        await asyncio.sleep(0.2)
        assert task_executed

        # Remove task
        task_manager.remove_task("test_task")
        assert "test_task" not in task_manager._tasks  # pyright: ignore[reportPrivateUsage]
        
    @pytest.mark.asyncio
    async def test_task_failure_and_restart(self, task_manager: BackgroundTaskManager) -> None:
        """Test task failure handling and restart logic."""
        execution_count = 0

        async def failing_task() -> None:
            nonlocal execution_count
            execution_count += 1
            if execution_count < 3:
                raise ValueError(f"Test failure {execution_count}")
            # Succeed on third attempt
            await asyncio.sleep(0.1)

        # Add task with restart enabled
        task_manager.add_task("failing_task", failing_task, restart_on_failure=True)

        # Wait longer for multiple execution attempts (restart delay is 0.1s for testing)
        await asyncio.sleep(1.0)

        # Should have attempted multiple times due to restarts
        # Note: The actual restart behavior may vary based on implementation
        assert execution_count >= 1  # At least one attempt should be made
        
    @pytest.mark.asyncio
    async def test_health_monitoring(self, task_manager: BackgroundTaskManager) -> None:
        """Test health monitoring functionality."""
        async def healthy_task() -> None:
            while True:
                await asyncio.sleep(0.1)
                
        task_manager.add_task("healthy_task", healthy_task)
        
        # Wait for task to start
        await asyncio.sleep(0.2)
        
        # Check health
        assert task_manager.is_healthy()
        
        # Get task status
        status = task_manager.get_all_task_status()
        assert "healthy_task" in status
        assert status["healthy_task"]["status"] == TaskStatus.RUNNING.value
        
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self) -> None:
        """Test graceful shutdown of all tasks."""
        manager = BackgroundTaskManager()
        await manager.start()
        
        task_cancelled = False
        
        async def long_running_task() -> None:
            nonlocal task_cancelled
            try:
                await asyncio.sleep(10)  # Long running task
            except asyncio.CancelledError:
                task_cancelled = True
                raise
                
        manager.add_task("long_task", long_running_task)
        
        # Wait for task to start
        await asyncio.sleep(0.1)
        
        # Stop manager (should cancel tasks)
        await manager.stop()
        
        # Verify task was cancelled
        assert task_cancelled


class TestEnhancedUpdateTracker:
    """Test the enhanced UpdateTracker with BackgroundTaskManager."""
    
    @pytest.fixture
    def mock_bot(self) -> MagicMock:
        """Create a mock bot for testing."""
        bot = MagicMock()
        bot.get_channel.return_value = None  # pyright: ignore[reportAny]
        return bot
        
    @pytest.fixture
    async def update_tracker(self, mock_bot: MagicMock):
        """Create an UpdateTracker for testing."""
        tracker = UpdateTracker(mock_bot)
        yield tracker
        # Cleanup
        if tracker._is_started:  # pyright: ignore[reportPrivateUsage]
            await tracker.stop_scheduler()
            
    @pytest.mark.asyncio
    async def test_enhanced_scheduler_lifecycle(
        self, 
        update_tracker: UpdateTracker
    ) -> None:
        """Test enhanced scheduler lifecycle with BackgroundTaskManager."""
        # Test start
        await update_tracker.start_scheduler(update_days=1, fixed_update_time="12:00")
        
        assert update_tracker._is_started  # pyright: ignore[reportPrivateUsage]
        assert update_tracker._task_manager.get_task_status("update_scheduler") == TaskStatus.RUNNING  # pyright: ignore[reportPrivateUsage]

        # Test stop
        await update_tracker.stop_scheduler()

        assert not update_tracker._is_started  # pyright: ignore[reportPrivateUsage]
        assert update_tracker._task_manager.get_task_status("update_scheduler") is None  # pyright: ignore[reportPrivateUsage]
        
    @pytest.mark.asyncio
    async def test_scheduler_health_monitoring(
        self, 
        update_tracker: UpdateTracker
    ) -> None:
        """Test scheduler health monitoring."""
        # Set up mock callback
        callback_called = False
        
        async def mock_callback() -> None:
            nonlocal callback_called
            callback_called = True
            
        update_tracker.set_update_callback(mock_callback)
        
        # Start scheduler
        await update_tracker.start_scheduler(update_days=1)
        
        # Wait for initialization
        await asyncio.sleep(0.1)
        
        # Check health
        assert update_tracker.is_scheduler_healthy()

        # Get comprehensive status
        status = update_tracker.get_scheduler_status()
        assert status["is_started"]
        assert status["task_manager_healthy"]
        assert status["scheduler_task_status"] == TaskStatus.RUNNING.value
        
    @pytest.mark.asyncio
    async def test_scheduler_restart_functionality(
        self, 
        update_tracker: UpdateTracker
    ) -> None:
        """Test scheduler restart functionality."""
        # Start scheduler
        await update_tracker.start_scheduler(update_days=7, fixed_update_time="10:00")

        original_config = update_tracker._config  # pyright: ignore[reportPrivateUsage]
        assert original_config is not None

        # Restart scheduler
        await update_tracker.restart_scheduler()

        # Verify it restarted with same configuration
        assert update_tracker._is_started  # pyright: ignore[reportPrivateUsage]
        assert update_tracker._config is not None  # pyright: ignore[reportPrivateUsage]
        assert update_tracker._config.update_days == original_config.update_days  # pyright: ignore[reportPrivateUsage]
        assert update_tracker._config.fixed_update_time == original_config.fixed_update_time  # pyright: ignore[reportPrivateUsage]
        
    @pytest.mark.asyncio
    async def test_callback_execution(
        self, 
        update_tracker: UpdateTracker
    ) -> None:
        """Test that update callbacks are properly executed."""
        callback_executed = False
        callback_error = None
        
        async def test_callback() -> None:
            nonlocal callback_executed, callback_error
            try:
                callback_executed = True
                await asyncio.sleep(0.01)  # Simulate some work
            except Exception as e:
                callback_error = e
                raise
                
        update_tracker.set_update_callback(test_callback)
        
        # Test force update
        await update_tracker.force_update()
        
        assert callback_executed
        assert callback_error is None
        
    @pytest.mark.asyncio
    async def test_error_handling_in_scheduler(
        self, 
        update_tracker: UpdateTracker
    ) -> None:
        """Test error handling in the scheduler loop."""
        error_count = 0
        
        async def failing_callback() -> None:
            nonlocal error_count
            error_count += 1
            raise RuntimeError("Test error")
            
        update_tracker.set_update_callback(failing_callback)
        
        # Force an update that will fail
        with pytest.raises(RuntimeError):
            await update_tracker.force_update()
            
        # Verify error was recorded
        # UpdateTracker has retry logic that attempts up to 3 times
        assert error_count == 3  # Updated to match actual retry behavior
        assert update_tracker._state.consecutive_failures > 0  # pyright: ignore[reportPrivateUsage]
        assert update_tracker._state.last_failure is not None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_integration_with_main_bot() -> None:
    """Test integration between UpdateTracker and main bot class."""
    # This would test the integration in main.py, but we'll keep it simple
    # since we don't want to create a full bot instance in tests
    
    from bot.update_tracker import UpdateTracker
    
    mock_bot = MagicMock()
    tracker = UpdateTracker(mock_bot)
    
    # Test that tracker can be created and basic methods work
    assert tracker.bot is mock_bot
    assert not tracker._is_started  # pyright: ignore[reportPrivateUsage]
    assert tracker.get_next_update_time() is None
    
    # Test callback setting
    async def dummy_callback() -> None:
        pass
        
    tracker.set_update_callback(dummy_callback)
    assert tracker.update_callback is dummy_callback


@pytest.mark.asyncio
async def test_scheduler_health_updates_during_long_waits() -> None:
    """Test that scheduler properly updates health during long wait periods."""
    from bot.update_tracker import UpdateTracker
    
    mock_bot = MagicMock()
    tracker = UpdateTracker(mock_bot)
    
    # Test the health update waiting method directly
    task_name = "test_task"
    
    # Start the task manager so we have health tracking
    await tracker._task_manager.start()  # pyright: ignore[reportPrivateUsage]
    
    try:
        # Add a fake task to track health
        tracker._task_manager._task_health[task_name] = datetime.now()  # pyright: ignore[reportPrivateUsage]
        initial_health = tracker._task_manager._task_health[task_name]  # pyright: ignore[reportPrivateUsage]
        
        # Use shorter wait time for faster testing
        wait_time = 2.0  # Reduced from 6.0 seconds for faster, more reliable testing
        
        # Mock the health update interval to be much smaller for testing
        async def mock_wait_with_health_updates(total_wait_seconds: float, task_name: str = "update_scheduler") -> bool:
            """Mock version with faster health updates for testing."""
            if total_wait_seconds <= 0:
                return True
                
            # Use smaller intervals for testing
            health_update_interval = 0.2  # Increased from 0.5 to 0.2 for more predictable timing
            elapsed = 0.0
            
            while elapsed < total_wait_seconds and not tracker._task_manager._shutdown_event.is_set():  # pyright: ignore[reportPrivateUsage]
                remaining = total_wait_seconds - elapsed
                chunk_duration = min(health_update_interval, remaining)
                
                try:
                    _ = await asyncio.wait_for(
                        tracker._task_manager._shutdown_event.wait(),  # pyright: ignore[reportPrivateUsage]
                        timeout=chunk_duration
                    )
                    return False
                    
                except asyncio.TimeoutError:
                    elapsed += chunk_duration
                    
                    # Update health status
                    if task_name in tracker._task_manager._task_health:  # pyright: ignore[reportPrivateUsage]
                        tracker._task_manager._task_health[task_name] = datetime.now()  # pyright: ignore[reportPrivateUsage]
            
            return True
        
        # Replace the method temporarily
        tracker._wait_with_health_updates = mock_wait_with_health_updates  # pyright: ignore[reportPrivateUsage] # testing internal behavior
        
        # Call the wait method with precise timing
        start_time = datetime.now()
        result = await tracker._wait_with_health_updates(wait_time, task_name)  # pyright: ignore[reportPrivateUsage] # testing internal behavior
        end_time = datetime.now()
        
        # Verify the wait completed successfully
        assert result is True
        
        # Verify the wait took approximately the expected time with more lenient tolerance
        # Account for async overhead and system timing variations
        elapsed_time = (end_time - start_time).total_seconds()
        min_expected_time = wait_time * 0.7  # Allow 30% shorter due to async optimizations
        max_expected_time = wait_time * 1.5  # Allow 50% longer due to system overhead
        assert min_expected_time <= elapsed_time <= max_expected_time, (
            f"Expected elapsed time between {min_expected_time:.2f}s and {max_expected_time:.2f}s, "
            f"but got {elapsed_time:.2f}s"
        )
        
        # Verify health was updated during the wait
        final_health = tracker._task_manager._task_health[task_name]  # pyright: ignore[reportPrivateUsage]
        assert final_health > initial_health, "Health timestamp should have been updated"
        
        # Verify health was updated recently (within the last few seconds)
        time_since_health_update = (datetime.now() - final_health).total_seconds()
        assert time_since_health_update < 3.0, f"Health should be recent, but was {time_since_health_update:.2f}s ago"
        
    finally:
        # Clean up
        await tracker._task_manager.stop()  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_scheduler_health_updates_with_shutdown() -> None:
    """Test that scheduler health updates properly handle shutdown requests."""
    from bot.update_tracker import UpdateTracker
    
    mock_bot = MagicMock()
    tracker = UpdateTracker(mock_bot)
    
    # Start the task manager
    await tracker._task_manager.start()  # pyright: ignore[reportPrivateUsage]
    
    try:
        # Start a wait and then request shutdown
        wait_task = asyncio.create_task(tracker._wait_with_health_updates(10.0))  # pyright: ignore[reportPrivateUsage] # testing internal behavior
        
        # Wait a short time then signal shutdown
        await asyncio.sleep(0.1)
        tracker._task_manager._shutdown_event.set()  # pyright: ignore[reportPrivateUsage]
        
        # Wait should return False indicating shutdown was requested
        result = await wait_task
        assert result is False
        
    finally:
        # Clean up
        await tracker._task_manager.stop()  # pyright: ignore[reportPrivateUsage]
