# utils/command_utils.py

import discord
import logging
from datetime import datetime, timedelta

class CommandMixin:
    """
    A mixin class providing common command functionality.
    To be used with commands.Cog classes.
    """
    def __init__(self):
        self.user_cooldowns = {}
        self.global_cooldown = datetime.now()

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
        # Check global cooldown
        if datetime.now() < self.global_cooldown:
            remaining = int((self.global_cooldown - datetime.now()).total_seconds())
            await interaction.response.send_message(
                self.translations["rate_limit_global"].format(
                    time=f"<t:{int((datetime.now() + timedelta(seconds=remaining)).timestamp())}:R>"
                ),
                ephemeral=True,
            )
            return False

        # Check user cooldown
        user_id = str(interaction.user.id)
        if (
            user_id in self.user_cooldowns
            and datetime.now() < self.user_cooldowns[user_id]
        ):
            remaining = int(
                (self.user_cooldowns[user_id] - datetime.now()).total_seconds()
            )
            await interaction.response.send_message(
                self.translations["rate_limit_user"].format(
                    time=f"<t:{int((datetime.now() + timedelta(seconds=remaining)).timestamp())}:R>"
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
        self.user_cooldowns[user_id] = datetime.now() + timedelta(
            minutes=user_minutes
        )
        self.global_cooldown = datetime.now() + timedelta(
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

    async def send_error_message(self, interaction: discord.Interaction, 
                               error_message: str, ephemeral: bool = True) -> None:
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
        except discord.HTTPException as e:
            logging.error(f"Failed to send error message: {str(e)}")

    async def handle_command_error(self, interaction: discord.Interaction, error: Exception, 
                                 command_name: str) -> None:
        """
        Handle command execution errors.

        Args:
            interaction: The Discord interaction
            error: The exception that occurred
            command_name: Name of the command that failed
        """
        logging.error(
            self.translations["log_command_error"].format(
                command=command_name, error=str(error)
            )
        )
        await self.send_error_message(
            interaction, self.translations["error_processing_command"]
        )

class ErrorHandlerMixin:
    """
    A mixin class providing error handling functionality for cogs.
    """
    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Default error handler for application commands in this cog."""
        if isinstance(error, discord.app_commands.CommandInvokeError):
            error = error.original
            
        logging.error(
            self.translations["log_command_error"].format(
                command=interaction.command.qualified_name if interaction.command else "Unknown",
                error=str(error)
            )
        )
        
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    self.translations["error_processing_command"],
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    self.translations["error_processing_command"],
                    ephemeral=True
                )
        except discord.errors.InteractionResponded:
            await interaction.followup.send(
                self.translations["error_processing_command"],
                ephemeral=True
            )
