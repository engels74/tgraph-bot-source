"""
Discord file upload utilities for TGraph Bot.

This module provides utilities for validating and handling Discord file uploads,
including file size limits, format validation, and error handling for graph images.
"""

import logging
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import NamedTuple, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord

from ..cli.paths import get_path_config

logger = logging.getLogger(__name__)

# Discord file size limits (in bytes)
DISCORD_FILE_SIZE_LIMIT_REGULAR = 8 * 1024 * 1024  # 8MB for regular users
DISCORD_FILE_SIZE_LIMIT_NITRO = 25 * 1024 * 1024  # 25MB for Nitro users

# Supported image formats for Discord
SUPPORTED_IMAGE_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

# Discord timestamp styles (from discord.py)
TimestampStyle = Literal["f", "F", "d", "D", "t", "T", "R"]


def get_local_timezone() -> ZoneInfo:
    """
    Get the system's local timezone.

    Returns:
        ZoneInfo object representing the local timezone
    """
    # Use the system's local timezone - cross-platform approach
    try:
        # Try "localtime" first (works on Linux/WSL)
        return ZoneInfo("localtime")
    except ZoneInfoNotFoundError:
        # Fall back to getting the key from datetime for macOS/Windows
        local_tz = datetime.now().astimezone().tzinfo
        if hasattr(local_tz, 'key'):
            key = getattr(local_tz, 'key')  # pyright: ignore[reportAny] # timezone key from system
            if isinstance(key, str):
                return ZoneInfo(key)
        # Final fallback: use UTC
        return ZoneInfo("UTC")


def get_local_now() -> datetime:
    """
    Get the current local datetime (timezone-aware).

    Returns:
        Current datetime in the system's local timezone
    """
    return datetime.now(get_local_timezone())


def ensure_timezone_aware(dt: datetime) -> datetime:
    """
    Ensure a datetime object is timezone-aware.

    Uses the system's local timezone for consistent scheduling.

    Args:
        dt: Datetime object that may be naive or timezone-aware

    Returns:
        Timezone-aware datetime object (local timezone)
    """
    if dt.tzinfo is None:
        # If naive, assume it's in local timezone
        return dt.replace(tzinfo=get_local_timezone())
    return dt


def format_next_update_timestamp(
    next_update: datetime, style: TimestampStyle = "R"
) -> str:
    """
    Format a datetime object as a Discord timestamp for next update display.

    Args:
        next_update: The datetime for the next update
        style: Discord timestamp style (default: 'R' for relative)

    Returns:
        Formatted Discord timestamp string
    """
    # Ensure timezone-aware datetime
    next_update = ensure_timezone_aware(next_update)

    # Use discord.py's format_dt function for consistent formatting
    return discord.utils.format_dt(next_update, style=style)


