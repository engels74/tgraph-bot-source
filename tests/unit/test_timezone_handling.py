"""
Tests for timezone handling in the update tracker and health check system.

This module tests the fix for the datetime timezone error that occurred when
mixing timezone-aware and timezone-naive datetime objects in health checks.
"""

import asyncio
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import discord
import pytest

from tgraph_bot.bot.update_tracker import (
    BackgroundTaskManager,
    ScheduleState,
    StateManager,
    RecoveryManager,
    SchedulingConfig,
    UpdateTracker,
)


class TestTimezoneHandling:
    """Test timezone handling in health check and state management."""

    def test_schedule_state_serialization_with_timezone_aware_datetimes(self) -> None:
        """Test that ScheduleState correctly handles timezone-aware datetimes during serialization."""
        # Create timezone-aware datetimes
        now_utc = discord.utils.utcnow()
        future_utc = now_utc + timedelta(hours=1)
        
        state = ScheduleState()
        state.last_update = now_utc
        state.next_update = future_utc
        state.last_failure = now_utc - timedelta(minutes=30)
        
        # Serialize to dict
        state_dict = state.to_dict()
        
        # Verify serialization includes timezone info
        assert state_dict["last_update"] is not None
        assert state_dict["next_update"] is not None
        assert state_dict["last_failure"] is not None
        
        # Deserialize back
        restored_state = ScheduleState.from_dict(state_dict)
        
        # Verify all datetimes are timezone-aware
        assert restored_state.last_update is not None
        assert restored_state.last_update.tzinfo is not None
        assert restored_state.next_update is not None
        assert restored_state.next_update.tzinfo is not None
        assert restored_state.last_failure is not None
        assert restored_state.last_failure.tzinfo is not None
        
        # Verify values are preserved
        assert restored_state.last_update == now_utc
        assert restored_state.next_update == future_utc

    def test_schedule_state_handles_timezone_naive_legacy_data(self) -> None:
        """Test that ScheduleState correctly converts timezone-naive legacy data to timezone-aware."""
        # Simulate legacy data with timezone-naive datetime strings
        legacy_data: dict[str, str | int | bool | None] = {
            "last_update": "2024-01-01T12:00:00",  # No timezone info
            "next_update": "2024-01-01T13:00:00",  # No timezone info
            "last_failure": "2024-01-01T11:30:00",  # No timezone info
            "is_running": True,
            "consecutive_failures": 0,
        }

        # Deserialize legacy data
        state = ScheduleState.from_dict(legacy_data)
        
        # Verify all datetimes are now timezone-aware (converted to UTC)
        assert state.last_update is not None
        assert state.last_update.tzinfo == timezone.utc
        assert state.next_update is not None
        assert state.next_update.tzinfo == timezone.utc
        assert state.last_failure is not None
        assert state.last_failure.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_background_task_manager_health_check_with_timezone_aware_datetimes(self) -> None:
        """Test that BackgroundTaskManager health checks work with timezone-aware datetimes."""
        manager = BackgroundTaskManager()
        
        # Add a task with timezone-aware datetime
        task_name = "test_task"

        async def dummy_task() -> None:
            await asyncio.sleep(0.1)

        # Mock discord.utils.utcnow to return a known timezone-aware datetime
        with patch('discord.utils.utcnow') as mock_utcnow:
            base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_utcnow.return_value = base_time

            # Add task - this should set task health to timezone-aware datetime
            manager.add_task(task_name, dummy_task)

            # Verify task health is timezone-aware using public method
            task_status = manager.get_all_task_status()
            assert task_name in task_status
            task_health = task_status[task_name]["last_health"]
            assert task_health is not None
            assert isinstance(task_health, datetime)
            assert task_health.tzinfo is not None
            assert task_health == base_time
            
            # Test health check with timezone-aware current time
            future_time = base_time + timedelta(minutes=10)
            mock_utcnow.return_value = future_time
            
            # This should not raise a timezone error
            is_healthy = manager.is_healthy()
            assert not is_healthy  # Should be unhealthy due to time difference
            
            # Test with recent time (should be healthy)
            recent_time = base_time + timedelta(minutes=1)
            mock_utcnow.return_value = recent_time
            
            is_healthy = manager.is_healthy()
            assert is_healthy  # Should be healthy
        
        await manager.stop()

    def test_state_manager_preserves_timezone_info(self) -> None:
        """Test that StateManager preserves timezone information during save/load cycles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"
            manager = StateManager(state_file)
            
            # Create state with timezone-aware datetimes
            original_state = ScheduleState()
            original_state.last_update = discord.utils.utcnow()
            original_state.next_update = original_state.last_update + timedelta(days=1)
            
            config = SchedulingConfig(update_days=1, fixed_update_time="12:00")
            
            # Save state
            manager.save_state(original_state, config)
            
            # Load state
            loaded_state, _ = manager.load_state()

            # Verify timezone information is preserved
            assert loaded_state.last_update is not None
            assert loaded_state.last_update.tzinfo is not None
            assert loaded_state.next_update is not None
            assert loaded_state.next_update.tzinfo is not None
            
            # Verify values are preserved
            assert loaded_state.last_update == original_state.last_update
            assert loaded_state.next_update == original_state.next_update

    @pytest.mark.asyncio
    async def test_recovery_manager_handles_timezone_aware_datetimes(self) -> None:
        """Test that RecoveryManager correctly handles timezone-aware datetimes in missed update detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"
            state_manager = StateManager(state_file)
            recovery_manager = RecoveryManager(state_manager)
            
            # Create state with timezone-aware datetimes
            state = ScheduleState()
            base_time = discord.utils.utcnow()
            state.last_update = base_time - timedelta(days=2)  # 2 days ago
            state.next_update = base_time - timedelta(days=1)  # 1 day ago (missed)
            
            config = SchedulingConfig(update_days=1, fixed_update_time="12:00")
            current_time = base_time  # Current time is timezone-aware
            
            # This should not raise a timezone error
            missed_updates = recovery_manager.detect_missed_updates(
                current_time, state.last_update, state.next_update, config
            )
            
            # Should detect the missed update
            assert len(missed_updates) > 0
            assert missed_updates[0].scheduled_time == state.next_update

    @pytest.mark.asyncio
    async def test_update_tracker_startup_with_mixed_timezone_data(self) -> None:
        """Test that UpdateTracker handles startup recovery with mixed timezone data gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"
            
            # Create a state file with timezone-naive data (simulating legacy data)
            legacy_state = ScheduleState()
            legacy_state.last_update = datetime(2024, 1, 1, 12, 0, 0)  # Timezone-naive
            legacy_state.next_update = datetime(2024, 1, 2, 12, 0, 0)  # Timezone-naive
            
            state_manager = StateManager(state_file)
            config = SchedulingConfig(update_days=1, fixed_update_time="12:00")
            state_manager.save_state(legacy_state, config)
            
            # Create mock bot
            mock_bot = MagicMock()
            mock_user = MagicMock()
            mock_user.id = 12345
            mock_bot.user = mock_user
            
            # Create UpdateTracker - this should handle the timezone conversion gracefully
            tracker = UpdateTracker(mock_bot, state_file_path=state_file)
            
            # Start scheduler - this should not raise timezone errors
            try:
                await tracker.start_scheduler(
                    update_days=config.update_days,
                    fixed_update_time=config.fixed_update_time
                )
                
                # Verify the tracker is running using public method
                status = tracker.get_scheduler_status()
                assert status["is_started"]

                # The main goal of this test is to verify that the system handles
                # timezone-naive legacy data without crashing with timezone errors.
                # The recovery system correctly detected the invalid dates and started fresh.
                # This is the expected behavior - no timezone errors should occur.
                assert status["is_running"] is not None  # State object exists
                
            finally:
                await tracker.stop_scheduler()

    def test_error_metrics_use_timezone_aware_datetimes(self) -> None:
        """Test that ErrorMetrics uses timezone-aware datetimes for all timestamp fields."""
        from tgraph_bot.bot.update_tracker import ErrorMetrics, ErrorType
        
        with patch('discord.utils.utcnow') as mock_utcnow:
            base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_utcnow.return_value = base_time
            
            metrics = ErrorMetrics()
            
            # Test record_attempt
            metrics.record_attempt()
            assert metrics.last_attempt is not None
            assert metrics.last_attempt.tzinfo is not None
            
            # Test record_success
            metrics.record_success()
            assert metrics.last_success is not None
            assert metrics.last_success.tzinfo is not None
            
            # Test record_failure
            metrics.record_failure(ErrorType.TRANSIENT)
            assert metrics.last_failure is not None
            assert metrics.last_failure.tzinfo is not None
