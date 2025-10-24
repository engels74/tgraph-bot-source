"""Data retention manager for automatic graph file cleanup.

This module provides functionality to automatically clean up old graph files
based on a configured retention period, helping manage disk space usage.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from tgraph_bot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class CleanupResult:
    """Result of a cleanup operation.

    Attributes:
        files_deleted: Number of files deleted
        bytes_reclaimed: Total bytes reclaimed from deleted files
        errors: Number of files that failed to delete
    """

    files_deleted: int
    bytes_reclaimed: int
    errors: int


@dataclass(slots=True)
class DataRetentionManager:
    """Manages automatic cleanup of old graph files.

    This class handles the identification and deletion of graph files that
    exceed the configured retention period, running daily cleanup at midnight.

    Attributes:
        output_dir: Directory containing graph files to manage
        keep_days: Number of days to retain graph files (1-365)

    Requirements: 12.1, 12.2, 12.3, 12.4, 12.5

    Examples:
        >>> manager = DataRetentionManager(
        ...     output_dir=Path("/data/graphs"),
        ...     keep_days=30
        ... )
        >>> result = await manager.cleanup_old_files()
        >>> print(f"Deleted {result.files_deleted} files")
    """

    output_dir: Path
    keep_days: int
    _task: asyncio.Task[None] | None = None

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not 1 <= self.keep_days <= 365:
            msg = f"keep_days must be between 1 and 365, got {self.keep_days}"
            raise ValueError(msg)

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def cleanup_old_files(self) -> CleanupResult:
        """Remove graph files older than the retention period.

        Identifies all PNG files in the output directory that are older than
        the configured retention period and deletes them. Tracks the number
        of files deleted and disk space reclaimed.

        Returns:
            CleanupResult with deletion statistics

        Requirements: 12.1, 12.2, 12.3, 12.5

        Examples:
            >>> manager = DataRetentionManager(Path("/data/graphs"), keep_days=7)
            >>> result = await manager.cleanup_old_files()
            >>> print(f"Reclaimed {result.bytes_reclaimed} bytes")
        """
        cutoff_time = datetime.now() - timedelta(days=self.keep_days)
        deleted_count = 0
        deleted_bytes = 0
        error_count = 0

        logger.info(
            (
                f"Starting cleanup: removing files older than {self.keep_days} days"
                f" (cutoff: {cutoff_time.isoformat()})"
            )
        )

        # Find all PNG files in the output directory
        try:
            png_files = list(self.output_dir.glob("*.png"))
        except OSError as e:
            logger.error(
                f"Failed to list files in {self.output_dir}: {e}", exc_info=True
            )
            return CleanupResult(
                files_deleted=0, bytes_reclaimed=0, errors=1
            )

        for file_path in png_files:
            try:
                # Get file modification time
                file_stat = file_path.stat()
                file_mtime = datetime.fromtimestamp(file_stat.st_mtime)

                # Check if file is older than retention period
                # Use <= to include files at exactly the cutoff time
                if file_mtime <= cutoff_time:
                    file_size = file_stat.st_size

                    # Delete the file
                    file_path.unlink()

                    deleted_count += 1
                    deleted_bytes += file_size

                    logger.debug(
                        (
                            f"Deleted old file: {file_path.name}"
                            f" (age: {(datetime.now() - file_mtime).days} days,"
                            f" size: {file_size} bytes)"
                        )
                    )

            except OSError as e:
                # Log error but continue with remaining files
                error_count += 1
                logger.error(
                    f"Failed to delete file {file_path.name}: {e}", exc_info=True
                )
                continue

        # Log cleanup summary
        result = CleanupResult(
            files_deleted=deleted_count,
            bytes_reclaimed=deleted_bytes,
            errors=error_count,
        )

        if deleted_count > 0 or error_count > 0:
            logger.info(
                (
                    f"Cleanup completed: deleted {deleted_count} files,"
                    f" reclaimed {deleted_bytes:,} bytes"
                    f" ({deleted_bytes / 1024 / 1024:.2f} MB),"
                    f" {error_count} errors"
                )
            )
        else:
            logger.debug("Cleanup completed: no files to delete")

        return result

    async def schedule_daily_cleanup(self) -> None:
        """Run cleanup daily at midnight local time.

        This method runs in an infinite loop, calculating the time until the
        next midnight and sleeping until then before triggering cleanup.

        Requirements: 12.4

        Examples:
            >>> manager = DataRetentionManager(Path("/data/graphs"), keep_days=7)
            >>> await manager.schedule_daily_cleanup()  # Runs forever
        """
        logger.info("Starting daily cleanup scheduler (runs at midnight)")

        while True:
            # Calculate time until next midnight
            now = datetime.now()
            tomorrow_midnight = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            sleep_seconds = (tomorrow_midnight - now).total_seconds()

            logger.debug(
                (
                    f"Next cleanup scheduled for {tomorrow_midnight.isoformat()}"
                    f" (in {sleep_seconds / 3600:.2f} hours)"
                )
            )

            # Sleep until midnight
            await asyncio.sleep(sleep_seconds)

            # Perform cleanup
            logger.info("Triggering scheduled cleanup at midnight")
            try:
                result = await self.cleanup_old_files()

                if result.errors > 0:
                    logger.warning(f"Scheduled cleanup had {result.errors} errors")
            except Exception as e:
                logger.error(
                    f"Scheduled cleanup failed with unexpected error: {e}",
                    exc_info=True,
                )

    async def start(self) -> None:
        """Start the scheduled cleanup task.

        Creates and starts a background task that runs daily cleanup at midnight.
        The task continues until explicitly stopped.

        Examples:
            >>> manager = DataRetentionManager(Path("/data/graphs"), keep_days=7)
            >>> await manager.start()
        """
        if self._task is not None:
            logger.warning("Cleanup scheduler already running")
            return

        self._task = asyncio.create_task(self.schedule_daily_cleanup())
        logger.info("Cleanup scheduler started")

    async def stop(self) -> None:
        """Stop the scheduled cleanup task.

        Cancels the background cleanup task and waits for it to complete.
        Handles cancellation gracefully.

        Examples:
            >>> manager = DataRetentionManager(Path("/data/graphs"), keep_days=7)
            >>> await manager.start()
            >>> # ... later ...
            >>> await manager.stop()
        """
        if self._task is None:
            logger.warning("Cleanup scheduler not running")
            return

        logger.info("Stopping cleanup scheduler")
        _ = self._task.cancel()

        try:
            await self._task
        except asyncio.CancelledError:
            logger.info("Cleanup scheduler stopped")

        self._task = None
