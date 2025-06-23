"""
Command utility functions for TGraph Bot.

This module contains utility functions specifically related to Discord commands,
such as formatting command output, argument parsing, response handling,
permission checking, and standardized interaction management.
"""

from __future__ import annotations

import logging
import re
from typing import TypeVar

import discord
import i18n

logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar("T")


def create_error_embed(
    title: str | None = None,
    description: str | None = None,
    color: discord.Color | None = None,
) -> discord.Embed:
    """
    Create a standardized error embed.

    Args:
        title: Title for the error embed
        description: Description of the error
        color: Color for the embed

    Returns:
        Discord embed for the error
    """
    if color is None:
        color = discord.Color.red()

    if title is None:
        title = i18n.translate("Error")
    if description is None:
        description = i18n.translate("An error occurred")

    embed = discord.Embed(title=title, description=description, color=color)
    _ = embed.set_footer(text="TGraph Bot")
    return embed


def create_success_embed(
    title: str | None = None,
    description: str | None = None,
    color: discord.Color | None = None,
) -> discord.Embed:
    """
    Create a standardized success embed.

    Args:
        title: Title for the success embed
        description: Description of the success
        color: Color for the embed

    Returns:
        Discord embed for the success message
    """
    if color is None:
        color = discord.Color.green()

    if title is None:
        title = i18n.translate("Success")
    if description is None:
        description = i18n.translate("Operation completed successfully")

    embed = discord.Embed(title=title, description=description, color=color)
    _ = embed.set_footer(text="TGraph Bot")
    return embed


def create_info_embed(
    title: str | None = None, description: str = "", color: discord.Color | None = None
) -> discord.Embed:
    """
    Create a standardized info embed.

    Args:
        title: Title for the info embed
        description: Description of the information
        color: Color for the embed

    Returns:
        Discord embed for the information
    """
    if color is None:
        color = discord.Color.blue()

    if title is None:
        title = i18n.translate("Information")

    embed = discord.Embed(title=title, description=description, color=color)
    _ = embed.set_footer(text="TGraph Bot")
    return embed


def format_config_value(key: str, value: str | int | float | bool | None) -> str:
    """
    Format a configuration value for display.

    Args:
        key: Configuration key name
        value: Configuration value

    Returns:
        Formatted string representation
    """
    # Hide sensitive values
    sensitive_keys = {"DISCORD_TOKEN", "TAUTULLI_API_KEY"}
    if key.upper() in sensitive_keys:
        return i18n.translate("***HIDDEN***")

    # Format boolean values
    if isinstance(value, bool):
        return i18n.translate("✅ Enabled") if value else i18n.translate("❌ Disabled")

    # Format None values
    if value is None:
        return i18n.translate("Not set")

    # Format string values
    if isinstance(value, str):
        if not value.strip():
            return i18n.translate("Empty")
        return str(value)

    # Default formatting for any other type
    return str(value)


def truncate_text(text: str, max_length: int = 1024) -> str:
    """
    Truncate text to fit within Discord embed field limits.

    Args:
        text: Text to truncate
        max_length: Maximum length allowed

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - 3] + "..."


def parse_time_string(time_str: str) -> tuple[int, int] | None:
    """
    Parse a time string in HH:MM format.

    Args:
        time_str: Time string to parse

    Returns:
        Tuple of (hour, minute) or None if invalid
    """
    if time_str == "XX:XX":
        return None

    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            return None

        hour = int(parts[0])
        minute = int(parts[1])

        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            return None

        return hour, minute

    except ValueError:
        return None


def format_uptime(seconds: int) -> str:
    """
    Format uptime seconds into a human-readable string.

    Args:
        seconds: Uptime in seconds

    Returns:
        Formatted uptime string
    """
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    parts: list[str] = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if remaining_seconds > 0 or not parts:
        parts.append(
            f"{remaining_seconds} second{'s' if remaining_seconds != 1 else ''}"
        )

    return ", ".join(parts)


def validate_email(email: str) -> bool:
    """
    Basic email validation.

    Args:
        email: Email address to validate

    Returns:
        True if email appears valid, False otherwise
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_channel_id(channel_id: str) -> int | None:
    """
    Validate and convert a Discord channel ID string to integer.

    Args:
        channel_id: Channel ID string to validate

    Returns:
        Channel ID as integer if valid, None otherwise
    """
    try:
        channel_id_int = int(channel_id)
        # Discord snowflake IDs are typically 17-19 digits long
        # and must be positive 64-bit integers
        if len(channel_id) >= 17 and 0 < channel_id_int < 2**63:
            return channel_id_int
        return None
    except ValueError:
        return None


