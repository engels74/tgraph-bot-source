"""
Main entry point for TGraph Bot.

This module initializes the bot, loads configuration and translations,
sets up logging, loads extensions, manages the main event loop,
background tasks, and handles overall bot lifecycle and error management.
"""

import asyncio
import logging
import sys
from typing import override

import discord
from discord.ext import commands

from config.manager import ConfigManager
from i18n import setup_i18n
from bot.extensions import load_extensions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("tgraph-bot.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


class TGraphBot(commands.Bot):
    """
    TGraph Bot - Discord bot for Tautulli graph generation and posting.

    This bot automatically generates and posts Tautulli graphs to Discord channels,
    provides user-specific statistics, and offers configuration management through
    Discord slash commands.
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

    @override
    async def setup_hook(self) -> None:
        """
        Setup hook called when the bot is starting up.

        This method loads extensions, syncs commands, and performs
        other initialization tasks.
        """
        logger.info("Setting up TGraph Bot...")

        # Get current configuration
        try:
            config = self.config_manager.get_current_config()
        except RuntimeError as e:
            logger.error(f"No configuration loaded: {e}")
            return

        # Setup internationalization
        setup_i18n(config.LANGUAGE)
        logger.info(f"Internationalization setup for language: {config.LANGUAGE}")

        # Load command extensions
        await load_extensions(self)
        logger.info("Command extensions loaded")

        # TODO: Setup background tasks
        # await self.setup_background_tasks()

        logger.info("TGraph Bot setup complete")
        
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

    @override
    async def on_error(self, event: str, *args: object, **kwargs: object) -> None:
        """Handle errors that occur during event processing."""
        logger.exception(f"Error in event {event}")

    @override
    async def close(self) -> None:
        """Clean shutdown of the bot."""
        logger.info("Shutting down TGraph Bot...")
        await super().close()


async def main() -> None:
    """
    Main entry point for the TGraph Bot application.

    This function creates the bot instance, loads the configuration,
    and starts the bot with proper error handling.
    """
    config_manager = ConfigManager()
    bot: TGraphBot | None = None

    try:
        # Load configuration from config.yml
        from pathlib import Path
        config_path = Path("config.yml")

        if not config_path.exists():
            logger.error("Configuration file 'config.yml' not found")
            logger.error("Please copy 'config.yml.sample' to 'config.yml' and configure it")
            sys.exit(1)

        # Load and set configuration
        config = config_manager.load_config(config_path)
        config_manager.set_current_config(config)
        logger.info("Configuration loaded successfully")

        # Create bot instance
        bot = TGraphBot(config_manager)

        # Start the bot
        logger.info("Starting TGraph Bot...")
        await bot.start(config.DISCORD_TOKEN)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        if bot is not None:
            await bot.close()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        if bot is not None:
            await bot.close()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Failed to start bot: {e}")
        sys.exit(1)
