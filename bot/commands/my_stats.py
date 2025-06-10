"""
Personal statistics command for TGraph Bot.

This module defines the /my_stats slash command, allowing users to request
their personal Plex statistics (graphs) via DM by providing their Plex email.
"""

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from graphs.user_graph_manager import UserGraphManager

if TYPE_CHECKING:
    from main import TGraphBot

logger = logging.getLogger(__name__)


class MyStatsCog(commands.Cog):
    """Cog for personal statistics commands."""

    def __init__(self, bot: commands.Bot) -> None:
        """
        Initialize the MyStats cog.

        Args:
            bot: The Discord bot instance
        """
        self.bot: commands.Bot = bot

    @property
    def tgraph_bot(self) -> "TGraphBot":
        """Get the TGraphBot instance with type safety."""
        from main import TGraphBot
        if not isinstance(self.bot, TGraphBot):
            raise TypeError("Bot must be a TGraphBot instance")
        return self.bot
        
    @app_commands.command(
        name="my_stats",
        description="Get your personal Plex statistics"
    )
    @app_commands.describe(
        email="Your Plex account email address"
    )
    async def my_stats(
        self, 
        interaction: discord.Interaction,
        email: str
    ) -> None:
        """
        Generate and send personal Plex statistics to the user via DM.
        
        Args:
            interaction: The Discord interaction
            email: The user's Plex email address
        """
        # TODO: Implement personal statistics generation

        # Acknowledge the command
        _ = await interaction.response.send_message(
            "Generating your personal statistics... This may take a moment.",
            ephemeral=True
        )

        try:
            # Generate personal graphs using user_graph_manager
            async with UserGraphManager(self.tgraph_bot.config_manager) as user_graph_manager:
                success = await user_graph_manager.process_user_stats_request(
                    user_id=interaction.user.id,
                    user_email=email,
                    bot=self.bot
                )

                if success:
                    # Follow up to let user know DM was sent
                    _ = await interaction.followup.send(
                        "Your personal statistics have been generated and sent via DM!",
                        ephemeral=True
                    )
                else:
                    # Error occurred during processing
                    _ = await interaction.followup.send(
                        "An error occurred while generating your statistics. Please check that your email is correct and try again later.",
                        ephemeral=True
                    )
                
        except Exception as e:
            logger.exception(f"Error generating personal stats for {interaction.user}: {e}")
            
            await interaction.followup.send(
                "An error occurred while generating your statistics. Please try again later.",
                ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.
    
    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(MyStatsCog(bot))