def calculate_next_update_time(
    update_days: int, fixed_update_time: str
) -> datetime | None:
    """
    Calculate the next scheduled update time based on configuration.

    This function now matches the scheduler logic exactly, including respecting
    the update_days interval from the last update when available.

    Args:
        update_days: Number of days between updates
        fixed_update_time: Fixed time for updates or "XX:XX" for interval-based

    Returns:
        Next update datetime, or None if calculation fails
    """
    try:
        # Use local timezone for consistent scheduling
        current_time = get_local_now()

        # Handle interval-based updates
        if fixed_update_time == "XX:XX":
            return current_time + timedelta(days=update_days)

        # Handle fixed time updates
        try:
            hour, minute = map(int, fixed_update_time.split(":"))
            update_time = time(hour, minute)
        except (ValueError, AttributeError):
            return None

        # Calculate next occurrence of the fixed time (timezone-aware)
        next_update = datetime.combine(current_time.date(), update_time)
        next_update = next_update.replace(tzinfo=get_local_timezone())

        # If time has passed today, schedule for tomorrow
        if next_update <= current_time:
            next_update += timedelta(days=1)

        # For UPDATE_DAYS > 1, ensure we respect the minimum interval from current time
        # This matches the scheduler logic for first launch
        if update_days > 1:
            min_next_update = current_time + timedelta(days=update_days)
            if next_update < min_next_update:
                # Find the next occurrence of fixed time on or after the minimum date
                next_update = datetime.combine(min_next_update.date(), update_time)
                next_update = next_update.replace(tzinfo=get_local_timezone())

        # Try to load scheduler state to respect update_days interval from last update
        # This matches the scheduler logic in bot/update_tracker.py
        scheduler_state_loaded = False
        try:
            import json

            # Try to find the scheduler state file using PathConfig
            path_config = get_path_config()
            state_file = path_config.get_scheduler_state_path()
            # Only try to read the file if it actually exists
            if state_file.exists():
                try:
                    with state_file.open("r") as f:
                        state_data = json.load(f)  # pyright: ignore[reportAny]

                    # First, try to use the next_update value directly from scheduler state
                    # This is the most accurate approach since the scheduler has already calculated it
                    if "state" in state_data and "next_update" in state_data["state"]:
                        next_update_str = state_data["state"]["next_update"]  # pyright: ignore[reportAny]
                        if next_update_str and isinstance(next_update_str, str):
                            try:
                                scheduler_next_update = datetime.fromisoformat(
                                    next_update_str
                                )

                                # Ensure scheduler_next_update is timezone-aware and in local timezone
                                if scheduler_next_update.tzinfo is None:
                                    scheduler_next_update = (
                                        scheduler_next_update.replace(
                                            tzinfo=get_local_timezone()
                                        )
                                    )
                                else:
                                    # Convert to local timezone to ensure consistent ZoneInfo type
                                    scheduler_next_update = (
                                        scheduler_next_update.astimezone(
                                            get_local_timezone()
                                        )
                                    )

                                # Use the scheduler's next_update if it's in the future
                                if scheduler_next_update > current_time:
                                    next_update = scheduler_next_update
                                    scheduler_state_loaded = True
                            except (ValueError, TypeError):
                                # If parsing fails, fall back to calculation from last_update
                                pass

                    # Fallback: calculate from last_update if next_update wasn't usable
                    if (
                        not scheduler_state_loaded
                        and "state" in state_data
                        and "last_update" in state_data["state"]
                    ):
                        last_update_str = state_data["state"]["last_update"]  # pyright: ignore[reportAny]
                        if last_update_str and isinstance(last_update_str, str):
                            last_update = datetime.fromisoformat(last_update_str)

                            # Ensure last_update is timezone-aware and in local timezone
                            if last_update.tzinfo is None:
                                last_update = last_update.replace(
                                    tzinfo=get_local_timezone()
                                )
                            else:
                                # Convert to local timezone to ensure consistent ZoneInfo type
                                last_update = last_update.astimezone(
                                    get_local_timezone()
                                )

                            # Respect the update_days interval if we have a last update
                            min_next_update = last_update + timedelta(days=update_days)
                            if next_update < min_next_update:
                                # Calculate how many days we need to add to meet the minimum interval
                                # We need to find the next occurrence of update_time that is >= min_next_update
                                candidate_date = min_next_update.date()
                                candidate_update = datetime.combine(
                                    candidate_date, update_time
                                )
                                # Ensure candidate_update is timezone-aware
                                candidate_update = candidate_update.replace(
                                    tzinfo=get_local_timezone()
                                )

                                # If the time on min_next_update date has already passed in min_next_update,
                                # move to the next day
                                if candidate_update < min_next_update:
                                    candidate_update += timedelta(days=1)

                                next_update = candidate_update
                                scheduler_state_loaded = True

                except (
                    OSError,
                    json.JSONDecodeError,
                    KeyError,
                    ValueError,
                ) as file_error:
                    # If we can't read or parse the state file, continue with the basic logic
                    logger.debug(
                        f"Could not load scheduler state for next update calculation: {file_error}"
                    )
        except Exception as e:
            # If any other error occurs, continue with the basic logic
            logger.debug(
                f"Could not load scheduler state for next update calculation: {e}"
            )

        # Special case for UPDATE_DAYS=1 on first launch (no scheduler state)
        # This matches the scheduler behavior: always add UPDATE_DAYS to current time on first run
        # regardless of whether the fixed time has passed today
        if not scheduler_state_loaded and update_days == 1:
            # On first launch, scheduler always adds UPDATE_DAYS to current time
            min_next_update = current_time + timedelta(days=1)
            next_update = datetime.combine(min_next_update.date(), update_time)
            next_update = next_update.replace(tzinfo=get_local_timezone())

        return next_update

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
            timestamp_str = format_next_update_timestamp(next_update, style="R")
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
