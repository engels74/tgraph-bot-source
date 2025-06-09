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
        self.bot = bot
        
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
        embed = discord.Embed(
            title="TGraph Bot",
            description="A Discord bot for automatically generating and posting Tautulli graphs",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Version",
            value="1.0.0",
            inline=True
        )
        
        embed.add_field(
            name="Author",
            value="engels74",
            inline=True
        )
        
        embed.add_field(
            name="GitHub",
            value="[tgraph-bot-source](https://github.com/engels74/tgraph-bot-source)",
            inline=True
        )
        
        embed.add_field(
            name="License",
            value="MIT License",
            inline=True
        )
        
        embed.add_field(
            name="Python Version",
            value="3.13+",
            inline=True
        )
        
        embed.add_field(
            name="Discord.py Version",
            value=discord.__version__,
            inline=True
        )
        
        embed.set_footer(text="TGraph Bot - Bringing Tautulli stats to Discord")
        
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.
    
    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(AboutCog(bot))