def validate_positive_integer(
    value: str, min_value: int = 1, max_value: int | None = None
) -> int | None:
    """
    Validate and convert a string to a positive integer within bounds.

    Args:
        value: String value to validate
        min_value: Minimum allowed value (default: 1)
        max_value: Maximum allowed value (default: None for no limit)

    Returns:
        Integer value if valid, None otherwise
    """
    try:
        int_value = int(value)
        if int_value < min_value:
            return None
        if max_value is not None and int_value > max_value:
            return None
        return int_value
    except ValueError:
        return None


def validate_color_hex(color: str) -> bool:
    """
    Validate a hexadecimal color string.

    Args:
        color: Color string to validate (e.g., "#FF0000" or "FF0000")

    Returns:
        True if valid hex color, False otherwise
    """
    # Remove # if present
    color = color.lstrip("#")

    # Check if it's a valid 6-character hex string
    if len(color) != 6:
        return False

    try:
        _ = int(color, 16)
        return True
    except ValueError:
        return False


def create_progress_embed(
    title: str, current: int, total: int, description: str = ""
) -> discord.Embed:
    """
    Create an embed showing progress.

    Args:
        title: Title for the progress embed
        current: Current progress value
        total: Total progress value
        description: Additional description

    Returns:
        Discord embed showing progress
    """
    percentage = (current / total * 100) if total > 0 else 0
    progress_bar_length = 20
    filled_length = int(progress_bar_length * current // total) if total > 0 else 0

    progress_bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)

    embed = discord.Embed(
        title=title, description=description, color=discord.Color.blue()
    )

    _ = embed.add_field(
        name=i18n.translate("Progress"),
        value=f"{progress_bar} {percentage:.1f}%\n{current}/{total}",
        inline=False,
    )

    _ = embed.set_footer(text="TGraph Bot")
    return embed


def create_cooldown_embed(
    command_name: str, retry_after_seconds: float
) -> discord.Embed:
    """
    Create a standardized cooldown embed for commands.

    Args:
        command_name: Name of the command that is on cooldown
        retry_after_seconds: Seconds until the command can be used again

    Returns:
        Discord embed for cooldown notification
    """
    # Format retry time
    if retry_after_seconds >= 60:
        retry_time = i18n.translate("{time:.1f} minutes", time=retry_after_seconds / 60)
    else:
        retry_time = i18n.translate("{time:.0f} seconds", time=retry_after_seconds)

    embed = create_error_embed(
        title=i18n.translate("Command on Cooldown"),
        description=i18n.translate(
            "The {command_name} command is currently on cooldown.",
            command_name=command_name,
        ),
    )

    _ = embed.add_field(
        name=i18n.translate("Retry After"), value=retry_time, inline=True
    )
    _ = embed.add_field(
        name=i18n.translate("Reason"),
        value=i18n.translate("This prevents server overload during graph generation"),
        inline=False,
    )

    return embed


# Interaction Response Utilities


async def safe_interaction_response(
    interaction: discord.Interaction,
    embed: discord.Embed | None = None,
    content: str | None = None,
    ephemeral: bool = False,
) -> bool:
    """
    Safely respond to an interaction, handling already-responded cases.

    Args:
        interaction: Discord interaction to respond to
        embed: Embed to send (optional)
        content: Text content to send (optional)
        ephemeral: Whether response should be ephemeral

    Returns:
        True if response was sent successfully, False otherwise
    """
    try:
        if interaction.response.is_done():
            # Use followup if already responded
            if content is not None and embed is not None:
                _ = await interaction.followup.send(
                    content=content, embed=embed, ephemeral=ephemeral
                )
            elif content is not None:
                _ = await interaction.followup.send(
                    content=content, ephemeral=ephemeral
                )
            elif embed is not None:
                _ = await interaction.followup.send(embed=embed, ephemeral=ephemeral)
            else:
                _ = await interaction.followup.send(
                    content=i18n.translate("No content provided"), ephemeral=ephemeral
                )
        else:
            # Use initial response
            if content is not None and embed is not None:
                _ = await interaction.response.send_message(
                    content=content, embed=embed, ephemeral=ephemeral
                )
            elif content is not None:
                _ = await interaction.response.send_message(
                    content=content, ephemeral=ephemeral
                )
            elif embed is not None:
                _ = await interaction.response.send_message(
                    embed=embed, ephemeral=ephemeral
                )
            else:
                _ = await interaction.response.send_message(
                    content=i18n.translate("No content provided"), ephemeral=ephemeral
                )
        return True
    except discord.HTTPException as e:
        logger.error(f"Failed to respond to interaction: {e}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error responding to interaction: {e}")
        return False


