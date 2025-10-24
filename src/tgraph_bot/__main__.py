"""Main application entry point for TGraph Bot.

This module implements the startup sequence, component initialization,
signal handling, and graceful shutdown for the Discord bot.

Requirements: 1.1, 1.4, 15.1, 15.2, 22.4, 22.5
"""

from __future__ import annotations

import asyncio
import signal
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

from tgraph_bot.bot import TGraphBot
from tgraph_bot.config.loader import ConfigLoader
from tgraph_bot.utils.errors import ConfigurationError
from tgraph_bot.utils.logging import get_logger, setup_logging
from tgraph_bot.utils.retention import DataRetentionManager
from tgraph_bot.web.server import WebUIServer

logger = get_logger(__name__)

# Default configuration file path
DEFAULT_CONFIG_PATH = "./config.yaml"


@asynccontextmanager
async def managed_bot(
    config_path: str,
) -> AsyncIterator[TGraphBot]:
    """Context manager for bot lifecycle management.

    This context manager handles:
    1. Configuration loading with environment variable overrides
    2. Bot instance creation
    3. Command cog loading
    4. Scheduler update executor setup
    5. Graceful shutdown on exit

    Args:
        config_path: Path to the YAML configuration file

    Yields:
        Initialized TGraphBot instance

    Raises:
        ConfigurationError: If configuration is invalid

    Requirements: 1.1, 1.4, 15.1, 15.2
    """
    logger.info(f"Loading configuration from {config_path}")

    # Load configuration with environment variable overrides
    config_loader = ConfigLoader()
    try:
        config = config_loader.load(config_path)
    except ConfigurationError as e:
        logger.error(f"Configuration validation failed: {e}", exc_info=True)
        raise

    logger.info("Configuration loaded and validated successfully")

    # Create bot instance
    logger.info("Creating Discord bot instance")
    bot = TGraphBot(
        config=config,
        config_loader=config_loader,
        config_path=config_path,
    )

    # Load command cogs
    logger.info("Loading command cogs")
    try:
        # Load GraphCommands cog
        from tgraph_bot.commands.graph_commands import setup as setup_graph_commands

        setup_graph_commands(bot)

        # Set the scheduler's update executor to the GraphCommands cog
        # The cog implements the UpdateExecutor protocol via execute_scheduled_update
        graph_commands_cog = bot.get_cog("GraphCommands")
        if graph_commands_cog is not None:
            # Cast to GraphCommands to satisfy type checker
            # The cog is guaranteed to be GraphCommands since we just loaded it
            from tgraph_bot.commands.graph_commands import GraphCommands

            bot.scheduler.update_executor = cast(GraphCommands, graph_commands_cog)
            logger.info("Scheduler update executor configured")
        else:
            logger.warning(
                "GraphCommands cog not found, scheduler will not execute updates"
            )

    except Exception as e:
        logger.error(f"Failed to load command cogs: {e}", exc_info=True)
        raise

    logger.info("Bot instance created successfully")

    try:
        yield bot
    finally:
        # Graceful shutdown
        logger.info("Shutting down bot")
        await bot.close()
        logger.info("Bot shutdown complete")


@asynccontextmanager
async def managed_web_server(
    bot: TGraphBot,
    config_path: str,
) -> AsyncIterator[WebUIServer | None]:
    """Context manager for web server lifecycle.

    Args:
        bot: TGraphBot instance
        config_path: Path to configuration file

    Yields:
        WebUIServer instance or None if web UI is disabled

    Requirements: 15.1, 15.2
    """
    if bot.config_loader is None:
        logger.warning("No config loader available, web server will not be started")
        yield None
        return

    # Get web UI configuration from environment variables
    # These are optional - if not set, web UI will not be started
    import os

    web_host = os.getenv("WEB_UI_HOST")
    web_port_str = os.getenv("WEB_UI_PORT")

    if web_host is None or web_port_str is None:
        logger.info(
            "Web UI not configured (WEB_UI_HOST or WEB_UI_PORT not set), skipping"
        )
        yield None
        return

    try:
        web_port = int(web_port_str)
    except ValueError:
        logger.warning(f"Invalid WEB_UI_PORT value: {web_port_str}, skipping web UI")
        yield None
        return

    # Create web server
    server = WebUIServer(
        config_loader=bot.config_loader,
        config_path=Path(config_path),
        host=web_host,
        port=web_port,
        bot_instance=bot,
    )

    # Start server
    logger.info(f"Starting Web UI server on {web_host}:{web_port}")
    await server.start()

    try:
        yield server
    finally:
        # Graceful shutdown
        logger.info("Stopping Web UI server")
        await server.stop()
        logger.info("Web UI server stopped")


