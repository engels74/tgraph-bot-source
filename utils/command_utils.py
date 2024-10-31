# utils/command_utils.py

import discord
import logging
from datetime import timedelta
from discord.utils import utcnow

class ErrorHandlingMixin:
    """
    A mixin class providing common error handling functionality.
    """
    async def handle_error(self, interaction: discord.Interaction, error: Exception, command_name: str = None) -> None:
        """
        Handle errors by logging and sending an error message to the user.

        Args:
            interaction: The Discord interaction
            error: The exception that occurred
            command_name: Name of the command that failed (optional)
        """
        # Log the error
        logging.error(
            self.translations["log_command_error"].format(
                command=command_name or (interaction.command.qualified_name if interaction.command else "Unknown"),
                error=str(error)
            )
        )
        # Send error message to the user
        await self.send_error_message(
            interaction, self.translations["error_processing_command"]
        )

    async def send_error_message(self, interaction: discord.Interaction, error_message: str, ephemeral: bool = True) -> None:
        """
        Send an error message to the user.

        Args:
            interaction: The Discord interaction
            error_message: The error message to send
            ephemeral: Whether the message should be ephemeral
        """
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(error_message, ephemeral=ephemeral)
            else:
                await interaction.followup.send(error_message, ephemeral=ephemeral)
        except discord.DiscordException as e:
            logging.error(f"Failed to send error message: {str(e)}")

class CommandMixin(ErrorHandlingMixin):
    """
    A mixin class providing common command functionality.
    To be used with commands.Cog classes.
    """
    def __init__(self):
        self.user_cooldowns = {}
        self.global_cooldown = utcnow()

    def _cleanup_cooldowns(self) -> None:
        """Remove expired cooldowns to prevent memory leaks."""
        now = utcnow()
        self.user_cooldowns = {
            user_id: timestamp 
            for user_id, timestamp in self.user_cooldowns.items() 
            if timestamp > now
        }

    def _format_cooldown_timestamp(self, remaining_seconds: int) -> str:
        """
        Format a cooldown timestamp for Discord's time formatting.
        
        Args:
            remaining_seconds: Number of seconds remaining on cooldown
            
        Returns:
            Formatted Discord timestamp string
        """
        future_time = utcnow() + timedelta(seconds=remaining_seconds)
        return f"<t:{int(future_time.timestamp())}:R>"

    async def check_cooldowns(self, interaction: discord.Interaction, 
                            user_minutes: int, global_seconds: int) -> bool:
        """
        Check if a command is on cooldown.

        Args:
            interaction: The Discord interaction
            user_minutes: Minutes for user-specific cooldown
            global_seconds: Seconds for global cooldown

        Returns:
            bool: True if command can proceed, False if on cooldown
        """
        # Clean up expired cooldowns
        self._cleanup_cooldowns()
        
        # Skip cooldown checks if both values are 0 or negative
        if global_seconds <= 0 and user_minutes <= 0:
            return True

        now = utcnow()

        # Check global cooldown only if global_seconds is positive
        if global_seconds > 0 and now < self.global_cooldown:
            remaining = int((self.global_cooldown - now).total_seconds())
            await interaction.response.send_message(
                self.translations["rate_limit_global"].format(
                    time=self._format_cooldown_timestamp(remaining)
                ),
                ephemeral=True,
            )
            return False

        # Check user cooldown only if user_minutes is positive
        if user_minutes > 0:
            user_id = str(interaction.user.id)
            if user_id in self.user_cooldowns and now < self.user_cooldowns[user_id]:
                remaining = int(
                    (self.user_cooldowns[user_id] - now).total_seconds()
                )
                await interaction.response.send_message(
                    self.translations["rate_limit_user"].format(
                        time=self._format_cooldown_timestamp(remaining)
                    ),
                    ephemeral=True,
                )
                return False

        return True

    def update_cooldowns(self, user_id: str, user_minutes: int, global_seconds: int) -> None:
        """
        Update command cooldowns after successful execution.

        Args:
            user_id: The user's ID
            user_minutes: Minutes for user-specific cooldown
            global_seconds: Seconds for global cooldown
        """
        now = utcnow()
        # Only update cooldowns if the respective values are positive
        if user_minutes > 0:
            self.user_cooldowns[user_id] = now + timedelta(
                minutes=user_minutes
            )
        if global_seconds > 0:
            self.global_cooldown = now + timedelta(
                seconds=global_seconds
            )

    async def log_command(self, interaction: discord.Interaction, command_name: str) -> None:
        """
        Log command execution.

        Args:
            interaction: The Discord interaction
            command_name: Name of the command being executed
        """
        logging.info(
            self.translations["log_command_executed"].format(
                command=command_name,
                user=f"{interaction.user.name}#{interaction.user.discriminator}",
            )
        )

    async def handle_command_error(self, interaction: discord.Interaction, error: Exception, command_name: str) -> None:
        """
        Handle command execution errors.

        Args:
            interaction: The Discord interaction
            error: The exception that occurred
            command_name: Name of the command that failed
        """
        await self.handle_error(interaction, error, command_name)

class ErrorHandlerMixin(ErrorHandlingMixin):
    """
    A mixin class providing error handling functionality for cogs.
    """
    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Default error handler for application commands in this cog."""
        logging.debug(f"Command error occurred: {error.__class__.__name__}")
        
        if isinstance(error, discord.app_commands.CommandInvokeError):
            error = error.original
        elif isinstance(error, discord.app_commands.CheckFailure):
            await self.send_error_message(
                interaction,
                self.translations["error_check_failure"],
                ephemeral=True
            )
            return
        elif isinstance(error, discord.app_commands.CommandOnCooldown):
            await self.send_error_message(
                interaction,
                self.translations["error_cooldown"],
                ephemeral=True
            )
            return
        await self.handle_error(interaction, error)
