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

from utils.error_handler import (
    ErrorContext,
    handle_command_error
)

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
        name="about",
        description="Display information about the bot"
    )
    async def about(self, interaction: discord.Interaction) -> None:
        """
        Display information about TGraph Bot.

        Args:
            interaction: The Discord interaction
        """
        try:
            # Import i18n for translations
            import i18n
            
            embed = discord.Embed(
                title=i18n.translate("TGraph Bot"),
                description=i18n.translate("TGraph Bot - Tautulli Discord Graph Generator"),
                color=discord.Color.blue()
            )

            _ = embed.add_field(
                name="Version",
                value="1.0.0",
                inline=True
            )

            _ = embed.add_field(
                name="Author",
                value="engels74",
                inline=True
            )

            _ = embed.add_field(
                name="GitHub",
                value="[tgraph-bot-source](https://github.com/engels74/tgraph-bot-source)",
                inline=True
            )

            _ = embed.add_field(
                name="License",
                value="AGPL-3.0",
                inline=True
            )

            _ = embed.add_field(
                name="Python Version",
                value="3.13+",
                inline=True
            )

            _ = embed.add_field(
                name="Discord.py Version",
                value=discord.__version__,
                inline=True
            )

            _ = embed.set_footer(text="TGraph Bot - Bringing Tautulli stats to Discord")

            _ = await interaction.response.send_message(embed=embed)

        except Exception as e:
            # Create error context for comprehensive logging
            context = ErrorContext(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id if interaction.guild else None,
                channel_id=interaction.channel.id if interaction.channel else None,
                command_name="about"
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
