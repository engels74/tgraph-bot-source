"""
About command for TGraph Bot.

This module defines the /about slash command, which displays
information about the bot including description, GitHub link, and license.
"""

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

import i18n
from utils.core.error_handler import ErrorContext, handle_command_error
from utils.core.version import get_version

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AboutCog(commands.Cog):
    """Cog for the /about command."""

    def __init__(self, bot: commands.Bot) -> None:
        """
        Initialize the About cog.

        Args:
            bot: The Discord bot instance
        """
        self.bot: commands.Bot = bot

    @app_commands.command(
        name="about", description=i18n.translate("Display information about the bot")
    )
    async def about(self, interaction: discord.Interaction) -> None:
        """
        Display information about TGraph Bot.

        Args:
            interaction: The Discord interaction
        """
        try:
            embed = discord.Embed(
                title=i18n.translate("TGraph Bot"),
                description=i18n.translate(
                    "TGraph Bot - Tautulli Discord Graph Generator"
                ),
                color=discord.Color.blue(),
            )

            _ = embed.add_field(
                name=i18n.translate("Version"), value=get_version(), inline=True
            )

            _ = embed.add_field(
                name=i18n.translate("Author"), value="engels74", inline=True
            )

            _ = embed.add_field(
                name=i18n.translate("GitHub"),
                value="[tgraph-bot-source](https://github.com/engels74/tgraph-bot-source)",
                inline=True,
            )

            _ = embed.add_field(
                name=i18n.translate("License"), value="AGPL-3.0", inline=True
            )

            _ = embed.add_field(
                name=i18n.translate("Wiki"),
                value="https://github.com/engels74/tgraph-bot/wiki",
                inline=True,
            )

            _ = embed.set_footer(
                text=i18n.translate("TGraph Bot - Bringing Tautulli stats to Discord")
            )

            _ = await interaction.response.send_message(embed=embed)

        except Exception as e:
            # Create error context for comprehensive logging
            context = ErrorContext(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id if interaction.guild else None,
                channel_id=interaction.channel.id if interaction.channel else None,
                command_name="about",
            )

            # Use enhanced error handling
            await handle_command_error(interaction, e, context)


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(AboutCog(bot))
