"""
Graph update command for TGraph Bot.

This module defines the /update_graphs slash command, allowing administrators
to manually trigger the regeneration and posting of server-wide statistics graphs.

Command Design Specifications:
- Name: /update_graphs
- Description: Manually update server graphs
- Permissions: Requires manage_guild permission (admin only)
- Cooldowns: Configurable per-user and global cooldowns
- Parameters: None (simple trigger command)
- Response: Ephemeral acknowledgment, then public posting of graphs
- Error Handling: Comprehensive with user-friendly messages
- Progress Tracking: Real-time feedback during generation
- File Upload: Automatic posting to configured Discord channel
"""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from graphs.graph_manager import GraphManager
from utils.command_utils import create_error_embed, create_success_embed, create_info_embed

if TYPE_CHECKING:
    from main import TGraphBot

logger = logging.getLogger(__name__)


class UpdateGraphsCog(commands.Cog):
    """
    Cog for manual graph update commands.

    This cog implements the /update_graphs slash command with:
    - Admin-only permissions (manage_guild required)
    - Configurable cooldowns for rate limiting
    - Non-blocking graph generation using GraphManager
    - Automatic posting to configured Discord channel
    - Comprehensive error handling and user feedback
    - Progress tracking during generation process
    """

    def __init__(self, bot: commands.Bot) -> None:
        """
        Initialize the UpdateGraphs cog.

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
        name="update_graphs",
        description="Manually trigger server-wide graph generation and posting"
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def update_graphs(self, interaction: discord.Interaction) -> None:
        """
        Manually trigger server-wide graph generation and posting.

        This command:
        1. Acknowledges the request with ephemeral message
        2. Uses GraphManager for non-blocking graph generation
        3. Posts generated graphs to configured Discord channel
        4. Provides progress feedback and error handling
        5. Respects configured cooldowns for rate limiting

        Args:
            interaction: The Discord interaction
        """
        # Acknowledge the command immediately
        embed = create_info_embed(
            title="Graph Update Started",
            description="Generating server graphs... This may take a few minutes."
        )
        _ = embed.add_field(
            name="Status",
            value="🔄 Initializing graph generation",
            inline=False
        )
        _ = embed.add_field(
            name="Estimated Time",
            value="2-5 minutes depending on data size",
            inline=False
        )

        _ = await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            # Get configuration for channel posting
            config = self.tgraph_bot.config_manager.get_current_config()
            target_channel = self.bot.get_channel(config.CHANNEL_ID)

            if target_channel is None:
                error_embed = create_error_embed(
                    title="Configuration Error",
                    description=f"Could not find Discord channel with ID: {config.CHANNEL_ID}"
                )
                _ = await interaction.followup.send(embed=error_embed, ephemeral=True)
                return

            # Verify channel is a text channel
            if not isinstance(target_channel, discord.TextChannel):
                error_embed = create_error_embed(
                    title="Configuration Error",
                    description=f"Channel {config.CHANNEL_ID} is not a text channel"
                )
                _ = await interaction.followup.send(embed=error_embed, ephemeral=True)
                return

            # Progress tracking callback for user feedback (must be sync)
            def progress_callback(message: str, current: int, total: int, metadata: dict[str, object]) -> None:
                """Update user on progress (sync callback for GraphManager)."""
                try:
                    # Schedule the async update in the event loop
                    _ = asyncio.create_task(self._update_progress_embed(interaction, message, current, total, metadata))
                except Exception as e:
                    logger.warning(f"Failed to schedule progress update: {e}")

            # Generate graphs using GraphManager
            async with GraphManager(self.tgraph_bot.config_manager) as graph_manager:
                graph_files = await graph_manager.generate_all_graphs(
                    progress_callback=progress_callback,
                    max_retries=3,
                    timeout_seconds=300.0
                )

                if not graph_files:
                    warning_embed = create_error_embed(
                        title="No Graphs Generated",
                        description="No graph files were created. This may be due to insufficient data or configuration issues."
                    )
                    _ = await interaction.followup.send(embed=warning_embed, ephemeral=True)
                    return

                # Post graphs to configured channel
                success_count = await self._post_graphs_to_channel(target_channel, graph_files)

                # Send completion message
                if success_count == len(graph_files):
                    success_embed = create_success_embed(
                        title="Graph Update Complete",
                        description=f"Successfully generated and posted {success_count} graphs to {target_channel.mention}"
                    )
                    _ = success_embed.add_field(
                        name="Generated Graphs",
                        value=f"{len(graph_files)} files",
                        inline=True
                    )
                    _ = success_embed.add_field(
                        name="Posted Successfully",
                        value=f"{success_count} files",
                        inline=True
                    )
                else:
                    warning_embed = create_error_embed(
                        title="Partial Success",
                        description=f"Generated {len(graph_files)} graphs but only posted {success_count} successfully"
                    )
                    _ = warning_embed.add_field(
                        name="Check Logs",
                        value="Some files may have failed to upload",
                        inline=False
                    )
                    _ = await interaction.followup.send(embed=warning_embed, ephemeral=True)
                    return

                _ = await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            logger.exception(f"Error updating graphs: {e}")

            error_embed = create_error_embed(
                title="Graph Update Failed",
                description="An error occurred while generating or posting graphs."
            )
            _ = error_embed.add_field(
                name="Error Details",
                value=str(e)[:1000] + ("..." if len(str(e)) > 1000 else ""),
                inline=False
            )
            _ = error_embed.add_field(
                name="Next Steps",
                value="Check bot logs for detailed error information",
                inline=False
            )

            _ = await interaction.followup.send(embed=error_embed, ephemeral=True)

    async def _update_progress_embed(
        self,
        interaction: discord.Interaction,
        message: str,
        current: int,
        total: int,
        metadata: dict[str, object]
    ) -> None:
        """
        Update the interaction with progress information.

        Args:
            interaction: The Discord interaction to update
            message: Progress message
            current: Current step
            total: Total steps
            metadata: Additional metadata
        """
        try:
            progress_embed = create_info_embed(
                title="Graph Generation Progress",
                description=f"Step {current}/{total}: {message}"
            )

            # Add progress bar
            progress_percentage = (current / total * 100) if total > 0 else 0
            progress_bar_length = 20
            filled_length = int(progress_bar_length * current // total) if total > 0 else 0
            progress_bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)

            _ = progress_embed.add_field(
                name="Progress",
                value=f"`{progress_bar}` {progress_percentage:.1f}%",
                inline=False
            )

            if metadata:
                if "elapsed_time" in metadata:
                    _ = progress_embed.add_field(
                        name="Elapsed Time",
                        value=f"{metadata['elapsed_time']:.1f}s",
                        inline=True
                    )

            _ = await interaction.edit_original_response(embed=progress_embed)
        except Exception as e:
            logger.warning(f"Failed to update progress embed: {e}")

    async def _post_graphs_to_channel(
        self,
        channel: discord.TextChannel,
        graph_files: list[str]
    ) -> int:
        """
        Post generated graph files to a Discord channel.

        Args:
            channel: Discord channel to post to
            graph_files: List of file paths to graph images

        Returns:
            Number of files successfully posted
        """
        success_count = 0

        try:
            for file_path in graph_files:
                try:
                    file_path_obj = Path(file_path)
                    if not file_path_obj.exists():
                        logger.warning(f"Graph file not found: {file_path}")
                        continue

                    # Create Discord file object
                    with file_path_obj.open('rb') as f:
                        discord_file = discord.File(f, filename=file_path_obj.name)

                        # Send the file to the channel
                        _ = await channel.send(file=discord_file)
                        success_count += 1
                        logger.debug(f"Successfully posted graph: {file_path_obj.name}")

                except Exception as e:
                    logger.error(f"Failed to post graph {file_path}: {e}")
                    continue

        except Exception as e:
            logger.exception(f"Error posting graphs to channel {channel.id}: {e}")

        logger.info(f"Posted {success_count}/{len(graph_files)} graphs to channel {channel.id}")
        return success_count


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.
    
    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(UpdateGraphsCog(bot))
