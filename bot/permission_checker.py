"""
Permission checking and logging for TGraph Bot.

This module handles checking and logging Discord bot permissions
across all guilds, ensuring the bot has appropriate access to function properly.
Uses Discord's native Integrations permissions system for command access control.
"""

import logging
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from discord.ext import commands

logger = logging.getLogger(__name__)


class PermissionChecker:
    """
    Handles bot permission checking and validation for Discord functionality.

    Note: Command-level permissions are handled by Discord's native Integrations
    system using default_member_permissions and app_commands.checks decorators.
    """

    def __init__(self, bot: "commands.Bot") -> None:
        """
        Initialize the permission checker.

        Args:
            bot: The Discord bot instance
        """
        self.bot: "commands.Bot" = bot

    async def check_bot_permissions(self, guild: discord.Guild) -> dict[str, bool]:
        """
        Check bot permissions in a specific guild.

        Args:
            guild: The Discord guild to check permissions in

        Returns:
            Dictionary mapping permission names to their status
        """
        bot_member = guild.me
        # Note: guild.me should never be None for a guild the bot is in,
        # but we check for type safety
        if bot_member is None:  # pyright: ignore[reportUnnecessaryComparison]
            logger.warning(f"Bot member not found in guild {guild.name}")
            return {}

        permissions = bot_member.guild_permissions

        required_permissions = {
            "send_messages": permissions.send_messages,
            "embed_links": permissions.embed_links,
            "attach_files": permissions.attach_files,
            "read_message_history": permissions.read_message_history,
            "manage_messages": permissions.manage_messages,
        }

        return required_permissions

    async def log_permission_status(self) -> None:
        """Log permission status for all guilds the bot is in."""
        for guild in self.bot.guilds:
            permissions = await self.check_bot_permissions(guild)

            missing_permissions = [
                perm for perm, has_perm in permissions.items() if not has_perm
            ]

            if missing_permissions:
                logger.warning(
                    f"Missing permissions in {guild.name}: {', '.join(missing_permissions)}"
                )
            else:
                logger.info(f"All required permissions present in {guild.name}")

    def get_permission_help_text(self) -> str:
        """
        Get help text for setting up Discord permissions.

        Returns:
            Help text explaining how to configure permissions
        """
        return (
            "**Discord Permission Setup:**\n"
            "Commands use Discord's native permission system. Server administrators can:\n"
            "1. Go to Server Settings > Integrations > Bots and Apps\n"
            "2. Find TGraph Bot and click 'Manage'\n"
            "3. Configure command permissions for roles, users, or channels\n"
            "4. Admin commands (config, update_graphs) require 'Manage Server' by default\n"
            "5. User commands (about, uptime, my_stats) are available to everyone by default"
        )
