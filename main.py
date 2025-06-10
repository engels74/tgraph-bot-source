"""
Main entry point for TGraph Bot.

This module initializes the bot, loads configuration and translations,
sets up logging, loads extensions, manages the main event loop,
background tasks, and handles overall bot lifecycle and error management.
"""

import asyncio
import logging
import logging.handlers
import signal
import sys
from collections.abc import Coroutine
from pathlib import Path
from typing import override

import discord
from discord.ext import commands

from config.manager import ConfigManager
from i18n import setup_i18n
from bot.extensions import load_extensions


def setup_logging() -> None:
    """
    Configure comprehensive logging with rotation and multiple handlers.

    Sets up both file and console logging with appropriate formatters,
    log rotation, and different log levels for different components.
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    simple_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    # File handler with rotation (10MB max, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "tgraph-bot.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Console handler for important messages
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # Error file handler for errors and above
    error_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "tgraph-bot-errors.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(error_handler)

    # Set specific log levels for noisy libraries
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Set our application loggers to INFO
    logging.getLogger("bot").setLevel(logging.INFO)
    logging.getLogger("config").setLevel(logging.INFO)
    logging.getLogger("i18n").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


class TGraphBot(commands.Bot):
    """
    TGraph Bot - Discord bot for Tautulli graph generation and posting.

    This bot automatically generates and posts Tautulli graphs to Discord channels,
    provides user-specific statistics, and offers configuration management through
    Discord slash commands.

    Features enhanced error handling, background task management, and graceful shutdown.
    """

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize the TGraph Bot with required intents and configuration."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True

        super().__init__(
            command_prefix="!",  # Fallback prefix, mainly using slash commands
            intents=intents,
            help_command=None,  # We'll implement custom help via slash commands
        )

        self.start_time: float = 0.0
        self.config_manager: ConfigManager = config_manager
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._is_shutting_down: bool = False

    def is_shutting_down(self) -> bool:
        """Check if the bot is currently shutting down."""
        return self._is_shutting_down

    @override
    async def setup_hook(self) -> None:
        """
        Setup hook called when the bot is starting up.

        This method loads extensions, syncs commands, and performs
        other initialization tasks with comprehensive error handling.
        """
        logger.info("Setting up TGraph Bot...")

        try:
            # Get current configuration
            try:
                config = self.config_manager.get_current_config()
            except RuntimeError as e:
                logger.error(f"No configuration loaded: {e}")
                raise RuntimeError("Bot setup failed: No configuration available") from e

            # Setup internationalization
            try:
                setup_i18n(config.LANGUAGE)
                logger.info(f"Internationalization setup for language: {config.LANGUAGE}")
            except Exception as e:
                logger.error(f"Failed to setup internationalization: {e}")
                # Continue with default language
                logger.warning("Continuing with default language settings")

            # Load command extensions
            try:
                extension_results = await load_extensions(self)
                successful_extensions = [r for r in extension_results if r.loaded]
                failed_extensions = [r for r in extension_results if not r.loaded]

                logger.info(f"Successfully loaded {len(successful_extensions)} extensions")
                if failed_extensions:
                    logger.warning(f"Failed to load {len(failed_extensions)} extensions")
                    for failed in failed_extensions:
                        logger.warning(f"  - {failed.name}: {failed.error}")

            except Exception as e:
                logger.error(f"Critical error loading extensions: {e}")
                raise RuntimeError("Bot setup failed: Extension loading failed") from e

            # Setup background tasks
            await self.setup_background_tasks()

            logger.info("TGraph Bot setup complete")

        except Exception as e:
            logger.exception(f"Fatal error during bot setup: {e}")
            # Set shutdown event to prevent the bot from continuing
            self._shutdown_event.set()
            raise

    async def setup_background_tasks(self) -> None:
        """
        Setup background tasks for the bot.

        This method initializes any background tasks that need to run
        continuously, such as scheduled graph updates or maintenance tasks.
        """
        logger.info("Setting up background tasks...")

        # TODO: Add actual background tasks here when implementing scheduled features
        # Example:
        # task = asyncio.create_task(self._periodic_health_check())
        # self._background_tasks.add(task)
        # task.add_done_callback(self._background_tasks.discard)

        logger.info("Background tasks setup complete")

    def create_background_task(self, coro: Coroutine[object, object, None], name: str | None = None) -> asyncio.Task[None]:
        """
        Create and track a background task.

        Args:
            coro: The coroutine to run as a background task
            name: Optional name for the task (for debugging)

        Returns:
            The created task
        """
        task = asyncio.create_task(coro, name=name)
        self._background_tasks.add(task)

        # Remove task from set when it completes
        task.add_done_callback(self._background_tasks.discard)

        logger.debug(f"Created background task: {name or task.get_name()}")
        return task

    async def cleanup_background_tasks(self) -> None:
        """
        Clean up all background tasks gracefully.

        Cancels all running background tasks and waits for them to complete.
        """
        if not self._background_tasks:
            logger.debug("No background tasks to clean up")
            return

        logger.info(f"Cleaning up {len(self._background_tasks)} background tasks...")

        # Cancel all tasks
        for task in self._background_tasks:
            if not task.done():
                _ = task.cancel()
                logger.debug(f"Cancelled task: {task.get_name()}")

        # Wait for all tasks to complete (with timeout)
        if self._background_tasks:
            try:
                _ = await asyncio.wait_for(
                    asyncio.gather(*self._background_tasks, return_exceptions=True),
                    timeout=10.0
                )
                logger.info("All background tasks cleaned up successfully")
            except asyncio.TimeoutError:
                logger.warning("Some background tasks did not complete within timeout")
            except Exception as e:
                logger.error(f"Error during background task cleanup: {e}")

        self._background_tasks.clear()

    async def on_ready(self) -> None:
        """Called when the bot has successfully connected to Discord."""
        if self.user is None:
            logger.error("Bot user is None after ready event")
            return

        logger.info(f"TGraph Bot is ready! Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")

        # Record start time for uptime tracking
        import time
        self.start_time = time.time()

        # Log additional connection information
        total_members = sum(guild.member_count or 0 for guild in self.guilds)
        logger.info(f"Serving {total_members} total members across all guilds")

        # Check if shutdown was requested during startup
        if self._shutdown_event.is_set():
            logger.warning("Shutdown requested during startup, initiating graceful shutdown")
            await self.close()

    @override
    async def on_error(self, event: str, *args: object, **kwargs: object) -> None:
        """
        Handle errors that occur during event processing.

        Provides detailed error logging and prevents the bot from crashing
        due to unhandled exceptions in event handlers.
        """
        logger.exception(f"Unhandled exception in event '{event}' with args: {args}")

        # Log additional context if available
        if args:
            logger.error(f"Event args: {args}")
        if kwargs:
            logger.error(f"Event kwargs: {kwargs}")

    async def on_disconnect(self) -> None:
        """Called when the bot disconnects from Discord."""
        logger.warning("Bot disconnected from Discord")

    async def on_resumed(self) -> None:
        """Called when the bot resumes a session."""
        logger.info("Bot session resumed")

    @override
    async def close(self) -> None:
        """
        Clean shutdown of the bot with comprehensive cleanup.

        Ensures all background tasks are properly cancelled and cleaned up,
        and all resources are released before shutting down.
        """
        if self._is_shutting_down:
            logger.debug("Shutdown already in progress, skipping duplicate close")
            return

        self._is_shutting_down = True
        logger.info("Initiating graceful shutdown of TGraph Bot...")

        try:
            # Set shutdown event to signal other components
            self._shutdown_event.set()

            # Clean up background tasks
            await self.cleanup_background_tasks()

            # Close the bot connection
            await super().close()

            logger.info("TGraph Bot shutdown complete")

        except Exception as e:
            logger.exception(f"Error during bot shutdown: {e}")
            # Still call parent close to ensure Discord connection is terminated
            try:
                await super().close()
            except Exception:
                logger.exception("Failed to close Discord connection during error recovery")


def setup_signal_handlers(bot: TGraphBot) -> None:
    """
    Setup signal handlers for graceful shutdown.

    Handles SIGTERM and SIGINT signals to ensure the bot shuts down gracefully
    when receiving termination signals from the operating system.
    """
    def signal_handler(signum: int, _frame: object) -> None:
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")

        # Create a task to close the bot gracefully
        loop = asyncio.get_event_loop()
        if loop.is_running():
            _ = loop.create_task(bot.close())
        else:
            logger.warning("Event loop not running, forcing immediate shutdown")
            sys.exit(1)

    # Register signal handlers for graceful shutdown
    _ = signal.signal(signal.SIGTERM, signal_handler)
    _ = signal.signal(signal.SIGINT, signal_handler)

    logger.debug("Signal handlers registered for graceful shutdown")


async def main() -> None:
    """
    Main entry point for the TGraph Bot application.

    This function sets up logging, loads configuration, creates the bot instance,
    sets up signal handlers, and starts the bot with comprehensive error handling.
    """
    # Setup logging first
    setup_logging()
    logger.info("TGraph Bot starting up...")

    config_manager = ConfigManager()
    bot: TGraphBot | None = None

    try:
        # Load configuration from config.yml
        config_path = Path("config.yml")

        if not config_path.exists():
            logger.error("Configuration file 'config.yml' not found")
            logger.error("Please copy 'config.yml.sample' to 'config.yml' and configure it")
            logger.error("Refer to the documentation for configuration instructions")
            sys.exit(1)

        # Load and validate configuration
        try:
            config = config_manager.load_config(config_path)
            config_manager.set_current_config(config)
            logger.info("Configuration loaded and validated successfully")
        except Exception as e:
            logger.exception(f"Failed to load configuration: {e}")
            logger.error("Please check your config.yml file for errors")
            sys.exit(1)

        # Create bot instance
        try:
            bot = TGraphBot(config_manager)
            logger.info("Bot instance created successfully")
        except Exception as e:
            logger.exception(f"Failed to create bot instance: {e}")
            sys.exit(1)

        # Setup signal handlers for graceful shutdown
        setup_signal_handlers(bot)

        # Start the bot
        logger.info("Starting TGraph Bot...")
        try:
            await bot.start(config.DISCORD_TOKEN)
        except discord.LoginFailure as e:
            logger.error(f"Failed to login to Discord: {e}")
            logger.error("Please check your Discord bot token in config.yml")
            sys.exit(1)
        except discord.HTTPException as e:
            logger.error(f"HTTP error connecting to Discord: {e}")
            logger.error("This may be a temporary Discord API issue, please try again later")
            sys.exit(1)
        except Exception as e:
            logger.exception(f"Unexpected error starting bot: {e}")
            raise

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except SystemExit:
        # Re-raise SystemExit to preserve exit codes
        raise
    except Exception as e:
        logger.exception(f"Fatal error in main: {e}")
        sys.exit(1)
    finally:
        # Ensure bot is properly closed
        if bot is not None and not bot.is_shutting_down():
            logger.info("Ensuring bot shutdown in finally block...")
            try:
                await bot.close()
            except Exception as e:
                logger.exception(f"Error during final bot cleanup: {e}")

        logger.info("TGraph Bot shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Logging is set up in main(), so this should work
        logger.info("Bot stopped by user")
    except Exception as e:
        # If logging isn't set up yet, fall back to basic logging
        try:
            logger.exception(f"Failed to start bot: {e}")
        except NameError:
            # Logger not available, use basic print
            print(f"Failed to start bot: {e}", file=sys.stderr)
        sys.exit(1)
