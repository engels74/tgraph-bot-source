"""
Progress tracking utilities for TGraph Bot.

This module provides standardized progress tracking and callback functionality
for long-running operations like graph generation, eliminating code duplication
across different command implementations.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable, final

import discord

from ... import i18n
from ...utils.discord.command_utils import create_info_embed

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@final
class ProgressCallbackManager:
    """
    Manages progress callbacks for Discord interactions.

    Provides standardized progress update functionality that can be reused
    across different commands and operations.
    """

    def __init__(self, interaction: discord.Interaction, operation_name: str) -> None:
        """
        Initialize the progress callback manager.

        Args:
            interaction: The Discord interaction to update
            operation_name: Name of the operation for display purposes
        """
        self.interaction: discord.Interaction = interaction
        self.operation_name: str = operation_name
        self._last_update_time: float = 0.0
        self._last_progress: float = 0.0  # Track last progress percentage
        self._update_interval: float = (
            0.2  # Minimum seconds between updates (reduced for faster operations)
        )

    def create_progress_callback(
        self,
    ) -> Callable[[str, int, int, dict[str, object]], None]:
        """
        Create a progress callback function for use with graph managers.

        Returns:
            Progress callback function that can be passed to graph generation methods
        """

        def progress_callback(
            message: str, current: int, total: int, metadata: dict[str, object]
        ) -> None:
            """
            Progress callback for graph generation operations.

            Args:
                message: Progress message to display
                current: Current step number
                total: Total number of steps
                metadata: Additional metadata about the operation
            """
            try:
                # Try to get the running event loop (more reliable than get_event_loop)
                try:
                    loop = asyncio.get_running_loop()
                    # Schedule the async update in the main event loop from thread
                    _ = asyncio.run_coroutine_threadsafe(
                        self._update_progress_embed(message, current, total, metadata),
                        loop,
                    )
                    # Don't wait for completion to avoid blocking
                    logger.debug(
                        f"Scheduled progress update: {message} ({current}/{total})"
                    )

                except RuntimeError:
                    # No running loop, try to create a task directly (we're in main thread)
                    try:
                        _ = asyncio.create_task(
                            self._update_progress_embed(
                                message, current, total, metadata
                            )
                        )
                        logger.debug(
                            f"Created task for progress update: {message} ({current}/{total})"
                        )
                    except RuntimeError:
                        logger.warning(
                            f"Could not schedule progress update: {message} ({current}/{total})"
                        )

            except Exception as e:
                # Log the error but don't let it break the graph generation
                logger.warning(
                    f"Failed to schedule progress update for {self.operation_name}: {e}"
                )
                logger.debug(
                    f"Progress update details - message: {message}, current: {current}, total: {total}"
                )

        return progress_callback

    async def _update_progress_embed(
        self, message: str, current: int, total: int, metadata: dict[str, object]
    ) -> None:
        """
        Update the progress embed with current status.

        Args:
            message: Progress message to display
            current: Current step number
            total: Total number of steps
            metadata: Additional metadata about the operation
        """
        import time

        # Rate limit updates to avoid Discord API spam, but allow critical updates
        current_time = time.time()
        time_since_last = current_time - self._last_update_time
        current_progress = (current / total * 100) if total > 0 else 0

        # Allow critical updates: final step, first update, normal interval passed, or significant progress jump
        is_critical_update = (
            current == total  # Final step (100%)
            or self._last_update_time == 0.0  # First update
            or time_since_last >= self._update_interval  # Normal rate limit passed
            or (current_progress - self._last_progress)
            >= 20.0  # Significant progress jump (20% or more)
        )

        if not is_critical_update:
            logger.debug(
                f"Rate limiting progress update: {message} ({current}/{total}) - {current_progress:.1f}%"
            )
            return

        try:
            # Calculate progress percentage
            progress_percent = (current / total * 100) if total > 0 else 0

            # Create progress bar
            progress_bar = self._create_progress_bar(progress_percent)

            # Create updated embed
            embed = create_info_embed(
                title=i18n.translate(
                    "{operation_name} Progress", operation_name=self.operation_name
                ),
                description=f"**{message}**\n\n{progress_bar}",
            )

            # Add progress details
            _ = embed.add_field(
                name=i18n.translate("Progress"),
                value=i18n.translate(
                    "{current}/{total} steps ({progress_percent:.1f}%)",
                    current=current,
                    total=total,
                    progress_percent=progress_percent,
                ),
                inline=True,
            )

            # Add timing information if available
            if "elapsed_time" in metadata:
                elapsed = metadata["elapsed_time"]
                if isinstance(elapsed, (int, float)):
                    _ = embed.add_field(
                        name=i18n.translate("Elapsed Time"),
                        value=f"{elapsed:.1f}s",
                        inline=True,
                    )

            # Add estimated time remaining if available
            if "estimated_remaining" in metadata:
                remaining = metadata["estimated_remaining"]
                if isinstance(remaining, (int, float)):
                    _ = embed.add_field(
                        name=i18n.translate("Est. Remaining"),
                        value=f"{remaining:.1f}s",
                        inline=True,
                    )

            # Update the interaction - try to edit the original response
            try:
                _ = await self.interaction.edit_original_response(embed=embed)
            except (discord.NotFound, discord.HTTPException):
                # If editing original response fails, try followup
                try:
                    _ = await self.interaction.followup.send(
                        embed=embed, ephemeral=True
                    )
                except discord.HTTPException:
                    # If all else fails, just log the issue
                    logger.debug(f"Could not update progress for {self.operation_name}")

            self._last_update_time = current_time
            self._last_progress = current_progress

        except discord.NotFound:
            # Original message was deleted, stop updating
            logger.debug(
                f"Progress message for {self.operation_name} was deleted, stopping updates"
            )
        except discord.HTTPException as e:
            logger.warning(f"Failed to update progress for {self.operation_name}: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error updating progress for {self.operation_name}: {e}"
            )

    def _create_progress_bar(self, percentage: float, length: int = 20) -> str:
        """
        Create a visual progress bar.

        Args:
            percentage: Progress percentage (0-100)
            length: Length of the progress bar in characters

        Returns:
            String representation of the progress bar
        """
        filled_length = int(length * percentage / 100)
        bar = "█" * filled_length + "░" * (length - filled_length)
        return f"`{bar}` {percentage:.1f}%"


# SimpleProgressTracker is now available from ...graphs.graph_modules.progress_tracker
