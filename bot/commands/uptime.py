# bot/commands/uptime.py

"""
Uptime command for TGraph Bot.
Tracks and displays the bot's running time since startup.
"""

from datetime import datetime, timezone, timedelta
from discord import app_commands
from discord.ext import commands
from typing import Any, Dict
from utils.command_utils import CommandMixin, ErrorHandlerMixin
import discord
import logging

class UptimeCog(commands.Cog, CommandMixin, ErrorHandlerMixin):
    """Cog for handling uptime tracking and display."""
    
    def __init__(self, bot: commands.Bot, config: Dict[str, Any], translations: Dict[str, str]):
        """Initialize the UptimeCog.
        
        Parameters
        ----------
        bot : commands.Bot
            The bot instance
        config : Dict[str, Any]
            Configuration dictionary
        translations : Dict[str, str]
            Translation strings dictionary
        """
        self.bot = bot
        self.config = config
        self.translations = translations
        # Store start time in UTC
        self.start_time = datetime.now(timezone.utc)
        # Initialize both mixins
        CommandMixin.__init__(self)
        ErrorHandlerMixin.__init__(self)
        super().__init__()  # Initialize Cog

    def format_uptime(self, delta: timedelta) -> str:
        """Format a timedelta into a human-readable string.
        
        Parameters
        ----------
        delta : timedelta
            The time difference to format
            
        Returns
        -------
        str
            Formatted uptime string
        """
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or not parts:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

        return ", ".join(parts)

    @app_commands.command(
        name="uptime",
        description="Show the bot's uptime"
    )
    async def uptime(self, interaction: discord.Interaction) -> None:
        """Show the bot's uptime since last startup.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance
        """
        try:
            # Get current time in UTC for consistency
            current_time = datetime.now(timezone.utc)
            uptime_delta = current_time - self.start_time

            # Format the uptime
            formatted_uptime = self.format_uptime(uptime_delta)

            # Send response
            response_message = self.translations["uptime_response"].format(
                uptime=formatted_uptime
            )
            
            await interaction.response.send_message(
                response_message,
                ephemeral=True
            )

            # Log command execution
            await self.log_command(interaction, "uptime")

        except Exception as e:
            logging.error(f"Error in uptime command: {str(e)}")
            await self.handle_error(interaction, e, "uptime")

async def setup(bot: commands.Bot) -> None:
    """Setup function for the uptime cog.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance
    """
    try:
        await bot.add_cog(UptimeCog(bot, bot.config, bot.translations))
    except Exception as e:
        logging.error(f"Failed to add UptimeCog: {e}")
        raise commands.ExtensionError(f"Failed to load UptimeCog: {e}") from e
