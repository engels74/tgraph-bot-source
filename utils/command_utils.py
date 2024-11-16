# utils/command_utils.py

from datetime import datetime, timedelta
from discord.utils import utcnow
from typing import Optional, Tuple
import discord
import logging

class ErrorHandlingMixin:
    """A mixin class providing common error handling functionality.
    
    This mixin requires the implementing class to provide a `translations` dictionary
    containing the following keys:
        - log_command_error: Format string with {command} and {error} placeholders
        - error_processing_command: Generic error message for command processing failures
    
    Attributes:
        translations (dict): Must be provided by the implementing class
    """
    async def handle_error(self, interaction: discord.Interaction, error: Exception, command_name: str = None) -> None:
        logging.error(
            self.translations["log_command_error"].format(
                command=command_name or (interaction.command.qualified_name if interaction.command else "Unknown"),
                error=str(error)
            )
        )
        await self.send_error_message(
            interaction, self.translations["error_processing_command"]
        )

    async def send_error_message(self, interaction: discord.Interaction, error_message: str, ephemeral: bool = True) -> None:
        """Send an error message with proper interaction response handling."""
        try:
            # Check if we can use response
            if not interaction.response.is_done():
                await interaction.response.send_message(error_message, ephemeral=ephemeral)
            else:
                # Use followup if response is already sent
                await interaction.followup.send(error_message, ephemeral=ephemeral)
        except discord.DiscordException as e:
            logging.error(f"Failed to send error message: {str(e)}")

class CommandMixin(ErrorHandlingMixin):
    def __init__(self):
        self.user_cooldowns = {}
        self.global_cooldown = None
        super().__init__()

    def format_time_remaining(self, seconds: float) -> str:
        """Format remaining time into a human-readable string."""
        if seconds < 60:
            return f"{int(seconds)} seconds"
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        if remaining_seconds == 0:
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        return f"{minutes} minute{'s' if minutes != 1 else ''} and {remaining_seconds} seconds"

    def get_remaining_time(self, target_time: Optional[datetime]) -> float:
        """Get remaining time in seconds."""
        if not target_time:
            return 0
        now = utcnow()
        return max(0, (target_time - now).total_seconds())

    def _cleanup_cooldowns(self) -> None:
        """Remove expired cooldowns."""
        now = utcnow()
        self.user_cooldowns = {
            user_id: cooldown 
            for user_id, cooldown in self.user_cooldowns.items() 
            if cooldown > now
        }
        if self.global_cooldown and self.global_cooldown <= now:
            self.global_cooldown = None

    def get_cooldown_status(self, user_id: str, user_minutes: int, global_seconds: int) -> Tuple[float, float]:
        """Get remaining cooldown times.
        
        Returns:
            Tuple of (user_remaining, global_remaining) in seconds
        """
        self._cleanup_cooldowns()
        
        user_remaining = 0
        global_remaining = 0

        if user_minutes > 0 and user_id in self.user_cooldowns:
            user_remaining = self.get_remaining_time(self.user_cooldowns[user_id])

        if global_seconds > 0 and self.global_cooldown:
            global_remaining = self.get_remaining_time(self.global_cooldown)

        return user_remaining, global_remaining

    async def check_cooldowns(
        self, 
        interaction: discord.Interaction, 
        user_minutes: int, 
        global_seconds: int
    ) -> bool:
        """Check if command is on cooldown."""
        if user_minutes <= 0 and global_seconds <= 0:
            return True

        user_remaining, global_remaining = self.get_cooldown_status(
            str(interaction.user.id),
            user_minutes,
            global_seconds
        )

        if user_remaining > 0 or global_remaining > 0:
            message_parts = []
            
            if user_remaining > 0:
                message_parts.append(
                    self.translations["rate_limit_personal"].format(
                        time=self.format_time_remaining(user_remaining)
                    )
                )
            
            if global_remaining > 0:
                message_parts.append(
                    self.translations["rate_limit_global"].format(
                        time=self.format_time_remaining(global_remaining)
                    )
                )

            cooldown_message = f"{self.translations['rate_limit_message']} ({', '.join(message_parts)})"
            
            # Use send_error_message to handle interaction responses consistently
            await self.send_error_message(interaction, cooldown_message, ephemeral=True)
            return False

        return True

    def update_cooldowns(self, user_id: str, user_minutes: int, global_seconds: int) -> None:
        """Set new cooldowns after command use."""
        now = utcnow()

        if user_minutes > 0:
            self.user_cooldowns[user_id] = now + timedelta(minutes=user_minutes)

        if global_seconds > 0:
            self.global_cooldown = now + timedelta(seconds=global_seconds)

        logging.debug(
            f"Updated cooldowns - User {user_id}: {self.user_cooldowns.get(user_id)}, "
            f"Global: {self.global_cooldown}"
        )

    async def log_command(self, interaction: discord.Interaction, command_name: str) -> None:
        logging.info(
            self.translations["log_command_executed"].format(
                command=command_name,
                user=f"{interaction.user.name}#{interaction.user.discriminator}",
            )
        )

    async def handle_command_error(self, interaction: discord.Interaction, error: Exception, command_name: str) -> None:
        await self.handle_error(interaction, error, command_name)

class ErrorHandlerMixin(ErrorHandlingMixin):
    """A mixin class providing error handling functionality for cogs.
    
    This mixin requires the implementing class to provide a `translations` dictionary
    containing the following keys:
        - error_check_failure: Message for permission/check failures
        - error_cooldown: Message for cooldown violations
        - error_processing_command: Generic error message (inherited from ErrorHandlingMixin)
        - log_command_error: Format string (inherited from ErrorHandlingMixin)
    
    Attributes:
        translations (dict): Must be provided by the implementing class
    """
    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
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
