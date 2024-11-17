# bot/commands/uptime.py

"""
Uptime command for TGraph Bot.
Tracks and displays the bot's running time since startup with enhanced error handling.
"""

from datetime import datetime, timezone, timedelta
from discord import app_commands
from discord.ext import commands
from typing import Any, Dict
from utils.command_utils import CommandMixin, ErrorHandlerMixin
import discord
import logging

class UptimeError(Exception):
    """Base exception for uptime command errors."""
    pass

class TimeFormatError(UptimeError):
    """Raised when time formatting fails."""
    pass

class CommandError(UptimeError):
    """Raised when command execution fails."""
    pass

class TimeCalculationError(UptimeError):
    """Raised when uptime calculation fails."""
    pass

class UptimeCog(commands.Cog, CommandMixin, ErrorHandlerMixin):
    """Cog for handling uptime tracking and display with enhanced error handling."""
    
    def __init__(self, bot: commands.Bot, config: Dict[str, Any], translations: Dict[str, str]):
        """
        Initialize the UptimeCog with proper error handling.
        
        Parameters
        ----------
        bot : commands.Bot
            The bot instance
        config : Dict[str, Any]
            Configuration dictionary
        translations : Dict[str, str]
            Translation strings dictionary
            
        Raises
        ------
        UptimeError
            If initialization fails
        """
        try:
            self.bot = bot
            self.config = config
            self.translations = translations
            # Store start time in UTC for consistent time calculations
            self.start_time = datetime.now(timezone.utc)
            
            # Initialize both mixins with proper error handling
            CommandMixin.__init__(self)
            ErrorHandlerMixin.__init__(self)
            super().__init__()  # Initialize Cog
            
        except Exception as e:
            error_msg = self.translations.get(
                'error_uptime_init',
                'Failed to initialize uptime tracking: {error}'
            ).format(error=str(e))
            logging.error(error_msg)
            raise UptimeError(error_msg) from e

    def format_uptime(self, delta: timedelta) -> str:
        """
        Format a timedelta into a human-readable string with enhanced validation.
        
        Parameters
        ----------
        delta : timedelta
            The time difference to format
            
        Returns
        -------
        str
            Formatted uptime string
            
        Raises
        ------
        TimeFormatError
            If formatting fails
        ValueError
            If delta is invalid
        """
        try:
            if not isinstance(delta, timedelta):
                raise ValueError("Input must be a timedelta object")

            if delta.total_seconds() < 0:
                raise ValueError("Time delta cannot be negative")

            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            units = {
                'day': days,
                'hour': hours,
                'minute': minutes,
                'second': seconds
            }
            
            parts = []
            for unit, value in units.items():
                if value > 0:
                    parts.append(f"{value} {unit}{'s' if value != 1 else ''}")

            return ", ".join(parts) if parts else "0 seconds"

        except ValueError as e:
            error_msg = self.translations.get(
                'error_time_format',
                'Invalid time format: {error}'
            ).format(error=str(e))
            logging.error(error_msg)
            raise TimeFormatError(error_msg) from e
        except Exception as e:
            error_msg = self.translations.get(
                'error_unexpected_format',
                'Unexpected error formatting uptime: {error}'
            ).format(error=str(e))
            logging.error(error_msg)
            raise TimeFormatError(error_msg) from e

    def calculate_uptime(self) -> timedelta:
        """
        Calculate current uptime with validation.
        
        Returns
        -------
        timedelta
            The calculated uptime
            
        Raises
        ------
        TimeCalculationError
            If calculation fails
        """
        try:
            current_time = datetime.now(timezone.utc)
            if current_time < self.start_time:
                raise ValueError("Current time cannot be before start time")
            return current_time - self.start_time
        except Exception as e:
            error_msg = self.translations.get(
                'error_uptime_calculation',
                'Failed to calculate uptime: {error}'
            ).format(error=str(e))
            logging.error(error_msg)
            raise TimeCalculationError(error_msg) from e

    @app_commands.command(
        name="uptime",
        description="Show the bot's uptime"
    )
    async def uptime(self, interaction: discord.Interaction) -> None:
        """
        Show the bot's uptime since last startup with enhanced error handling.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance
        """
        try:
            uptime_delta = self.calculate_uptime()
            formatted_uptime = self.format_uptime(uptime_delta)

            response_message = self.translations.get(
                "uptime_response",
                "Bot has been running for {uptime}"
            ).format(uptime=formatted_uptime)
            
            await interaction.response.send_message(
                response_message,
                ephemeral=True
            )

            # Log command execution with proper error handling
            await self.log_command(interaction, "uptime")

        except (TimeFormatError, TimeCalculationError) as e:
            await self.handle_error(interaction, e, "uptime")
        except discord.HTTPException as e:
            error_msg = self.translations.get(
                'error_discord_communication',
                'Failed to send uptime message: {error}'
            ).format(error=str(e))
            logging.error(error_msg)
            await self.handle_error(interaction, CommandError(error_msg), "uptime")
        except Exception as e:
            error_msg = self.translations.get(
                'error_unexpected_uptime',
                'Unexpected error in uptime command: {error}'
            ).format(error=str(e))
            logging.error(error_msg)
            await self.handle_error(interaction, CommandError(error_msg), "uptime")

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ) -> None:
        """
        Handle application command errors with proper error chains.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance
        error : app_commands.AppCommandError
            The error that occurred
        """
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original
            if isinstance(error, UptimeError):
                await self.send_error_message(
                    interaction,
                    str(error),
                    ephemeral=True
                )
                return
        await super().cog_app_command_error(interaction, error)

async def setup(bot: commands.Bot) -> None:
    """
    Setup function for the uptime cog with proper error handling.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance
        
    Raises
    ------
    UptimeError
        If cog setup fails
    """
    try:
        await bot.add_cog(UptimeCog(bot, bot.config, bot.translations))
    except Exception as e:
        error_msg = f"Failed to setup uptime cog: {str(e)}"
        logging.error(error_msg)
        raise UptimeError(error_msg) from e
