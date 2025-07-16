"""
Startup sequence for TGraph Bot.

This module handles the bot's startup sequence which includes:
1. Cleaning up previous messages posted by the bot
2. Posting initial graphs in configured channels
3. Setting up scheduler state for proper timing
"""

import asyncio
import logging

from typing import TYPE_CHECKING, Protocol, runtime_checkable
from collections.abc import Sequence
import discord

from ..graphs.graph_manager import GraphManager
from ..utils.discord.discord_file_utils import (
    validate_file_for_discord,
    create_discord_file_safe,
    create_graph_specific_embed,
)
from .permission_checker import PermissionChecker

if TYPE_CHECKING:
    from ..config.manager import ConfigManager
    from .update_tracker import UpdateTracker


@runtime_checkable
class TGraphBotProtocol(Protocol):
    """Protocol for TGraph bot with custom attributes."""

    config_manager: "ConfigManager"
    update_tracker: "UpdateTracker"

    @property
    def guilds(self) -> Sequence[discord.Guild]: ...

    @property
    def tree(self) -> discord.app_commands.CommandTree: ...

    @property
    def user(self) -> discord.ClientUser | None: ...

    def get_channel(
        self, id: int, /
    ) -> (
        discord.abc.GuildChannel | discord.abc.PrivateChannel | discord.Thread | None
    ): ...


logger = logging.getLogger(__name__)


