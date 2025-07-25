"""
Unified time management utilities for TGraph Bot.

This package provides consistent timezone and scheduling utilities
across the entire application.
"""

from .timezone import (
    get_system_timezone,
    get_system_now,
    ensure_timezone_aware,
    to_system_timezone,
    format_for_discord,
    TimestampStyle,
)
from .scheduling import (
    calculate_next_update_time,
    parse_fixed_time,
    is_valid_fixed_time,
    calculate_next_fixed_time,
    calculate_next_interval_time,
)

__all__ = [
    "get_system_timezone",
    "get_system_now",
    "ensure_timezone_aware",
    "to_system_timezone",
    "format_for_discord",
    "TimestampStyle",
    "calculate_next_update_time",
    "parse_fixed_time",
    "is_valid_fixed_time",
    "calculate_next_fixed_time",
    "calculate_next_interval_time",
]
