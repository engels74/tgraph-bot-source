"""
Uptime command for TGraph Bot.

This module defines the /uptime slash command, which displays
how long the bot has been running since its last start.
"""

import logging
import time
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ... import i18n
from ...utils.core.error_handler import ErrorContext, handle_command_error

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class UptimeCog(commands.Cog):
    """Cog for the /uptime command."""

    def __init__(self, bot: commands.Bot) -> None:
        """
        Initialize the Uptime cog.

        Args:
            bot: The Discord bot instance
        """
        self.bot: commands.Bot = bot

    @app_commands.command(name="uptime", description=i18n.translate("Show bot uptime"))
    async def uptime(self, interaction: discord.Interaction) -> None:
        """
        Display how long the bot has been running.

        Args:
            interaction: The Discord interaction
        """
        try:
            # Get start time from bot instance
            start_time = getattr(self.bot, "start_time", time.time())
            current_time = time.time()
            uptime_seconds = int(current_time - start_time)

            # Calculate uptime components
            days = uptime_seconds // 86400
            hours = (uptime_seconds % 86400) // 3600
            minutes = (uptime_seconds % 3600) // 60
            seconds = uptime_seconds % 60

            # Format uptime string with internationalization
            uptime_parts: list[str] = []
            if days > 0:
                uptime_parts.append(i18n.ngettext("{n} day", "{n} days", days))
            if hours > 0:
                uptime_parts.append(i18n.ngettext("{n} hour", "{n} hours", hours))
            if minutes > 0:
                uptime_parts.append(i18n.ngettext("{n} minute", "{n} minutes", minutes))
            if seconds > 0 or not uptime_parts:
                uptime_parts.append(i18n.ngettext("{n} second", "{n} seconds", seconds))

            uptime_string = ", ".join(uptime_parts)

            embed = discord.Embed(
                title=i18n.translate("Bot Uptime"), color=discord.Color.green()
            )

            _ = embed.add_field(
                name=i18n.translate("Uptime"), value=uptime_string, inline=False
            )

            _ = embed.add_field(
                name=i18n.translate("Started"),
                value=f"<t:{int(start_time)}:F>",
                inline=False,
            )

            _ = embed.set_footer(text=i18n.translate("TGraph Bot is running smoothly!"))

            _ = await interaction.response.send_message(embed=embed)

        except Exception as e:
            # Create error context for comprehensive logging
            context = ErrorContext(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id if interaction.guild else None,
                channel_id=interaction.channel.id if interaction.channel else None,
                command_name="uptime",
            )

            # Use enhanced error handling
            await handle_command_error(interaction, e, context)


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(UptimeCog(bot))
