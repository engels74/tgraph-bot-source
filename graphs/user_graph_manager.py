"""
User graph manager for TGraph Bot.

This module handles graph generation for the /my_stats command.
Like the main manager, it uses asyncio.to_thread() to execute the CPU-bound
graph generation, ensuring the bot remains responsive while creating
personalized graphs for a user.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from .graph_modules.data_fetcher import DataFetcher
from .graph_modules.graph_factory import GraphFactory
from .graph_modules.utils import cleanup_old_files, ensure_graph_directory

# Import shared classes from graph_manager
from .graph_manager import GraphGenerationError, ResourceCleanupError, ProgressTracker

if TYPE_CHECKING:
    from config.manager import ConfigManager

logger = logging.getLogger(__name__)


class UserGraphManager:
    """Handles graph generation for personal user statistics."""

    def __init__(self, config_manager: "ConfigManager") -> None:
        """
        Initialize the user graph manager.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager: "ConfigManager" = config_manager
        self._data_fetcher: DataFetcher | None = None
        self._graph_factory: GraphFactory | None = None

    async def __aenter__(self) -> "UserGraphManager":
        """Async context manager entry."""
        await self._initialize_components()
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object) -> None:
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
            max_retries=3
        )
        _ = await self._data_fetcher.__aenter__()

        # Initialize GraphFactory
        self._graph_factory = GraphFactory(config)

        logger.debug("UserGraphManager components initialized")

    async def _cleanup_components(self) -> None:
        """Clean up DataFetcher and other resources."""
        if self._data_fetcher is not None:
            await self._data_fetcher.__aexit__(None, None, None)
            self._data_fetcher = None

        self._graph_factory = None
        logger.debug("UserGraphManager components cleaned up")

    async def generate_user_graphs(
        self,
        user_email: str,
        progress_callback: Callable[[str, int, int, dict[str, object]], None] | None = None,
        max_retries: int = 3,
        timeout_seconds: float = 180.0
    ) -> list[str]:
        """
        Generate personal graphs for a specific user with enhanced error handling.

        Args:
            user_email: The user's Plex email address
            progress_callback: Optional callback for progress updates
            max_retries: Maximum number of retry attempts for failed operations
            timeout_seconds: Maximum time to wait for graph generation

        Returns:
            List of file paths to generated user graph images

        Raises:
            RuntimeError: If components are not initialized
            GraphGenerationError: If graph generation fails after retries
            asyncio.TimeoutError: If generation exceeds timeout
        """
        if self._data_fetcher is None or self._graph_factory is None:
            raise RuntimeError("UserGraphManager components not initialized. Use as async context manager.")

        logger.info(f"Starting personal graph generation for user: {user_email}")

        # Initialize progress tracker
        progress_tracker = ProgressTracker(progress_callback)

        try:
            # Step 1: Fetch user-specific data with retry logic
            progress_tracker.update("Fetching user data from Tautulli API", 1, 3)
            config = self.config_manager.get_current_config()

            user_data = await self._fetch_user_graph_data_with_retry(
                user_email,
                config.TIME_RANGE_DAYS,
                max_retries,
                progress_tracker
            )

            # Step 2: Validate user data
            progress_tracker.update("Validating user data", 2, 3)
            if not self._validate_user_graph_data(user_data, progress_tracker):
                raise GraphGenerationError(f"Invalid or insufficient data for user {user_email}")

            # Step 3: Generate graphs with timeout protection
            progress_tracker.update("Generating user graphs in separate thread", 3, 3)
            logger.debug("Starting user graph generation with timeout protection")

            try:
                graph_files = await asyncio.wait_for(
                    asyncio.to_thread(self._generate_user_graphs_sync, user_email, user_data, progress_tracker),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                error_msg = f"User graph generation exceeded timeout of {timeout_seconds} seconds"
                progress_tracker.add_error(error_msg)
                raise asyncio.TimeoutError(error_msg)

            # Final validation
            valid_files = self._validate_generated_user_files(graph_files, user_email, progress_tracker)

            summary = progress_tracker.get_summary()
            logger.info(f"User graph generation completed for {user_email}: {len(valid_files)} files, " +
                       f"{summary['error_count']} errors, {summary['warning_count']} warnings, " +
                       f"total time: {summary['total_time']:.2f}s")

            return valid_files

        except Exception as e:
            progress_tracker.add_error(f"Critical error in user graph generation: {str(e)}")
            summary = progress_tracker.get_summary()
            logger.exception(f"User graph generation failed for {user_email} after {summary['total_time']:.2f}s: {e}")

            if isinstance(e, (GraphGenerationError, asyncio.TimeoutError)):
                raise
            else:
                raise GraphGenerationError(f"Unexpected error during user graph generation: {e}") from e

    async def _fetch_user_graph_data(self, user_email: str, time_range_days: int) -> dict[str, object]:
        """
        Fetch user-specific data for graph generation from Tautulli API.

        Args:
            user_email: The user's Plex email address
            time_range_days: Number of days to fetch data for

        Returns:
            Dictionary containing user-specific data needed for graph generation

        Raises:
            RuntimeError: If DataFetcher is not initialized
        """
        if self._data_fetcher is None:
            raise RuntimeError("DataFetcher not initialized")

        logger.debug(f"Fetching user graph data for {user_email} ({time_range_days} days)")

        try:
            # Look up user by email to get user ID
            user_info = await self._data_fetcher.find_user_by_email(user_email)
            if user_info is None:
                raise ValueError(f"User not found with email: {user_email}")

            # Extract user ID from user info
            user_id = user_info.get("user_id")
            if user_id is None:
                raise ValueError(f"User ID not found for email: {user_email}")

            # Convert user_id to int safely
            if isinstance(user_id, (int, str)):
                user_id_int = int(user_id)
            else:
                raise ValueError(f"Invalid user ID type for email: {user_email}")

            # Fetch play history data for the specific user
            play_history = await self._data_fetcher.get_play_history(
                time_range=time_range_days,
                user_id=user_id_int
            )

            user_data: dict[str, object] = {
                "play_history": play_history,
                "time_range_days": time_range_days,
                "user_email": user_email,
                "user_id": user_id,
                "user_info": user_info,
            }

            logger.debug(f"Successfully fetched user graph data for {user_email}")
            return user_data

        except Exception as e:
            logger.exception(f"Error fetching user graph data for {user_email}: {e}")
            raise

    async def _fetch_user_graph_data_with_retry(
        self,
        user_email: str,
        time_range_days: int,
        max_retries: int,
        progress_tracker: ProgressTracker
    ) -> dict[str, object]:
        """
        Fetch user graph data with retry logic and exponential backoff.

        Args:
            user_email: The user's Plex email address
            time_range_days: Number of days to fetch data for
            max_retries: Maximum number of retry attempts
            progress_tracker: Progress tracker for error reporting

        Returns:
            Dictionary containing user-specific data needed for graph generation

        Raises:
            GraphGenerationError: If all retry attempts fail
        """
        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = min(2.0 ** attempt, 30.0)  # Exponential backoff, max 30s
                    progress_tracker.add_warning(f"Retrying user data fetch for {user_email} (attempt {attempt + 1}/{max_retries + 1}) after {delay}s delay")
                    await asyncio.sleep(delay)

                return await self._fetch_user_graph_data(user_email, time_range_days)

            except Exception as e:
                last_exception = e
                error_msg = f"User data fetch attempt {attempt + 1} failed for {user_email}: {str(e)}"

                if attempt < max_retries:
                    progress_tracker.add_warning(error_msg)
                    logger.warning(error_msg)
                else:
                    progress_tracker.add_error(f"All {max_retries + 1} user data fetch attempts failed for {user_email}")
                    logger.error(f"Final user data fetch attempt failed for {user_email}: {e}")

        # If we get here, all retries failed
        raise GraphGenerationError(f"Failed to fetch user data for {user_email} after {max_retries + 1} attempts") from last_exception

    def _validate_user_graph_data(self, data: dict[str, object], progress_tracker: ProgressTracker) -> bool:
        """
        Validate that the fetched user data is sufficient for graph generation.

        Args:
            data: The user data dictionary to validate
            progress_tracker: Progress tracker for warning/error reporting

        Returns:
            True if data is valid, False otherwise
        """
        try:
            # Check for required keys
            required_keys = ["play_history", "user_email", "user_id", "user_info"]
            for key in required_keys:
                if key not in data:
                    progress_tracker.add_error(f"Missing '{key}' in user data")
                    return False

            play_history = data["play_history"]
            user_email = data["user_email"]

            # Check if play_history has data
            if not isinstance(play_history, dict):
                progress_tracker.add_error(f"Play history is not a dictionary for user {user_email}")
                return False

            # Check for data content (this depends on Tautulli API structure)
            if not play_history:
                progress_tracker.add_warning(f"Play history is empty for user {user_email} - graphs may be minimal")
                return True  # Empty data is still valid, just results in empty graphs

            logger.debug(f"User data validation passed for {user_email}")
            return True

        except Exception as e:
            progress_tracker.add_error(f"User data validation error: {str(e)}")
            logger.exception(f"Error during user data validation: {e}")
            return False

    def _validate_generated_user_files(self, graph_files: list[str], user_email: str, progress_tracker: ProgressTracker) -> list[str]:
        """
        Validate that generated user graph files exist and are accessible.

        Args:
            graph_files: List of file paths to validate
            user_email: User email for logging context
            progress_tracker: Progress tracker for warning/error reporting

        Returns:
            List of valid file paths
        """
        valid_files: list[str] = []

        for file_path in graph_files:
            try:
                path = Path(file_path)

                if not path.exists():
                    progress_tracker.add_error(f"Generated user file does not exist for {user_email}: {file_path}")
                    continue

                if not path.is_file():
                    progress_tracker.add_error(f"User path is not a file for {user_email}: {file_path}")
                    continue

                if path.stat().st_size == 0:
                    progress_tracker.add_warning(f"Generated user file is empty for {user_email}: {file_path}")
                    continue

                valid_files.append(file_path)

            except Exception as e:
                progress_tracker.add_error(f"Error validating user file {file_path} for {user_email}: {str(e)}")
                logger.exception(f"User file validation error for {user_email} - {file_path}: {e}")

        logger.debug(f"Validated {len(valid_files)}/{len(graph_files)} generated user files for {user_email}")
        return valid_files

    def _generate_user_graphs_sync(self, user_email: str, data: dict[str, object], progress_tracker: ProgressTracker | None = None) -> list[str]:
        """
        Synchronous user graph generation (runs in separate thread).

        Args:
            user_email: The user's Plex email address
            data: Dictionary containing the data needed for graph generation
            progress_tracker: Optional progress tracker for error reporting

        Returns:
            List of file paths to generated user graph images

        Raises:
            RuntimeError: If GraphFactory is not initialized
            GraphGenerationError: If user graph generation fails
        """
        if self._graph_factory is None:
            raise RuntimeError("GraphFactory not initialized")

        logger.debug(f"Starting synchronous user graph generation for {user_email}")

        try:
            # Ensure user graph output directory exists
            user_graph_dir_path = f"graphs/output/users/{user_email.replace('@', '_at_')}"
            user_graph_dir = ensure_graph_directory(user_graph_dir_path)

            # Generate user-specific graphs using GraphFactory
            # The data is already filtered for this specific user
            logger.info(f"Generating personal graphs for {user_email}")

            # GraphFactory should be initialized in __aenter__
            assert self._graph_factory is not None, "GraphFactory not initialized"

            # Use GraphFactory to generate all enabled graphs with user-specific data
            # This will create graphs filtered to the specific user's activity
            generated_paths = self._graph_factory.generate_all_graphs(data)

            # Move generated graphs to user-specific directory
            user_specific_paths: list[str] = []
            for path in generated_paths:
                if path:
                    try:
                        # Create user-specific filename
                        original_filename = Path(path).name
                        user_filename = f"{user_email.replace('@', '_at_')}_{original_filename}"
                        user_path = user_graph_dir / user_filename

                        # Move file to user directory
                        _ = Path(path).rename(user_path)
                        user_specific_paths.append(str(user_path))
                    except Exception as e:
                        error_msg = f"Failed to move graph file {path} for user {user_email}: {e}"
                        if progress_tracker:
                            progress_tracker.add_error(error_msg)
                        logger.error(error_msg)

            if progress_tracker:
                if not user_specific_paths:
                    progress_tracker.add_warning(f"No user graphs were generated for {user_email}")
                else:
                    logger.debug(f"Generated {len(user_specific_paths)} user graphs synchronously for {user_email}")

            return user_specific_paths

        except Exception as e:
            error_msg = f"Error in synchronous user graph generation for {user_email}: {e}"
            if progress_tracker:
                progress_tracker.add_error(error_msg)
            logger.exception(error_msg)
            raise GraphGenerationError(error_msg) from e
        
    async def send_user_graphs_dm(
        self,
        user_id: int,
        graph_files: list[str],
        bot: object  # Discord bot instance
    ) -> bool:
        """
        Send generated user graphs via Discord DM.

        Args:
            user_id: Discord user ID
            graph_files: List of file paths to graph images
            bot: Discord bot instance for sending messages

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Sending {len(graph_files)} personal graphs to user {user_id}")

        try:
            import discord

            # Get the Discord user - bot should be a discord.Client or discord.Bot
            get_user_func = getattr(bot, 'get_user', None)
            if get_user_func is None:
                logger.error("Bot does not have get_user method")
                return False
            user = get_user_func(user_id)
            if user is None:
                logger.error(f"Could not find Discord user with ID {user_id}")
                return False

            # Create embed for the personal statistics
            embed = discord.Embed(
                title="📊 Your Personal Plex Statistics",
                description="Here are your personalized viewing statistics!",
                color=discord.Color.blue()
            )

            # Add some metadata
            _ = embed.set_footer(text="Generated by TGraph Bot")

            # Send graphs as files
            files_to_send: list[discord.File] = []
            for graph_path in graph_files:
                if Path(graph_path).exists():
                    files_to_send.append(discord.File(graph_path))

            if files_to_send:
                # Send the embed with attached files
                send_result = await user.send(embed=embed, files=files_to_send)  # pyright: ignore[reportAny]
                _ = send_result
                logger.info(f"Successfully sent {len(files_to_send)} graphs to user {user_id}")
                return True
            else:
                # Send just the embed if no files
                send_result = await user.send(embed=embed)  # pyright: ignore[reportAny]
                _ = send_result
                logger.warning(f"No graph files found to send to user {user_id}")
                return True

        except Exception as e:
            logger.exception(f"Error sending graphs to user {user_id}: {e}")
            return False
            
    async def cleanup_user_graphs(
        self,
        graph_files: list[str],
        timeout_seconds: float = 30.0
    ) -> dict[str, object]:
        """
        Clean up temporary user graph files using async threading with enhanced error handling.

        Args:
            graph_files: List of file paths to clean up
            timeout_seconds: Maximum time to wait for cleanup operations

        Returns:
            Dictionary with cleanup statistics

        Raises:
            ResourceCleanupError: If cleanup fails
            asyncio.TimeoutError: If cleanup exceeds timeout
        """
        logger.info(f"Cleaning up {len(graph_files)} temporary user graph files")

        start_time = time.time()

        try:
            # Use asyncio.to_thread() for file I/O operations with timeout
            try:
                deleted_count = await asyncio.wait_for(
                    asyncio.to_thread(self._cleanup_user_graphs_sync, graph_files),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                error_msg = f"User graph cleanup exceeded timeout of {timeout_seconds} seconds"
                logger.error(error_msg)
                raise asyncio.TimeoutError(error_msg)

            cleanup_time = time.time() - start_time
            cleanup_stats: dict[str, object] = {
                "files_deleted": deleted_count,
                "total_files": len(graph_files),
                "cleanup_time": cleanup_time,
                "success": True
            }

            logger.info(f"Successfully cleaned up {deleted_count}/{len(graph_files)} user graph files in {cleanup_time:.2f}s")
            return cleanup_stats

        except Exception as e:
            cleanup_time = time.time() - start_time
            logger.exception(f"Error cleaning up user graph files after {cleanup_time:.2f}s: {e}")

            if isinstance(e, asyncio.TimeoutError):
                raise
            else:
                raise ResourceCleanupError(f"Failed to cleanup user graph files: {e}") from e

    def _cleanup_user_graphs_sync(self, graph_files: list[str]) -> int:
        """
        Synchronous cleanup of user graph files (runs in separate thread).

        Args:
            graph_files: List of file paths to clean up

        Returns:
            Number of files successfully deleted
        """
        deleted_count = 0

        for file_path in graph_files:
            try:
                path_obj = Path(file_path)
                if path_obj.exists() and path_obj.is_file():
                    path_obj.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted user graph file: {file_path}")
                elif path_obj.exists():
                    logger.warning(f"Path exists but is not a file: {file_path}")
                else:
                    logger.debug(f"File already deleted or does not exist: {file_path}")
            except OSError as e:
                logger.warning(f"Failed to delete user graph file {file_path}: {e}")

        logger.debug(f"Cleaned up {deleted_count}/{len(graph_files)} user graph files")
        return deleted_count

    async def cleanup_old_user_graphs(self, user_email: str, keep_days: int | None = None) -> None:
        """
        Clean up old user graph files based on retention policy using async threading.

        Args:
            user_email: The user's email to clean up graphs for
            keep_days: Number of days to keep graph files (uses config if None)
        """
        if keep_days is None:
            config = self.config_manager.get_current_config()
            keep_days = config.KEEP_DAYS

        logger.info(f"Cleaning up user graphs for {user_email} older than {keep_days} days")

        try:
            # Use asyncio.to_thread() for file I/O operations
            user_graph_dir = Path(f"graphs/output/users/{user_email.replace('@', '_at_')}")
            _ = await asyncio.to_thread(
                cleanup_old_files,
                user_graph_dir,
                keep_days
            )

            logger.info(f"Successfully cleaned up old user graph files for {user_email}")

        except Exception as e:
            logger.exception(f"Error cleaning up old user graphs for {user_email}: {e}")

    async def process_user_stats_request(
        self,
        user_id: int,
        user_email: str,
        bot: object  # Discord bot instance
    ) -> dict[str, object]:
        """
        Process a complete user statistics request with full async threading support and detailed reporting.

        Args:
            user_id: Discord user ID
            user_email: User's Plex email address
            bot: Discord bot instance for sending DMs

        Returns:
            Dictionary with processing statistics and results
        """
        logger.info(f"Processing stats request for user {user_id} ({user_email})")

        start_time = time.time()

        try:
            # Generate user graphs (uses async threading internally)
            graph_files = await self.generate_user_graphs(user_email)

            # Send via DM
            success = await self.send_user_graphs_dm(user_id, graph_files, bot)

            # Cleanup temporary files (uses async threading)
            cleanup_stats = await self.cleanup_user_graphs(graph_files)

            # Cleanup old user graphs (uses async threading)
            await self.cleanup_old_user_graphs(user_email)

            processing_time = time.time() - start_time

            result_stats: dict[str, object] = {
                "success": success,
                "user_id": user_id,
                "user_email": user_email,
                "graphs_generated": len(graph_files),
                "cleanup_stats": cleanup_stats,
                "processing_time": processing_time
            }

            if success:
                logger.info(f"Successfully processed stats request for user {user_id} in {processing_time:.2f}s")
            else:
                logger.warning(f"Failed to send stats to user {user_id} after {processing_time:.2f}s")

            return result_stats

        except Exception as e:
            processing_time = time.time() - start_time
            error_stats: dict[str, object] = {
                "success": False,
                "user_id": user_id,
                "user_email": user_email,
                "error": str(e),
                "processing_time": processing_time
            }

            logger.exception(f"Error processing stats request for user {user_id} after {processing_time:.2f}s: {e}")
            return error_stats
