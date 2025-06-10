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
from typing import TYPE_CHECKING, Callable

from .graph_modules.data_fetcher import DataFetcher
from .graph_modules.graph_factory import GraphFactory
from .graph_modules.utils import cleanup_old_files, ensure_graph_directory

if TYPE_CHECKING:
    from config.manager import ConfigManager

logger = logging.getLogger(__name__)


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

        logger.debug("GraphManager components initialized")

    async def _cleanup_components(self) -> None:
        """Clean up DataFetcher and other resources."""
        if self._data_fetcher is not None:
            await self._data_fetcher.__aexit__(None, None, None)
            self._data_fetcher = None

        self._graph_factory = None
        logger.debug("GraphManager components cleaned up")

    async def generate_all_graphs(self, progress_callback: Callable[[str, int, int], None] | None = None) -> list[str]:
        """
        Generate all enabled graphs for the server with optional progress tracking.

        This method:
        1. Fetches data from Tautulli API (async)
        2. Generates graphs using GraphFactory (sync, in thread)
        3. Returns list of generated graph file paths

        Args:
            progress_callback: Optional callback for progress updates (message, current, total)

        Returns:
            List of file paths to generated graph images

        Raises:
            RuntimeError: If components are not initialized
            Exception: If graph generation fails
        """
        if self._data_fetcher is None or self._graph_factory is None:
            raise RuntimeError("GraphManager components not initialized. Use as async context manager.")

        logger.info("Starting server-wide graph generation")

        try:
            # Step 1: Fetch data from Tautulli API (async, non-blocking)
            if progress_callback:
                progress_callback("Fetching data from Tautulli API", 1, 3)
            logger.debug("Fetching data from Tautulli API")
            config = self.config_manager.get_current_config()
            data = await self._fetch_graph_data(config.TIME_RANGE_DAYS)

            # Step 2: Generate graphs using asyncio.to_thread() (non-blocking)
            if progress_callback:
                progress_callback("Generating graphs", 2, 3)
            logger.debug("Starting graph generation in separate thread")
            graph_files = await asyncio.to_thread(
                self._generate_graphs_sync,
                data
            )

            if progress_callback:
                progress_callback("Graph generation complete", 3, 3)
            logger.info(f"Successfully generated {len(graph_files)} graphs")
            return graph_files

        except Exception as e:
            logger.exception(f"Error generating graphs: {e}")
            raise

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

        logger.debug(f"Fetching graph data for {time_range_days} days")

        try:
            # Fetch play history data for all users
            play_history = await self._data_fetcher.get_play_history(
                time_range=time_range_days
            )

            # Additional data can be fetched here as needed
            # For now, we'll use the play history as the primary data source

            data: dict[str, object] = {
                "play_history": play_history,
                "time_range_days": time_range_days,
            }

            logger.debug("Successfully fetched graph data from Tautulli API")
            return data

        except Exception as e:
            logger.exception(f"Error fetching graph data: {e}")
            raise

    def _generate_graphs_sync(self, data: dict[str, object]) -> list[str]:
        """
        Synchronous graph generation (runs in separate thread).

        This method uses the existing GraphFactory.generate_all_graphs()
        method which handles resource management and cleanup properly.

        Args:
            data: Dictionary containing the data needed for graph generation

        Returns:
            List of file paths to generated graph images

        Raises:
            RuntimeError: If GraphFactory is not initialized
        """
        if self._graph_factory is None:
            raise RuntimeError("GraphFactory not initialized")

        logger.debug("Starting synchronous graph generation")

        try:
            # Ensure graph output directory exists
            graph_dir_path = "graphs/output"
            _ = ensure_graph_directory(graph_dir_path)

            # Use GraphFactory to generate all enabled graphs
            # This method already handles proper resource management and cleanup
            generated_paths = self._graph_factory.generate_all_graphs(data)

            logger.debug(f"Generated {len(generated_paths)} graphs synchronously")
            return generated_paths

        except Exception as e:
            logger.exception(f"Error in synchronous graph generation: {e}")
            raise

        
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
            
    async def cleanup_old_graphs(self, keep_days: int | None = None) -> None:
        """
        Clean up old graph files based on retention policy.

        Args:
            keep_days: Number of days to keep graph files (uses config if None)
        """
        if keep_days is None:
            config = self.config_manager.get_current_config()
            keep_days = config.KEEP_DAYS

        logger.info(f"Cleaning up graphs older than {keep_days} days")

        try:
            from pathlib import Path

            # Use asyncio.to_thread() for file I/O operations
            graph_dir = Path("graphs/output")
            _ = await asyncio.to_thread(
                cleanup_old_files,
                graph_dir,
                keep_days
            )

            logger.info("Successfully cleaned up old graph files")

        except Exception as e:
            logger.exception(f"Error cleaning up old graphs: {e}")
            raise
            
    async def update_graphs_full_cycle(self) -> None:
        """
        Perform a complete graph update cycle.
        
        This includes generation, posting to Discord, and cleanup.
        """
        logger.info("Starting full graph update cycle")
        
        try:
            # Generate graphs
            graph_files = await self.generate_all_graphs()
            
            # Post to Discord
            await self.post_graphs_to_discord(graph_files)
            
            # Cleanup old files
            await self.cleanup_old_graphs()
            
            logger.info("Full graph update cycle completed successfully")
            
        except Exception as e:
            logger.exception(f"Error in full graph update cycle: {e}")
            raise
