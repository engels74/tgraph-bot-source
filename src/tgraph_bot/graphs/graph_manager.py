"""
Graph manager for TGraph Bot.

This module acts as the central orchestrator for server-wide graph generation.
It uses the GraphFactory to create graph instances, fetches data via DataFetcher,
and triggers generation. Crucially, it runs the blocking Matplotlib/Seaborn graph
creation code in a separate thread using asyncio.to_thread() to prevent freezing
the bot's event loop.

Architecture:
- GraphManager: Central orchestrator for server-wide graph generation
- Coordinates with GraphFactory for graph instance creation
- Uses DataFetcher for async data retrieval from Tautulli API
- Implements asyncio.to_thread() for non-blocking CPU-bound operations
- Provides progress tracking, error handling, and resource cleanup
- Integrates with Discord for posting and message management
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Callable
from collections.abc import Mapping

from .graph_modules.data.data_fetcher import DataFetcher
from .graph_modules.core.graph_factory import GraphFactory
from .graph_modules.utils.progress_tracker import ProgressTracker
from .graph_modules.utils.utils import cleanup_old_files, get_current_graph_storage_path

if TYPE_CHECKING:
    from ..config.manager import ConfigManager

logger = logging.getLogger(__name__)


class GraphGenerationError(Exception):
    """Custom exception for graph generation errors."""

    pass


class ResourceCleanupError(Exception):
    """Custom exception for resource cleanup errors."""

    pass


# ProgressTracker is now imported from .graph_modules.progress_tracker


class GraphManager:
    """
    Central orchestrator for server-wide graph generation.

    This class coordinates the entire graph generation process:
    1. Uses DataFetcher to retrieve data from Tautulli API (async)
    2. Uses GraphFactory to create and generate graphs (sync, in thread)
    3. Manages Discord posting and cleanup operations (async)
    4. Provides progress tracking and comprehensive error handling

    All CPU-bound operations are executed in separate threads using
    asyncio.to_thread() to prevent blocking the bot's event loop.
    """

    def __init__(self, config_manager: "ConfigManager") -> None:
        """
        Initialize the graph manager with configuration.

        Args:
            config_manager: Configuration manager instance for accessing bot config
        """
        self.config_manager: "ConfigManager" = config_manager
        self._data_fetcher: DataFetcher | None = None
        self._graph_factory: GraphFactory | None = None

    async def __aenter__(self) -> "GraphManager":
        """Async context manager entry."""
        await self._initialize_components()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit with cleanup."""
        await self._cleanup_components()

    async def _initialize_components(self) -> None:
        """Initialize DataFetcher and GraphFactory components."""
        config = self.config_manager.get_current_config()

        # Initialize DataFetcher with async context manager
        self._data_fetcher = DataFetcher(
            base_url=config.TAUTULLI_URL,
            api_key=config.TAUTULLI_API_KEY,
            timeout=30.0,
            max_retries=3,
        )
        _ = await self._data_fetcher.__aenter__()

        # Initialize GraphFactory
        self._graph_factory = GraphFactory(config)

        logger.debug("GraphManager components initialized")

    async def _cleanup_components(self) -> None:
        """Clean up DataFetcher and other resources."""
        if self._data_fetcher is not None:
            await self._data_fetcher.__aexit__(None, None, None)
            self._data_fetcher = None

        self._graph_factory = None
        logger.debug("GraphManager components cleaned up")

    async def generate_all_graphs(
        self,
        progress_callback: Callable[[str, int, int, dict[str, object]], None]
        | None = None,
        max_retries: int = 3,
        timeout_seconds: float = 300.0,
    ) -> list[str]:
        """
        Generate all enabled graphs for the server with enhanced error handling and progress tracking.

        This method:
        1. Fetches data from Tautulli API (async) with retry logic
        2. Generates graphs using GraphFactory (sync, in thread) with timeout
        3. Returns list of generated graph file paths
        4. Provides detailed progress tracking with error states

        Args:
            progress_callback: Optional callback for progress updates (message, current, total, metadata)
            max_retries: Maximum number of retry attempts for failed operations
            timeout_seconds: Maximum time to wait for graph generation

        Returns:
            List of file paths to generated graph images

        Raises:
            RuntimeError: If components are not initialized
            GraphGenerationError: If graph generation fails after retries
            asyncio.TimeoutError: If generation exceeds timeout
        """
        if self._data_fetcher is None or self._graph_factory is None:
            raise RuntimeError(
                "GraphManager components not initialized. Use as async context manager."
            )

        logger.info(
            "Starting server-wide graph generation with enhanced error handling"
        )

        # Initialize progress tracker
        progress_tracker = ProgressTracker(progress_callback)

        try:
            # Step 1: Fetch data from Tautulli API with retry logic
            progress_tracker.update("Initializing data fetch from Tautulli API", 1, 4)
            config = self.config_manager.get_current_config()

            data = await self._fetch_graph_data_with_retry(
                config.TIME_RANGE_DAYS, max_retries, progress_tracker
            )

            progress_tracker.update(
                "Data fetch completed successfully", 2, 4, data_size=len(str(data))
            )

            # Step 2: Validate data before generation
            progress_tracker.update("Validating fetched data", 3, 4)
            if not self._validate_graph_data(data, progress_tracker):
                raise GraphGenerationError(
                    "Invalid or insufficient data for graph generation"
                )

            # Step 3: Generate graphs with timeout protection
            progress_tracker.update(
                "Starting graph generation in separate thread", 4, 4
            )
            logger.debug("Starting graph generation with timeout protection")

            try:
                graph_files = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._generate_graphs_sync, data, progress_tracker
                    ),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                error_msg = (
                    f"Graph generation exceeded timeout of {timeout_seconds} seconds"
                )
                progress_tracker.add_error(error_msg)
                raise asyncio.TimeoutError(error_msg)

            # Final validation
            valid_files = self._validate_generated_files(graph_files, progress_tracker)

            summary = progress_tracker.get_summary()
            logger.info(
                f"Graph generation completed: {len(valid_files)} files, "
                + f"{summary['error_count']} errors, {summary['warning_count']} warnings, "
                + f"total time: {summary['total_time']:.2f}s"
            )

            return valid_files

        except Exception as e:
            progress_tracker.add_error(f"Critical error in graph generation: {str(e)}")
            summary = progress_tracker.get_summary()
            logger.exception(
                f"Graph generation failed after {summary['total_time']:.2f}s: {e}"
            )

            if isinstance(e, (GraphGenerationError, asyncio.TimeoutError)):
                raise
            else:
                raise GraphGenerationError(
                    f"Unexpected error during graph generation: {e}"
                ) from e

    async def _fetch_graph_data(self, time_range_days: int) -> dict[str, object]:
        """
        Fetch all required data for graph generation from Tautulli API.

        Args:
            time_range_days: Number of days to fetch data for

        Returns:
            Dictionary containing all data needed for graph generation

        Raises:
            RuntimeError: If DataFetcher is not initialized
        """
        if self._data_fetcher is None:
            raise RuntimeError("DataFetcher not initialized")

        config = self.config_manager.get_current_config()
        time_range_months = config.TIME_RANGE_MONTHS

        logger.debug(
            f"Fetching graph data for {time_range_days} days and {time_range_months} months"
        )

        try:
            # Fetch play history data for all users (used by most graphs)
            play_history = await self._data_fetcher.get_play_history(
                time_range=time_range_days
            )

            # Fetch monthly play data using the native Tautulli endpoint (for monthly graphs)
            monthly_plays: Mapping[
                str, object
            ] = await self._data_fetcher.get_plays_per_month(
                time_range_months=time_range_months
            )

            data: dict[str, object] = {
                "data": play_history,
                "monthly_plays": monthly_plays,
                "time_range_days": time_range_days,
                "time_range_months": time_range_months,
            }

            logger.debug("Successfully fetched graph data from Tautulli API")
            return data

        except Exception as e:
            logger.exception(f"Error fetching graph data: {e}")
            raise

    async def _fetch_graph_data_with_retry(
        self, time_range_days: int, max_retries: int, progress_tracker: ProgressTracker
    ) -> dict[str, object]:
        """
        Fetch graph data with retry logic and exponential backoff.

        Args:
            time_range_days: Number of days to fetch data for
            max_retries: Maximum number of retry attempts
            progress_tracker: Progress tracker for error reporting

        Returns:
            Dictionary containing all data needed for graph generation

        Raises:
            GraphGenerationError: If all retry attempts fail
        """
        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = min(2.0**attempt, 30.0)  # Exponential backoff, max 30s
                    progress_tracker.add_warning(
                        f"Retrying data fetch (attempt {attempt + 1}/{max_retries + 1}) after {delay}s delay"
                    )
                    await asyncio.sleep(delay)

                return await self._fetch_graph_data(time_range_days)

            except Exception as e:
                last_exception = e
                error_msg = f"Data fetch attempt {attempt + 1} failed: {str(e)}"

                if attempt < max_retries:
                    progress_tracker.add_warning(error_msg)
                    logger.warning(error_msg)
                else:
                    progress_tracker.add_error(
                        f"All {max_retries + 1} data fetch attempts failed"
                    )
                    logger.error(f"Final data fetch attempt failed: {e}")

        # If we get here, all retries failed
        raise GraphGenerationError(
            f"Failed to fetch data after {max_retries + 1} attempts"
        ) from last_exception

    def _validate_graph_data(
        self, data: dict[str, object], progress_tracker: ProgressTracker
    ) -> bool:
        """
        Validate that the fetched data is sufficient for graph generation.

        Args:
            data: The data dictionary to validate
            progress_tracker: Progress tracker for warning/error reporting

        Returns:
            True if data is valid, False otherwise
        """
        try:
            # Check for required keys
            if "data" not in data:
                progress_tracker.add_error("Missing 'data' in data")
                return False

            if "monthly_plays" not in data:
                progress_tracker.add_error("Missing 'monthly_plays' in data")
                return False

            play_history = data["data"]
            monthly_plays = data["monthly_plays"]

            # Check if play_history has data
            if not isinstance(play_history, dict):
                progress_tracker.add_error("Play history is not a dictionary")
                return False

            # Check if monthly_plays has data
            if not isinstance(monthly_plays, dict):
                progress_tracker.add_error("Monthly plays is not a dictionary")
                return False

            # Check for data content (this depends on Tautulli API structure)
            if not play_history:
                progress_tracker.add_warning(
                    "Play history is empty - most graphs may be minimal"
                )

            if not monthly_plays:
                progress_tracker.add_warning(
                    "Monthly plays is empty - monthly graph may be minimal"
                )

            logger.debug("Data validation passed")
            return True

        except Exception as e:
            progress_tracker.add_error(f"Data validation error: {str(e)}")
            logger.exception(f"Error during data validation: {e}")
            return False

    def _validate_generated_files(
        self, graph_files: list[str], progress_tracker: ProgressTracker
    ) -> list[str]:
        """
        Validate that generated graph files exist and are accessible.

        Args:
            graph_files: List of file paths to validate
            progress_tracker: Progress tracker for warning/error reporting

        Returns:
            List of valid file paths
        """
        from pathlib import Path

        valid_files: list[str] = []

        for file_path in graph_files:
            try:
                path = Path(file_path)

                if not path.exists():
                    progress_tracker.add_error(
                        f"Generated file does not exist: {file_path}"
                    )
                    continue

                if not path.is_file():
                    progress_tracker.add_error(f"Path is not a file: {file_path}")
                    continue

                if path.stat().st_size == 0:
                    progress_tracker.add_warning(
                        f"Generated file is empty: {file_path}"
                    )
                    continue

                valid_files.append(file_path)

            except Exception as e:
                progress_tracker.add_error(
                    f"Error validating file {file_path}: {str(e)}"
                )
                logger.exception(f"File validation error for {file_path}: {e}")

        logger.debug(f"Validated {len(valid_files)}/{len(graph_files)} generated files")
        return valid_files

    def _generate_graphs_sync(
        self, data: dict[str, object], progress_tracker: ProgressTracker | None = None
    ) -> list[str]:
        """
        Synchronous graph generation (runs in separate thread).

        This method uses the existing GraphFactory.generate_all_graphs()
        method which handles resource management and cleanup properly.

        Args:
            data: Dictionary containing the data needed for graph generation
            progress_tracker: Optional progress tracker for error reporting

        Returns:
            List of file paths to generated graph images

        Raises:
            RuntimeError: If GraphFactory is not initialized
            GraphGenerationError: If graph generation fails
        """
        if self._graph_factory is None:
            raise RuntimeError("GraphFactory not initialized")

        logger.debug("Starting synchronous graph generation")

        try:
            # Ensure graph output directory exists using date-based structure
            _ = get_current_graph_storage_path()

            # Use GraphFactory to generate all enabled graphs
            # This method already handles proper resource management and cleanup
            generated_paths = self._graph_factory.generate_all_graphs(data)

            if progress_tracker:
                if not generated_paths:
                    progress_tracker.add_warning("No graphs were generated")
                else:
                    logger.debug(
                        f"Generated {len(generated_paths)} graphs synchronously"
                    )

            return generated_paths

        except Exception as e:
            error_msg = f"Error in synchronous graph generation: {e}"
            if progress_tracker:
                progress_tracker.add_error(error_msg)
            logger.exception(error_msg)
            raise GraphGenerationError(error_msg) from e

    async def post_graphs_to_discord(self, graph_files: list[str]) -> None:
        """
        Post generated graphs to the configured Discord channel.

        Args:
            graph_files: List of file paths to graph images
        """
        logger.info(f"Posting {len(graph_files)} graphs to Discord")

        try:
            # TODO: Implement Discord posting
            # This will require bot instance and channel configuration

            logger.info("Placeholder: Posting graphs to Discord")

        except Exception as e:
            logger.exception(f"Error posting graphs to Discord: {e}")
            raise

    async def cleanup_old_graphs(
        self,
        keep_days: int | None = None,
        timeout_seconds: float = 60.0,
        progress_callback: Callable[[str, int, int, dict[str, object]], None]
        | None = None,
    ) -> dict[str, object]:
        """
        Clean up old graph files based on retention policy with enhanced error handling.

        Args:
            keep_days: Number of days to keep graph files (uses config if None)
            timeout_seconds: Maximum time to wait for cleanup operations
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with cleanup statistics

        Raises:
            ResourceCleanupError: If cleanup fails
            asyncio.TimeoutError: If cleanup exceeds timeout
        """
        if keep_days is None:
            config = self.config_manager.get_current_config()
            keep_days = config.KEEP_DAYS

        logger.info(f"Starting cleanup of graphs older than {keep_days} days")

        progress_tracker = ProgressTracker(progress_callback)

        try:
            from pathlib import Path

            progress_tracker.update("Initializing cleanup operation", 1, 3)

            # Use asyncio.to_thread() for file I/O operations with timeout
            # For cleanup, we need to handle the entire date-based structure
            base_graphs_dir = Path("data") / "graphs"

            progress_tracker.update("Scanning for old files", 2, 3)

            try:
                deleted_count = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._cleanup_dated_graphs, base_graphs_dir, keep_days
                    ),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                error_msg = (
                    f"Cleanup operation exceeded timeout of {timeout_seconds} seconds"
                )
                progress_tracker.add_error(error_msg)
                raise asyncio.TimeoutError(error_msg)

            progress_tracker.update(
                "Cleanup completed", 3, 3, files_deleted=deleted_count
            )

            summary = progress_tracker.get_summary()
            cleanup_stats = {
                "files_deleted": deleted_count,
                "keep_days": keep_days,
                "cleanup_time": summary["total_time"],
                "errors": summary["errors"],
                "warnings": summary["warnings"],
            }

            logger.info(
                f"Successfully cleaned up {deleted_count} old graph files in {summary['total_time']:.2f}s"
            )
            return cleanup_stats

        except Exception as e:
            progress_tracker.add_error(f"Critical error during cleanup: {str(e)}")
            summary = progress_tracker.get_summary()
            logger.exception(f"Cleanup failed after {summary['total_time']:.2f}s: {e}")

            if isinstance(e, asyncio.TimeoutError):
                raise
            else:
                raise ResourceCleanupError(f"Failed to cleanup old graphs: {e}") from e

    async def update_graphs_full_cycle(self) -> dict[str, object]:
        """
        Perform a complete graph update cycle with detailed reporting.

        This includes generation, posting to Discord, and cleanup.

        Returns:
            Dictionary with cycle statistics and results
        """
        logger.info("Starting full graph update cycle")

        cycle_start_time = time.time()

        try:
            # Generate graphs
            graph_files = await self.generate_all_graphs()

            # Post to Discord
            await self.post_graphs_to_discord(graph_files)

            # Cleanup old files
            cleanup_stats = await self.cleanup_old_graphs()

            cycle_time = time.time() - cycle_start_time

            cycle_results: dict[str, object] = {
                "graphs_generated": len(graph_files),
                "cleanup_stats": cleanup_stats,
                "total_cycle_time": cycle_time,
                "success": True,
            }

            logger.info(
                f"Full graph update cycle completed successfully in {cycle_time:.2f}s"
            )
            return cycle_results

        except Exception as e:
            cycle_time = time.time() - cycle_start_time

            logger.exception(
                f"Error in full graph update cycle after {cycle_time:.2f}s: {e}"
            )
            raise

    def _cleanup_dated_graphs(self, base_dir: Path, keep_days: int) -> int:
        """
        Clean up old graph files from the date-based directory structure.

        Args:
            base_dir: Base directory containing date-based subdirectories
            keep_days: Number of days to keep files

        Returns:
            Number of files deleted
        """
        from datetime import datetime, timedelta

        total_deleted = 0

        if not base_dir.exists():
            logger.debug(f"Base graphs directory does not exist: {base_dir}")
            return 0

        cutoff_date = datetime.now() - timedelta(days=keep_days)

        # Iterate through date-based subdirectories
        for date_dir in base_dir.iterdir():
            if not date_dir.is_dir():
                continue

            # Parse directory name to check if it's a date (YYYY-MM-DD format)
            try:
                dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
                if dir_date < cutoff_date:
                    # This date directory is too old, clean it up
                    deleted_count = cleanup_old_files(
                        date_dir, 0
                    )  # Delete all files in old date dir
                    total_deleted += deleted_count

                    # Remove empty directory after cleanup
                    try:
                        if not any(date_dir.iterdir()):  # Directory is empty
                            date_dir.rmdir()
                            logger.debug(f"Removed empty date directory: {date_dir}")
                    except OSError as e:
                        logger.warning(
                            f"Could not remove empty directory {date_dir}: {e}"
                        )

            except ValueError:
                # Not a date directory, skip
                logger.debug(f"Skipping non-date directory: {date_dir}")
                continue

        logger.info(f"Cleaned up {total_deleted} files from date-based graph structure")
        return total_deleted
