"""
Discord file upload utilities for TGraph Bot.

This module provides utilities for validating and handling Discord file uploads,
including file size limits, format validation, and error handling for graph images.
"""

import logging
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import NamedTuple

import discord

logger = logging.getLogger(__name__)

# Discord file size limits (in bytes)
DISCORD_FILE_SIZE_LIMIT_REGULAR = 8 * 1024 * 1024  # 8MB for regular users
DISCORD_FILE_SIZE_LIMIT_NITRO = 25 * 1024 * 1024   # 25MB for Nitro users

# Supported image formats for Discord
SUPPORTED_IMAGE_FORMATS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}


def calculate_next_update_time(update_days: int, fixed_update_time: str | None = None) -> datetime | None:
    """
    Calculate the next scheduled update time based on configuration.
    
    Args:
        update_days: Number of days between updates
        fixed_update_time: Fixed time in HH:MM format or "XX:XX" for interval-based updates
        
    Returns:
        Next update datetime or None if calculation fails
    """
    try:
        current_time = datetime.now()
        
        # Handle interval-based updates
        if not fixed_update_time or fixed_update_time == "XX:XX":
            # Simply add update_days to current time
            return current_time + timedelta(days=update_days)
        
        # Handle fixed time updates
        # Parse the fixed time
        try:
            hour, minute = map(int, fixed_update_time.split(":"))
            target_time = time(hour, minute)
        except (ValueError, IndexError):
            logger.warning(f"Invalid fixed update time format: {fixed_update_time}")
            return None
        
        # Calculate next occurrence
        next_update = current_time.replace(
            hour=target_time.hour,
            minute=target_time.minute,
            second=0,
            microsecond=0
        )
        
        # If the time has already passed today, move to the next scheduled day
        if next_update <= current_time:
            next_update += timedelta(days=1)
        
        # Now ensure it aligns with update_days interval
        # Find the next valid day based on update_days interval
        days_until_next = update_days - (next_update.date() - current_time.date()).days % update_days
        if days_until_next == update_days and next_update > current_time:
            # Already on a valid day and time hasn't passed
            return next_update
        else:
            # Move to the next valid day
            return next_update + timedelta(days=days_until_next)
            
    except Exception as e:
        logger.error(f"Error calculating next update time: {e}")
        return None


