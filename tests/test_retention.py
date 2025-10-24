"""Tests for data retention manager.

This test suite validates the data retention functionality including:
- File age checking based on keep_days configuration
- Deletion of old graph files (PNG files)
- Tracking and logging of deleted file count and bytes reclaimed
- Daily cleanup scheduling at midnight
- Graceful error handling for file deletion failures

Requirements tested: 12.1, 12.2, 12.3, 12.4, 12.5
"""

# pyright: reportPrivateUsage=false, reportAny=false, reportUnusedVariable=false

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from datetime import datetime as real_datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from tgraph_bot.utils.retention import CleanupResult, DataRetentionManager


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Fixture providing a temporary output directory for graph files."""
    output_dir = tmp_path / "graphs"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def retention_manager(temp_output_dir: Path) -> DataRetentionManager:
    """Fixture providing a DataRetentionManager with default settings."""
    return DataRetentionManager(
        output_dir=temp_output_dir,
        keep_days=7,
    )


def create_test_file(
    output_dir: Path,
    filename: str,
    *,
    age_days: int = 0,
    size_bytes: int = 1024,
) -> Path:
    """Create a test PNG file with specific age and size.

    Args:
        output_dir: Directory to create the file in
        filename: Name of the file to create
        age_days: Number of days in the past to set modification time
        size_bytes: Size of the file in bytes

    Returns:
        Path to the created file
    """
    file_path = output_dir / filename
    _ = file_path.write_bytes(b"0" * size_bytes)

    # Set modification time to simulate file age
    if age_days > 0:
        old_time = datetime.now() - timedelta(days=age_days)
        timestamp = old_time.timestamp()
        # Use os.utime to set both access and modification times
        import os

        os.utime(file_path, (timestamp, timestamp))

    return file_path


class TestDataRetentionManagerInitialization:
    """Tests for DataRetentionManager initialization.

    Requirements tested: 12.1
    """

    def test_initialization_valid_keep_days(self, temp_output_dir: Path) -> None:
        """Test initialization with valid keep_days value."""
        manager = DataRetentionManager(
            output_dir=temp_output_dir,
            keep_days=30,
        )
        assert manager.output_dir == temp_output_dir
        assert manager.keep_days == 30
        assert manager._task is None

    def test_initialization_creates_output_directory(self, tmp_path: Path) -> None:
        """Test that initialization creates output directory if it doesn't exist."""
        non_existent_dir = tmp_path / "graphs" / "nested"
        manager = DataRetentionManager(
            output_dir=non_existent_dir,
            keep_days=7,
        )
        assert non_existent_dir.exists()
        assert non_existent_dir.is_dir()

    @pytest.mark.parametrize(
        "invalid_days",
        [0, -1, 366, 1000],
    )
    def test_initialization_invalid_keep_days(
        self, temp_output_dir: Path, invalid_days: int
    ) -> None:
        """Test initialization fails with invalid keep_days values."""
        with pytest.raises(ValueError, match="keep_days must be between 1 and 365"):
            _ = DataRetentionManager(
                output_dir=temp_output_dir,
                keep_days=invalid_days,
            )

    @pytest.mark.parametrize(
        "valid_days",
        [1, 7, 30, 90, 180, 365],
    )
    def test_initialization_valid_range(
        self, temp_output_dir: Path, valid_days: int
    ) -> None:
        """Test initialization succeeds with valid keep_days range."""
        manager = DataRetentionManager(
            output_dir=temp_output_dir,
            keep_days=valid_days,
        )
        assert manager.keep_days == valid_days


