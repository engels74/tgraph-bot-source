# bot/commands/uptime.py

"""
Uptime command for TGraph Bot.
Tracks and displays the bot's running time since startup.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime, timezone
from typing import Any, Dict
from utils.command_utils import CommandMixin, ErrorHandlerMixin

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
        # Use UTC as base timezone for consistent time handling
        self.start_time = datetime.now(timezone.utc).astimezone()
        # Initialize both mixins
        CommandMixin.__init__(self)
        ErrorHandlerMixin.__init__(self)
        super().__init__()  # Initialize Cog

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

        Raises
        ------
        ValueError
            If there's an error calculating the uptime
        KeyError
            If required translation keys are missing
        Exception
            For any other unexpected errors
        """
        try:
            # Use UTC for consistent time calculation
            current_time = datetime.now(timezone.utc).astimezone()
            uptime = current_time - self.start_time

            # Format the uptime in a readable way
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            # Build the uptime string with proper pluralization
            uptime_parts = []
            if days > 0:
                uptime_parts.append(f"{days} day{'s' if days != 1 else ''}")
            if hours > 0:
                uptime_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes > 0:
                uptime_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            if seconds > 0 or not uptime_parts:
                uptime_parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

            formatted_uptime = ", ".join(uptime_parts)

            try:
                response_message = self.translations["uptime_response"].format(
                    uptime=formatted_uptime
                )
            except KeyError as ke:
                logging.error(f"Missing translation key: {ke}")
                raise KeyError(f"Missing required translation key: {ke}") from ke

            await interaction.response.send_message(
                response_message,
                ephemeral=True
            )

            # Log command execution
            try:
                await self.log_command(interaction, "uptime")
            except Exception as e:
                logging.error(f"Failed to log uptime command: {e}")

        except ValueError as ve:
            logging.error(f"Error calculating uptime: {ve}")
            raise
        except KeyError as ke:
            logging.error(f"Missing translation key: {ke}")
            raise
        except discord.HTTPException as he:
            logging.error(f"Discord API error: {he}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in uptime command: {e}")
            raise

async def setup(bot: commands.Bot) -> None:
    """Setup function for the uptime cog.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance

    Raises
    ------
    commands.ExtensionError
        If the cog cannot be added to the bot
    """
    try:
        await bot.add_cog(UptimeCog(bot, bot.config, bot.translations))
    except Exception as e:
        logging.error(f"Failed to add UptimeCog: {e}")
        raise commands.ExtensionError(f"Failed to load UptimeCog: {e}") from e
