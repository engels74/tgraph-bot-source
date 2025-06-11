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
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from graphs.graph_manager import GraphManager
from utils.command_utils import create_error_embed, create_success_embed, create_info_embed, create_cooldown_embed
from utils.discord_file_utils import upload_files_to_channel
from utils.error_handler import (
    ErrorContext,
    handle_command_error,
    APIError,
    NetworkError,
    ConfigurationError,
    error_handler
)

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
        # Store cooldown tracking
        self._user_cooldowns: dict[int, float] = {}
        self._global_cooldown: float = 0.0

    @property
    def tgraph_bot(self) -> "TGraphBot":
        """Get the TGraphBot instance with type safety."""
        from main import TGraphBot
        if not isinstance(self.bot, TGraphBot):
            raise TypeError("Bot must be a TGraphBot instance")
        return self.bot

    def _check_cooldowns(self, interaction: discord.Interaction) -> tuple[bool, float]:
        """
        Check if the user is on cooldown for the update_graphs command.

        Args:
            interaction: The Discord interaction

        Returns:
            Tuple of (is_on_cooldown, retry_after_seconds)
        """
        import time

        current_time = time.time()
        config = self.tgraph_bot.config_manager.get_current_config()

        # Check global cooldown
        global_cooldown_seconds = config.UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS
        if global_cooldown_seconds > 0:
            if current_time < self._global_cooldown:
                return True, self._global_cooldown - current_time

        # Check per-user cooldown
        user_cooldown_seconds = config.UPDATE_GRAPHS_COOLDOWN_MINUTES * 60
        if user_cooldown_seconds > 0:
            user_id = interaction.user.id
            if user_id in self._user_cooldowns:
                if current_time < self._user_cooldowns[user_id]:
                    return True, self._user_cooldowns[user_id] - current_time

        return False, 0.0

    def _update_cooldowns(self, interaction: discord.Interaction) -> None:
        """
        Update cooldown timers after successful command execution.

        Args:
            interaction: The Discord interaction
        """
        import time

        current_time = time.time()
        config = self.tgraph_bot.config_manager.get_current_config()

        # Update global cooldown
        global_cooldown_seconds = config.UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS
        if global_cooldown_seconds > 0:
            self._global_cooldown = current_time + global_cooldown_seconds

        # Update per-user cooldown
        user_cooldown_seconds = config.UPDATE_GRAPHS_COOLDOWN_MINUTES * 60
        if user_cooldown_seconds > 0:
            user_id = interaction.user.id
            self._user_cooldowns[user_id] = current_time + user_cooldown_seconds

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
        1. Checks cooldowns and rate limits
        2. Acknowledges the request with ephemeral message
        3. Uses GraphManager for non-blocking graph generation
        4. Posts generated graphs to configured Discord channel
        5. Provides progress feedback and error handling
        6. Updates cooldowns after successful execution

        Args:
            interaction: The Discord interaction
        """
        # Check cooldowns first
        is_on_cooldown, retry_after = self._check_cooldowns(interaction)
        if is_on_cooldown:
            cooldown_embed = create_cooldown_embed("update graphs", retry_after)
            _ = await interaction.response.send_message(embed=cooldown_embed, ephemeral=True)
            return

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
                raise ConfigurationError(
                    f"Could not find Discord channel with ID: {config.CHANNEL_ID}",
                    user_message=f"Could not find Discord channel with ID: {config.CHANNEL_ID}. Please check the bot configuration."
                )

            # Verify channel is a text channel
            if not isinstance(target_channel, discord.TextChannel):
                raise ConfigurationError(
                    f"Channel {config.CHANNEL_ID} is not a text channel",
                    user_message=f"Channel {config.CHANNEL_ID} is not a text channel. Please configure a valid text channel."
                )

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

                # Update cooldowns after successful execution
                self._update_cooldowns(interaction)

        except Exception as e:
            # Create error context for comprehensive logging
            try:
                config = self.tgraph_bot.config_manager.get_current_config()
                target_channel_id = config.CHANNEL_ID
            except Exception:
                target_channel_id = None

            context = ErrorContext(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id if interaction.guild else None,
                channel_id=interaction.channel.id if interaction.channel else None,
                command_name="update_graphs",
                additional_context={
                    "target_channel_id": target_channel_id
                }
            )

            # Use enhanced error handling
            await handle_command_error(interaction, e, context)

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

    @error_handler(retry_attempts=2, retry_delay=1.0)
    async def _post_graphs_to_channel(
        self,
        channel: discord.TextChannel,
        graph_files: list[str]
    ) -> int:
        """
        Post generated graph files to a Discord channel with enhanced validation and error handling.

        Args:
            channel: Discord channel to post to
            graph_files: List of file paths to graph images

        Returns:
            Number of files successfully posted

        Raises:
            APIError: If Discord API fails
            NetworkError: If network issues occur
        """
        if not graph_files:
            logger.warning("No graph files provided for posting")
            return 0

        try:
            # Create embed for the graph posting
            embed = create_info_embed(
                title="📊 Server Statistics Update",
                description="Fresh server statistics graphs generated!"
            )
            _ = embed.add_field(
                name="Generated",
                value=f"{len(graph_files)} graphs",
                inline=True
            )
            _ = embed.set_footer(text="Generated by TGraph Bot")

            # Use the enhanced file upload utility
            upload_result = await upload_files_to_channel(
                channel=channel,
                file_paths=graph_files,
                embed=embed,
                use_nitro_limits=False  # Use regular Discord limits for server posting
            )

            if upload_result.success:
                logger.info(f"Successfully posted {upload_result.files_uploaded}/{len(graph_files)} graphs to channel {channel.id}")
                return upload_result.files_uploaded
            else:
                # Convert upload failure to appropriate exception
                error_msg = f"Failed to post graphs to channel {channel.id}: {upload_result.error_message}"
                logger.error(error_msg)

                # Classify the error type based on the error message
                error_message = upload_result.error_message or "Unknown upload error"
                if "rate limit" in error_message.lower():
                    raise APIError(error_msg, user_message="Discord rate limit reached. Please try again later.")
                elif "permission" in error_message.lower():
                    raise APIError(error_msg, user_message="Bot lacks permission to post in the configured channel.")
                else:
                    raise APIError(error_msg, user_message="Failed to upload graphs to Discord.")

        except discord.Forbidden as e:
            raise APIError(f"Permission denied while posting graphs: {e}", user_message="Bot lacks permission to post in the configured channel.") from e
        except discord.HTTPException as e:
            raise APIError(f"Discord API error while posting graphs: {e}", user_message="Discord API error occurred while posting graphs.") from e
        except Exception as e:
            raise NetworkError(f"Unexpected error while posting graphs: {e}", user_message="Network error occurred while posting graphs.") from e


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.
    
    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(UpdateGraphsCog(bot))