@asynccontextmanager
async def managed_retention_manager(
    bot: TGraphBot,
) -> AsyncIterator[DataRetentionManager]:
    """Context manager for data retention manager lifecycle.

    Args:
        bot: TGraphBot instance

    Yields:
        DataRetentionManager instance

    Requirements: 15.1, 15.2
    """
    # Create retention manager using keep_graphs_days from system config
    output_dir = Path(bot.config.system.output_directory)
    keep_days = bot.config.system.keep_graphs_days

    manager = DataRetentionManager(
        output_dir=output_dir,
        keep_days=keep_days,
    )

    # Start scheduled cleanup
    logger.info(f"Starting data retention manager (keep {keep_days} days)")
    await manager.start()

    try:
        yield manager
    finally:
        # Graceful shutdown
        logger.info("Stopping data retention manager")
        await manager.stop()
        logger.info("Data retention manager stopped")


async def run_bot(config_path: str) -> None:
    """Run the bot with all components.

    This function orchestrates the complete startup sequence:
    1. Load configuration
    2. Initialize bot
    3. Start web server
    4. Start retention manager
    5. Connect to Discord
    6. Run until shutdown signal

    Args:
        config_path: Path to configuration file

    Requirements: 1.1, 1.4, 15.1, 15.2, 22.4, 22.5
    """
    logger.info("Starting TGraph Bot")

    # Use structured concurrency with context managers
    async with managed_bot(config_path) as bot:
        async with managed_web_server(bot, config_path) as _web_server:
            async with managed_retention_manager(bot) as _retention_manager:
                # Connect to Discord with retry logic
                logger.info("Connecting to Discord")
                try:
                    # Use bot's connect_with_retry method which handles reconnection
                    await bot.connect_with_retry()
                except Exception as e:
                    logger.error(f"Failed to connect to Discord: {e}", exc_info=True)
                    raise

                logger.info("TGraph Bot started successfully")

                # Wait for bot to be ready
                await bot.wait_until_ready()
                logger.info("Bot is ready and connected")

                # Keep running until close() is called
                # The bot will be closed when a shutdown signal is received
                while not bot.is_closed():
                    await asyncio.sleep(1)

    logger.info("TGraph Bot shutdown complete")


def setup_signal_handlers(loop: asyncio.AbstractEventLoop) -> None:
    """Setup signal handlers for graceful shutdown.

    Handles SIGTERM and SIGINT to trigger graceful shutdown.

    Args:
        loop: Event loop to stop on signal

    Requirements: 15.1, 15.2, 22.5
    """

    def signal_handler(sig: int) -> None:
        """Handle shutdown signals."""
        sig_name = signal.Signals(sig).name
        logger.info(f"Received {sig_name}, initiating graceful shutdown")
        # Stop the event loop, which will trigger cleanup in context managers
        loop.stop()

    # Register signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    logger.info("Signal handlers registered (SIGTERM, SIGINT)")


def main() -> None:
    """Main entry point for the application.

    This function:
    1. Sets up logging
    2. Loads configuration
    3. Initializes all components
    4. Sets up signal handlers
    5. Runs the bot
    6. Handles graceful shutdown

    Requirements: 1.1, 1.4, 15.1, 15.2, 22.4, 22.5
    """
    # Setup logging first
    setup_logging()

    logger.info("=" * 60)
    logger.info("TGraph Bot - Discord Tautulli Graph Generator")
    logger.info("=" * 60)

    # Get configuration path from environment or use default
    import os

    config_path = os.getenv("TGRAPH_CONFIG_PATH", DEFAULT_CONFIG_PATH)
    logger.info(f"Using configuration file: {config_path}")

    # Create event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Setup signal handlers for graceful shutdown
    setup_signal_handlers(loop)

    try:
        # Run the bot
        loop.run_until_complete(run_bot(config_path))
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup
        logger.info("Cleaning up event loop")
        try:
            # Cancel all remaining tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                _ = task.cancel()

            # Wait for all tasks to complete cancellation
            if pending:
                _ = loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
        finally:
            loop.close()
            logger.info("Event loop closed")

    logger.info("TGraph Bot exited successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()
