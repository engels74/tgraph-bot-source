"""
Test recovery and schedule integrity mechanisms for UpdateTracker.

This module tests the enhanced recovery capabilities, persistent state management,
missed update detection, and schedule integrity validation and repair.
"""

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.update_tracker import (
    UpdateTracker,
    ScheduleState,
    SchedulingConfig,
    StateManager,
    RecoveryManager,
)


class TestStateManager:
    """Test the StateManager class for persistent state storage."""
    
    def test_state_manager_initialization(self) -> None:
        """Test StateManager initialization with default and custom paths."""
        # Test with default path
        manager = StateManager()
        assert manager.state_file_path.name == "scheduler_state.json"
        assert "data" in str(manager.state_file_path)
        
        # Test with custom path
        custom_path = Path("/tmp/test_state.json")
        manager = StateManager(custom_path)
        assert manager.state_file_path == custom_path
    
    def test_save_and_load_state(self) -> None:
        """Test saving and loading scheduler state."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"
            manager = StateManager(state_file)
            
            # Create test state and config
            state = ScheduleState()
            state.last_update = datetime(2024, 1, 1, 12, 0, 0)
            state.next_update = datetime(2024, 1, 8, 12, 0, 0)
            state.consecutive_failures = 2
            state.last_failure = datetime(2024, 1, 7, 12, 0, 0)
            
            config = SchedulingConfig(update_days=7, fixed_update_time="12:00")
            
            # Save state
            manager.save_state(state, config)
            assert state_file.exists()
            
            # Load state
            loaded_state, loaded_config = manager.load_state()
            
            # Verify loaded state
            assert loaded_state.last_update == state.last_update
            assert loaded_state.next_update == state.next_update
            assert loaded_state.consecutive_failures == state.consecutive_failures
            assert loaded_state.last_failure == state.last_failure
            
            # Verify loaded config
            assert loaded_config is not None
            assert loaded_config.update_days == config.update_days
            assert loaded_config.fixed_update_time == config.fixed_update_time
    
    def test_load_nonexistent_state(self) -> None:
        """Test loading state when no file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "nonexistent.json"
            manager = StateManager(state_file)
            
            state, config = manager.load_state()
            
            # Should return default state
            assert isinstance(state, ScheduleState)
            assert state.last_update is None
            assert state.next_update is None
            assert state.consecutive_failures == 0
            assert config is None
    
    def test_load_corrupted_state(self) -> None:
        """Test loading corrupted state file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "corrupted.json"
            manager = StateManager(state_file)
            
            # Create corrupted JSON file
            _ = state_file.write_text("{ invalid json }")
            
            state, config = manager.load_state()
            
            # Should return default state and backup corrupted file
            assert isinstance(state, ScheduleState)
            assert state.last_update is None
            assert config is None
            
            # Check that backup was created
            backup_files = list(state_file.parent.glob("*.corrupted.*.json"))
            assert len(backup_files) == 1
    
    def test_delete_state(self) -> None:
        """Test deleting state file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"
            manager = StateManager(state_file)
            
            # Create and save state
            state = ScheduleState()
            manager.save_state(state)
            assert state_file.exists()
            
            # Delete state
            manager.delete_state()
            assert not state_file.exists()


