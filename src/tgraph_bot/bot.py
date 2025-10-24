"""Discord bot core for TGraph Bot.

This module implements the main Discord bot class and connection management
with reconnection logic and event handlers.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 19.2, 19.4
"""

import asyncio
from typing import override

import nextcord
from nextcord.ext import commands

from tgraph_bot.config.loader import ConfigLoader
from tgraph_bot.config.models import BotConfig
from tgraph_bot.rate_limiting.rate_limiter import RateLimiter
from tgraph_bot.scheduler.task_scheduler import TaskScheduler
from tgraph_bot.utils.errors import ConfigurationError
from tgraph_bot.utils.logging import (
    get_logger,
    log_operation_complete,
    log_operation_start,
)

# Type aliases using PEP 695 syntax
type ValidationErrors = list[str]

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
        config_loader: Configuration loader for reloading from file
        config_path: Path to the configuration file
    """

    def __init__(
        self,
        config: BotConfig,
        *,
        config_loader: ConfigLoader | None = None,
        config_path: str | None = None,
    ) -> None:
        """Initialize the TGraph Bot with configuration.

        Args:
            config: Bot configuration from YAML
            config_loader: Optional ConfigLoader for reloading configuration
            config_path: Optional path to configuration file for reloading

        Requirements: 1.1, 1.5
        """
        # Configure intents for the bot
        # Using default intents which excludes privileged intents (members, presences, message_content)
        # This bot only uses slash commands and posts messages, so message_content is not needed
        intents = nextcord.Intents.default()
        intents.guilds = True  # Required for guild information and slash commands
        intents.members = False  # Not needed - bot doesn't track member joins/leaves

        # Initialize parent Bot class
        super().__init__(
            command_prefix="!",  # Prefix for text commands (slash commands are primary)
            intents=intents,
            help_command=None,  # Disable default help command
        )

        # Store configuration
        self.config: BotConfig = config
        self.config_loader: ConfigLoader | None = config_loader
        self.config_path: str | None = config_path

        # Initialize rate limiter
        self.rate_limiter: RateLimiter = RateLimiter(config=config.rate_limiting)

        # Initialize task scheduler
        # Note: update_executor will be set later when commands are loaded
        self.scheduler: TaskScheduler = TaskScheduler(
            config=config.automation, update_executor=None
        )

        # Connection management
        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 5
        self._reconnect_delay_base: float = 2.0  # Base delay in seconds

        # Startup task tracking
        self._startup_complete: bool = False

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
        On first connection, performs startup tasks:
        - Cleans up old bot messages in the configured channel
        - Generates and posts initial graphs

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

        # Perform startup tasks only on first connection (not on reconnects)
        # Set flag BEFORE async operation to prevent race condition if on_ready fires twice
        if not self._startup_complete:
            self._startup_complete = True
            await self._perform_startup_tasks()

    async def _perform_startup_tasks(self) -> None:
        """Perform startup tasks after bot connects to Discord.

        This method:
        1. Cleans up old bot messages in the configured channel
        2. Generates and posts initial graphs

        Errors are logged but do not prevent bot startup.
        """
        _ = log_operation_start(logger, "startup_tasks")

        try:
            # Get the configured channel
            channel_id = self.config.services.discord.channel_id
            channel = self.get_channel(channel_id)

            if channel is None:
                logger.error(
                    f"Configured channel {channel_id} not found. Skipping startup tasks.",
                    extra={"channel_id": channel_id},
                )
                return

            # Verify channel is a text channel
            if not isinstance(channel, nextcord.TextChannel):
                logger.error(
                    f"Configured channel {channel_id} is not a text channel. Skipping startup tasks.",
                    extra={
                        "channel_id": channel_id,
                        "channel_type": type(channel).__name__,
                    },
                )
                return

            # Task 1: Clean up old bot messages
            await self._cleanup_bot_messages(channel)

            # Task 2: Generate and post initial graphs
            await self._post_initial_graphs()

            _ = log_operation_complete(logger, "startup_tasks")

        except Exception:
            logger.error(
                "Error during startup tasks. Bot will continue running.",
                exc_info=True,
            )

    async def _cleanup_bot_messages(self, channel: nextcord.TextChannel) -> None:
        """Delete all messages posted by this bot in the specified channel.

        Args:
            channel: The Discord text channel to clean up

        Uses nextcord's purge() method with a check function to filter
        only messages authored by the bot.
        """
        _ = log_operation_start(logger, "cleanup_bot_messages")

        try:
            if self.user is None:
                logger.error("Cannot cleanup messages: bot user is None")
                return

            # Define check function to filter bot's own messages
            def is_bot_message(message: nextcord.Message) -> bool:
                return message.author == self.user

            # Purge bot messages (limit=None means check all messages)
            # bulk=False allows deletion without manage_messages permission
            deleted = await channel.purge(
                limit=None,
                check=is_bot_message,
                bulk=False,
            )

            logger.info(
                f"Cleaned up {len(deleted)} bot message(s) from channel",
                extra={
                    "channel_id": channel.id,
                    "deleted_count": len(deleted),
                },
            )

            _ = log_operation_complete(logger, "cleanup_bot_messages")

        except nextcord.Forbidden:
            logger.error(
                "Missing permissions to delete messages in channel",
                extra={"channel_id": channel.id},
            )
        except nextcord.HTTPException as e:
            logger.error(
                f"HTTP error while cleaning up messages: {e}",
                extra={"channel_id": channel.id},
                exc_info=True,
            )
        except Exception:
            logger.error(
                "Unexpected error during message cleanup",
                extra={"channel_id": channel.id},
                exc_info=True,
            )

    async def _post_initial_graphs(self) -> None:
        """Generate and post initial graphs to the configured channel.

        Calls the GraphCommands cog's _generate_and_post_graphs method
        to reuse existing graph generation and posting logic.
        """
        _ = log_operation_start(logger, "post_initial_graphs")

        try:
            # Get the GraphCommands cog without importing to avoid circular dependency
            # Use duck typing to check for the required method
            logger.info("Attempting to get GraphCommands cog for initial graph posting")
            graph_commands_cog = self.get_cog("GraphCommands")

            if graph_commands_cog is None:
                logger.error(
                    "GraphCommands cog not loaded. Skipping initial graph posting."
                )
                return

            # Check if the cog has the required method using duck typing
            if not hasattr(graph_commands_cog, "_generate_and_post_graphs"):
                logger.error(
                    "GraphCommands cog does not have _generate_and_post_graphs method. Skipping initial graph posting."
                )
                return

            logger.info("GraphCommands cog found, generating and posting initial graphs")

            # Generate and post graphs (no username filter = all graphs)
            # Intentional access to protected method for code reuse within same package
            # Type is unknown due to duck typing to avoid circular import
            metadata_list = await graph_commands_cog._generate_and_post_graphs()  # pyright: ignore[reportAttributeAccessIssue, reportUnknownVariableType, reportUnknownMemberType]

            logger.info(
                f"Posted {len(metadata_list)} initial graph(s)",  # pyright: ignore[reportUnknownArgumentType]
                extra={"graph_count": len(metadata_list)},  # pyright: ignore[reportUnknownArgumentType]
            )

            _ = log_operation_complete(logger, "post_initial_graphs", success=True)

        except Exception as e:
            logger.error(
                f"Error posting initial graphs: {e}. Bot will continue running.",
                exc_info=True,
            )
            _ = log_operation_complete(logger, "post_initial_graphs", success=False, error=str(e))

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

    async def reload_configuration(
        self, new_config: BotConfig | None = None, *, config_path: str | None = None
    ) -> None:
        """Reload bot configuration without restarting.

        Updates the bot's configuration and reconfigures components that support
        hot reloading (scheduler, rate limiter). Some changes may require a full
        restart to take effect (e.g., Discord token changes).

        This method supports two modes:
        1. Direct config: Pass a BotConfig object as new_config
        2. Load from file: Pass config_path or use the stored config_path

        Args:
            new_config: New configuration to apply (optional if loading from file)
            config_path: Path to configuration file to load (optional, uses stored path if not provided)

        Raises:
            ConfigurationError: If the new configuration is invalid or cannot be loaded
            ValueError: If neither new_config nor config_path is available

        Requirements: 3.4, 15.1, 15.5
        """
        _ = log_operation_start(logger, "reload_configuration")

        old_config = self.config
        old_rate_limiter = self.rate_limiter

        try:
            # Determine the configuration to apply
            config_to_apply: BotConfig

            if new_config is not None:
                # Mode 1: Direct config provided
                logger.info("Reloading configuration from provided config object")
                config_to_apply = new_config
            else:
                # Mode 2: Load from file
                path_to_use = config_path or self.config_path
                if path_to_use is None:
                    raise ValueError(
                        "Cannot reload configuration: no config_path provided and no stored config_path"
                    )

                if self.config_loader is None:
                    raise ValueError(
                        "Cannot reload configuration from file: no config_loader available"
                    )

                logger.info(
                    f"Reloading configuration from file: {path_to_use}",
                    extra={"config_path": path_to_use},
                )

                # Load configuration from file
                config_to_apply = self.config_loader.load(path_to_use)

            # Validate configuration before applying
            if self.config_loader is not None:
                validation_errors: ValidationErrors = self.config_loader.validate(
                    config_to_apply
                )
                if validation_errors:
                    error_msg = f"Configuration validation failed: {'; '.join(validation_errors)}"
                    logger.error(
                        error_msg,
                        extra={"validation_errors": validation_errors},
                    )
                    raise ConfigurationError(
                        error_msg,
                        field_name="configuration",
                        expected_value="valid configuration values",
                    )

            logger.info("Configuration validation passed, applying changes")

            # Apply new configuration
            self.config = config_to_apply

            # Reconfigure scheduler if automation settings changed
            if config_to_apply.automation != old_config.automation:
                logger.info(
                    "Reconfiguring task scheduler",
                    extra={
                        "old_enabled": old_config.automation.enabled,
                        "new_enabled": config_to_apply.automation.enabled,
                        "old_interval": old_config.automation.update_interval_days,
                        "new_interval": config_to_apply.automation.update_interval_days,
                    },
                )
                await self.scheduler.stop()
                # Preserve the update_executor when reconfiguring
                old_executor = self.scheduler.update_executor
                self.scheduler = TaskScheduler(
                    config=config_to_apply.automation, update_executor=old_executor
                )
                if config_to_apply.automation.enabled:
                    await self.scheduler.start()

            # Reconfigure rate limiter if rate limiting settings changed
            # Preserve existing cooldowns by copying them to the new rate limiter
            if config_to_apply.rate_limiting != old_config.rate_limiting:
                logger.info(
                    "Reconfiguring rate limiter (preserving existing cooldowns)",
                    extra={
                        "old_config_cooldown": old_config.rate_limiting.config.user_cooldown_minutes,
                        "new_config_cooldown": config_to_apply.rate_limiting.config.user_cooldown_minutes,
                    },
                )
                # Get current cooldown state before creating new rate limiter
                user_cooldowns, global_cooldowns = old_rate_limiter.get_cooldown_state()

                # Create new rate limiter with new config
                new_rate_limiter = RateLimiter(config=config_to_apply.rate_limiting)

                # Restore cooldown state to preserve existing cooldowns
                new_rate_limiter.restore_cooldown_state(
                    user_cooldowns, global_cooldowns
                )

                self.rate_limiter = new_rate_limiter

            logger.info(
                "Configuration reloaded successfully",
                extra={
                    "automation_enabled": config_to_apply.automation.enabled,
                    "language": config_to_apply.system.language,
                },
            )
            log_operation_complete(logger, "reload_configuration", success=True)

        except Exception as e:
            # Restore old configuration on failure
            logger.error(
                f"Configuration reload failed, restoring previous configuration: {e}",
                exc_info=True,
                extra={"error_type": type(e).__name__},
            )
            self.config = old_config
            self.rate_limiter = old_rate_limiter
            log_operation_complete(
                logger, "reload_configuration", success=False, error=str(e)
            )
            raise
