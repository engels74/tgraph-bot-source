"""
Permission checking and logging for TGraph Bot.

This module handles checking and logging Discord command permissions
for the bot across all guilds, ensuring commands have appropriate access controls.
"""

import logging
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from discord.ext import commands

logger = logging.getLogger(__name__)


class PermissionChecker:
    """Handles permission checking and validation for Discord commands."""
    
    def __init__(self, bot: "commands.Bot") -> None:
        """
        Initialize the permission checker.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        
    async def check_bot_permissions(self, guild: discord.Guild) -> dict[str, bool]:
        """
        Check bot permissions in a specific guild.
        
        Args:
            guild: The Discord guild to check permissions in
            
        Returns:
            Dictionary mapping permission names to their status
        """
        if guild.me is None:
            logger.warning(f"Bot member not found in guild {guild.name}")
            return {}
            
        permissions = guild.me.guild_permissions
        
        required_permissions = {
            "send_messages": permissions.send_messages,
            "embed_links": permissions.embed_links,
            "attach_files": permissions.attach_files,
            "use_slash_commands": permissions.use_slash_commands,
            "read_message_history": permissions.read_message_history,
            "manage_messages": permissions.manage_messages,
        }
        
        return required_permissions
        
    async def log_permission_status(self) -> None:
        """Log permission status for all guilds the bot is in."""
        for guild in self.bot.guilds:
            permissions = await self.check_bot_permissions(guild)
            
            missing_permissions = [
                perm for perm, has_perm in permissions.items() 
                if not has_perm
            ]
            
            if missing_permissions:
                logger.warning(
                    f"Missing permissions in {guild.name}: {', '.join(missing_permissions)}"
                )
            else:
                logger.info(f"All required permissions present in {guild.name}")
                
    async def check_user_permissions(
        self, 
        interaction: discord.Interaction,
        required_permissions: list[str]
    ) -> bool:
        """
        Check if a user has required permissions for a command.
        
        Args:
            interaction: The Discord interaction
            required_permissions: List of required permission names
            
        Returns:
            True if user has all required permissions, False otherwise
        """
        if interaction.guild is None:
            # DM context - allow for personal commands
            return True
            
        if interaction.user == interaction.guild.owner:
            # Guild owner always has permissions
            return True
            
        if not isinstance(interaction.user, discord.Member):
            return False
            
        user_permissions = interaction.user.guild_permissions
        
        for permission in required_permissions:
            if not getattr(user_permissions, permission, False):
                logger.warning(
                    f"User {interaction.user} lacks permission {permission} "
                    f"in guild {interaction.guild.name}"
                )
                return False
                
        return True
        
    def is_admin_command(self, command_name: str) -> bool:
        """
        Check if a command requires admin permissions.
        
        Args:
            command_name: Name of the command
            
        Returns:
            True if command requires admin permissions
        """
        admin_commands = {
            "config",
            "update_graphs",
        }
        
        return command_name in admin_commands
