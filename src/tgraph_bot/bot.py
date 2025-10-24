"""Discord bot core for TGraph Bot.

This module implements the main Discord bot class and connection management
with reconnection logic and event handlers.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 19.2, 19.4
"""

import asyncio
from typing import override

import nextcord
from nextcord.ext import commands

from tgraph_bot.config.models import BotConfig
from tgraph_bot.rate_limiting.rate_limiter import RateLimiter
from tgraph_bot.scheduler.task_scheduler import TaskScheduler
from tgraph_bot.utils.logging import get_logger, log_operation_complete, log_operation_start

logger = get_logger(__name__)


class TGraphBot(commands.Bot):
    """Main Discord bot class for TGraph Bot.

    This class extends nextcord.Bot to provide:
    - Configuration management
    - Rate limiting integration
    - Task scheduling for automated updates
    - Reconnection logic with exponential backoff
    - Comprehensive logging

    Attributes:
        config: Bot configuration loaded from YAML
        rate_limiter: Rate limiter for command cooldowns
        scheduler: Task scheduler for automated graph updates
    """

    def __init__(self, config: BotConfig) -> None:
        """Initialize the TGraph Bot with configuration.

        Args:
            config: Bot configuration from YAML

        Requirements: 1.1, 1.5
        """
        # Configure intents for the bot
        intents = nextcord.Intents.default()
        intents.message_content = True  # Required for message commands if any
        intents.guilds = True  # Required for guild information
        intents.members = False  # Not needed for this bot

        # Initialize parent Bot class
        super().__init__(
            command_prefix="!",  # Prefix for text commands (slash commands are primary)
            intents=intents,
            help_command=None,  # Disable default help command
        )

        # Store configuration
        self.config: BotConfig = config

        # Initialize rate limiter
        self.rate_limiter: RateLimiter = RateLimiter(config.rate_limiting)

        # Initialize task scheduler
        # Note: update_executor will be set later when commands are loaded
        self.scheduler: TaskScheduler = TaskScheduler(config.automation, update_executor=None)

        # Connection management
        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 5
        self._reconnect_delay_base: float = 2.0  # Base delay in seconds

        logger.info(
            "TGraph Bot initialized",
            extra={
                "discord_channel_id": config.services.discord.channel_id,
                "automation_enabled": config.automation.enabled,
                "language": config.system.language,
            },
        )

    async def on_ready(self) -> None:
        """Event handler called when bot successfully connects to Discord.

        Logs connection status with timestamp and starts scheduled tasks if enabled.

        Requirements: 1.4, 1.5
        """
        if self.user is None:
            logger.error("Bot connected but user information is not available")
            return

        logger.info(
            f"Discord bot connected successfully as {self.user.name} (ID: {self.user.id})",
            extra={
                "user_id": self.user.id,
                "username": self.user.name,
                "guild_count": len(self.guilds),
            },
        )

        # Reset reconnection attempts counter on successful connection
        self._reconnect_attempts = 0

        # Start task scheduler if automation is enabled
        if self.config.automation.enabled:
            logger.info("Starting automated graph update scheduler")
            await self.scheduler.start()

    async def on_disconnect(self) -> None:
        """Event handler called when bot loses connection to Discord.

        Logs disconnection and prepares for reconnection attempt.

        Requirements: 1.3
        """
        logger.warning(
            "Discord bot disconnected",
            extra={"reconnect_attempts": self._reconnect_attempts},
        )

    async def on_resumed(self) -> None:
        """Event handler called when bot resumes connection after disconnect.

        Logs successful reconnection.

        Requirements: 1.3
        """
        logger.info("Discord bot connection resumed successfully")
        self._reconnect_attempts = 0

    @override
    async def on_error(self, event: str, *args: object, **kwargs: object) -> None:
        """Event handler for unhandled errors during event processing.

        Args:
            event: Name of the event that raised the error
            args: Positional arguments passed to the event
            kwargs: Keyword arguments passed to the event

        Requirements: 1.3
        """
        logger.error(
            f"Unhandled error in event: {event}",
            extra={"event": event},
            exc_info=True,
        )

    async def connect_with_retry(self) -> None:
        """Connect to Discord with exponential backoff retry logic.

        Attempts to connect up to max_reconnect_attempts times with exponentially
        increasing delays between attempts. If all attempts fail, raises the last
        exception.

        Raises:
            Exception: If connection fails after all retry attempts

        Requirements: 1.3
        """
        while self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                _ = log_operation_start(
                    logger,
                    "discord_connect",
                    details={
                        "attempt": self._reconnect_attempts + 1,
                        "max_attempts": self._max_reconnect_attempts,
                    },
                )

                # Start the bot connection
                await self.start(self.config.services.discord.token)

                # If we reach here, connection was successful
                log_operation_complete(logger, "discord_connect", success=True)
                return

            except Exception as e:
                self._reconnect_attempts += 1
                log_operation_complete(
                    logger,
                    "discord_connect",
                    success=False,
                    error=str(e),
                )

                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    logger.critical(
                        f"Failed to connect to Discord after {self._max_reconnect_attempts} attempts",
                        extra={"error": str(e)},
                    )
                    raise

                # Calculate exponential backoff delay: base * (2 ^ attempt)
                delay = self._reconnect_delay_base * (2.0**self._reconnect_attempts)
                logger.info(
                    f"Retrying connection in {delay:.1f} seconds (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})",
                    extra={"delay_seconds": delay},
                )
                await asyncio.sleep(delay)

    @override
    async def close(self) -> None:
        """Close the bot connection and cleanup resources.

        Stops the scheduler and closes the Discord connection gracefully.
        """
        logger.info("Shutting down TGraph Bot")

        # Stop scheduler if it's running
        if self.config.automation.enabled:
            logger.info("Stopping task scheduler")
            await self.scheduler.stop()

        # Close Discord connection
        await super().close()

        logger.info("TGraph Bot shutdown complete")

    async def reload_configuration(self, new_config: BotConfig) -> None:
        """Reload bot configuration without restarting.

        Updates the bot's configuration and reconfigures components that support
        hot reloading (scheduler, rate limiter). Some changes may require a full
        restart to take effect (e.g., Discord token changes).

        Args:
            new_config: New configuration to apply

        Raises:
            ConfigurationError: If the new configuration is invalid
        """
        _ = log_operation_start(logger, "reload_configuration")

        old_config = self.config
        self.config = new_config

        try:
            # Reconfigure scheduler if automation settings changed
            if new_config.automation != old_config.automation:
                logger.info("Reconfiguring task scheduler")
                await self.scheduler.stop()
                # Preserve the update_executor when reconfiguring
                old_executor = self.scheduler.update_executor
                self.scheduler = TaskScheduler(new_config.automation, update_executor=old_executor)
                if new_config.automation.enabled:
                    await self.scheduler.start()

            # Reconfigure rate limiter if rate limiting settings changed
            if new_config.rate_limiting != old_config.rate_limiting:
                logger.info("Reconfiguring rate limiter")
                # Rate limiter preserves existing cooldowns
                self.rate_limiter = RateLimiter(new_config.rate_limiting)

            log_operation_complete(logger, "reload_configuration", success=True)

        except Exception as e:
            # Restore old configuration on failure
            self.config = old_config
            log_operation_complete(
                logger, "reload_configuration", success=False, error=str(e)
            )
            raise
