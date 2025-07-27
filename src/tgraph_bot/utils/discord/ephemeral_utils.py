"""
Ephemeral message utilities for TGraph Bot.

This module provides utilities for sending and editing ephemeral Discord interaction
responses with automatic deletion after a specified timeout. These utilities ensure
consistent behavior across all ephemeral messages in the bot.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import discord

logger = logging.getLogger(__name__)

# Default timeout for ephemeral message deletion (60 seconds)
DEFAULT_EPHEMERAL_DELETION_TIMEOUT: float = 60.0


async def send_ephemeral_with_deletion(
    interaction: discord.Interaction,
    *,
    content: str | None = None,
    embed: discord.Embed | None = None,
    view: discord.ui.View | None = None,
    delete_after: float = DEFAULT_EPHEMERAL_DELETION_TIMEOUT,
) -> None:
    """
    Send an ephemeral interaction response with automatic deletion.

    This function sends an ephemeral message that will be automatically deleted
    after the specified timeout. It handles both initial responses and followup
    messages depending on whether the interaction has already been responded to.

    Args:
        interaction: The Discord interaction to respond to
        content: The text content of the message (optional)
        embed: The embed to include in the message (optional)
        view: The view (UI components) to include in the message (optional)
        delete_after: Time in seconds after which to delete the message (default: 60.0)

    Raises:
        ValueError: If delete_after is not positive
        ValueError: If neither content nor embed is provided
        Exception: If the Discord API call fails

    Example:
        >>> await send_ephemeral_with_deletion(
        ...     interaction,
        ...     content="This message will be deleted in 60 seconds",
        ...     delete_after=60.0
        ... )
    """
    # Validate delete_after parameter
    if delete_after <= 0:
        msg = "delete_after must be positive"
        raise ValueError(msg)

    # Validate that at least content or embed is provided
    if content is None and embed is None:
        msg = "Must provide either content or embed"
        raise ValueError(msg)

    # Prepare message parameters
    # Use Any for type annotations since the discord.py library has complex overloads
    message_params: dict[str, Any] = {  # pyright: ignore[reportExplicitAny]
        "ephemeral": True,
        "delete_after": delete_after,
    }

    if content is not None:
        message_params["content"] = content
    if embed is not None:
        message_params["embed"] = embed
    if view is not None:
        message_params["view"] = view

    logger.debug(
        "Sending ephemeral message with %ss deletion timeout for user %s in command %s",
        delete_after,
        interaction.user.id,
        getattr(interaction.command, 'name', 'unknown')
    )

    try:
        # Check if the interaction has already been responded to
        if interaction.response.is_done():
            # Use followup for additional messages
            _ = await interaction.followup.send(**message_params)  # pyright: ignore[reportAny,reportUnknownVariableType]
        else:
            # Use initial response
            _ = await interaction.response.send_message(**message_params)  # pyright: ignore[reportAny]

    except Exception as e:
        logger.error(
            f"Failed to send ephemeral message for user {interaction.user.id}: {e}",
            exc_info=True,
        )
        raise


async def edit_ephemeral_with_deletion(
    interaction: discord.Interaction,
    *,
    content: str | None = None,
    embed: discord.Embed | None = None,
    view: discord.ui.View | None = None,
    delete_after: float = DEFAULT_EPHEMERAL_DELETION_TIMEOUT,
) -> None:
    """
    Edit an ephemeral interaction response with automatic deletion.

    This function edits the original ephemeral interaction response and sets
    a new deletion timeout. This is useful for updating status messages or
    providing progress updates.

    Args:
        interaction: The Discord interaction to edit the response for
        content: The new text content of the message (optional)
        embed: The new embed to include in the message (optional)
        view: The new view (UI components) to include in the message (optional)
        delete_after: Time in seconds after which to delete the message (default: 60.0)

    Raises:
        ValueError: If delete_after is not positive
        Exception: If the Discord API call fails

    Example:
        >>> await edit_ephemeral_with_deletion(
        ...     interaction,
        ...     content="Updated message content",
        ...     delete_after=30.0
        ... )
    """
    # Validate delete_after parameter
    if delete_after <= 0:
        msg = "delete_after must be positive"
        raise ValueError(msg)

    # Prepare message parameters
    # Use Any for type annotations since the discord.py library has complex overloads
    message_params: dict[str, Any] = {  # pyright: ignore[reportExplicitAny]
        "delete_after": delete_after,
    }

    if content is not None:
        message_params["content"] = content
    if embed is not None:
        message_params["embed"] = embed
    if view is not None:
        message_params["view"] = view

    logger.debug(
        "Editing ephemeral message with %ss deletion timeout for user %s in command %s",
        delete_after,
        interaction.user.id,
        getattr(interaction.command, 'name', 'unknown')
    )

    try:
        # Edit the original interaction response
        _ = await interaction.edit_original_response(**message_params)  # pyright: ignore[reportAny]

    except Exception as e:
        logger.error(
            f"Failed to edit ephemeral message for user {interaction.user.id}: {e}",
            exc_info=True,
        )
        raise


