"""
Tests for the scheduler next_update field bug.

This test file demonstrates and verifies the fix for the bug where
the next_update field in scheduler_state.json is not being updated
correctly after a successful scheduled update execution.

Bug Description:
- After successful update, last_update is correctly updated
- But next_update still points to the just-executed time instead of the next future time
- This causes the state file to show incorrect next_update values
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from pathlib import Path

from src.tgraph_bot.bot.update_tracker import UpdateTracker
from src.tgraph_bot.bot.scheduling.types import SchedulingConfig, ScheduleState
from src.tgraph_bot.bot.scheduling.persistence import StateManager
from src.tgraph_bot.bot.scheduling.schedule import UpdateSchedule
from src.tgraph_bot.utils.time import get_system_timezone
from tests.utils.test_helpers import create_mock_discord_bot


class TestNextUpdateBugFix:
    """Test the specific bug where next_update field is not updated after successful execution."""

    @pytest.fixture
    def mock_bot(self) -> AsyncMock:
        """Create a mock Discord bot."""
        return create_mock_discord_bot()  # pyright: ignore[reportReturnType]

    @pytest.fixture
    def temp_state_file(self, tmp_path: Path) -> Path:
        """Create a temporary state file path."""
        return tmp_path / "test_scheduler_state.json"

    @pytest.fixture
    def update_tracker(
        self, mock_bot: AsyncMock, temp_state_file: Path
    ) -> UpdateTracker:
        """Create an UpdateTracker with temporary state file."""
        tracker = UpdateTracker(mock_bot, state_file_path=temp_state_file)
        tracker.disable_recovery()  # Disable recovery for cleaner testing
        return tracker

    @pytest.mark.asyncio
    async def test_next_update_field_updated_after_successful_interval_based_update(
        self, update_tracker: UpdateTracker, temp_state_file: Path
    ) -> None:
        """
        Test that next_update field is correctly updated after successful interval-based update.

        This test demonstrates the bug:
        1. Set up a scheduled update time
        2. Execute the update successfully
        3. Verify that next_update points to the NEXT future time, not the just-executed time
        """
        # Arrange: Set up update callback
        update_callback = AsyncMock()
        update_tracker.set_update_callback(update_callback)

        # Arrange: Create initial state with specific times
        base_time = datetime(2025, 7, 27, 0, 5, 0, tzinfo=get_system_timezone())

        # Set up the state as if we're about to execute an update
        config = SchedulingConfig(
            update_days=1, fixed_update_time="XX:XX"
        )  # Daily interval
        state = ScheduleState()
        state.last_update = base_time - timedelta(
            days=1
        )  # Previous update was 1 day ago
        state.next_update = base_time  # We're about to execute this update

        # Manually set the internal state for testing
        update_tracker._config = config  # pyright: ignore[reportPrivateUsage]
        update_tracker._state = state  # pyright: ignore[reportPrivateUsage]

        # Create the schedule object

        update_tracker._schedule = UpdateSchedule(config, state)  # pyright: ignore[reportPrivateUsage]

        # Act: Trigger the update (this simulates what happens in the scheduler loop)
        await update_tracker._trigger_update_for_testing()  # pyright: ignore[reportPrivateUsage]

        # Assert: Verify the callback was called
        update_callback.assert_called_once()

        # Assert: Verify last_update was updated to execution time
        current_state = update_tracker._get_state_for_testing()  # pyright: ignore[reportPrivateUsage]
        assert current_state.last_update is not None
        assert (
            current_state.last_update >= base_time
        )  # Should be at or after the scheduled time

        # Assert: Verify next_update was updated to the NEXT future time
        # This is the key assertion that will FAIL before the fix
        assert current_state.next_update is not None
        assert (
            current_state.next_update > base_time
        )  # Should be AFTER the just-executed time

        # For daily interval, next update should be ~1 day later
        expected_next_update = base_time + timedelta(days=1)
        time_diff = abs(
            (current_state.next_update - expected_next_update).total_seconds()
        )
        assert time_diff < 60  # Within 1 minute tolerance

        # Assert: Verify state persistence if recovery is enabled
        if update_tracker.is_recovery_enabled():
            # Save and reload state to verify persistence
            state_manager = StateManager(temp_state_file)
            state_manager.save_state(current_state, config)

            loaded_state, _ = state_manager.load_state()
            assert loaded_state.next_update == current_state.next_update

    @pytest.mark.asyncio
    async def test_next_update_field_updated_after_successful_fixed_time_update(
        self,
        update_tracker: UpdateTracker,
        temp_state_file: Path,  # pyright: ignore[reportUnusedParameter]
    ) -> None:
        """
        Test that next_update field is correctly updated after successful fixed-time update.
        """
        # Arrange: Set up update callback
        update_callback = AsyncMock()
        update_tracker.set_update_callback(update_callback)

        # Arrange: Create initial state with fixed time scheduling
        base_time = datetime(
            2025, 7, 27, 14, 30, 0, tzinfo=get_system_timezone()
        )  # 2:30 PM

        # Set up the state as if we're about to execute an update
        config = SchedulingConfig(
            update_days=7, fixed_update_time="14:30"
        )  # Weekly at 2:30 PM
        state = ScheduleState()
        state.last_update = base_time - timedelta(
            days=7
        )  # Previous update was 1 week ago
        state.next_update = base_time  # We're about to execute this update

        # Manually set the internal state for testing
        update_tracker._config = config  # pyright: ignore[reportPrivateUsage]
        update_tracker._state = state  # pyright: ignore[reportPrivateUsage]

        # Create the schedule object

        update_tracker._schedule = UpdateSchedule(config, state)  # pyright: ignore[reportPrivateUsage]

        # Act: Trigger the update
        await update_tracker._trigger_update_for_testing()  # pyright: ignore[reportPrivateUsage]

        # Assert: Verify the callback was called
        update_callback.assert_called_once()

        # Assert: Verify last_update was updated
        current_state = update_tracker._get_state_for_testing()  # pyright: ignore[reportPrivateUsage]
        assert current_state.last_update is not None
        assert current_state.last_update >= base_time

        # Assert: Verify next_update was updated to the NEXT future time
        # This is the key assertion that will FAIL before the fix
        assert current_state.next_update is not None
        assert (
            current_state.next_update > base_time
        )  # Should be AFTER the just-executed time

        # For weekly fixed time, next update should be exactly 7 days later at same time
        expected_next_update = base_time + timedelta(days=7)
        assert current_state.next_update == expected_next_update
        assert current_state.next_update.time() == base_time.time()  # Same time of day

    @pytest.mark.asyncio
    async def test_state_persistence_includes_updated_next_update(
        self, update_tracker: UpdateTracker, temp_state_file: Path
    ) -> None:
        """
        Test that the state file correctly persists the updated next_update field.

        This test verifies that the bug fix persists to disk correctly.
        """
        # Arrange
        update_tracker.enable_recovery()  # Enable persistence
        update_callback = AsyncMock()
        update_tracker.set_update_callback(update_callback)

        base_time = datetime(2025, 7, 27, 10, 0, 0, tzinfo=get_system_timezone())

        config = SchedulingConfig(
            update_days=2, fixed_update_time="XX:XX"
        )  # Every 2 days
        state = ScheduleState()
        state.last_update = base_time - timedelta(days=2)
        state.next_update = base_time

        update_tracker._config = config  # pyright: ignore[reportPrivateUsage]
        update_tracker._state = state  # pyright: ignore[reportPrivateUsage]


        update_tracker._schedule = UpdateSchedule(config, state)  # pyright: ignore[reportPrivateUsage]

        # Act: Trigger update
        await update_tracker._trigger_update_for_testing()  # pyright: ignore[reportPrivateUsage]

        # Assert: Load state from file and verify next_update is correctly persisted
        state_manager = StateManager(temp_state_file)
        loaded_state, _ = state_manager.load_state()

        assert loaded_state.next_update is not None
        assert loaded_state.next_update > base_time  # Should be in the future

        # For 2-day interval, should be ~2 days later
        expected_next_update = base_time + timedelta(days=2)
        time_diff = abs(
            (loaded_state.next_update - expected_next_update).total_seconds()
        )
        assert time_diff < 60  # Within 1 minute tolerance

    @pytest.mark.asyncio
    async def test_bug_reproduction_scenario(
        self, update_tracker: UpdateTracker
    ) -> None:
        """
        Test that reproduces the exact bug scenario described in the issue.

        Scenario:
        - Bot executes scheduled update at 2025-07-27 00:05:00+02:00
        - Log shows "Next update scheduled for: 2025-07-28 00:05:00+02:00"
        - But scheduler_state.json shows next_update: "2025-07-27T00:05:00+02:00" (old time)
        """
        # Arrange: Set up the exact scenario from the bug report
        update_callback = AsyncMock()
        update_tracker.set_update_callback(update_callback)

        # Exact times from the bug report
        scheduled_time = datetime(2025, 7, 27, 0, 5, 0, tzinfo=get_system_timezone())
        expected_next_time = datetime(
            2025, 7, 28, 0, 5, 0, tzinfo=get_system_timezone()
        )

        config = SchedulingConfig(
            update_days=1, fixed_update_time="00:05"
        )  # Daily at 00:05
        state = ScheduleState()
        state.last_update = scheduled_time - timedelta(days=1)  # Previous update
        state.next_update = scheduled_time  # About to execute this update

        update_tracker._config = config  # pyright: ignore[reportPrivateUsage]
        update_tracker._state = state  # pyright: ignore[reportPrivateUsage]


        update_tracker._schedule = UpdateSchedule(config, state)  # pyright: ignore[reportPrivateUsage]

        # Act: Execute the update (simulate the scheduler loop execution)
        await update_tracker._trigger_update_for_testing()  # pyright: ignore[reportPrivateUsage]

        # Assert: Verify the bug is fixed
        final_state = update_tracker._get_state_for_testing()  # pyright: ignore[reportPrivateUsage]

        # This assertion will FAIL before the fix (demonstrating the bug)
        # After the fix, it should PASS
        assert final_state.next_update is not None
        assert final_state.next_update == expected_next_time, (
            f"Expected next_update to be {expected_next_time}, "
            f"but got {final_state.next_update}. "
            f"This indicates the bug where next_update is not updated after successful execution."
        )

    @pytest.mark.asyncio
    async def test_multiple_consecutive_updates_maintain_correct_next_update(
        self, update_tracker: UpdateTracker
    ) -> None:
        """
        Test that multiple consecutive updates maintain correct next_update values.

        This ensures the fix works correctly over multiple update cycles.
        """
        # Arrange
        update_callback = AsyncMock()
        update_tracker.set_update_callback(update_callback)

        base_time = datetime(2025, 7, 27, 12, 0, 0, tzinfo=get_system_timezone())
        config = SchedulingConfig(
            update_days=1, fixed_update_time="XX:XX"
        )  # Daily interval

        update_tracker._config = config  # pyright: ignore[reportPrivateUsage]


        # Simulate 3 consecutive updates
        current_time = base_time
        for i in range(3):
            # Set up state for this iteration
            state = ScheduleState()
            if i == 0:
                state.last_update = current_time - timedelta(days=1)
            else:
                state.last_update = current_time
            state.next_update = current_time

            update_tracker._state = state  # pyright: ignore[reportPrivateUsage]
            update_tracker._schedule = UpdateSchedule(config, state)  # pyright: ignore[reportPrivateUsage]

            # Execute update
            await update_tracker._trigger_update_for_testing()  # pyright: ignore[reportPrivateUsage]

            # Verify next_update is correctly set
            updated_state = update_tracker._get_state_for_testing()  # pyright: ignore[reportPrivateUsage]
            expected_next = current_time + timedelta(days=1)

            assert updated_state.next_update is not None
            time_diff = abs((updated_state.next_update - expected_next).total_seconds())
            assert time_diff < 60, (
                f"Update {i + 1}: next_update not correctly calculated"
            )

            # Move to next day for next iteration
            current_time += timedelta(days=1)

        # Verify callback was called for each update
        assert update_callback.call_count == 3
