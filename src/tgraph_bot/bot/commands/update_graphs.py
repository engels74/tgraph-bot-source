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

import logging
from pathlib import Path
from typing import TYPE_CHECKING
import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from ... import i18n
from ...graphs.graph_manager import GraphManager
from ...utils.discord.base_command_cog import BaseCommandCog, BaseCooldownConfig
from ...utils.discord.command_utils import (
    create_error_embed,
    create_success_embed,
    create_info_embed,
    create_cooldown_embed,
)
from ...utils.core.config_utils import ConfigurationHelper
from ...utils.discord.discord_file_utils import (
    validate_file_for_discord,
    create_discord_file_safe,
    create_graph_specific_embed,
)
from ...utils.core.error_handler import APIError, NetworkError, error_handler
from ...utils.discord.progress_utils import ProgressCallbackManager

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class UpdateGraphsCog(BaseCommandCog):
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
        # Configure cooldown settings for this command
        cooldown_config = BaseCooldownConfig(
            user_cooldown_config_key="UPDATE_GRAPHS_COOLDOWN_MINUTES",
            global_cooldown_config_key="UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS",
        )

        # Initialize base class with cooldown configuration
        super().__init__(bot, cooldown_config)

        # Create configuration helper
        self.config_helper: ConfigurationHelper = ConfigurationHelper(
            self.tgraph_bot.config_manager
        )

    @app_commands.command(
        name="update_graphs",
        description=i18n.translate(
            "Manually trigger server-wide graph generation and posting"
        ),
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def update_graphs(self, interaction: discord.Interaction) -> None:
        """
        Manually trigger server-wide graph generation and posting.

        This command:
        1. Checks cooldowns and rate limits
        2. Acknowledges the request with ephemeral message
        3. Cleans up previous bot messages from the target channel
        4. Uses GraphManager for non-blocking graph generation
        5. Posts generated graphs to configured Discord channel
        6. Provides progress feedback and error handling
        7. Updates cooldowns after successful execution

        Args:
            interaction: The Discord interaction
        """
        # Check cooldowns first
        is_on_cooldown, retry_after = self.check_cooldowns(interaction)
        if is_on_cooldown:
            cooldown_embed = create_cooldown_embed(
                i18n.translate("update graphs"), retry_after
            )
            _ = await interaction.response.send_message(
                embed=cooldown_embed, ephemeral=True
            )
            return

        # Acknowledge the command immediately
        embed = create_info_embed(
            title=i18n.translate("Graph Update Started"),
            description=i18n.translate(
                "Generating server graphs... This may take a few minutes."
            ),
        )
        _ = embed.add_field(
            name=i18n.translate("Status"),
            value=i18n.translate("🔄 Initializing graph generation"),
            inline=False,
        )
        _ = embed.add_field(
            name=i18n.translate("Estimated Time"),
            value=i18n.translate("2-5 minutes depending on data size"),
            inline=False,
        )

        _ = await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            # Validate Discord channel using helper
            target_channel = self.config_helper.validate_discord_channel(self.bot)

            # Step 1: Clean up previous bot messages
            logger.info(
                "Cleaning up previous bot messages before posting new graphs..."
            )
            await self._cleanup_bot_messages(target_channel)

            # Create progress callback manager for real-time updates
            progress_manager = ProgressCallbackManager(
                interaction, i18n.translate("Graph Generation")
            )
            progress_callback = progress_manager.create_progress_callback()

            # Step 2: Generate graphs using GraphManager
            async with GraphManager(self.tgraph_bot.config_manager) as graph_manager:
                graph_files = await graph_manager.generate_all_graphs(
                    progress_callback=progress_callback,
                    max_retries=3,
                    timeout_seconds=300.0,
                )

                if not graph_files:
                    warning_embed = create_error_embed(
                        title=i18n.translate("No Graphs Generated"),
                        description=i18n.translate(
                            "No graph files were created. This may be due to insufficient data or configuration issues."
                        ),
                    )
                    _ = await interaction.followup.send(
                        embed=warning_embed, ephemeral=True
                    )
                    return

                # Step 3: Post graphs to configured channel (now posts individual messages)
                success_count = await self._post_graphs_to_channel(
                    target_channel, graph_files
                )

                # Send completion message
                if success_count == len(graph_files):
                    success_embed = create_success_embed(
                        title=i18n.translate("Graph Update Complete"),
                        description=i18n.translate(
                            "Successfully generated and posted {count} graphs to {channel}",
                            count=success_count,
                            channel=target_channel.mention,
                        ),
                    )
                    _ = success_embed.add_field(
                        name=i18n.translate("Generated Graphs"),
                        value=i18n.translate("{count} files", count=len(graph_files)),
                        inline=True,
                    )
                    _ = success_embed.add_field(
                        name=i18n.translate("Posted Successfully"),
                        value=i18n.translate(
                            "{count} individual messages", count=success_count
                        ),
                        inline=True,
                    )
                else:
                    warning_embed = create_error_embed(
                        title=i18n.translate("Partial Success"),
                        description=i18n.translate(
                            "Generated {total} graphs but only posted {success} successfully",
                            total=len(graph_files),
                            success=success_count,
                        ),
                    )
                    _ = warning_embed.add_field(
                        name=i18n.translate("Check Logs"),
                        value=i18n.translate("Some files may have failed to upload"),
                        inline=False,
                    )
                    _ = await interaction.followup.send(
                        embed=warning_embed, ephemeral=True
                    )
                    return

                _ = await interaction.followup.send(embed=success_embed, ephemeral=True)

                # Update cooldowns after successful execution
                self.update_cooldowns(interaction)

        except Exception as e:
            # Use base class error handling with additional context
            try:
                config = self.get_current_config()
                additional_context: dict[str, object] = {
                    "target_channel_id": config.CHANNEL_ID
                }
            except Exception:
                additional_context = {}

            await self.handle_command_error(
                interaction, e, "update_graphs", additional_context
            )

    async def _cleanup_bot_messages(self, channel: discord.TextChannel) -> None:
        """
        Clean up previous messages posted by the bot in the specified channel.

        This method removes all messages that were posted by this bot instance,
        implementing the same cleanup logic used during bot startup and automated updates.

        Args:
            channel: The Discord text channel to clean up
        """
        logger.info(f"Starting message cleanup in channel: {channel.name}")

        try:
            # Check bot permissions
            if not channel.permissions_for(channel.guild.me).manage_messages:
                logger.warning(
                    f"Bot lacks 'Manage Messages' permission in {channel.name}"
                )
                logger.info("Attempting to delete only bot's own messages...")

            deleted_count = 0
            error_count = 0

            # Fetch messages in batches and delete bot's own messages
            async for message in channel.history(limit=None):
                # Only delete messages from this bot
                if self.bot.user and message.author.id == self.bot.user.id:
                    try:
                        await message.delete()
                        deleted_count += 1

                        # Rate limit protection - Discord allows 5 deletes per second
                        if deleted_count % 5 == 0:
                            await asyncio.sleep(1.0)

                    except discord.Forbidden:
                        logger.warning(
                            f"Cannot delete message {message.id} - insufficient permissions"
                        )
                        error_count += 1
                    except discord.NotFound:
                        # Message already deleted, continue
                        pass
                    except discord.HTTPException as e:
                        logger.error(f"HTTP error deleting message {message.id}: {e}")
                        error_count += 1

                        # If we hit rate limits, wait longer
                        if e.status == 429:
                            retry_after = getattr(e, "retry_after", 5.0)
                            logger.info(
                                f"Rate limited, waiting {retry_after} seconds..."
                            )
                            await asyncio.sleep(retry_after)

            logger.info(
                f"Message cleanup completed: {deleted_count} messages deleted, {error_count} errors"
            )

            if error_count > 0:
                logger.warning(f"Encountered {error_count} errors during cleanup")

        except Exception as e:
            logger.error(
                f"Error during message cleanup in {channel.name}: {e}", exc_info=True
            )
            # Continue with the update process even if cleanup fails
            raise

    @error_handler(retry_attempts=2, retry_delay=1.0)
    async def _post_graphs_to_channel(
        self, channel: discord.TextChannel, graph_files: list[str]
    ) -> int:
        """
        Post generated graph files to a Discord channel as individual messages with specific embeds.

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

        success_count = 0

        # Get config values for next update time calculation
        try:
            config = self.get_current_config()
            update_days = config.UPDATE_DAYS
            fixed_update_time = config.FIXED_UPDATE_TIME
        except Exception:
            # If we can't get config, just use None values
            update_days = None
            fixed_update_time = None

        try:
            for graph_file in graph_files:
                try:
                    # Validate the file first
                    validation = validate_file_for_discord(
                        graph_file, use_nitro_limits=False
                    )
                    if not validation.valid:
                        logger.error(
                            f"File validation failed for {graph_file}: {validation.error_message}"
                        )
                        continue

                    # Create Discord file object
                    discord_file = create_discord_file_safe(graph_file)
                    if not discord_file:
                        logger.error(
                            f"Failed to create Discord file object for {graph_file}"
                        )
                        continue

                    # Create graph-specific embed with scheduling info
                    embed = create_graph_specific_embed(
                        graph_file, update_days, fixed_update_time
                    )

                    # Post individual message with graph and its specific embed
                    _ = await channel.send(file=discord_file, embed=embed)
                    success_count += 1

                    logger.info(f"Successfully posted graph: {Path(graph_file).name}")

                except discord.Forbidden as e:
                    error_msg = (
                        f"Permission denied while posting graph {graph_file}: {e}"
                    )
                    logger.error(error_msg)
                    raise APIError(
                        error_msg,
                        user_message=i18n.translate(
                            "Bot lacks permission to post in the configured channel."
                        ),
                    ) from e

                except discord.HTTPException as e:
                    error_msg = (
                        f"Discord API error while posting graph {graph_file}: {e}"
                    )
                    logger.error(error_msg)
                    if "rate limit" in str(e).lower():
                        raise APIError(
                            error_msg,
                            user_message=i18n.translate(
                                "Discord rate limit reached. Please try again later."
                            ),
                        ) from e
                    else:
                        raise APIError(
                            error_msg,
                            user_message=i18n.translate(
                                "Discord API error occurred while posting graphs."
                            ),
                        ) from e

                except Exception as e:
                    logger.error(f"Unexpected error posting graph {graph_file}: {e}")
                    # Continue with other graphs even if one fails
                    continue

            logger.info(
                f"Successfully posted {success_count}/{len(graph_files)} graphs as individual messages"
            )
            return success_count

        except (APIError, NetworkError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            raise NetworkError(
                f"Unexpected error while posting graphs: {e}",
                user_message=i18n.translate(
                    "Network error occurred while posting graphs."
                ),
            ) from e


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(UpdateGraphsCog(bot))