class StartupSequence:
    """
    Manages the bot's startup sequence.

    This includes cleaning up old messages, posting initial graphs,
    and ensuring the scheduler state is properly initialized.
    """

    def __init__(self, bot: TGraphBotProtocol) -> None:
        """
        Initialize the startup sequence.

        Args:
            bot: The TGraph bot instance
        """
        self.bot: TGraphBotProtocol = bot
        self.cleanup_completed: bool = False
        self.initial_post_completed: bool = False

    async def run(self) -> None:
        """
        Execute the complete startup sequence.

        This is the main entry point for the startup sequence and should
        be called when the bot is ready.
        """
        logger.info("Starting TGraph Bot startup sequence...")

        # Run each step independently to ensure all are attempted

        # Step 1: Check permissions
        try:
            await self.check_permissions()
        except Exception as e:
            logger.error(f"Error during permission checking: {e}", exc_info=True)

        # Step 2: Clean up previous messages
        try:
            await self.cleanup_previous_messages()
        except Exception as e:
            logger.error(f"Error during message cleanup: {e}", exc_info=True)

        # Step 3: Post initial graphs
        try:
            await self.post_initial_graphs()
        except Exception as e:
            logger.error(f"Error during initial graph posting: {e}", exc_info=True)

        # Step 4: Update scheduler state
        try:
            await self.update_scheduler_state()
        except Exception as e:
            logger.error(f"Error updating scheduler state: {e}", exc_info=True)

        logger.info("Startup sequence completed")

    async def check_permissions(self) -> None:
        """
        Check bot and slash command permissions across all guilds.

        This step runs early in the startup sequence to identify any permission
        issues that might affect bot functionality.
        """
        logger.info("Checking bot and slash command permissions...")

        # Give Discord API more time to process recently synced commands
        # Discord API can take several seconds to propagate command changes
        logger.debug("Waiting for Discord API to process synced commands...")
        import asyncio
        await asyncio.sleep(5.0)

        permission_checker = PermissionChecker(self.bot)
        await permission_checker.log_permission_status()

        logger.info("Permission check completed")

    async def cleanup_previous_messages(self) -> None:
        """
        Clean up previous messages posted by the bot in configured channels.

        This deletes both regular messages and investigates ephemeral message handling.
        """
        logger.info("Starting message cleanup...")

        try:
            config = self.bot.config_manager.get_current_config()
            channel = self.bot.get_channel(config.CHANNEL_ID)

            if not isinstance(channel, discord.TextChannel):
                logger.warning(
                    f"Channel {config.CHANNEL_ID} is not a text channel or not found"
                )
                return

            # Check bot permissions
            if not channel.permissions_for(channel.guild.me).manage_messages:
                logger.warning(
                    f"Bot lacks 'Manage Messages' permission in {channel.name}"
                )
                logger.info("Attempting to delete only bot's own messages...")

            deleted_count = 0
            error_count = 0

            # Fetch messages in batches
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
                        # Message already deleted
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

            # Document ephemeral message limitations
            logger.info(
                "Note: Ephemeral messages cannot be deleted by the bot after creation. "
                + "They persist until users dismiss them manually. This is a Discord API limitation."
            )

            self.cleanup_completed = True

        except Exception as e:
            logger.error(f"Error during message cleanup: {e}", exc_info=True)
            # Continue with startup even if cleanup fails

    async def post_initial_graphs(self) -> None:
        """
        Post all graphs initially, similar to the /update_graphs command.

        This ensures fresh graphs are available immediately after bot startup.
        """
        logger.info("Posting initial graphs...")

        try:
            config = self.bot.config_manager.get_current_config()
            channel = self.bot.get_channel(config.CHANNEL_ID)

            if not isinstance(channel, discord.TextChannel):
                logger.error(
                    f"Channel {config.CHANNEL_ID} is not a text channel or not found"
                )
                return

            # Generate all graphs
            async with GraphManager(self.bot.config_manager) as graph_manager:
                graph_files = await graph_manager.generate_all_graphs(
                    max_retries=3, timeout_seconds=300.0
                )

                if not graph_files:
                    logger.warning("No graphs generated during startup")
                    return

                # Post graphs to channel
                success_count = await self._post_graphs_to_channel(channel, graph_files)

                logger.info(
                    f"Initial graph posting complete: {success_count}/{len(graph_files)} graphs posted"
                )

                self.initial_post_completed = success_count > 0

        except Exception as e:
            logger.error(f"Error during initial graph posting: {e}", exc_info=True)
            # Continue with startup even if posting fails

    async def _post_graphs_to_channel(
        self, channel: discord.TextChannel, graph_files: list[str]
    ) -> int:
        """
        Post generated graph files to a Discord channel.

        Args:
            channel: Discord text channel to post to
            graph_files: List of graph file paths to post

        Returns:
            Number of successfully posted graphs
        """
        from pathlib import Path

        success_count = 0

        # Get config values for next update time calculation
        try:
            config = self.bot.config_manager.get_current_config()
            update_days = config.UPDATE_DAYS
            fixed_update_time = config.FIXED_UPDATE_TIME
        except Exception:
            # If we can't get config, just use None values
            update_days = None
            fixed_update_time = None

        for graph_file in graph_files:
            try:
                file_path = Path(graph_file)
                if not file_path.exists():
                    logger.warning(f"Graph file not found: {graph_file}")
                    continue

                # Validate the file
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

                # Post the graph
                _ = await channel.send(file=discord_file, embed=embed)
                success_count += 1
                logger.debug(f"Posted graph: {file_path.name}")

                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Failed to post graph {graph_file}: {e}")

        return success_count

    async def update_scheduler_state(self) -> None:
        """
        Update the scheduler state to reflect the initial posting time.

        This ensures future scheduled updates calculate correctly from
        the startup posting time.
        """
        logger.info("Updating scheduler state...")

        try:
            if not self.initial_post_completed:
                logger.warning(
                    "Skipping scheduler state update - no graphs were posted"
                )
                return

            # Get current time as the baseline for scheduling
            current_time = discord.utils.utcnow()

            update_tracker = self.bot.update_tracker

            # Access the scheduler's state
            if hasattr(update_tracker, "_state"):
                update_tracker._state.last_update = current_time  # pyright: ignore[reportPrivateUsage]
                logger.info(f"Set scheduler last update time to: {current_time}")

                # Save the state
                if hasattr(update_tracker, "_state_manager") and hasattr(
                    update_tracker, "_config"
                ):
                    state_manager = update_tracker._state_manager  # pyright: ignore[reportPrivateUsage]
                    state_manager.save_state(
                        update_tracker._state,  # pyright: ignore[reportPrivateUsage]
                        update_tracker._config,  # pyright: ignore[reportPrivateUsage]
                    )
                    logger.info("Scheduler state saved to disk")

                # Log next update time
                if hasattr(update_tracker, "get_next_update_time"):
                    next_update = update_tracker.get_next_update_time()
                    if next_update:
                        logger.info(f"Next scheduled update: {next_update}")
            else:
                logger.warning("Update tracker state not accessible")

        except Exception as e:
            logger.error(f"Error updating scheduler state: {e}", exc_info=True)
            # Continue - scheduler will use its default behavior

    def is_completed(self) -> bool:
        """
        Check if the startup sequence has completed successfully.

        Returns:
            True if all critical startup tasks completed
        """
        return self.cleanup_completed and self.initial_post_completed
