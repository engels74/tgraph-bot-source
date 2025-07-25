"""
Unified timezone handling utilities for TGraph Bot.

This module provides consistent timezone handling across the entire application,
replacing scattered timezone logic with a centralized, well-tested system.
"""

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord


# Type alias for Discord timestamp styles
TimestampStyle = Literal["t", "T", "d", "D", "f", "F", "R"]


def get_system_timezone() -> ZoneInfo:
    """
    Get the system's local timezone.

    This function provides a consistent way to get the system timezone
    across different platforms (Linux/WSL, macOS, Windows).

    Returns:
        ZoneInfo object representing the local timezone

    Examples:
        >>> tz = get_system_timezone()
        >>> isinstance(tz, ZoneInfo)
        True
    """
    # Use the system's local timezone - cross-platform approach
    try:
        # Try "localtime" first (works on Linux/WSL)
        return ZoneInfo("localtime")
    except ZoneInfoNotFoundError:
        # Fall back to getting the key from datetime for macOS/Windows
        local_tz = datetime.now().astimezone().tzinfo
        if hasattr(local_tz, "key"):
            key = getattr(local_tz, "key")  # pyright: ignore[reportAny] # timezone key from system
            if isinstance(key, str):
                return ZoneInfo(key)
        # Final fallback: use UTC
        return ZoneInfo("UTC")


def get_system_now() -> datetime:
    """
    Get the current datetime in the system's local timezone.

    Returns:
        Current datetime in the system's local timezone (timezone-aware)

    Examples:
        >>> now = get_system_now()
        >>> now.tzinfo is not None
        True
        >>> isinstance(now.tzinfo, ZoneInfo)
        True
    """
    return datetime.now(get_system_timezone())


def ensure_timezone_aware(dt: datetime) -> datetime:
    """
    Ensure a datetime object is timezone-aware.

    If the datetime is naive (no timezone info), it will be assumed to be
    in the system's local timezone. If it's already timezone-aware, it
    will be returned unchanged.

    Args:
        dt: Datetime object that may be naive or timezone-aware

    Returns:
        Timezone-aware datetime object

    Examples:
        >>> naive_dt = datetime(2025, 7, 25, 14, 30, 0)
        >>> aware_dt = ensure_timezone_aware(naive_dt)
        >>> aware_dt.tzinfo is not None
        True
        
        >>> already_aware = datetime(2025, 7, 25, 14, 30, 0, tzinfo=ZoneInfo("UTC"))
        >>> result = ensure_timezone_aware(already_aware)
        >>> result is already_aware
        True
    """
    if dt.tzinfo is None:
        # If naive, assume it's in local timezone
        return dt.replace(tzinfo=get_system_timezone())
    return dt


def to_system_timezone(dt: datetime) -> datetime:
    """
    Convert a datetime to the system's local timezone.

    If the datetime is naive, it will first be made timezone-aware using
    the system timezone, then returned. If it's already timezone-aware,
    it will be converted to the system timezone.

    Args:
        dt: Datetime object to convert

    Returns:
        Datetime object in the system's local timezone

    Examples:
        >>> utc_dt = datetime(2025, 7, 25, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
        >>> local_dt = to_system_timezone(utc_dt)
        >>> local_dt.tzinfo.key == get_system_timezone().key
        True
        
        >>> naive_dt = datetime(2025, 7, 25, 14, 30, 0)
        >>> local_dt = to_system_timezone(naive_dt)
        >>> local_dt.tzinfo.key == get_system_timezone().key
        True
    """
    # First ensure it's timezone-aware
    aware_dt = ensure_timezone_aware(dt)
    
    # Convert to system timezone
    return aware_dt.astimezone(get_system_timezone())


def format_for_discord(
    dt: datetime, style: TimestampStyle = "F"
) -> str:
    """
    Format a datetime object as a Discord timestamp.

    This function ensures the datetime is properly timezone-aware before
    formatting it for Discord, which fixes the timezone display issues.

    Args:
        dt: The datetime to format
        style: Discord timestamp style (default: 'F' for full date/time)

    Returns:
        Formatted Discord timestamp string

    Examples:
        >>> dt = datetime(2025, 7, 25, 23, 59, 0)
        >>> timestamp = format_for_discord(dt)
        >>> timestamp.startswith("<t:")
        True
        >>> timestamp.endswith(":F>")
        True
    """
    # Ensure timezone-aware datetime in system timezone
    aware_dt = to_system_timezone(dt)
    
    # Use discord.py's format_dt function for consistent formatting
    return discord.utils.format_dt(aware_dt, style=style)
