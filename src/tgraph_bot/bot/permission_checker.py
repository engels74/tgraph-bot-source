"""
Permission checking and logging for TGraph Bot.

This module handles checking and logging Discord bot permissions and slash command
permissions across all guilds. It provides comprehensive permission analysis including
bot permissions, command-level permission settings, and security warnings for
potentially misconfigured admin commands.
"""

import asyncio
import logging
import unicodedata
from typing import TYPE_CHECKING, Protocol, cast
from collections.abc import Sequence

import discord
from discord import app_commands

if TYPE_CHECKING:
    pass


class BotProtocol(Protocol):
    """Protocol for bot instances that can be used with PermissionChecker."""

    @property
    def guilds(self) -> Sequence[discord.Guild]: ...

    @property
    def tree(self) -> discord.app_commands.CommandTree: ...

logger = logging.getLogger(__name__)


class PermissionChecker:
    """
    Handles comprehensive bot and slash command permission checking.

    This class provides:
    - Bot permission validation across guilds
    - Slash command permission analysis
    - Security warnings for misconfigured admin commands
    - Formatted permission status logging with modern table output
    """

    # Expected command permissions based on their functionality
    EXPECTED_COMMAND_PERMISSIONS: dict[str, dict[str, str | bool]] = {
        "about": {"admin_required": False, "description": "Bot information"},
        "config": {"admin_required": True, "description": "Configuration management"},
        "my_stats": {"admin_required": False, "description": "Personal statistics"},
        "update_graphs": {"admin_required": True, "description": "Manual graph generation"},
        "test_scheduler": {"admin_required": True, "description": "Scheduler testing"},
        "uptime": {"admin_required": False, "description": "Bot uptime information"},
    }

    def __init__(self, bot: BotProtocol) -> None:
        """
        Initialize the permission checker.

        Args:
            bot: The Discord bot instance
        """
        self.bot: BotProtocol = bot

    async def check_bot_permissions(self, guild: discord.Guild) -> dict[str, bool]:
        """
        Check bot permissions in a specific guild.

        Args:
            guild: The Discord guild to check permissions in

        Returns:
            Dictionary mapping permission names to their status
        """
        bot_member = guild.me
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
            "use_application_commands": permissions.use_application_commands,
        }

        return required_permissions

    async def _fetch_commands_with_retry(
        self, guild: discord.Guild | None = None, max_retries: int = 3
    ) -> list[app_commands.AppCommand]:
        """
        Fetch commands from Discord API with retry logic for rate limiting.

        Args:
            guild: The guild to fetch commands for, or None for global commands
            max_retries: Maximum number of retry attempts

        Returns:
            List of application commands from Discord API

        Raises:
            discord.HTTPException: If non-rate-limit HTTP error occurs
        """
        for attempt in range(max_retries):
            try:
                if guild:
                    commands = await self.bot.tree.fetch_commands(guild=guild)
                else:
                    commands = await self.bot.tree.fetch_commands()

                guild_context = f"guild {guild.name}" if guild else "global"
                logger.debug(
                    f"Successfully fetched {len(commands)} commands from Discord API "
                    + f"for {guild_context} on attempt {attempt + 1}"
                )
                return commands

            except discord.HTTPException as e:
                # Handle rate limiting (HTTP 429)
                if e.status == 429:
                    retry_after = 1.0  # Default retry delay
                    if hasattr(e, 'response') and e.response and hasattr(e.response, 'headers'):
                        retry_after_header = e.response.headers.get('Retry-After')
                        if retry_after_header:
                            try:
                                retry_after = float(retry_after_header)
                            except (ValueError, TypeError):
                                pass  # Use default if header is invalid

                    if attempt < max_retries - 1:
                        logger.debug(
                            f"Rate limited on attempt {attempt + 1}, retrying after {retry_after}s"
                        )
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        logger.warning(
                            f"Rate limited on final attempt {attempt + 1}, giving up"
                        )
                        raise
                else:
                    # Non-rate-limit HTTP error, don't retry
                    logger.debug(f"HTTP error on attempt {attempt + 1}: {e}")
                    raise

        # This should never be reached due to the raise statements above
        return []

    async def get_slash_commands(self, guild: discord.Guild | None = None) -> list[app_commands.AppCommand]:
        """
        Get all slash commands for a guild or globally using Discord API.

        This method directly fetches commands from Discord's API rather than relying
        on local command tree state, which ensures we get the actual registered
        commands with their proper IDs and metadata.

        Args:
            guild: The guild to get commands for, or None for global commands

        Returns:
            List of application commands registered with Discord
        """
        try:
            # Directly fetch from Discord API with retry logic
            commands = await self._fetch_commands_with_retry(guild)

            guild_context = f"guild {guild.name}" if guild else "global"
            if commands:
                logger.debug(f"Found {len(commands)} registered commands for {guild_context}")
            else:
                logger.debug(f"No registered commands found for {guild_context}")

            return commands

        except discord.HTTPException as e:
            guild_context = f"guild {guild.name}" if guild else "global"
            logger.warning(f"Failed to fetch commands from Discord API for {guild_context}: {e}")
            return []

        except Exception as e:
            guild_context = f"guild {guild.name}" if guild else "global"
            logger.error(
                f"Unexpected error getting slash commands for {guild_context}: {e}",
                exc_info=True
            )
            return []

    def _analyze_command_permissions(self, command: app_commands.AppCommand) -> dict[str, str | bool]:
        """
        Analyze a command's permission configuration.

        Args:
            command: The application command to analyze

        Returns:
            Dictionary with permission analysis results
        """
        analysis = {
            "name": command.name,
            "has_default_permissions": command.default_member_permissions is not None,
            "requires_manage_guild": False,
            "is_admin_command": False,
            "security_warning": False,
            "warning_message": "",
        }

        # Check if this is an expected admin command
        expected = self.EXPECTED_COMMAND_PERMISSIONS.get(command.name, {})
        analysis["is_admin_command"] = bool(expected.get("admin_required", False))


        # Check default member permissions
        if command.default_member_permissions:
            analysis["requires_manage_guild"] = command.default_member_permissions.manage_guild

        # Security analysis for admin commands
        if analysis["is_admin_command"]:
            if not analysis["has_default_permissions"]:
                analysis["security_warning"] = True
                analysis["warning_message"] = "Admin command has no default permission restrictions"
            elif not analysis["requires_manage_guild"]:
                analysis["security_warning"] = True
                analysis["warning_message"] = "Admin command doesn't require Manage Server permission"

        return analysis

    async def _check_command_sync_status(self, guild: discord.Guild | None = None) -> dict[str, object]:
        """
        Check the sync status of commands to help with debugging.

        Args:
            guild: The guild to check, or None for global commands

        Returns:
            Dictionary with sync status information
        """
        status: dict[str, object] = {
            "local_commands_count": 0,
            "api_commands_count": 0,
            "local_command_names": [],
            "api_command_names": [],
            "sync_needed": False,
        }

        try:
            # Check local commands (what's in the command tree)
            if guild:
                local_commands = self.bot.tree.get_commands(guild=guild)
            else:
                local_commands = self.bot.tree.get_commands()

            status["local_commands_count"] = len(local_commands)
            status["local_command_names"] = [cmd.name for cmd in local_commands]

            # Check API commands (what's registered with Discord)
            try:
                api_commands = await self._fetch_commands_with_retry(guild, max_retries=1)
                status["api_commands_count"] = len(api_commands)
                status["api_command_names"] = [cmd.name for cmd in api_commands]

                # Check if sync is needed (different command counts or names)
                local_names = set(status["local_command_names"])
                api_names = set(status["api_command_names"])
                status["sync_needed"] = local_names != api_names

            except Exception as e:
                logger.debug(f"Could not fetch API commands for sync check: {e}")
                status["api_error"] = str(e)

        except Exception as e:
            logger.debug(f"Error checking command sync status: {e}")
            status["error"] = str(e)

        return status

    async def _analyze_enhanced_command_permissions(
        self, command: app_commands.AppCommand, guild: discord.Guild
    ) -> dict[str, str | list[str]]:
        """
        Analyze a command's permission configuration with enhanced detail.

        This method fetches and analyzes the complete permission setup for a command,
        including default permissions, role overrides, user overrides, and channel restrictions.

        Args:
            command: The application command to analyze
            guild: The Discord guild to analyze permissions for

        Returns:
            Dictionary with enhanced permission analysis results including:
            - name: Command name
            - accessible_by: Human-readable description of who can use the command
            - permission_overrides: List of role/user permission overrides
            - channel_restrictions: List of channel-specific permissions
        """
        analysis: dict[str, str | list[str]] = {
            "name": command.name,
            "accessible_by": "Accessible to all members",
            "permission_overrides": [],
            "channel_restrictions": [],
        }

        # Start with default accessible state - focus on Integration settings, not default permissions
        # Default permissions are bot developer settings, not server admin Integration settings
        analysis["accessible_by"] = "Accessible to all members"

        # Fetch guild-specific permission overrides
        try:
            guild_permissions = await command.fetch_permissions(guild)
            
            if guild_permissions and guild_permissions.permissions:
                # Process permission overrides
                role_overrides: list[str] = []
                user_overrides: list[str] = []
                channel_restrictions: list[str] = []
                
                for perm in guild_permissions.permissions:
                    if perm.type == discord.AppCommandPermissionType.role:
                        role = guild.get_role(perm.id)
                        if role:
                            status = "Allowed" if perm.permission else "Denied"
                            role_overrides.append(f"{role.name} ({status})")
                    
                    elif perm.type == discord.AppCommandPermissionType.user:
                        member = guild.get_member(perm.id)
                        if member:
                            status = "Allowed" if perm.permission else "Denied"
                            user_overrides.append(f"{member.display_name} ({status})")
                    
                    elif perm.type == discord.AppCommandPermissionType.channel:
                        channel = guild.get_channel(perm.id)
                        if channel:
                            status = "Allowed" if perm.permission else "Restricted"
                            channel_restrictions.append(f"#{channel.name} ({status})")

                # Update analysis with overrides
                analysis["permission_overrides"] = role_overrides + user_overrides
                analysis["channel_restrictions"] = channel_restrictions
                
                # Update accessible_by description to show Integration settings
                if role_overrides or user_overrides:
                    # Show the actual server admin's Integration permission settings
                    override_desc = ", ".join(role_overrides + user_overrides)
                    analysis["accessible_by"] = override_desc
                elif guild_permissions.permissions:
                    # If permissions exist but no role/user overrides, might have channel-only restrictions
                    analysis["accessible_by"] = "Integration settings configured"
                        
        except (discord.HTTPException, discord.Forbidden, discord.NotFound) as e:
            # Permission fetch failed - log debug info but continue with default analysis
            logger.debug(f"Failed to fetch permissions for command {command.name} in {guild.name}: {e}")
        except Exception as e:
            # Unexpected error - log but don't crash
            logger.warning(f"Unexpected error fetching permissions for {command.name}: {e}")

        return analysis

    async def _analyze_integration_permissions(self, guild: discord.Guild, commands: list[app_commands.AppCommand] | None = None) -> dict[str, str]:
        """
        Analyze Discord Integration permissions that control global access to the bot.
        
        This fetches the server admin's Integration settings that control:
        - Global "Roles & members" access to ALL bot commands
        - Global "Channels" restrictions for ALL bot commands
        
        Args:
            guild: The Discord guild to analyze
            commands: Optional list of commands to use (avoids re-fetching)
            
        Returns:
            Dictionary with integration permission analysis:
            - global_roles_access: Description of which roles can use the bot
            - global_channels_access: Description of channel restrictions
        """
        analysis = {
            "global_roles_access": "Not configured (all members)",
            "global_channels_access": "None (all channels)",
        }
        
        try:
            # Use provided commands or fetch them (optimization: prefer provided)
            if commands is None:
                commands = await self.bot.tree.fetch_commands(guild=guild)
            
            if commands:
                # Check if there are any guild-level integration settings
                # by looking at the first command's permissions as a proxy
                first_command = commands[0]
                try:
                    guild_permissions = await first_command.fetch_permissions(guild)
                    
                    if guild_permissions and guild_permissions.permissions:
                        # Analyze if there are global-like restrictions
                        roles_mentioned: list[str] = []
                        channels_mentioned: list[str] = []
                        
                        for perm in guild_permissions.permissions:
                            if perm.type == discord.AppCommandPermissionType.role:
                                role = guild.get_role(perm.id)
                                if role:
                                    if perm.id == guild.default_role.id:  # @everyone role
                                        if not perm.permission:
                                            analysis["global_roles_access"] = "Restricted from @everyone"
                                    else:
                                        status = "Allowed" if perm.permission else "Denied"
                                        roles_mentioned.append(f"{role.name} ({status})")
                            
                            elif perm.type == discord.AppCommandPermissionType.channel:
                                channel = guild.get_channel(perm.id)
                                if channel:
                                    status = "Allowed" if perm.permission else "Restricted"
                                    channels_mentioned.append(f"#{channel.name} ({status})")
                        
                        # Build descriptions from found permissions
                        if roles_mentioned:
                            analysis["global_roles_access"] = ", ".join(roles_mentioned[:3])  # Limit display
                            if len(roles_mentioned) > 3:
                                analysis["global_roles_access"] += f" (+{len(roles_mentioned) - 3} more)"
                        
                        if channels_mentioned:
                            analysis["global_channels_access"] = ", ".join(channels_mentioned[:2])  # Limit display
                            if len(channels_mentioned) > 2:
                                analysis["global_channels_access"] += f" (+{len(channels_mentioned) - 2} more)"
                    
                except (discord.HTTPException, discord.Forbidden, discord.NotFound):
                    # Permission fetch failed - use defaults
                    pass
            
        except (discord.HTTPException, discord.Forbidden) as e:
            # Failed to access integration permissions
            logger.debug(f"Failed to fetch integration permissions for {guild.name}: {e}")
            analysis["global_roles_access"] = "Unable to fetch (need Manage Server)"
            analysis["global_channels_access"] = "Unable to fetch (need Manage Server)"
        except Exception as e:
            # Unexpected error
            logger.warning(f"Unexpected error fetching integration permissions for {guild.name}: {e}")
        
        return analysis

    def _format_enhanced_permission_table(
        self, 
        guild: discord.Guild, 
        bot_permissions: dict[str, bool],
        enhanced_command_analyses: list[dict[str, str | list[str]]],
        integration_analysis: dict[str, str] | None = None
    ) -> str:
        """
        Format enhanced permission information into a modern table matching the reference format.

        Args:
            guild: The Discord guild
            bot_permissions: Bot permission status
            enhanced_command_analyses: List of enhanced command permission analyses

        Returns:
            Formatted table string with detailed permission information
        """
        lines: list[str] = []
        total_width = 80  # Total width including border characters

        # Header with guild info
        lines.append("┌" + "─" * (total_width - 2) + "┐")
        guild_name = guild.name[:50] if len(guild.name) > 50 else guild.name
        header_content = f" 🔐 Permission Status for {guild_name}"
        lines.append(self._pad_line_to_width(header_content, total_width))
        lines.append("├" + "─" * (total_width - 2) + "┤")

        # Bot Permissions section (detailed list of Discord permissions)
        bot_header = " 🤖 Bot Permissions"
        lines.append(self._pad_line_to_width(bot_header, total_width))
        lines.append("├" + "─" * (total_width - 2) + "┤")
        
        # Show detailed Discord permissions with status
        for perm_name, has_perm in bot_permissions.items():
            status_indicator = "✅ Granted" if has_perm else "❌ Missing"
            perm_display = perm_name.replace("_", " ").title()
            perm_row = f" {perm_display:<30} | {status_indicator:<45}"
            lines.append(self._pad_line_to_width(perm_row, total_width))
        
        # Add visual separation between sections
        lines.append("├" + "─" * (total_width - 2) + "┤")

        # Integration Access Control section with proper headers
        integration_header = " ⚙️ Integration Access Control"
        lines.append(self._pad_line_to_width(integration_header, total_width))
        lines.append("├" + "─" * (total_width - 2) + "┤")
        
        # Table headers for integration section
        table_header_row = f" {'Permission Entity':<30} | {'Status':<45}"
        lines.append(self._pad_line_to_width(table_header_row, total_width))
        lines.append("├" + "─" * (total_width - 2) + "┤")
        
        # Use integration analysis if provided, otherwise use defaults
        if integration_analysis:
            global_roles_desc = integration_analysis.get("global_roles_access", "Not configured (all members)")
            global_channels_desc = integration_analysis.get("global_channels_access", "None (all channels)")
        else:
            global_roles_desc = "Not configured (all members)"
            global_channels_desc = "None (all channels)"
        
        # Global role access
        global_access_row = f" {'Global Roles & Members':<30} | {global_roles_desc:<45}"
        lines.append(self._pad_line_to_width(global_access_row, total_width))
        
        # Global channel restrictions
        global_channels_row = f" {'Global Channel Restrictions':<30} | {global_channels_desc:<45}"
        lines.append(self._pad_line_to_width(global_channels_row, total_width))
        lines.append("├" + "─" * (total_width - 2) + "┤")

        # Command permissions section (keeping the same header format)
        cmd_header_row = f" {'Command':<30} | {'Accessible by':<45}"
        lines.append(self._pad_line_to_width(cmd_header_row, total_width))
        lines.append("├" + "─" * (total_width - 2) + "┤")
        
        if not enhanced_command_analyses:
            no_cmd_row = f" {'No commands found':<30} | {'':<45}"
            lines.append(self._pad_line_to_width(no_cmd_row, total_width))
        else:
            # Sort commands alphabetically by name
            sorted_analyses = sorted(enhanced_command_analyses, key=lambda x: str(x["name"]).lower())
            for analysis in sorted_analyses:
                name = str(analysis["name"])
                accessible_by = str(analysis["accessible_by"])
                
                # Truncate accessible_by if too long
                if len(accessible_by) > 45:
                    accessible_by = accessible_by[:42] + "..."
                
                cmd_row = f" /{name:<29} | {accessible_by:<45}"
                lines.append(self._pad_line_to_width(cmd_row, total_width))
                
                # Add channel restriction info if present
                channel_restrictions = analysis.get("channel_restrictions", [])
                if isinstance(channel_restrictions, list) and channel_restrictions:
                    for restriction in channel_restrictions:
                        restriction_row = f" {'':<30} | {str(restriction):<45}"
                        lines.append(self._pad_line_to_width(restriction_row, total_width))

        # Close table
        lines.append("└" + "─" * (total_width - 2) + "┘")

        return "\n".join(lines)

    def _build_bot_permissions_description(self, bot_permissions: dict[str, bool]) -> str:
        """
        Build a concise description of bot permissions status.

        Args:
            bot_permissions: Dictionary of permission name to status

        Returns:
            Human-readable description of bot permission status
        """
        missing_perms = [perm for perm, has_perm in bot_permissions.items() if not has_perm]
        
        if not missing_perms:
            return "All required permissions granted"
        elif len(missing_perms) <= 2:
            missing_display = [perm.replace("_", " ").title() for perm in missing_perms]
            return f"Missing: {', '.join(missing_display)}"
        else:
            return f"Missing {len(missing_perms)} permissions"

    def _calculate_visual_width(self, text: str) -> int:
        """
        Calculate the visual width of text accounting for wide Unicode characters.

        This is important for proper alignment in terminals where emojis and other
        wide characters take up 2 display columns instead of 1.

        Args:
            text: The text to measure

        Returns:
            The visual width in terminal columns
        """
        width = 0
        for char in text:
            if unicodedata.east_asian_width(char) in ('F', 'W'):
                # Full-width or wide characters (like emojis) take 2 columns
                width += 2
            elif unicodedata.combining(char):
                # Combining characters don't add visual width
                width += 0
            else:
                # Normal characters take 1 column
                width += 1
        return width

    def _pad_line_to_width(self, content: str, total_width: int) -> str:
        """
        Pad a line to a specific total width, accounting for Unicode characters.

        This ensures all table lines have exactly the same visual width,
        which is important for proper alignment in terminals. It properly handles
        emojis and other wide Unicode characters that take up 2 display columns.

        Args:
            content: The content to pad (without border characters)
            total_width: The desired total width including border characters

        Returns:
            Properly padded line with border characters
        """
        # For content lines, we want: │ + content + padding + │
        # So the content area is total_width - 2 (for the two │ characters)
        target_visual_width = total_width - 2

        # Calculate the current visual width of the content
        current_visual_width = self._calculate_visual_width(content)

        # Calculate how much padding we need based on visual width
        if current_visual_width > target_visual_width:
            # Content is too wide - we need to truncate
            # This is tricky with Unicode, so we'll truncate character by character
            # until we fit within the target width
            truncated_content = ""
            for char in content:
                test_content = truncated_content + char
                if self._calculate_visual_width(test_content) <= target_visual_width:
                    truncated_content = test_content
                else:
                    break
            padded_content = truncated_content
            # Add any remaining padding needed
            remaining_width = target_visual_width - self._calculate_visual_width(padded_content)
            padded_content += " " * remaining_width
        else:
            # Content fits - just add padding spaces
            padding_needed = target_visual_width - current_visual_width
            padded_content = content + " " * padding_needed

        return f"│{padded_content}│"

    def _format_permission_table(self, guild: discord.Guild, bot_permissions: dict[str, bool],
                                command_analyses: list[dict[str, str | bool]]) -> str:
        """
        Format permission information into a modern table.

        Args:
            guild: The Discord guild
            bot_permissions: Bot permission status
            command_analyses: List of command permission analyses

        Returns:
            Formatted table string
        """
        lines: list[str] = []
        total_width = 80  # Total width including border characters

        # Header with guild info
        lines.append("┌" + "─" * (total_width - 2) + "┐")
        guild_name = guild.name[:50] if len(guild.name) > 50 else guild.name
        header_content = f" 🔐 Permission Status for {guild_name}"
        lines.append(self._pad_line_to_width(header_content, total_width))
        lines.append("├" + "─" * (total_width - 2) + "┤")

        # Bot permissions section
        bot_header = " 🤖 Bot Permissions"
        lines.append(self._pad_line_to_width(bot_header, total_width))
        lines.append("├" + "─" * (total_width - 2) + "┤")

        for perm_name, has_perm in bot_permissions.items():
            status = "✅" if has_perm else "❌"
            perm_display = perm_name.replace("_", " ").title()
            perm_content = f" {status} {perm_display}"
            lines.append(self._pad_line_to_width(perm_content, total_width))

        # Command permissions section
        lines.append("├" + "─" * (total_width - 2) + "┤")
        cmd_header = " ⚡ Slash Command Analysis"
        lines.append(self._pad_line_to_width(cmd_header, total_width))
        lines.append("├" + "─" * (total_width - 2) + "┤")

        if not command_analyses:
            no_cmd_content = " No commands found"
            lines.append(self._pad_line_to_width(no_cmd_content, total_width))
        else:
            for analysis in command_analyses:
                name = str(analysis["name"])
                is_admin = bool(analysis["is_admin_command"])
                has_perms = bool(analysis["has_default_permissions"])
                requires_manage = bool(analysis["requires_manage_guild"])
                has_warning = bool(analysis["security_warning"])

                # Command status indicators
                admin_indicator = "🔒" if is_admin else "🔓"
                perm_indicator = "✅" if has_perms else "❌"
                manage_indicator = "🛡️" if requires_manage else "📝"
                warning_indicator = "⚠️" if has_warning else "  "

                # Format command line with proper spacing
                cmd_content = f" {warning_indicator}{admin_indicator} /{name:<15} {perm_indicator} {manage_indicator} {perm_indicator}"
                lines.append(self._pad_line_to_width(cmd_content, total_width))

                # Add warning message if present
                if has_warning and analysis["warning_message"]:
                    warning_msg = str(analysis["warning_message"])
                    # Truncate warning message to fit within table (leave room for prefix)
                    max_warning_width = total_width - 10  # Account for border and prefix
                    if len(warning_msg) > max_warning_width:
                        warning_msg = warning_msg[:max_warning_width - 3] + "..."
                    warning_content = f"   ⚠️  {warning_msg}"
                    lines.append(self._pad_line_to_width(warning_content, total_width))

        # Legend
        lines.append("├" + "─" * (total_width - 2) + "┤")
        legend_content = " Legend: 🔒=Admin 🔓=User ✅=Has Perms ❌=No Perms 🛡️=Manage Server"
        lines.append(self._pad_line_to_width(legend_content, total_width))
        lines.append("└" + "─" * (total_width - 2) + "┘")

        return "\n".join(lines)

    def _log_command_registration_summary(
        self,
        guild_commands: list[app_commands.AppCommand],
        global_commands: list[app_commands.AppCommand],
        guild_local_count: int,
        guild_api_count: int,
        global_local_count: int,
        global_api_count: int,
    ) -> None:
        """
        Log a comprehensive but concise summary of command registration status.
        
        Args:
            guild_commands: Guild-specific commands from Discord API
            global_commands: Global commands from Discord API
            guild_local_count: Number of guild-specific commands in local tree
            guild_api_count: Number of guild-specific commands registered with Discord
            global_local_count: Number of global commands in local tree
            global_api_count: Number of global commands registered with Discord
        """
        # Determine registration strategy and health
        has_global = len(global_commands) > 0
        has_guild = len(guild_commands) > 0
        
        if has_global and not has_guild:
            strategy = "global commands (recommended)"
            is_healthy = global_local_count == global_api_count
        elif has_guild and not has_global:
            strategy = "guild-specific commands"
            is_healthy = guild_local_count == guild_api_count
        elif has_global and has_guild:
            strategy = "mixed global + guild commands"
            is_healthy = (global_local_count == global_api_count) and (guild_local_count == guild_api_count)
        else:
            strategy = "no commands"
            is_healthy = False

        # Log the summary
        if has_global or has_guild:
            status_emoji = "✅" if is_healthy else "⚠️"
            
            logger.info(f"{status_emoji} Command registration strategy: {strategy}")
            
            if has_global:
                global_names = [cmd.name for cmd in global_commands]
                sync_status = "synced" if global_local_count == global_api_count else "out of sync"
                logger.info(f"   Global: {len(global_commands)} registered ({sync_status}) - {', '.join(sorted(global_names))}")
            
            if has_guild:
                guild_names = [cmd.name for cmd in guild_commands]
                sync_status = "synced" if guild_local_count == guild_api_count else "out of sync"
                logger.info(f"   Guild-specific: {len(guild_commands)} registered ({sync_status}) - {', '.join(sorted(guild_names))}")
            
            # Note about sync status if there are issues
            if not is_healthy:
                if has_global and global_local_count != global_api_count:
                    logger.warning(f"   ⚠️  Global command sync issue: {global_local_count} local vs {global_api_count} registered")
                if has_guild and guild_local_count != guild_api_count:
                    logger.warning(f"   ⚠️  Guild command sync issue: {guild_local_count} local vs {guild_api_count} registered")
        else:
            logger.info("📋 Command registration: using global commands (0 guild-specific is normal)")

    def _log_no_commands_found(
        self,
        guild: discord.Guild,
        guild_local_count: int,
        guild_api_count: int,
        global_local_count: int,
        global_api_count: int,
    ) -> None:
        """
        Log detailed diagnostics when no commands are found, with context about what might be wrong.
        
        Args:
            guild: The Discord guild being analyzed
            guild_local_count: Number of guild-specific commands in local tree
            guild_api_count: Number of guild-specific commands registered with Discord
            global_local_count: Number of global commands in local tree
            global_api_count: Number of global commands registered with Discord
        """
        logger.warning(f"❌ No commands available in {guild.name} - this indicates a problem:")
        
        # Analyze the specific issue
        total_local = guild_local_count + global_local_count
        total_api = guild_api_count + global_api_count
        
        if total_local > 0 and total_api == 0:
            logger.warning("   🔄 Commands exist locally but aren't registered with Discord")
            logger.warning("   💡 Solution: Run command sync (bot may need restart or manual sync)")
        elif total_local == 0 and total_api == 0:
            logger.warning("   📋 No commands found locally or on Discord")
            logger.warning("   💡 Solution: Check that bot extensions loaded properly")
        elif total_local == 0 and total_api > 0:
            logger.warning("   🔄 Commands registered with Discord but not found locally") 
            logger.warning("   💡 Solution: Check that bot extensions are loading correctly")
        else:
            logger.warning("   🤔 Inconsistent command state detected")
            logger.warning(f"   📊 Local: guild={guild_local_count}, global={global_local_count}")
            logger.warning(f"   📊 Discord: guild={guild_api_count}, global={global_api_count}")
        
        logger.warning("   🔧 Troubleshooting steps:")
        logger.warning("     1. Check bot permissions (Use Application Commands)")
        logger.warning("     2. Verify Discord API connectivity")
        logger.warning("     3. Check for command sync failures in logs")
        logger.warning("     4. Consider restarting the bot")

    async def check_slash_command_permissions(self, guild: discord.Guild) -> None:
        """
        Check and log slash command permissions for a specific guild.
        Optimized version that minimizes Discord API calls and uses concurrency.

        Args:
            guild: The Discord guild to check permissions for
        """
        try:
            # Get bot permissions (this is fast, no API call)
            bot_permissions = await self.check_bot_permissions(guild)

            # Fetch both guild and global commands concurrently to minimize API calls
            logger.info(f"Analyzing command registration status for {guild.name}...")
            
            guild_commands_task = self.get_slash_commands(guild)
            global_commands_task = self.get_slash_commands(None)
            
            # Run both command fetches concurrently
            guild_commands, global_commands = await asyncio.gather(
                guild_commands_task, global_commands_task, return_exceptions=True
            )
            
            # Handle potential exceptions from concurrent operations
            if isinstance(guild_commands, Exception):
                logger.warning(f"Failed to fetch guild commands: {guild_commands}")
                guild_commands = []
            if isinstance(global_commands, Exception):
                logger.warning(f"Failed to fetch global commands: {global_commands}")
                global_commands = []
                
            # Ensure type safety for mypy
            guild_commands = guild_commands if isinstance(guild_commands, list) else []
            global_commands = global_commands if isinstance(global_commands, list) else []

            # Calculate sync information from the already-fetched data (no additional API calls)
            guild_local_count = len(self.bot.tree.get_commands(guild=guild))
            guild_api_count = len(guild_commands)
            global_local_count = len(self.bot.tree.get_commands())
            global_api_count = len(global_commands)

            # Log comprehensive command registration summary
            self._log_command_registration_summary(
                guild_commands, global_commands,
                guild_local_count, guild_api_count, global_local_count, global_api_count
            )

            # Combine both command lists (guild commands take precedence)
            all_commands = guild_commands + global_commands

            # Remove duplicates efficiently using dict to preserve order (Python 3.7+)
            unique_commands: dict[str, app_commands.AppCommand] = {}
            for cmd in all_commands:
                if cmd.name not in unique_commands:
                    unique_commands[cmd.name] = cmd
            commands: list[app_commands.AppCommand] = list(unique_commands.values())

            # Handle case where no commands are found
            if not commands:
                self._log_no_commands_found(guild, guild_local_count, guild_api_count, global_local_count, global_api_count)
            else:
                command_names = [cmd.name for cmd in commands]
                logger.info(f"✅ {len(commands)} commands available: {', '.join(sorted(command_names))}")

            # Analyze commands concurrently for better performance
            command_analyses: list[dict[str, str | bool]] = []
            enhanced_command_analyses: list[dict[str, str | list[str]]] = []
            security_warnings: list[str] = []

            # Create tasks for enhanced analysis (which includes API calls)
            enhanced_analysis_tasks = [
                self._analyze_enhanced_command_permissions(command, guild)
                for command in commands
            ]
            
            # Run enhanced analyses concurrently
            enhanced_results = await asyncio.gather(*enhanced_analysis_tasks, return_exceptions=True)
            
            for i, command in enumerate(commands):
                # Run basic analysis (no API calls)
                old_analysis = self._analyze_command_permissions(command)
                command_analyses.append(old_analysis)

                # Get enhanced analysis result
                enhanced_result = enhanced_results[i]
                if isinstance(enhanced_result, Exception):
                    logger.debug(f"Failed enhanced analysis for {command.name}: {enhanced_result}")
                    # Fallback to basic analysis data
                    enhanced_analysis: dict[str, str | list[str]] = {
                        "name": command.name,
                        "accessible_by": "Accessible to all members",
                        "permission_overrides": [],
                        "channel_restrictions": [],
                    }
                else:
                    # Type narrowing: we know it's not an Exception here
                    # Use explicit cast since type narrowing isn't working properly
                    enhanced_analysis = cast(dict[str, str | list[str]], enhanced_result)
                
                enhanced_command_analyses.append(enhanced_analysis)

                # Check if this is an admin command and generate security warnings based on actual accessibility
                expected = self.EXPECTED_COMMAND_PERMISSIONS.get(command.name, {})
                is_admin_command = bool(expected.get("admin_required", False))
                
                if is_admin_command:
                    # Only check security if enhanced_analysis is valid (not an exception fallback)
                    if not isinstance(enhanced_result, Exception):
                        accessible_by = str(enhanced_analysis["accessible_by"])
                        # Security warning if admin command is accessible to all members
                        if accessible_by == "Accessible to all members":
                            warning_msg = f"/{command.name}: Admin command has no permission restrictions"
                            security_warnings.append(warning_msg)

            # Analyze Discord Integration permissions (only if we have commands to check)
            # Pass the already-fetched commands to avoid redundant API calls
            if commands:
                try:
                    # Use guild commands for integration analysis, or combined commands if no guild-specific commands
                    analysis_commands = guild_commands if guild_commands else commands
                    integration_analysis = await self._analyze_integration_permissions(guild, analysis_commands)
                except Exception as e:
                    logger.debug(f"Integration analysis failed: {e}")
                    integration_analysis = {
                        "global_roles_access": "Not configured (all members)",
                        "global_channels_access": "None (all channels)",
                    }
            else:
                integration_analysis = {
                    "global_roles_access": "Not configured (all members)",
                    "global_channels_access": "None (all channels)",
                }

            # Format and log the enhanced permission table
            table = self._format_enhanced_permission_table(guild, bot_permissions, enhanced_command_analyses, integration_analysis)
            logger.info(f"Permission status for {guild.name}:\n{table}")

            # Log security warnings separately
            if security_warnings:
                logger.warning(f"Security warnings for {guild.name}:")
                for warning in sorted(security_warnings):
                    logger.warning(f"  ⚠️  {warning}")

            # Log missing bot permissions
            missing_bot_perms = [perm for perm, has_perm in bot_permissions.items() if not has_perm]
            if missing_bot_perms:
                logger.warning(f"Missing bot permissions in {guild.name}: {', '.join(missing_bot_perms)}")

        except Exception as e:
            logger.error(f"Error checking permissions for {guild.name}: {e}", exc_info=True)

    async def log_permission_status(self) -> None:
        """
        Log comprehensive permission status for all guilds the bot is in.

        This is the main entry point for permission checking during startup.
        """
        if not self.bot.guilds:
            logger.warning("Bot is not in any guilds - cannot check permissions")
            return

        logger.info(f"Checking permissions across {len(self.bot.guilds)} guild(s)...")

        for guild in self.bot.guilds:
            await self.check_slash_command_permissions(guild)

        logger.info("Permission check completed for all guilds")

    def get_permission_help_text(self) -> str:
        """
        Get comprehensive help text for setting up Discord permissions.

        Returns:
            Help text explaining how to configure permissions
        """
        return (
            "**Discord Permission Setup Guide:**\n\n"
            "**Bot Permissions:**\n"
            "• Send Messages - Required for all bot responses\n"
            "• Embed Links - Required for rich message formatting\n"
            "• Attach Files - Required for graph image uploads\n"
            "• Read Message History - Required for message cleanup\n"
            "• Manage Messages - Required for cleaning up old bot messages\n"
            "• Use Application Commands - Required for slash commands\n\n"
            "**Slash Command Permissions:**\n"
            "Commands use Discord's native Integrations permission system:\n"
            "1. Go to Server Settings > Integrations > Bots and Apps\n"
            "2. Find TGraph Bot and click 'Manage'\n"
            "3. Configure command permissions for roles, users, or channels\n\n"
            "**Recommended Command Permissions:**\n"
            "• `/about`, `/uptime`, `/my_stats` - Available to all members\n"
            "• `/config`, `/update_graphs`, `/test_scheduler` - Require 'Manage Server'\n\n"
            "**Security Notes:**\n"
            "• Admin commands should always require 'Manage Server' permission\n"
            "• Review permission warnings in startup logs\n"
            "• Test permissions after configuration changes"
        )
