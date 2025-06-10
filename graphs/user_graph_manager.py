"""
User graph manager for TGraph Bot.

This module handles graph generation for the /my_stats command.
Like the main manager, it uses asyncio.to_thread() to execute the CPU-bound
graph generation, ensuring the bot remains responsive while creating
personalized graphs for a user.
"""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .graph_modules.data_fetcher import DataFetcher
from .graph_modules.graph_factory import GraphFactory
from .graph_modules.utils import cleanup_old_files, ensure_graph_directory

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

    async def generate_user_graphs(self, user_email: str) -> list[str]:
        """
        Generate personal graphs for a specific user.

        Args:
            user_email: The user's Plex email address

        Returns:
            List of file paths to generated user graph images

        Raises:
            RuntimeError: If components are not initialized
            Exception: If graph generation fails
        """
        if self._data_fetcher is None or self._graph_factory is None:
            raise RuntimeError("UserGraphManager components not initialized. Use as async context manager.")

        logger.info(f"Starting personal graph generation for user: {user_email}")

        try:
            # Step 1: Fetch user-specific data from Tautulli API (async, non-blocking)
            logger.debug(f"Fetching user data for {user_email}")
            config = self.config_manager.get_current_config()
            user_data = await self._fetch_user_graph_data(user_email, config.TIME_RANGE_DAYS)

            # Step 2: Generate graphs using asyncio.to_thread() (non-blocking)
            logger.debug("Starting user graph generation in separate thread")
            graph_files = await asyncio.to_thread(
                self._generate_user_graphs_sync,
                user_email,
                user_data
            )

            logger.info(f"Generated {len(graph_files)} personal graphs for {user_email}")
            return graph_files

        except Exception as e:
            logger.exception(f"Error generating personal graphs for {user_email}: {e}")
            raise

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
            # TODO: Implement user ID lookup by email
            # For now, we'll fetch general play history and filter by user
            # In a real implementation, you'd want to:
            # 1. Look up user ID by email from Tautulli
            # 2. Fetch user-specific play history

            # Fetch play history data for the user
            play_history = await self._data_fetcher.get_play_history(
                time_range=time_range_days,
                user_id=None  # TODO: Replace with actual user ID lookup
            )

            user_data: dict[str, object] = {
                "play_history": play_history,
                "time_range_days": time_range_days,
                "user_email": user_email,
            }

            logger.debug(f"Successfully fetched user graph data for {user_email}")
            return user_data

        except Exception as e:
            logger.exception(f"Error fetching user graph data for {user_email}: {e}")
            raise

    def _generate_user_graphs_sync(self, user_email: str, data: dict[str, object]) -> list[str]:  # pyright: ignore[reportUnusedParameter]
        """
        Synchronous user graph generation (runs in separate thread).

        Args:
            user_email: The user's Plex email address
            data: Dictionary containing the data needed for graph generation (unused in placeholder)

        Returns:
            List of file paths to generated user graph images

        Raises:
            RuntimeError: If GraphFactory is not initialized
        """
        if self._graph_factory is None:
            raise RuntimeError("GraphFactory not initialized")

        logger.debug(f"Starting synchronous user graph generation for {user_email}")

        try:
            # Ensure user graph output directory exists
            user_graph_dir_path = f"graphs/output/users/{user_email.replace('@', '_at_')}"
            _ = ensure_graph_directory(user_graph_dir_path)

            # TODO: Implement user-specific graph generation
            # This would involve:
            # 1. Filtering data for the specific user
            # 2. Creating user-specific graph instances
            # 3. Generating personalized graphs
            # For now, we'll use a placeholder implementation

            logger.info(f"Placeholder: Generating personal graphs for {user_email}")
            # Return empty list for now - this will be implemented in future tasks
            generated_paths: list[str] = []

            logger.debug(f"Generated {len(generated_paths)} user graphs synchronously")
            return generated_paths

        except Exception as e:
            logger.exception(f"Error in synchronous user graph generation for {user_email}: {e}")
            raise
        
    async def send_user_graphs_dm(
        self, 
        user_id: int, 
        graph_files: list[str]
    ) -> bool:
        """
        Send generated user graphs via Discord DM.
        
        Args:
            user_id: Discord user ID
            graph_files: List of file paths to graph images
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Sending {len(graph_files)} personal graphs to user {user_id}")
        
        try:
            # TODO: Implement Discord DM sending
            # This will require bot instance and file handling
            
            logger.info(f"Placeholder: Sending graphs to user {user_id}")
            return True
            
        except Exception as e:
            logger.exception(f"Error sending graphs to user {user_id}: {e}")
            return False
            
    async def cleanup_user_graphs(self, graph_files: list[str]) -> None:
        """
        Clean up temporary user graph files using async threading.

        Args:
            graph_files: List of file paths to clean up
        """
        logger.info(f"Cleaning up {len(graph_files)} temporary user graph files")

        try:
            # Use asyncio.to_thread() for file I/O operations
            _ = await asyncio.to_thread(
                self._cleanup_user_graphs_sync,
                graph_files
            )

            logger.info("Successfully cleaned up user graph files")

        except Exception as e:
            logger.exception(f"Error cleaning up user graph files: {e}")

    def _cleanup_user_graphs_sync(self, graph_files: list[str]) -> None:
        """
        Synchronous cleanup of user graph files (runs in separate thread).

        Args:
            graph_files: List of file paths to clean up
        """
        deleted_count = 0

        for file_path in graph_files:
            try:
                path_obj = Path(file_path)
                if path_obj.exists() and path_obj.is_file():
                    path_obj.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted user graph file: {file_path}")
            except OSError as e:
                logger.warning(f"Failed to delete user graph file {file_path}: {e}")

        logger.debug(f"Cleaned up {deleted_count} user graph files")

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
        user_email: str
    ) -> bool:
        """
        Process a complete user statistics request with full async threading support.

        Args:
            user_id: Discord user ID
            user_email: User's Plex email address

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Processing stats request for user {user_id} ({user_email})")

        try:
            # Generate user graphs (uses async threading internally)
            graph_files = await self.generate_user_graphs(user_email)

            # Send via DM
            success = await self.send_user_graphs_dm(user_id, graph_files)

            # Cleanup temporary files (uses async threading)
            await self.cleanup_user_graphs(graph_files)

            # Cleanup old user graphs (uses async threading)
            await self.cleanup_old_user_graphs(user_email)

            if success:
                logger.info(f"Successfully processed stats request for user {user_id}")
            else:
                logger.warning(f"Failed to send stats to user {user_id}")

            return success

        except Exception as e:
            logger.exception(f"Error processing stats request for user {user_id}: {e}")
            return False
