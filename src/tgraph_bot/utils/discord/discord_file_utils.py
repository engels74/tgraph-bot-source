"""
Discord file upload utilities for TGraph Bot.

This module provides utilities for validating and handling Discord file uploads,
including file size limits, format validation, and error handling for graph images.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Literal

import discord

from ..time import format_for_discord

logger = logging.getLogger(__name__)

# Discord file size limits (in bytes)
DISCORD_FILE_SIZE_LIMIT_REGULAR = 8 * 1024 * 1024  # 8MB for regular users
DISCORD_FILE_SIZE_LIMIT_NITRO = 25 * 1024 * 1024  # 25MB for Nitro users

# Supported image formats for Discord
SUPPORTED_IMAGE_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

# Discord timestamp styles (from discord.py)
TimestampStyle = Literal["f", "F", "d", "D", "t", "T", "R"]


# Timezone and time functions are now imported from utils.time
# get_system_timezone, get_system_now, ensure_timezone_aware


def format_next_update_timestamp(
    next_update: datetime, style: TimestampStyle = "F"
) -> str:
    """
    Format a datetime object as a Discord timestamp for next update display.

    Args:
        next_update: The datetime for the next update
        style: Discord timestamp style (default: 'F' for full date/time)

    Returns:
        Formatted Discord timestamp string
    """
    # Use the unified Discord formatting function
    return format_for_discord(next_update, style=style)


def calculate_next_update_time(
    update_days: int, fixed_update_time: str
) -> datetime | None:
    """
    Calculate the next scheduled update time based on configuration.

    This function is now a simple wrapper around the unified scheduling system.

    Args:
        update_days: Number of days between updates
        fixed_update_time: Fixed time for updates or "XX:XX" for interval-based

    Returns:
        Next update datetime, or None if calculation fails
    """
    try:
        # Use the unified scheduling function from utils.time
        from ..time import calculate_next_update_time as unified_calculate
        return unified_calculate(update_days, fixed_update_time)
    except Exception:
        return None


def create_graph_specific_embed(
    graph_file_path: str,
    update_days: int | None = None,
    fixed_update_time: str | None = None,
) -> discord.Embed:
    """
    Create a graph-specific embed based on the graph filename.

    Args:
        graph_file_path: Path to the graph file
        update_days: Number of days between updates (for showing next update time)
        fixed_update_time: Fixed time for updates or "XX:XX" for interval-based

    Returns:
        Discord embed with graph-specific title and description
    """
    file_path = Path(graph_file_path)
    filename = file_path.stem.lower()  # Get filename without extension

    # Import i18n locally to avoid circular imports
    from ...i18n import translate

    # Map graph filenames to titles and descriptions
    graph_info = {
        "daily_play_count": {
            "title": translate("📈 Daily Play Count"),
            "description": translate(
                "Shows the number of plays per day over the selected time period."
            ),
        },
        "play_count_by_dayofweek": {
            "title": translate("📊 Play Count by Day of Week"),
            "description": translate(
                "Displays play activity patterns across different days of the week."
            ),
        },
        "play_count_by_hourofday": {
            "title": translate("🕐 Play Count by Hour of Day"),
            "description": translate(
                "Shows when users are most active throughout the day."
            ),
        },
        "play_count_by_month": {
            "title": translate("📅 Play Count by Month"),
            "description": translate("Monthly play activity trends over time."),
        },
        "top_10_platforms": {
            "title": translate("💻 Top 10 Platforms"),
            "description": translate(
                "Most popular platforms used for media consumption."
            ),
        },
        "top_10_users": {
            "title": translate("👥 Top 10 Users"),
            "description": translate("Most active users in the selected time period."),
        },
    }

    # Find the best match for the filename
    info = None
    for key, value in graph_info.items():
        if key in filename:
            info = value
            break

    # Fallback for unknown graph types
    if not info:
        info = {
            "title": translate("📊 Graph"),
            "description": translate(
                "Statistical visualization of Plex activity data."
            ),
        }

    # Create the embed
    embed = discord.Embed(
        title=info["title"], description=info["description"], color=discord.Color.blue()
    )

    # Set the image to reference the attachment - this integrates the image within the embed
    _ = embed.set_image(url=f"attachment://{file_path.name}")

    # Add next update time if configuration is provided
    if update_days is not None and fixed_update_time is not None:
        next_update = calculate_next_update_time(update_days, fixed_update_time)
        if next_update:
            # Use the optimized timestamp formatting function
            timestamp_str = format_next_update_timestamp(next_update)
            current_description = embed.description or ""
            embed.description = (
                current_description + f"\n\nNext update: {timestamp_str}"
            )

    return embed


class FileValidationResult(NamedTuple):
    """Result of file validation for Discord upload."""

    valid: bool
    error_message: str | None = None
    file_size: int | None = None
    file_format: str | None = None


class DiscordUploadResult(NamedTuple):
    """Result of Discord file upload attempt."""

    success: bool
    message_id: int | None = None
    error_message: str | None = None
    files_uploaded: int = 0


def validate_file_for_discord(
    file_path: str | Path, use_nitro_limits: bool = False
) -> FileValidationResult:
    """
    Validate a file for Discord upload compatibility.

    Args:
        file_path: Path to the file to validate
        use_nitro_limits: Whether to use Nitro file size limits (25MB vs 8MB)

    Returns:
        FileValidationResult with validation status and details
    """
    # Import i18n locally to avoid circular imports
    from ...i18n import translate

    try:
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            return FileValidationResult(
                valid=False,
                error_message=translate(
                    "File does not exist: {file_path}", file_path=file_path
                ),
            )

        # Check if it's actually a file
        if not path.is_file():
            return FileValidationResult(
                valid=False,
                error_message=translate(
                    "Path is not a file: {file_path}", file_path=file_path
                ),
            )

        # Get file size
        file_size = path.stat().st_size

        # Check if file is empty
        if file_size == 0:
            return FileValidationResult(
                valid=False,
                error_message=translate(
                    "File is empty: {file_path}", file_path=file_path
                ),
                file_size=file_size,
            )

        # Check file size limits
        size_limit = (
            DISCORD_FILE_SIZE_LIMIT_NITRO
            if use_nitro_limits
            else DISCORD_FILE_SIZE_LIMIT_REGULAR
        )
        if file_size > size_limit:
            limit_mb = size_limit / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            return FileValidationResult(
                valid=False,
                error_message=translate(
                    "File too large: {actual_mb:.1f}MB exceeds {limit_mb:.0f}MB limit",
                    actual_mb=actual_mb,
                    limit_mb=limit_mb,
                ),
                file_size=file_size,
            )

        # Check file format
        file_format = path.suffix.lower()
        if file_format not in SUPPORTED_IMAGE_FORMATS:
            supported_formats = ", ".join(SUPPORTED_IMAGE_FORMATS)
            return FileValidationResult(
                valid=False,
                error_message=translate(
                    "Unsupported file format: {file_format}. Supported: {supported_formats}",
                    file_format=file_format,
                    supported_formats=supported_formats,
                ),
                file_size=file_size,
                file_format=file_format,
            )

        # All validations passed
        return FileValidationResult(
            valid=True, file_size=file_size, file_format=file_format
        )

    except Exception as e:
        logger.exception(f"Error validating file {file_path}: {e}")
        return FileValidationResult(
            valid=False, error_message=f"Validation error: {str(e)}"
        )


def create_discord_file_safe(
    file_path: str | Path, filename: str | None = None
) -> discord.File | None:
    """
    Safely create a Discord File object with validation.

    Args:
        file_path: Path to the file
        filename: Optional custom filename for Discord

    Returns:
        Discord File object or None if validation fails
    """
    try:
        path = Path(file_path)

        # Validate file first
        validation = validate_file_for_discord(path)
        if not validation.valid:
            logger.warning(
                f"File validation failed for {file_path}: {validation.error_message}"
            )
            return None

        # Use provided filename or derive from path
        display_filename = filename or path.name

        # Create Discord file object
        with path.open("rb") as f:
            discord_file = discord.File(f, filename=display_filename)

        logger.debug(
            f"Created Discord file object for {file_path} ({validation.file_size} bytes)"
        )
        return discord_file

    except Exception as e:
        logger.error(f"Failed to create Discord file object for {file_path}: {e}")
        return None


async def upload_files_to_channel(
    channel: discord.TextChannel,
    file_paths: list[str],
    embed: discord.Embed | None = None,
    use_nitro_limits: bool = False,
) -> DiscordUploadResult:
    """
    Upload multiple files to a Discord channel with validation and error handling.

    Args:
        channel: Discord channel to upload to
        file_paths: List of file paths to upload
        embed: Optional embed to send with files
        use_nitro_limits: Whether to use Nitro file size limits

    Returns:
        DiscordUploadResult with upload status and details
    """
    if not file_paths:
        # Import i18n locally to avoid circular imports
        from ...i18n import translate

        return DiscordUploadResult(
            success=False, error_message=translate("No files provided for upload")
        )

    try:
        # Validate and create Discord file objects
        discord_files: list[discord.File] = []
        validation_errors: list[str] = []

        for file_path in file_paths:
            validation = validate_file_for_discord(file_path, use_nitro_limits)
            if validation.valid:
                discord_file = create_discord_file_safe(file_path)
                if discord_file:
                    discord_files.append(discord_file)
                else:
                    # Import i18n locally to avoid circular imports
                    from ...i18n import translate

                    validation_errors.append(
                        translate(
                            "Failed to create Discord file for: {file_path}",
                            file_path=file_path,
                        )
                    )
            else:
                validation_errors.append(f"{file_path}: {validation.error_message}")

        # Log validation errors
        if validation_errors:
            for error in validation_errors:
                logger.warning(f"File validation error: {error}")

        # Check if we have any valid files to upload
        if not discord_files:
            # Import i18n locally to avoid circular imports
            from ...i18n import translate

            errors = "; ".join(validation_errors)
            return DiscordUploadResult(
                success=False,
                error_message=translate(
                    "No valid files to upload. Errors: {errors}", errors=errors
                ),
            )

        # Upload files to Discord
        try:
            if embed:
                message = await channel.send(embed=embed, files=discord_files)
            else:
                message = await channel.send(files=discord_files)

            logger.info(
                f"Successfully uploaded {len(discord_files)} files to channel {channel.id}"
            )
            return DiscordUploadResult(
                success=True, message_id=message.id, files_uploaded=len(discord_files)
            )

        except discord.HTTPException as e:
            error_msg = f"Discord upload failed: {e}"
            logger.error(error_msg)
            return DiscordUploadResult(success=False, error_message=error_msg)

    except Exception as e:
        error_msg = f"Unexpected error during file upload: {e}"
        logger.exception(error_msg)
        return DiscordUploadResult(success=False, error_message=error_msg)


async def upload_files_to_user_dm(
    user: discord.User | discord.Member,
    file_paths: list[str],
    embed: discord.Embed | None = None,
    use_nitro_limits: bool = False,
) -> DiscordUploadResult:
    """
    Upload multiple files to a user's DM with validation and error handling.

    Args:
        user: Discord user to send DM to
        file_paths: List of file paths to upload
        embed: Optional embed to send with files
        use_nitro_limits: Whether to use Nitro file size limits

    Returns:
        DiscordUploadResult with upload status and details
    """
    if not file_paths:
        # Import i18n locally to avoid circular imports
        from ...i18n import translate

        return DiscordUploadResult(
            success=False, error_message=translate("No files provided for upload")
        )

    try:
        # Validate and create Discord file objects
        discord_files: list[discord.File] = []
        validation_errors: list[str] = []

        for file_path in file_paths:
            validation = validate_file_for_discord(file_path, use_nitro_limits)
            if validation.valid:
                discord_file = create_discord_file_safe(file_path)
                if discord_file:
                    discord_files.append(discord_file)
                else:
                    # Import i18n locally to avoid circular imports
                    from ...i18n import translate

                    validation_errors.append(
                        translate(
                            "Failed to create Discord file for: {file_path}",
                            file_path=file_path,
                        )
                    )
            else:
                validation_errors.append(f"{file_path}: {validation.error_message}")

        # Log validation errors
        if validation_errors:
            for error in validation_errors:
                logger.warning(f"File validation error: {error}")

        # Check if we have any valid files to upload
        if not discord_files:
            # Import i18n locally to avoid circular imports
            from ...i18n import translate

            errors = "; ".join(validation_errors)
            return DiscordUploadResult(
                success=False,
                error_message=translate(
                    "No valid files to upload. Errors: {errors}", errors=errors
                ),
            )

        # Upload files to user DM
        try:
            if embed:
                message = await user.send(embed=embed, files=discord_files)
            else:
                message = await user.send(files=discord_files)

            logger.info(
                f"Successfully uploaded {len(discord_files)} files to user {user.id} DM"
            )
            return DiscordUploadResult(
                success=True, message_id=message.id, files_uploaded=len(discord_files)
            )

        except discord.HTTPException as e:
            error_msg = f"Discord DM upload failed: {e}"
            logger.error(error_msg)
            return DiscordUploadResult(success=False, error_message=error_msg)

    except Exception as e:
        error_msg = f"Unexpected error during DM upload: {e}"
        logger.exception(error_msg)
        return DiscordUploadResult(success=False, error_message=error_msg)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted file size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
