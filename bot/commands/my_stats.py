"""
Personal statistics command for TGraph Bot.

This module defines the /my_stats slash command, allowing users to request
their personal Plex statistics (graphs) via DM by providing their Plex email.

Command Design Specifications:
- Name: /my_stats
- Description: Get your personal Plex statistics
- Parameters: email (required) - User's Plex account email address
- Permissions: Available to all users (no restrictions)
- Cooldowns: 5 minutes per-user, 60 seconds global
- Response: Ephemeral acknowledgment, then private DM with graphs
- Error Handling: Comprehensive with user-friendly messages
- Privacy: Email-based user identification for Plex statistics
- File Upload: Automatic DM delivery of personal graph images
"""

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from graphs.user_graph_manager import UserGraphManager
from utils.command_utils import create_error_embed, create_success_embed, create_info_embed

if TYPE_CHECKING:
    from main import TGraphBot

logger = logging.getLogger(__name__)


class MyStatsCog(commands.Cog):
    """
    Cog for personal statistics commands.

    This cog implements the /my_stats slash command with:
    - Email-based user identification for Plex statistics
    - Personal graph generation via UserGraphManager
    - Private DM delivery of generated graphs
    - Configurable cooldowns for rate limiting
    - Comprehensive error handling and user feedback
    - Non-blocking graph generation using async threading
    """

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
        description="Get your personal Plex statistics via DM"
    )
    @app_commands.describe(
        email="Your Plex account email address (used to identify your statistics)"
    )
    async def my_stats(
        self,
        interaction: discord.Interaction,
        email: str
    ) -> None:
        """
        Generate and send personal Plex statistics to the user via DM.

        This command:
        1. Validates the provided email format
        2. Uses UserGraphManager for non-blocking graph generation
        3. Sends generated graphs privately via Discord DM
        4. Provides progress feedback and error handling
        5. Respects configured cooldowns for rate limiting

        Args:
            interaction: The Discord interaction
            email: The user's Plex email address for identification
        """
        # Basic email validation
        if not email or "@" not in email or "." not in email:
            error_embed = create_error_embed(
                title="Invalid Email",
                description="Please provide a valid email address."
            )
            _ = error_embed.add_field(
                name="Example",
                value="user@example.com",
                inline=False
            )
            _ = await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Acknowledge the command with informative message
        embed = create_info_embed(
            title="Personal Statistics Request",
            description="Generating your personal Plex statistics... This may take a moment."
        )
        _ = embed.add_field(
            name="Email",
            value=email,
            inline=True
        )
        _ = embed.add_field(
            name="Delivery Method",
            value="Direct Message (DM)",
            inline=True
        )
        _ = embed.add_field(
            name="Estimated Time",
            value="1-3 minutes",
            inline=True
        )

        _ = await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            # Generate personal graphs using user_graph_manager
            async with UserGraphManager(self.tgraph_bot.config_manager) as user_graph_manager:
                result_stats = await user_graph_manager.process_user_stats_request(
                    user_id=interaction.user.id,
                    user_email=email,
                    bot=self.bot
                )

                if result_stats and result_stats.get("success", False):
                    # Success - graphs were generated and sent
                    success_embed = create_success_embed(
                        title="Personal Statistics Complete",
                        description="Your personal Plex statistics have been generated and sent via DM!"
                    )

                    # Add statistics from the result
                    graphs_generated = result_stats.get("graphs_generated", 0)
                    processing_time = result_stats.get("processing_time", 0)

                    _ = success_embed.add_field(
                        name="Graphs Generated",
                        value=f"{graphs_generated} personal graphs",
                        inline=True
                    )
                    _ = success_embed.add_field(
                        name="Processing Time",
                        value=f"{processing_time:.1f} seconds",
                        inline=True
                    )
                    _ = success_embed.add_field(
                        name="Check Your DMs",
                        value="Your graphs have been sent privately",
                        inline=False
                    )

                    _ = await interaction.followup.send(embed=success_embed, ephemeral=True)
                else:
                    # Error occurred during processing
                    error_embed = create_error_embed(
                        title="Statistics Generation Failed",
                        description="Unable to generate your personal statistics."
                    )
                    _ = error_embed.add_field(
                        name="Possible Causes",
                        value="• Email not found in Plex server\n• Insufficient data for graphs\n• Temporary server issue",
                        inline=False
                    )
                    _ = error_embed.add_field(
                        name="Next Steps",
                        value="• Verify your email is correct\n• Ensure you have Plex activity\n• Try again in a few minutes",
                        inline=False
                    )

                    _ = await interaction.followup.send(embed=error_embed, ephemeral=True)

        except Exception as e:
            logger.exception(f"Error generating personal stats for {interaction.user} ({email}): {e}")

            error_embed = create_error_embed(
                title="Unexpected Error",
                description="An unexpected error occurred while generating your statistics."
            )
            _ = error_embed.add_field(
                name="Error Details",
                value=str(e)[:500] + ("..." if len(str(e)) > 500 else ""),
                inline=False
            )
            _ = error_embed.add_field(
                name="Support",
                value="If this persists, please contact the server administrators",
                inline=False
            )

            _ = await interaction.followup.send(embed=error_embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.
    
    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(MyStatsCog(bot))