class TestCleanupOldFiles:
    """Tests for cleanup_old_files method.

    Requirements tested: 12.1, 12.2, 12.3, 12.5
    """

    @pytest.mark.asyncio
    async def test_cleanup_no_files(self, retention_manager: DataRetentionManager) -> None:
        """Test cleanup when output directory is empty."""
        result = await retention_manager.cleanup_old_files()

        assert result.files_deleted == 0
        assert result.bytes_reclaimed == 0
        assert result.errors == 0

    @pytest.mark.asyncio
    async def test_cleanup_only_new_files(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test cleanup when all files are within retention period."""
        # Create files that are new (within 7-day retention)
        _ = create_test_file(retention_manager.output_dir, "graph1.png", age_days=1)
        _ = create_test_file(retention_manager.output_dir, "graph2.png", age_days=3)
        _ = create_test_file(retention_manager.output_dir, "graph3.png", age_days=6)

        result = await retention_manager.cleanup_old_files()

        assert result.files_deleted == 0
        assert result.bytes_reclaimed == 0
        assert result.errors == 0

    @pytest.mark.asyncio
    async def test_cleanup_only_old_files(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test cleanup when all files exceed retention period."""
        # Create files that are old (beyond 7-day retention)
        _ = create_test_file(
            retention_manager.output_dir, "old_graph1.png", age_days=8, size_bytes=2048
        )
        _ = create_test_file(
            retention_manager.output_dir, "old_graph2.png", age_days=10, size_bytes=3072
        )
        _ = create_test_file(
            retention_manager.output_dir, "old_graph3.png", age_days=30, size_bytes=1024
        )

        result = await retention_manager.cleanup_old_files()

        assert result.files_deleted == 3
        assert result.bytes_reclaimed == 2048 + 3072 + 1024
        assert result.errors == 0

        # Verify files were actually deleted
        remaining_files = list(retention_manager.output_dir.glob("*.png"))
        assert len(remaining_files) == 0

    @pytest.mark.asyncio
    async def test_cleanup_mixed_files(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test cleanup with mix of old and new files."""
        # Create new files (within retention period)
        _ = create_test_file(
            retention_manager.output_dir, "new_graph1.png", age_days=1, size_bytes=1024
        )
        _ = create_test_file(
            retention_manager.output_dir, "new_graph2.png", age_days=5, size_bytes=2048
        )

        # Create old files (beyond retention period)
        _ = create_test_file(
            retention_manager.output_dir, "old_graph1.png", age_days=8, size_bytes=3072
        )
        _ = create_test_file(
            retention_manager.output_dir, "old_graph2.png", age_days=15, size_bytes=4096
        )

        result = await retention_manager.cleanup_old_files()

        assert result.files_deleted == 2
        assert result.bytes_reclaimed == 3072 + 4096
        assert result.errors == 0

        # Verify only new files remain
        remaining_files = sorted(
            [f.name for f in retention_manager.output_dir.glob("*.png")]
        )
        assert remaining_files == ["new_graph1.png", "new_graph2.png"]

    @pytest.mark.asyncio
    async def test_cleanup_ignores_non_png_files(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test cleanup only processes PNG files, ignoring other formats."""
        # Create old PNG files
        _ = create_test_file(
            retention_manager.output_dir, "old_graph.png", age_days=10, size_bytes=1024
        )

        # Create old non-PNG files (should be ignored)
        old_txt_file = retention_manager.output_dir / "old_file.txt"
        _ = old_txt_file.write_text("test data")
        import os

        old_time = (datetime.now() - timedelta(days=10)).timestamp()
        _ = os.utime(old_txt_file, (old_time, old_time))

        old_jpg_file = retention_manager.output_dir / "old_image.jpg"
        _ = old_jpg_file.write_bytes(b"image data")
        _ = os.utime(old_jpg_file, (old_time, old_time))

        result = await retention_manager.cleanup_old_files()

        # Should only delete PNG files
        assert result.files_deleted == 1
        assert result.bytes_reclaimed == 1024
        assert result.errors == 0

        # Verify non-PNG files remain
        assert old_txt_file.exists()
        assert old_jpg_file.exists()
        assert not (retention_manager.output_dir / "old_graph.png").exists()

    @pytest.mark.asyncio
    async def test_cleanup_exact_retention_boundary(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test cleanup behavior at exact retention boundary."""
        # Create file exactly at retention period (7 days)
        # Files at or beyond the cutoff are deleted
        _ = create_test_file(
            retention_manager.output_dir,
            "boundary_graph.png",
            age_days=7,
            size_bytes=1024,
        )

        # Create file just beyond retention period (7 days + 1 hour)
        old_file = retention_manager.output_dir / "just_old.png"
        _ = old_file.write_bytes(b"0" * 2048)
        old_time = datetime.now() - timedelta(days=7, hours=1)
        import os

        _ = os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))

        # Create file within retention period (6 days)
        new_file = create_test_file(
            retention_manager.output_dir,
            "new_graph.png",
            age_days=6,
            size_bytes=512,
        )

        result = await retention_manager.cleanup_old_files()

        # Files at or beyond the boundary should be deleted
        assert result.files_deleted == 2
        assert result.bytes_reclaimed == 1024 + 2048
        assert not (retention_manager.output_dir / "boundary_graph.png").exists()
        assert not old_file.exists()
        assert new_file.exists()

    @pytest.mark.asyncio
    async def test_cleanup_tracks_bytes_correctly(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test that cleanup accurately tracks bytes reclaimed."""
        # Create old files with specific sizes
        sizes = [1024, 2048, 4096, 8192, 16384]
        for i, size in enumerate(sizes):
            _ = create_test_file(
                retention_manager.output_dir,
                f"old_graph_{i}.png",
                age_days=10,
                size_bytes=size,
            )

        result = await retention_manager.cleanup_old_files()

        assert result.files_deleted == len(sizes)
        assert result.bytes_reclaimed == sum(sizes)
        assert result.errors == 0

    @pytest.mark.asyncio
    async def test_cleanup_handles_file_deletion_error(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test cleanup handles file deletion errors gracefully and continues."""
        # Create old files
        file1 = create_test_file(
            retention_manager.output_dir, "graph1.png", age_days=10, size_bytes=1024
        )
        file2 = create_test_file(
            retention_manager.output_dir, "graph2.png", age_days=10, size_bytes=2048
        )
        file3 = create_test_file(
            retention_manager.output_dir, "graph3.png", age_days=10, size_bytes=3072
        )

        # Mock file2.unlink() to raise an error
        original_unlink = Path.unlink

        def mock_unlink(self: Path, missing_ok: bool = False) -> None:
            if self.name == "graph2.png":
                raise OSError("Permission denied")
            original_unlink(self, missing_ok=missing_ok)

        with patch.object(Path, "unlink", mock_unlink):
            result = await retention_manager.cleanup_old_files()

        # Should delete files 1 and 3, but fail on file 2
        assert result.files_deleted == 2
        assert result.bytes_reclaimed == 1024 + 3072
        assert result.errors == 1

        # File 2 should still exist due to error
        assert file2.exists()
        assert not file1.exists()
        assert not file3.exists()

    @pytest.mark.asyncio
    async def test_cleanup_handles_directory_list_error(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test cleanup handles directory listing errors."""
        # Mock glob to raise an error
        with patch.object(Path, "glob", side_effect=OSError("Access denied")):
            result = await retention_manager.cleanup_old_files()

        assert result.files_deleted == 0
        assert result.bytes_reclaimed == 0
        assert result.errors == 1

    @pytest.mark.asyncio
    async def test_cleanup_different_retention_periods(
        self, temp_output_dir: Path
    ) -> None:
        """Test cleanup with different retention periods."""
        # Create files of various ages
        _ = create_test_file(temp_output_dir, "file_1day.png", age_days=1)
        _ = create_test_file(temp_output_dir, "file_5days.png", age_days=5)
        _ = create_test_file(temp_output_dir, "file_10days.png", age_days=10)
        _ = create_test_file(temp_output_dir, "file_30days.png", age_days=30)
        _ = create_test_file(temp_output_dir, "file_60days.png", age_days=60)

        # Test with 7-day retention
        manager_7days = DataRetentionManager(output_dir=temp_output_dir, keep_days=7)
        result = await manager_7days.cleanup_old_files()
        assert result.files_deleted == 3  # 10, 30, 60 days old

        # Recreate all files
        for f in temp_output_dir.glob("*.png"):
            f.unlink()
        _ = create_test_file(temp_output_dir, "file_1day.png", age_days=1)
        _ = create_test_file(temp_output_dir, "file_5days.png", age_days=5)
        _ = create_test_file(temp_output_dir, "file_10days.png", age_days=10)
        _ = create_test_file(temp_output_dir, "file_30days.png", age_days=30)
        _ = create_test_file(temp_output_dir, "file_60days.png", age_days=60)

        # Test with 15-day retention
        manager_15days = DataRetentionManager(output_dir=temp_output_dir, keep_days=15)
        result = await manager_15days.cleanup_old_files()
        assert result.files_deleted == 2  # 30, 60 days old


class TestScheduledCleanup:
    """Tests for scheduled daily cleanup at midnight.

    Requirements tested: 12.4
    """

    @pytest.mark.asyncio
    async def test_schedule_daily_cleanup_calculates_next_midnight(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test that scheduler correctly calculates next midnight."""
        with patch("tgraph_bot.utils.retention.datetime") as mock_datetime:
            # Mock current time: 10:00 AM on Jan 15
            mock_now = datetime(2024, 1, 15, 10, 0, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = real_datetime

            # Mock asyncio.sleep to capture the sleep duration
            sleep_duration = None

            async def mock_sleep(seconds: float) -> None:
                nonlocal sleep_duration
                sleep_duration = seconds
                # Raise exception to break the infinite loop
                raise asyncio.CancelledError

            with patch("asyncio.sleep", side_effect=mock_sleep):
                try:
                    await retention_manager.schedule_daily_cleanup()
                except asyncio.CancelledError:
                    pass

            # Should sleep until midnight tomorrow (14 hours from 10 AM)
            expected_seconds = 14 * 3600  # 14 hours in seconds
            assert sleep_duration is not None
            assert abs(sleep_duration - expected_seconds) < 1  # Allow 1 second tolerance

    @pytest.mark.asyncio
    async def test_schedule_daily_cleanup_runs_cleanup(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test that scheduled cleanup actually runs cleanup_old_files."""
        cleanup_called = False

        async def mock_cleanup(_self: DataRetentionManager) -> CleanupResult:
            nonlocal cleanup_called
            cleanup_called = True
            # Break the loop after first cleanup
            raise asyncio.CancelledError

        # Mock sleep to return immediately
        with patch("tgraph_bot.utils.retention.DataRetentionManager.cleanup_old_files", new=mock_cleanup):
            with patch("asyncio.sleep", side_effect=AsyncMock()):
                try:
                    await retention_manager.schedule_daily_cleanup()
                except asyncio.CancelledError:
                    pass

        assert cleanup_called

    @pytest.mark.asyncio
    async def test_schedule_daily_cleanup_handles_cleanup_error(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test that scheduler handles cleanup errors gracefully."""
        cleanup_count = 0

        async def mock_cleanup_with_error(_self: DataRetentionManager) -> CleanupResult:
            nonlocal cleanup_count
            cleanup_count += 1
            if cleanup_count == 1:
                # First call raises an error
                raise RuntimeError("Unexpected cleanup error")
            # Second call succeeds and breaks the loop
            raise asyncio.CancelledError

        # Mock sleep to return immediately
        with patch("tgraph_bot.utils.retention.DataRetentionManager.cleanup_old_files", new=mock_cleanup_with_error):
            with patch("asyncio.sleep", side_effect=AsyncMock()):
                try:
                    await retention_manager.schedule_daily_cleanup()
                except asyncio.CancelledError:
                    pass

        # Should have attempted cleanup twice (once with error, once to break loop)
        assert cleanup_count == 2

    @pytest.mark.asyncio
    async def test_start_creates_background_task(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test that start() creates a background task."""
        assert retention_manager._task is None

        # Mock schedule_daily_cleanup to avoid infinite loop
        async def mock_schedule(_self: DataRetentionManager) -> None:
            await asyncio.sleep(0.1)

        with patch("tgraph_bot.utils.retention.DataRetentionManager.schedule_daily_cleanup", new=mock_schedule):
            await retention_manager.start()

            assert retention_manager._task is not None
            assert isinstance(retention_manager._task, asyncio.Task)

            # Clean up
            await retention_manager.stop()

    @pytest.mark.asyncio
    async def test_start_does_not_create_duplicate_tasks(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test that calling start() multiple times doesn't create duplicate tasks."""
        # Mock schedule_daily_cleanup to avoid infinite loop
        async def mock_schedule(_self: DataRetentionManager) -> None:
            await asyncio.sleep(0.1)

        with patch("tgraph_bot.utils.retention.DataRetentionManager.schedule_daily_cleanup", new=mock_schedule):
            await retention_manager.start()
            first_task = retention_manager._task

            await retention_manager.start()  # Call again
            second_task = retention_manager._task

            # Should be the same task
            assert first_task is second_task

            # Clean up
            await retention_manager.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test that stop() cancels the background task."""
        # Mock schedule_daily_cleanup to avoid infinite loop
        async def mock_schedule(_self: DataRetentionManager) -> None:
            await asyncio.sleep(10)  # Long sleep

        with patch("tgraph_bot.utils.retention.DataRetentionManager.schedule_daily_cleanup", new=mock_schedule):
            await retention_manager.start()
            assert retention_manager._task is not None

            await retention_manager.stop()

            assert retention_manager._task is None

    @pytest.mark.asyncio
    async def test_stop_without_start(
        self, retention_manager: DataRetentionManager
    ) -> None:
        """Test that stop() handles case where task was never started."""
        assert retention_manager._task is None

        # Should not raise an error
        await retention_manager.stop()

        assert retention_manager._task is None
