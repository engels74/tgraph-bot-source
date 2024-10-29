# bot/commands/uptime.py

"""
Uptime command for TGraph Bot.
Tracks and displays the bot's running time since startup.
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from utils.command_utils import CommandMixin, ErrorHandlerMixin

class UptimeCog(commands.Cog, CommandMixin, ErrorHandlerMixin):
    """Cog for handling uptime tracking and display."""
    
    def __init__(self, bot: commands.Bot, config: dict, translations: dict):
        self.bot = bot
        self.config = config
        self.translations = translations
        self.start_time = datetime.now().astimezone()
        CommandMixin.__init__(self)

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
        # Optional cooldown check - uncomment if needed
        # if not await self.check_cooldowns(interaction, 1, 30):  # 1 min user, 30 sec global
        #     return

        try:
            current_time = datetime.now().astimezone()
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
            if seconds > 0 or not uptime_parts:  # Include seconds if it's the only non-zero value
                uptime_parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

            formatted_uptime = ", ".join(uptime_parts)

            await interaction.response.send_message(
                self.translations["uptime_response"].format(uptime=formatted_uptime),
                ephemeral=True
            )

            # Log successful command execution
            await self.log_command(interaction, "uptime")

            # Update cooldowns if they were implemented
            # self.update_cooldowns(str(interaction.user.id), 1, 30)

        except Exception:
            # Let the mixin's error handler handle it
            raise

async def setup(bot: commands.Bot) -> None:
    """Setup function for the uptime cog.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance
    """
    await bot.add_cog(UptimeCog(bot, bot.config, bot.translations))