def create_graph_specific_embed(
    graph_file_path: str,
    update_days: int | None = None,
    fixed_update_time: str | None = None
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
    
    # Map graph filenames to titles and descriptions
    graph_info = {
        "daily_play_count": {
            "title": "📈 Daily Play Count",
            "description": "Shows the number of plays per day over the selected time period"
        },
        "play_count_by_dayofweek": {
            "title": "📊 Play Count by Day of Week", 
            "description": "Displays how play activity varies across different days of the week"
        },
        "play_count_by_hourofday": {
            "title": "🕐 Play Count by Hour of Day",
            "description": "Shows when users are most active throughout the day"
        },
        "play_count_by_month": {
            "title": "📅 Play Count by Month",
            "description": "Monthly breakdown of viewing activity over time"
        },
        "top_10_users": {
            "title": "👥 Top 10 Users",
            "description": "Most active users ranked by total play count"
        },
        "top_10_platforms": {
            "title": "📱 Top 10 Platforms", 
            "description": "Most popular devices and platforms used for streaming"
        },
        "sample_graph": {
            "title": "🧪 Sample Data Visualization",
            "description": "Example graph for testing and demonstration purposes"
        }
    }
    
    # Find matching graph info
    graph_data = None
    for graph_type, info in graph_info.items():
        if graph_type in filename:
            graph_data = info
            break
    
    # Default fallback if no match found
    if graph_data is None:
        graph_data = {
            "title": "📊 Server Statistics",
            "description": "Generated server statistics graph"
        }
    
    # Build the description
    description_parts = [graph_data["description"]]
    
    # Add next update time if config values are provided
    if update_days is not None and fixed_update_time is not None:
        next_update = calculate_next_update_time(update_days, fixed_update_time)
        if next_update:
            # Convert to Discord timestamp format (R = relative time)
            timestamp = int(next_update.timestamp())
            description_parts.append(f"\nNext update: <t:{timestamp}:R>")
    
    # Create embed with graph-specific information
    embed = discord.Embed(
        title=graph_data["title"],
        description="\n".join(description_parts),
        color=discord.Color.blue()
    )
    
    # Set the graph image as the main embed image
    _ = embed.set_image(url=f"attachment://{file_path.name}")
    _ = embed.set_footer(text="Generated by TGraph Bot")
    
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


def validate_file_for_discord(file_path: str | Path, use_nitro_limits: bool = False) -> FileValidationResult:
    """
    Validate a file for Discord upload compatibility.
    
    Args:
        file_path: Path to the file to validate
        use_nitro_limits: Whether to use Nitro file size limits (25MB vs 8MB)
        
    Returns:
        FileValidationResult with validation status and details
    """
    try:
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            return FileValidationResult(
                valid=False,
                error_message=f"File does not exist: {file_path}"
            )
        
        # Check if it's actually a file
        if not path.is_file():
            return FileValidationResult(
                valid=False,
                error_message=f"Path is not a file: {file_path}"
            )
        
        # Get file size
        file_size = path.stat().st_size
        
        # Check if file is empty
        if file_size == 0:
            return FileValidationResult(
                valid=False,
                error_message=f"File is empty: {file_path}",
                file_size=file_size
            )
        
        # Check file size limits
        size_limit = DISCORD_FILE_SIZE_LIMIT_NITRO if use_nitro_limits else DISCORD_FILE_SIZE_LIMIT_REGULAR
        if file_size > size_limit:
            limit_mb = size_limit / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            return FileValidationResult(
                valid=False,
                error_message=f"File too large: {actual_mb:.1f}MB exceeds {limit_mb:.0f}MB limit",
                file_size=file_size
            )
        
        # Check file format
        file_format = path.suffix.lower()
        if file_format not in SUPPORTED_IMAGE_FORMATS:
            return FileValidationResult(
                valid=False,
                error_message=f"Unsupported file format: {file_format}. Supported: {', '.join(SUPPORTED_IMAGE_FORMATS)}",
                file_size=file_size,
                file_format=file_format
            )
        
        # All validations passed
        return FileValidationResult(
            valid=True,
            file_size=file_size,
            file_format=file_format
        )
        
    except Exception as e:
        logger.exception(f"Error validating file {file_path}: {e}")
        return FileValidationResult(
            valid=False,
            error_message=f"Validation error: {str(e)}"
        )


def create_discord_file_safe(file_path: str | Path, filename: str | None = None) -> discord.File | None:
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
            logger.warning(f"File validation failed for {file_path}: {validation.error_message}")
            return None
        
        # Use provided filename or derive from path
        display_filename = filename or path.name
        
        # Create Discord file object
        with path.open('rb') as f:
            discord_file = discord.File(f, filename=display_filename)
            
        logger.debug(f"Created Discord file object for {file_path} ({validation.file_size} bytes)")
        return discord_file
        
    except Exception as e:
        logger.error(f"Failed to create Discord file object for {file_path}: {e}")
        return None


async def upload_files_to_channel(
    channel: discord.TextChannel,
    file_paths: list[str],
    embed: discord.Embed | None = None,
    use_nitro_limits: bool = False
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
        return DiscordUploadResult(
            success=False,
            error_message="No files provided for upload"
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
                    validation_errors.append(f"Failed to create Discord file for {file_path}")
            else:
                validation_errors.append(f"{file_path}: {validation.error_message}")
        
        # Log validation errors
        if validation_errors:
            for error in validation_errors:
                logger.warning(f"File validation error: {error}")
        
        # Check if we have any valid files to upload
        if not discord_files:
            return DiscordUploadResult(
                success=False,
                error_message=f"No valid files to upload. Errors: {'; '.join(validation_errors)}"
            )
        
        # Upload files to Discord
        try:
            if embed:
                message = await channel.send(embed=embed, files=discord_files)
            else:
                message = await channel.send(files=discord_files)
            
            logger.info(f"Successfully uploaded {len(discord_files)} files to channel {channel.id}")
            return DiscordUploadResult(
                success=True,
                message_id=message.id,
                files_uploaded=len(discord_files)
            )
            
        except discord.HTTPException as e:
            error_msg = f"Discord upload failed: {e}"
            logger.error(error_msg)
            return DiscordUploadResult(
                success=False,
                error_message=error_msg
            )
        
    except Exception as e:
        error_msg = f"Unexpected error during file upload: {e}"
        logger.exception(error_msg)
        return DiscordUploadResult(
            success=False,
            error_message=error_msg
        )


async def upload_files_to_user_dm(
    user: discord.User | discord.Member,
    file_paths: list[str],
    embed: discord.Embed | None = None,
    use_nitro_limits: bool = False
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
        return DiscordUploadResult(
            success=False,
            error_message="No files provided for upload"
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
                    validation_errors.append(f"Failed to create Discord file for {file_path}")
            else:
                validation_errors.append(f"{file_path}: {validation.error_message}")
        
        # Log validation errors
        if validation_errors:
            for error in validation_errors:
                logger.warning(f"File validation error: {error}")
        
        # Check if we have any valid files to upload
        if not discord_files:
            return DiscordUploadResult(
                success=False,
                error_message=f"No valid files to upload. Errors: {'; '.join(validation_errors)}"
            )
        
        # Upload files to user DM
        try:
            if embed:
                message = await user.send(embed=embed, files=discord_files)
            else:
                message = await user.send(files=discord_files)
            
            logger.info(f"Successfully uploaded {len(discord_files)} files to user {user.id} DM")
            return DiscordUploadResult(
                success=True,
                message_id=message.id,
                files_uploaded=len(discord_files)
            )
            
        except discord.HTTPException as e:
            error_msg = f"Discord DM upload failed: {e}"
            logger.error(error_msg)
            return DiscordUploadResult(
                success=False,
                error_message=error_msg
            )
        
    except Exception as e:
        error_msg = f"Unexpected error during DM upload: {e}"
        logger.exception(error_msg)
        return DiscordUploadResult(
            success=False,
            error_message=error_msg
        )


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
