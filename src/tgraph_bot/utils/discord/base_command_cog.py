"""
Base command cog for TGraph Bot.

This module provides a base class for all command cogs with common functionality
including cooldown management, TGraphBot access, error handling, and configuration access.
This eliminates code duplication across command cogs and provides a consistent interface.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, cast, final

import discord
from discord.ext import commands

from ...utils.core.error_handler import ErrorContext, handle_command_error
from .ephemeral_utils import send_ephemeral_with_deletion, edit_ephemeral_with_deletion

if TYPE_CHECKING:
    from ...main import TGraphBot
    from ...config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


@final
class BaseCooldownConfig:
    """Configuration for cooldown settings."""

    def __init__(
        self,
        user_cooldown_config_key: str,
        global_cooldown_config_key: str,
        user_cooldown_multiplier: int = 60,  # Convert minutes to seconds
    ) -> None:
        """
        Initialize cooldown configuration.

        Args:
            user_cooldown_config_key: Config key for per-user cooldown (in minutes)
            global_cooldown_config_key: Config key for global cooldown (in seconds)
            user_cooldown_multiplier: Multiplier to convert user cooldown to seconds
        """
        self.user_cooldown_config_key: str = user_cooldown_config_key
        self.global_cooldown_config_key: str = global_cooldown_config_key
        self.user_cooldown_multiplier: int = user_cooldown_multiplier


class BaseCommandCog(commands.Cog):
    """
    Base class for all TGraph Bot command cogs.

    Provides common functionality including:
    - TGraphBot instance access with type safety
    - Cooldown management with configurable settings
    - Error context creation and handling
    - Configuration access helpers
    - Standardized logging patterns
    """

    def __init__(
        self, bot: commands.Bot, cooldown_config: BaseCooldownConfig | None = None
    ) -> None:
        """
        Initialize the base command cog.

        Args:
            bot: The Discord bot instance
            cooldown_config: Optional cooldown configuration for this cog
        """
        self.bot: commands.Bot = bot
        self.cooldown_config: BaseCooldownConfig | None = cooldown_config

        # Cooldown tracking (only if cooldown_config is provided)
        if cooldown_config:
            self._user_cooldowns: dict[int, float] = {}
            self._global_cooldown: float = 0.0

    @property
    def tgraph_bot(self) -> "TGraphBot":
        """
        Get the TGraphBot instance with proper type checking.

        Returns:
            TGraphBot instance

        Raises:
            TypeError: If bot is not a TGraphBot instance
        """
        # Import here to avoid circular imports
        from ...main import TGraphBot

        # Strict type checking - only allow actual TGraphBot instances
        if isinstance(self.bot, TGraphBot):
            return self.bot

        # Additional check for class name (for edge cases during extension loading)
        if (
            hasattr(self.bot, "__class__")
            and self.bot.__class__.__name__ == "TGraphBot"
        ):
            # Verify it has the required TGraphBot attributes
            if hasattr(self.bot, "config_manager") and hasattr(
                self.bot, "update_tracker"
            ):
                return cast("TGraphBot", self.bot)

        raise TypeError(f"Expected TGraphBot instance, got {type(self.bot)}")

    def get_current_config(self) -> "TGraphBotConfig":
        """
        Get the current bot configuration.

        Returns:
            Current configuration object
        """
        return self.tgraph_bot.config_manager.get_current_config()

    def check_cooldowns(self, interaction: discord.Interaction) -> tuple[bool, float]:
        """
        Check if the user is on cooldown for this command.

        Args:
            interaction: The Discord interaction

        Returns:
            Tuple of (is_on_cooldown, retry_after_seconds)
        """
        if not self.cooldown_config:
            return False, 0.0

        current_time = time.time()
        config = self.get_current_config()

        # Check global cooldown
        from ...graphs.graph_modules.config.config_accessor import ConfigAccessor
        config_accessor = ConfigAccessor(config)
        global_cooldown_seconds = config_accessor.get_int_value(
            self.cooldown_config.global_cooldown_config_key, 0
        )
        if global_cooldown_seconds > 0:
            if current_time < self._global_cooldown:
                return True, self._global_cooldown - current_time

        # Check per-user cooldown
        user_cooldown_minutes = config_accessor.get_int_value(
            self.cooldown_config.user_cooldown_config_key, 0
        )
        user_cooldown_seconds = (
            user_cooldown_minutes * self.cooldown_config.user_cooldown_multiplier
        )
        if user_cooldown_seconds > 0:
            user_id = interaction.user.id
            if user_id in self._user_cooldowns:
                if current_time < self._user_cooldowns[user_id]:
                    return True, self._user_cooldowns[user_id] - current_time

        return False, 0.0

    def update_cooldowns(self, interaction: discord.Interaction) -> None:
        """
        Update cooldown timers after successful command execution.

        Args:
            interaction: The Discord interaction
        """
        if not self.cooldown_config:
            return

        current_time = time.time()
        config = self.get_current_config()

        from ...graphs.graph_modules.config.config_accessor import ConfigAccessor
        config_accessor = ConfigAccessor(config)

        # Update global cooldown
        global_cooldown_seconds = config_accessor.get_int_value(
            self.cooldown_config.global_cooldown_config_key, 0
        )
        if global_cooldown_seconds > 0:
            self._global_cooldown = current_time + global_cooldown_seconds

        # Update per-user cooldown
        user_cooldown_minutes = config_accessor.get_int_value(
            self.cooldown_config.user_cooldown_config_key, 0
        )
        user_cooldown_seconds = (
            user_cooldown_minutes * self.cooldown_config.user_cooldown_multiplier
        )
        if user_cooldown_seconds > 0:
            user_id = interaction.user.id
            self._user_cooldowns[user_id] = current_time + user_cooldown_seconds

    def create_error_context(
        self,
        interaction: discord.Interaction,
        command_name: str,
        additional_context: dict[str, object] | None = None,
    ) -> ErrorContext:
        """
        Create an error context for comprehensive logging.

        Args:
            interaction: The Discord interaction
            command_name: Name of the command being executed
            additional_context: Additional context information

        Returns:
            ErrorContext object for error handling
        """
        return ErrorContext(
            user_id=interaction.user.id,
            guild_id=interaction.guild.id if interaction.guild else None,
            channel_id=interaction.channel.id if interaction.channel else None,
            command_name=command_name,
            additional_context=additional_context or {},
        )

    async def handle_command_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        command_name: str,
        additional_context: dict[str, object] | None = None,
    ) -> None:
        """
        Handle command errors with standardized error context.

        Args:
            interaction: The Discord interaction
            error: The exception that occurred
            command_name: Name of the command being executed
            additional_context: Additional context information
        """
        context = self.create_error_context(
            interaction, command_name, additional_context
        )
        await handle_command_error(interaction, error, context)

    async def send_ephemeral_response(
        self,
        interaction: discord.Interaction,
        *,
        content: str | None = None,
        embed: discord.Embed | None = None,
        view: discord.ui.View | None = None,
        delete_after: float | None = None,
    ) -> None:
        """
        Send an ephemeral interaction response with automatic deletion.

        This method is a convenience wrapper around the ephemeral_utils function
        that provides consistent ephemeral messaging behavior across all command cogs.
        The message will be automatically deleted after the configured timeout.

        Args:
            interaction: The Discord interaction to respond to
            content: The text content of the message (optional)
            embed: The embed to include in the message (optional)
            view: The view (UI components) to include in the message (optional)
            delete_after: Time in seconds after which to delete the message (optional, uses config default)

        Raises:
            ValueError: If delete_after is not positive
            ValueError: If neither content nor embed is provided
            Exception: If the Discord API call fails

        Example:
            >>> await self.send_ephemeral_response(
            ...     interaction,
            ...     content="This command completed successfully!"
            ... )
        """
        # Try to get config, fallback to None if not available (e.g., in tests)
        try:
            config = self.get_current_config()
        except (TypeError, AttributeError):
            config = None

        await send_ephemeral_with_deletion(
            interaction,
            content=content,
            embed=embed,
            view=view,
            delete_after=delete_after,
            config=config,
        )

    async def edit_ephemeral_response(
        self,
        interaction: discord.Interaction,
        *,
        content: str | None = None,
        embed: discord.Embed | None = None,
        view: discord.ui.View | None = None,
        delete_after: float | None = None,
    ) -> None:
        """
        Edit an ephemeral interaction response with automatic deletion.

        This method is a convenience wrapper around the ephemeral_utils function
        that provides consistent ephemeral message editing behavior across all
        command cogs. The edited message will be automatically deleted after
        the configured timeout.

        Args:
            interaction: The Discord interaction to edit the response for
            content: The new text content of the message (optional)
            embed: The new embed to include in the message (optional)
            view: The new view (UI components) to include in the message (optional)
            delete_after: Time in seconds after which to delete the message (optional, uses config default)

        Raises:
            ValueError: If delete_after is not positive
            Exception: If the Discord API call fails

        Example:
            >>> await self.edit_ephemeral_response(
            ...     interaction,
            ...     content="Configuration updated successfully!"
            ... )
        """
        # Try to get config, fallback to None if not available (e.g., in tests)
        try:
            config = self.get_current_config()
        except (TypeError, AttributeError):
            config = None

        await edit_ephemeral_with_deletion(
            interaction,
            content=content,
            embed=embed,
            view=view,
            delete_after=delete_after,
            config=config,
        )