async def safe_interaction_edit(
    interaction: discord.Interaction,
    embed: discord.Embed | None = None,
    content: str | None = None,
) -> bool:
    """
    Safely edit an interaction response.

    Args:
        interaction: Discord interaction to edit
        embed: New embed content (optional)
        content: New text content (optional)

    Returns:
        True if edit was successful, False otherwise
    """
    try:
        _ = await interaction.edit_original_response(content=content, embed=embed)
        return True
    except discord.HTTPException as e:
        logger.error(f"Failed to edit interaction response: {e}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error editing interaction response: {e}")
        return False


async def send_error_response(
    interaction: discord.Interaction,
    title: str | None = None,
    description: str | None = None,
    ephemeral: bool = True,
) -> bool:
    """
    Send a standardized error response to an interaction.

    Args:
        interaction: Discord interaction to respond to
        title: Error title
        description: Error description
        ephemeral: Whether response should be ephemeral

    Returns:
        True if response was sent successfully, False otherwise
    """
    if title is None:
        title = i18n.translate("Error")
    if description is None:
        description = i18n.translate("An error occurred")

    error_embed = create_error_embed(title=title, description=description)
    return await safe_interaction_response(
        interaction=interaction, embed=error_embed, ephemeral=ephemeral
    )


async def send_success_response(
    interaction: discord.Interaction,
    title: str | None = None,
    description: str | None = None,
    ephemeral: bool = False,
) -> bool:
    """
    Send a standardized success response to an interaction.

    Args:
        interaction: Discord interaction to respond to
        title: Success title
        description: Success description
        ephemeral: Whether response should be ephemeral

    Returns:
        True if response was sent successfully, False otherwise
    """
    if title is None:
        title = i18n.translate("Success")
    if description is None:
        description = i18n.translate("Operation completed successfully")

    success_embed = create_success_embed(title=title, description=description)
    return await safe_interaction_response(
        interaction=interaction, embed=success_embed, ephemeral=ephemeral
    )


# Permission and Command Utilities


def check_manage_guild_permission(interaction: discord.Interaction) -> bool:
    """
    Check if the user has manage guild permissions.

    Args:
        interaction: Discord interaction to check

    Returns:
        True if user has manage guild permissions, False otherwise
    """
    if interaction.guild is None:
        return False

    # Check if user is guild owner
    if interaction.guild.owner_id == interaction.user.id:
        return True

    # Check if user has manage guild permission
    if isinstance(interaction.user, discord.Member):
        return interaction.user.guild_permissions.manage_guild

    # For testing: check if user has guild_permissions attribute (mock support)
    guild_permissions = getattr(interaction.user, "guild_permissions", None)
    if guild_permissions is not None:
        manage_guild = getattr(guild_permissions, "manage_guild", None)  # pyright: ignore[reportAny]
        if manage_guild is not None:
            return bool(manage_guild)  # pyright: ignore[reportAny]

    return False


def format_command_help(
    command_name: str,
    description: str,
    usage: str | None = None,
    examples: list[str] | None = None,
) -> discord.Embed:
    """
    Create a standardized help embed for a command.

    Args:
        command_name: Name of the command
        description: Description of what the command does
        usage: Usage syntax (optional)
        examples: List of usage examples (optional)

    Returns:
        Discord embed with command help information
    """
    embed = create_info_embed(
        title=f"Command: /{command_name}", description=description
    )

    if usage:
        _ = embed.add_field(name="Usage", value=f"`{usage}`", inline=False)

    if examples:
        example_text = "\n".join(f"`{example}`" for example in examples)
        _ = embed.add_field(name="Examples", value=example_text, inline=False)

    return embed
