"""
Command utility functions for TGraph Bot.

This module contains utility functions specifically related to Discord commands,
such as formatting command output or complex argument parsing.
"""

import logging
from typing import Any, Optional

import discord

logger = logging.getLogger(__name__)


def create_error_embed(
    title: str = "Error",
    description: str = "An error occurred",
    color: discord.Color = discord.Color.red()
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
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text="TGraph Bot")
    return embed


def create_success_embed(
    title: str = "Success",
    description: str = "Operation completed successfully",
    color: discord.Color = discord.Color.green()
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
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text="TGraph Bot")
    return embed


def create_info_embed(
    title: str = "Information",
    description: str = "",
    color: discord.Color = discord.Color.blue()
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
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text="TGraph Bot")
    return embed


def format_config_value(key: str, value: Any) -> str:
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
        return "***HIDDEN***"
        
    # Format boolean values
    if isinstance(value, bool):
        return "✅ Enabled" if value else "❌ Disabled"
        
    # Format None values
    if value is None:
        return "Not set"
        
    # Format string values
    if isinstance(value, str):
        if not value.strip():
            return "Empty"
        return str(value)
        
    # Format numeric values
    if isinstance(value, (int, float)):
        return str(value)
        
    # Default formatting
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
        
    return text[:max_length - 3] + "..."


def parse_time_string(time_str: str) -> Optional[tuple[int, int]]:
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
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if remaining_seconds > 0 or not parts:
        parts.append(f"{remaining_seconds} second{'s' if remaining_seconds != 1 else ''}")
        
    return ", ".join(parts)


def validate_email(email: str) -> bool:
    """
    Basic email validation.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email appears valid, False otherwise
    """
    import re
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def create_progress_embed(
    title: str,
    current: int,
    total: int,
    description: str = ""
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
        title=title,
        description=description,
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Progress",
        value=f"{progress_bar} {percentage:.1f}%\n{current}/{total}",
        inline=False
    )
    
    embed.set_footer(text="TGraph Bot")
    return embed