class TestRecoveryManager:
    """Test the RecoveryManager class for recovery operations."""
    
    @pytest.fixture
    def recovery_manager(self) -> RecoveryManager:
        """Create a RecoveryManager for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"
            state_manager = StateManager(state_file)
            return RecoveryManager(state_manager)
    
    def test_detect_missed_updates_no_history(self, recovery_manager: RecoveryManager) -> None:
        """Test missed update detection with no update history."""
        current_time = datetime.now()
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        
        missed_updates = recovery_manager.detect_missed_updates(
            current_time, None, None, config
        )
        
        assert len(missed_updates) == 0
    
    def test_detect_missed_scheduled_update(self, recovery_manager: RecoveryManager) -> None:
        """Test detection of missed scheduled update."""
        current_time = datetime.now()
        last_update = current_time - timedelta(days=8)
        next_update = current_time - timedelta(hours=2)  # Missed by 2 hours
        config = SchedulingConfig(update_days=7, fixed_update_time="12:00")
        
        missed_updates = recovery_manager.detect_missed_updates(
            current_time, last_update, next_update, config
        )
        
        assert len(missed_updates) == 1
        assert missed_updates[0].scheduled_time == next_update
        assert missed_updates[0].reason == "missed_scheduled_update"
    
    def test_detect_multiple_interval_missed_updates(self, recovery_manager: RecoveryManager) -> None:
        """Test detection of multiple missed interval updates."""
        current_time = datetime.now()
        last_update = current_time - timedelta(days=21)  # 3 weeks ago
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        
        missed_updates = recovery_manager.detect_missed_updates(
            current_time, last_update, None, config
        )
        
        # Should detect 2 missed intervals (at 7 and 14 days)
        assert len(missed_updates) == 2
        for update in missed_updates:
            assert update.reason == "interval_based_missed_update"
    
    def test_validate_schedule_integrity_valid(self, recovery_manager: RecoveryManager) -> None:
        """Test schedule integrity validation with valid state."""
        current_time = datetime.now()
        state = ScheduleState()
        state.last_update = current_time - timedelta(days=3)
        state.next_update = current_time + timedelta(days=4)
        state.consecutive_failures = 1
        state.last_failure = current_time - timedelta(hours=1)
        
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        
        is_valid, issues = recovery_manager.validate_schedule_integrity(
            current_time, state, config
        )
        
        assert is_valid
        assert len(issues) == 0
    
    def test_validate_schedule_integrity_invalid(self, recovery_manager: RecoveryManager) -> None:
        """Test schedule integrity validation with invalid state."""
        current_time = datetime.now()
        state = ScheduleState()
        state.next_update = current_time - timedelta(hours=1)  # In the past
        state.consecutive_failures = 15  # Excessive failures
        
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        
        is_valid, issues = recovery_manager.validate_schedule_integrity(
            current_time, state, config
        )
        
        assert not is_valid
        assert len(issues) >= 2  # Should detect multiple issues
        assert any("in the past" in issue for issue in issues)
        assert any("Excessive consecutive failures" in issue for issue in issues)
    
    def test_repair_schedule_state(self, recovery_manager: RecoveryManager) -> None:
        """Test schedule state repair functionality."""
        current_time = datetime.now()
        state = ScheduleState()
        state.next_update = current_time - timedelta(hours=1)  # In the past
        state.consecutive_failures = 10
        state.last_failure = current_time - timedelta(days=5)  # Old failure
        state.is_running = True
        
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        
        repaired_state = recovery_manager.repair_schedule_state(
            current_time, state, config
        )
        
        # Check repairs
        assert repaired_state.next_update is not None and repaired_state.next_update > current_time  # Fixed future time
        assert repaired_state.consecutive_failures == 0  # Reset old failures
        assert not repaired_state.is_running  # Cleared running state
    
    @pytest.mark.asyncio
    async def test_perform_recovery_with_callback(self, recovery_manager: RecoveryManager) -> None:
        """Test comprehensive recovery with update callback."""
        current_time = datetime.now()
        state = ScheduleState()
        state.last_update = current_time - timedelta(days=8)
        state.next_update = current_time - timedelta(hours=1)  # Missed
        
        config = SchedulingConfig(update_days=7, fixed_update_time="XX:XX")
        
        # Mock update callback
        update_callback = AsyncMock()
        
        recovered_state, processed_updates = await recovery_manager.perform_recovery(
            current_time, state, config, update_callback
        )
        
        # Should have processed the missed update
        assert len(processed_updates) == 1
        assert update_callback.call_count == 1
        assert recovered_state.last_update == current_time  # Updated after processing


class TestUpdateTrackerRecovery:
    """Test UpdateTracker recovery integration."""
    
    @pytest.mark.asyncio
    async def test_update_tracker_with_recovery_enabled(self) -> None:
        """Test UpdateTracker initialization with recovery enabled."""
        mock_bot = MagicMock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"
            
            tracker = UpdateTracker(mock_bot, state_file_path=state_file)
            
            assert tracker.is_recovery_enabled()
            assert tracker._state_manager.state_file_path == state_file  # pyright: ignore[reportPrivateUsage]
    
    @pytest.mark.asyncio
    async def test_recovery_status_reporting(self) -> None:
        """Test recovery status reporting functionality."""
        mock_bot = MagicMock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"
            
            tracker = UpdateTracker(mock_bot, state_file_path=state_file)
            
            # Test initial status
            status = tracker.get_recovery_status()
            assert status["recovery_enabled"] is True
            assert status["state_file_exists"] is False
            assert isinstance(status["state_file_path"], str) and str(state_file) in status["state_file_path"]
    
    @pytest.mark.asyncio
    async def test_clear_persistent_state(self) -> None:
        """Test clearing persistent state."""
        mock_bot = MagicMock()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"
            
            tracker = UpdateTracker(mock_bot, state_file_path=state_file)
            
            # Create some state
            tracker._state_manager.save_state(ScheduleState())  # pyright: ignore[reportPrivateUsage]
            assert state_file.exists()
            
            # Clear state
            tracker.clear_persistent_state()
            assert not state_file.exists()


if __name__ == "__main__":
    # Run a simple test to verify recovery mechanisms work
    async def main() -> None:
        test_instance = TestStateManager()
        test_instance.test_state_manager_initialization()
        test_instance.test_save_and_load_state()
        test_instance.test_load_nonexistent_state()
        test_instance.test_delete_state()
        print("✅ Recovery and schedule integrity tests passed!")

    asyncio.run(main())
