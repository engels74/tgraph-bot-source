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
        self.bot = bot
        
    @app_commands.command(
        name="uptime",
        description="Show bot uptime"
    )
    async def uptime(self, interaction: discord.Interaction) -> None:
        """
        Display how long the bot has been running.
        
        Args:
            interaction: The Discord interaction
        """
        # Get start time from bot instance
        start_time = getattr(self.bot, 'start_time', time.time())
        current_time = time.time()
        uptime_seconds = int(current_time - start_time)
        
        # Calculate uptime components
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        
        # Format uptime string
        uptime_parts = []
        if days > 0:
            uptime_parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            uptime_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            uptime_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or not uptime_parts:
            uptime_parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
            
        uptime_string = ", ".join(uptime_parts)
        
        embed = discord.Embed(
            title="Bot Uptime",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Uptime",
            value=uptime_string,
            inline=False
        )
        
        embed.add_field(
            name="Started",
            value=f"<t:{int(start_time)}:F>",
            inline=False
        )
        
        embed.set_footer(text="TGraph Bot is running smoothly!")
        
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.
    
    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(UptimeCog(bot))
