"""Rate limiting system for command cooldowns.

This module implements rate limiting for Discord commands with both
user-specific and global cooldowns to prevent spam and server overload.

Requirements implemented: 11.1, 11.2, 11.3, 11.4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TypedDict

from tgraph_bot.config.models import RateLimitingConfig


class CooldownInfo(TypedDict):
    """Information about an active cooldown.

    Attributes:
        remaining_seconds: Number of seconds remaining in the cooldown
        is_user_cooldown: True if user cooldown, False if global cooldown
    """

    remaining_seconds: float
    is_user_cooldown: bool


@dataclass(slots=True)
class RateLimiter:
    """Manages command rate limiting with user and global cooldowns.

    This class tracks cooldowns for different commands with both per-user
    and global limits. User cooldowns prevent individual users from spamming,
    while global cooldowns prevent server overload from multiple users.

    Attributes:
        config: Rate limiting configuration for all commands
        _user_cooldowns: Dict mapping (command, user_id) to expiration time
        _global_cooldowns: Dict mapping command to expiration time
    """

    config: RateLimitingConfig
    _user_cooldowns: dict[tuple[str, int], datetime] = field(default_factory=dict)
    _global_cooldowns: dict[str, datetime] = field(default_factory=dict)

    def check_cooldown(self, command: str, user_id: int) -> CooldownInfo | None:
        """Check if a command is on cooldown for a user.

        Checks both user-specific and global cooldowns. If either is active,
        returns information about the active cooldown. User cooldown takes
        priority if both are active.

        Args:
            command: The command name to check
            user_id: The Discord user ID

        Returns:
            CooldownInfo if on cooldown, None if command can be used
        """
        now = datetime.now()

        # Get cooldown configuration for this command
        command_config = self._get_command_config(command)
        if command_config is None:
            return None

        # Check user cooldown first (higher priority)
        if command_config.user_cooldown_minutes > 0:
            user_key = (command, user_id)
            if user_key in self._user_cooldowns:
                expiration = self._user_cooldowns[user_key]
                if now < expiration:
                    remaining = (expiration - now).total_seconds()
                    return CooldownInfo(
                        remaining_seconds=remaining,
                        is_user_cooldown=True,
                    )

        # Check global cooldown
        if command_config.global_cooldown_seconds > 0:
            if command in self._global_cooldowns:
                expiration = self._global_cooldowns[command]
                if now < expiration:
                    remaining = (expiration - now).total_seconds()
                    return CooldownInfo(
                        remaining_seconds=remaining,
                        is_user_cooldown=False,
                    )

        return None

    def record_usage(self, command: str, user_id: int) -> None:
        """Record command usage and set cooldowns.

        Records the current time as the start of cooldown periods for
        both user-specific and global cooldowns based on the command's
        configuration.

        Args:
            command: The command name that was used
            user_id: The Discord user ID who used the command
        """
        now = datetime.now()

        # Get cooldown configuration for this command
        command_config = self._get_command_config(command)
        if command_config is None:
            return

        # Record user cooldown
        if command_config.user_cooldown_minutes > 0:
            user_key = (command, user_id)
            expiration = now + timedelta(minutes=command_config.user_cooldown_minutes)
            self._user_cooldowns[user_key] = expiration

        # Record global cooldown
        if command_config.global_cooldown_seconds > 0:
            expiration = now + timedelta(seconds=command_config.global_cooldown_seconds)
            self._global_cooldowns[command] = expiration

    def cleanup_expired(self) -> None:
        """Remove expired cooldown entries.

        This method should be called periodically to prevent memory
        buildup from old cooldown entries. It removes all entries
        where the expiration time has passed.
        """
        now = datetime.now()

        # Clean up expired user cooldowns
        expired_user_keys = [
            key for key, expiration in self._user_cooldowns.items() if now >= expiration
        ]
        for key in expired_user_keys:
            del self._user_cooldowns[key]

        # Clean up expired global cooldowns
        expired_global_keys = [
            command
            for command, expiration in self._global_cooldowns.items()
            if now >= expiration
        ]
        for command in expired_global_keys:
            del self._global_cooldowns[command]

    def _get_command_config(self, command: str):
        """Get the CommandLimits config for a given command.

        Args:
            command: The command name

        Returns:
            CommandLimits configuration or None if command not found
        """
        command_map = {
            "config": self.config.config,
            "update_graphs": self.config.update_graphs,
            "my_stats": self.config.my_stats,
        }
        return command_map.get(command)
