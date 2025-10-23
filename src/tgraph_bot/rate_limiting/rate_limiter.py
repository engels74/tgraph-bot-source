"""Rate limiting system for command cooldowns.

This module implements rate limiting for Discord commands with both
user-specific and global cooldowns to prevent spam and server overload.

Requirements implemented: 11.1, 11.2, 11.3, 11.4, 11.5, 23.1, 23.2, 23.3, 23.4, 23.5
"""

from __future__ import annotations

import asyncio
import contextvars
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TypedDict

from tgraph_bot.config.models import RateLimitingConfig

# Context variable for tracking the current user making a request
# This enables automatic user tracking across async operations without
# explicit parameter passing. Defaults to None when no user is set.
# Requirements: 23.1, 23.3, 23.4, 23.5
current_user_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_user_id", default=None
)


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
        _cleanup_task: Background task for periodic cooldown cleanup
    """

    config: RateLimitingConfig
    _user_cooldowns: dict[tuple[str, int], datetime] = field(default_factory=dict)
    _global_cooldowns: dict[str, datetime] = field(default_factory=dict)
    _cleanup_task: asyncio.Task[None] | None = field(default=None, init=False)

    def check_cooldown(self, command: str, user_id: int | None = None) -> CooldownInfo | None:
        """Check if a command is on cooldown for a user.

        Checks both user-specific and global cooldowns. If either is active,
        returns information about the active cooldown. User cooldown takes
        priority if both are active.

        Args:
            command: The command name to check
            user_id: The Discord user ID. If None, uses current_user_id context variable.

        Returns:
            CooldownInfo if on cooldown, None if command can be used

        Raises:
            ValueError: If user_id is None and current_user_id context variable is not set
        """
        # Get user_id from context variable if not provided
        if user_id is None:
            user_id = current_user_id.get()
            if user_id is None:
                raise ValueError(
                    "user_id must be provided or current_user_id context variable must be set"
                )

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

    def record_usage(self, command: str, user_id: int | None = None) -> None:
        """Record command usage and set cooldowns.

        Records the current time as the start of cooldown periods for
        both user-specific and global cooldowns based on the command's
        configuration.

        Args:
            command: The command name that was used
            user_id: The Discord user ID who used the command. If None, uses current_user_id context variable.

        Raises:
            ValueError: If user_id is None and current_user_id context variable is not set
        """
        # Get user_id from context variable if not provided
        if user_id is None:
            user_id = current_user_id.get()
            if user_id is None:
                raise ValueError(
                    "user_id must be provided or current_user_id context variable must be set"
                )

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

    async def start_periodic_cleanup(self, *, interval_seconds: float = 3600.0) -> None:
        """Start a background task that periodically cleans up expired cooldowns.

        This method starts an asyncio task that runs cleanup_expired() every
        interval_seconds. By default, cleanup runs every hour (3600.0 seconds).

        Args:
            interval_seconds: How often to run cleanup (default: 3600.0 = 1 hour)

        Note:
            This task runs continuously until stop_periodic_cleanup() is called.
            Requirements: 23.2 (automatic context inheritance in async tasks)
        """
        if self._cleanup_task is not None and not self._cleanup_task.done():
            # Task already running
            return

        self._cleanup_task = asyncio.create_task(
            self._periodic_cleanup_loop(interval_seconds)
        )

    async def stop_periodic_cleanup(self) -> None:
        """Stop the periodic cleanup background task.

        This method cancels the background cleanup task and waits for it
        to complete gracefully.
        """
        if self._cleanup_task is not None and not self._cleanup_task.done():
            _ = self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass  # Expected when cancelling
            self._cleanup_task = None

    async def _periodic_cleanup_loop(self, interval_seconds: float) -> None:
        """Internal method that runs the periodic cleanup loop.

        Args:
            interval_seconds: How often to run cleanup
        """
        while True:
            await asyncio.sleep(interval_seconds)
            self.cleanup_expired()

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
