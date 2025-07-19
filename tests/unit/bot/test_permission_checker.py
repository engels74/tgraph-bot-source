"""
Tests for the bot permission checker module.

This module tests the permission checking functionality including:
- Bot permission validation
- Slash command permission analysis
- Security warning generation
- Permission table formatting
- Rate limiting and retry logic
- Discord API command fetching
"""

from unittest.mock import AsyncMock, MagicMock, patch

import discord

from src.tgraph_bot.bot.permission_checker import PermissionChecker


class TestPermissionChecker:
    """Test the PermissionChecker class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_bot: MagicMock = MagicMock()  # pyright: ignore[reportUninitializedInstanceVariable]
        self.mock_bot.guilds = []
        self.mock_bot.tree = MagicMock(spec=discord.app_commands.CommandTree)
        self.permission_checker: PermissionChecker = PermissionChecker(self.mock_bot)  # pyright: ignore[reportUninitializedInstanceVariable]
        self.mock_guild: MagicMock = MagicMock(spec=discord.Guild)  # pyright: ignore[reportUninitializedInstanceVariable]

    async def test_check_bot_permissions_success(self):
        """Test successful bot permission checking."""
        # Setup mock permissions
        permissions = MagicMock()
        permissions.send_messages = True
        permissions.embed_links = True
        permissions.attach_files = True
        permissions.read_message_history = True
        permissions.manage_messages = True
        permissions.use_application_commands = True

        self.mock_guild.me.guild_permissions = permissions  # pyright: ignore[reportAny]

        result = await self.permission_checker.check_bot_permissions(self.mock_guild)

        expected = {
            "send_messages": True,
            "embed_links": True,
            "attach_files": True,
            "read_message_history": True,
            "manage_messages": True,
            "use_application_commands": True,
        }

        assert result == expected

    async def test_check_bot_permissions_missing_some(self):
        """Test bot permission checking with missing permissions."""
        # Setup mock permissions with some missing
        permissions = MagicMock()
        permissions.send_messages = True
        permissions.embed_links = False
        permissions.attach_files = True
        permissions.read_message_history = False
        permissions.manage_messages = True
        permissions.use_application_commands = True

        self.mock_guild.me.guild_permissions = permissions  # pyright: ignore[reportAny]

        result = await self.permission_checker.check_bot_permissions(self.mock_guild)

        assert result["send_messages"] is True
        assert result["embed_links"] is False
        assert result["read_message_history"] is False

    async def test_check_bot_permissions_no_bot_member(self):
        """Test bot permission checking when bot member is None."""
        self.mock_guild.me = None

        result = await self.permission_checker.check_bot_permissions(self.mock_guild)

        assert result == {}

    async def test_get_slash_commands_guild(self) -> None:
        """Test getting slash commands for a specific guild."""
        # Mock API commands from fetch_commands() - new implementation goes directly to API
        mock_api_command1 = MagicMock()
        mock_api_command1.name = "about"
        mock_api_command2 = MagicMock()
        mock_api_command2.name = "config"
        mock_api_commands = [mock_api_command1, mock_api_command2]

        self.mock_bot.tree.fetch_commands = AsyncMock(return_value=mock_api_commands)  # pyright: ignore[reportAny]

        result = await self.permission_checker.get_slash_commands(self.mock_guild)

        assert len(result) == 2
        assert result[0].name == "about"
        assert result[1].name == "config"
        # Should call fetch_commands directly to get AppCommand objects from Discord API
        self.mock_bot.tree.fetch_commands.assert_called_once_with(guild=self.mock_guild)  # pyright: ignore[reportAny]

    async def test_get_slash_commands_global(self) -> None:
        """Test getting global slash commands."""
        # Mock API commands from fetch_commands() - new implementation goes directly to API
        mock_api_command = MagicMock()
        mock_api_command.name = "uptime"
        mock_api_commands = [mock_api_command]

        self.mock_bot.tree.fetch_commands = AsyncMock(return_value=mock_api_commands)  # pyright: ignore[reportAny]

        result = await self.permission_checker.get_slash_commands()

        assert len(result) == 1
        assert result[0].name == "uptime"
        # Should call fetch_commands directly to get AppCommand objects from Discord API
        self.mock_bot.tree.fetch_commands.assert_called_once_with()  # pyright: ignore[reportAny]

    async def test_get_slash_commands_http_error(self) -> None:
        """Test handling HTTP errors when fetching commands."""
        # Mock fetch_commands fails with non-rate-limit error
        self.mock_bot.tree.fetch_commands = AsyncMock(  # pyright: ignore[reportAny]
            side_effect=discord.HTTPException(MagicMock(status=500), "API Error")
        )

        result = await self.permission_checker.get_slash_commands(self.mock_guild)

        assert result == []
        # Should only call once for non-rate-limit errors (no retry)
        assert self.mock_bot.tree.fetch_commands.call_count == 1  # pyright: ignore[reportAny]

    async def test_get_slash_commands_no_local_commands(self) -> None:
        """Test getting slash commands when API returns empty list."""
        # Mock API commands from fetch_commands() returning empty list
        self.mock_bot.tree.fetch_commands = AsyncMock(return_value=[])  # pyright: ignore[reportAny]

        result = await self.permission_checker.get_slash_commands(self.mock_guild)

        assert len(result) == 0
        # Should call fetch_commands directly
        self.mock_bot.tree.fetch_commands.assert_called_once_with(guild=self.mock_guild)  # pyright: ignore[reportAny]

    async def test_get_slash_commands_retry_success(self) -> None:
        """Test successful command retrieval after initial rate limit failure."""
        # Mock API commands
        mock_api_command = MagicMock()
        mock_api_command.name = "test"
        mock_api_commands = [mock_api_command]

        # First call fails with rate limit, second succeeds
        rate_limit_error = discord.HTTPException(
            response=MagicMock(status=429, headers={"Retry-After": "0.1"}),
            message="Rate limited",
        )

        self.mock_bot.tree.fetch_commands = AsyncMock(  # pyright: ignore[reportAny]
            side_effect=[
                rate_limit_error,  # First attempt fails with rate limit
                mock_api_commands,  # Second attempt succeeds
            ]
        )

        # Mock asyncio.sleep to speed up test
        with patch(
            "src.tgraph_bot.bot.permission_checker.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            result = await self.permission_checker.get_slash_commands(self.mock_guild)

        assert len(result) == 1
        assert result[0].name == "test"
        # Should call fetch_commands twice (first fails with rate limit, second succeeds)
        assert self.mock_bot.tree.fetch_commands.call_count == 2  # pyright: ignore[reportAny]

    def test_analyze_command_permissions_user_command(self) -> None:
        """Test analyzing permissions for a user command."""
        command = MagicMock()
        command.name = "about"
        command.default_member_permissions = None

        result = self.permission_checker._analyze_command_permissions(command)  # pyright: ignore[reportPrivateUsage]

        assert result["name"] == "about"
        assert result["is_admin_command"] is False
        assert result["security_warning"] is False
        assert result["has_default_permissions"] is False

    def test_analyze_command_permissions_admin_command_secure(self) -> None:
        """Test analyzing permissions for a properly secured admin command."""
        permissions = MagicMock()
        permissions.manage_guild = True
        command = MagicMock()
        command.name = "config"
        command.default_member_permissions = permissions

        result = self.permission_checker._analyze_command_permissions(command)  # pyright: ignore[reportPrivateUsage]

        assert result["name"] == "config"
        assert result["is_admin_command"] is True
        assert result["requires_manage_guild"] is True
        assert result["security_warning"] is False

    def test_analyze_command_permissions_admin_command_insecure(self) -> None:
        """Test analyzing permissions for an insecure admin command."""
        command = MagicMock()
        command.name = "update_graphs"
        command.default_member_permissions = None

        result = self.permission_checker._analyze_command_permissions(command)  # pyright: ignore[reportPrivateUsage]

        assert result["name"] == "update_graphs"
        assert result["is_admin_command"] is True
        assert result["security_warning"] is True
        assert "no default permission restrictions" in str(result["warning_message"])

    def test_analyze_command_permissions_admin_command_wrong_perms(self) -> None:
        """Test analyzing admin command with wrong permission requirements."""
        permissions = MagicMock()
        permissions.manage_guild = False  # Should be True for admin commands
        command = MagicMock()
        command.name = "test_scheduler"
        command.default_member_permissions = permissions

        result = self.permission_checker._analyze_command_permissions(command)  # pyright: ignore[reportPrivateUsage]

        assert result["name"] == "test_scheduler"
        assert result["is_admin_command"] is True
        assert result["requires_manage_guild"] is False
        assert result["security_warning"] is True
        assert "doesn't require Manage Server" in str(result["warning_message"])

    def test_format_permission_table(self) -> None:
        """Test formatting permission information into a table."""
        # Set up a proper guild name for the mock
        self.mock_guild.name = "Test Guild"

        bot_permissions = {
            "send_messages": True,
            "embed_links": False,
            "attach_files": True,
        }

        command_analyses = [
            {
                "name": "about",
                "is_admin_command": False,
                "has_default_permissions": False,
                "requires_manage_guild": False,
                "security_warning": False,
                "warning_message": "",
            },
            {
                "name": "config",
                "is_admin_command": True,
                "has_default_permissions": True,
                "requires_manage_guild": True,
                "security_warning": False,
                "warning_message": "",
            },
        ]

        result = self.permission_checker._format_permission_table(  # pyright: ignore[reportPrivateUsage]
            self.mock_guild, bot_permissions, command_analyses
        )

        assert "Test Guild" in result
        assert "Bot Permissions" in result
        assert "Slash Command Analysis" in result
        assert "✅" in result  # For permissions that are present
        assert "❌" in result  # For permissions that are missing
        assert "/about" in result
        assert "/config" in result
        assert "Legend:" in result

    def test_format_permission_table_alignment(self) -> None:
        """Test that the permission table has proper alignment with all vertical borders lined up."""
        # Set up a proper guild name for the mock
        self.mock_guild.name = "NoobSkateCrew"

        bot_permissions = {
            "send_messages": True,
            "embed_links": True,
            "attach_files": True,
            "read_message_history": True,
            "manage_messages": True,
            "use_application_commands": True,
        }

        command_analyses = [
            {
                "name": "about",
                "is_admin_command": False,
                "has_default_permissions": False,
                "requires_manage_guild": False,
                "security_warning": False,
                "warning_message": "",
            },
            {
                "name": "config",
                "is_admin_command": True,
                "has_default_permissions": True,
                "requires_manage_guild": True,
                "security_warning": False,
                "warning_message": "",
            },
            {
                "name": "update_graphs",
                "is_admin_command": True,
                "has_default_permissions": False,
                "requires_manage_guild": False,
                "security_warning": True,
                "warning_message": "Admin command has no default permission restrictions",
            },
        ]

        result = self.permission_checker._format_permission_table(  # pyright: ignore[reportPrivateUsage]
            self.mock_guild, bot_permissions, command_analyses
        )

        lines = result.split("\n")

        # Import unicodedata for visual width calculation
        import unicodedata

        def visual_width(text: str) -> int:
            """Calculate the visual width of text accounting for wide characters."""
            width = 0
            for char in text:
                if unicodedata.east_asian_width(char) in ("F", "W"):
                    width += 2  # Full-width or wide characters
                elif unicodedata.combining(char):
                    width += 0  # Combining characters don't add width
                else:
                    width += 1  # Normal characters
            return width

        # Check that all lines have exactly the same VISUAL width (80 columns)
        # This is what matters for proper alignment in terminals
        expected_visual_width = 80
        for i, line in enumerate(lines):
            actual_visual_width = visual_width(line)
            assert actual_visual_width == expected_visual_width, (
                f"Line {i + 1} has incorrect visual width: {actual_visual_width} (expected {expected_visual_width})\nLine: '{line}'"
            )

        # Check that all lines have proper border characters
        for i, line in enumerate(lines):
            if i == 0:  # Top border
                assert line.startswith("┌") and line.endswith("┐"), (
                    f"Top border line {i + 1} malformed: '{line}'"
                )
            elif i == len(lines) - 1:  # Bottom border
                assert line.startswith("└") and line.endswith("┘"), (
                    f"Bottom border line {i + 1} malformed: '{line}'"
                )
            elif "├" in line:  # Separator lines
                assert line.startswith("├") and line.endswith("┤"), (
                    f"Separator line {i + 1} malformed: '{line}'"
                )
            else:  # Content lines
                assert line.startswith("│") and line.endswith("│"), (
                    f"Content line {i + 1} malformed: '{line}'"
                )

        # Verify specific content is present and properly formatted
        assert "🔐 Permission Status for NoobSkateCrew" in result
        assert "🤖 Bot Permissions" in result
        assert "⚡ Slash Command Analysis" in result
        assert (
            "Legend: 🔒=Admin 🔓=User ✅=Has Perms ❌=No Perms 🛡️=Manage Server"
            in result
        )

        # Check that warning messages are properly formatted
        assert "⚠️  Admin command has no default permission restrictions" in result

    def test_pad_line_to_width(self) -> None:
        """Test the line padding functionality."""
        import unicodedata

        def visual_width(text: str) -> int:
            """Calculate the visual width of text accounting for wide characters."""
            width = 0
            for char in text:
                if unicodedata.east_asian_width(char) in ("F", "W"):
                    width += 2  # Full-width or wide characters
                elif unicodedata.combining(char):
                    width += 0  # Combining characters don't add width
                else:
                    width += 1  # Normal characters
            return width

        # Test regular ASCII text
        result = self.permission_checker._pad_line_to_width("Hello World", 20)  # pyright: ignore[reportPrivateUsage]
        assert visual_width(result) == 20  # Visual width should match
        assert len(result) == 20  # For ASCII, character length equals visual width
        assert result.startswith("│") and result.endswith("│")
        assert "Hello World" in result

        # Test text with emojis
        result = self.permission_checker._pad_line_to_width(" 🔐 Test", 20)  # pyright: ignore[reportPrivateUsage]
        assert visual_width(result) == 20  # Visual width should match
        assert len(result) == 19  # Character length will be less due to emoji
        assert result.startswith("│") and result.endswith("│")
        assert "🔐 Test" in result

        # Test empty string
        result = self.permission_checker._pad_line_to_width("", 10)  # pyright: ignore[reportPrivateUsage]
        assert visual_width(result) == 10
        assert len(result) == 10
        assert result == "│        │"  # 8 spaces between borders

    def test_pad_line_to_width_visual_alignment(self) -> None:
        """Test that lines with emojis have proper visual alignment."""
        # Test that lines with different emoji content have the same visual width
        line1 = self.permission_checker._pad_line_to_width(" ✅ Send Messages", 50)  # pyright: ignore[reportPrivateUsage]
        line2 = self.permission_checker._pad_line_to_width(" 🔐 Permission Status", 50)  # pyright: ignore[reportPrivateUsage]
        line3 = self.permission_checker._pad_line_to_width(" Regular ASCII text", 50)  # pyright: ignore[reportPrivateUsage]

        # Import unicodedata for visual width calculation
        import unicodedata

        def visual_width(text: str) -> int:
            """Calculate the visual width of text accounting for wide characters."""
            width = 0
            for char in text:
                if unicodedata.east_asian_width(char) in ("F", "W"):
                    width += 2  # Full-width or wide characters
                elif unicodedata.combining(char):
                    width += 0  # Combining characters don't add width
                else:
                    width += 1  # Normal characters
            return width

        # All lines should have the same VISUAL width (which is what matters for alignment)
        expected_visual_width = 50
        assert visual_width(line1) == expected_visual_width
        assert visual_width(line2) == expected_visual_width
        assert visual_width(line3) == expected_visual_width

        # Lines with emojis will have fewer characters but same visual width
        assert len(line1) == 49  # Has emoji, so fewer characters
        assert len(line2) == 49  # Has emoji, so fewer characters
        assert len(line3) == 50  # No emoji, so character count matches visual width

        # All lines should start and end with border characters
        assert line1.startswith("│") and line1.endswith("│")
        assert line2.startswith("│") and line2.endswith("│")
        assert line3.startswith("│") and line3.endswith("│")

        # The content between the borders should have consistent visual padding
        content1 = line1[1:-1]  # Remove border characters
        content2 = line2[1:-1]
        content3 = line3[1:-1]

        # All content should have the same visual width (48 characters for 50-char line)
        expected_content_visual_width = 48
        assert visual_width(content1) == expected_content_visual_width
        assert visual_width(content2) == expected_content_visual_width
        assert visual_width(content3) == expected_content_visual_width

    async def test_security_warnings_based_on_accessibility(self) -> None:
        """Test that security warnings are generated based on actual command accessibility."""
        # Setup mock bot permissions
        permissions = MagicMock()
        permissions.send_messages = True
        permissions.embed_links = True
        permissions.attach_files = True
        permissions.read_message_history = True
        permissions.manage_messages = True
        permissions.use_application_commands = True
        self.mock_guild.me.guild_permissions = permissions  # pyright: ignore[reportAny]

        # Create mock commands - all admin commands with default permissions but accessible to all
        mock_commands: list[MagicMock] = []
        for cmd_name in ["config", "update_graphs", "test_scheduler"]:
            mock_cmd = MagicMock(spec=discord.app_commands.Command)
            mock_cmd.name = cmd_name
            mock_permissions = MagicMock(spec=discord.Permissions)
            mock_permissions.manage_guild = True
            mock_cmd.default_member_permissions = mock_permissions
            mock_commands.append(mock_cmd)

        # Mock the command fetching
        self.mock_bot.tree.fetch_commands = AsyncMock(return_value=mock_commands)  # pyright: ignore[reportAny]

        # Mock sync status
        with patch.object(
            self.permission_checker,
            "_check_command_sync_status",
            new_callable=AsyncMock,
        ) as mock_sync:
            mock_sync.return_value = {
                "local_commands_count": 3,
                "api_commands_count": 3,
                "local_command_names": ["config", "update_graphs", "test_scheduler"],
                "api_command_names": ["config", "update_graphs", "test_scheduler"],
                "sync_needed": False,
            }

            # Mock enhanced analysis to return "Accessible to all members" for all admin commands
            async def mock_enhanced_analysis(
                command: MagicMock, _guild: MagicMock
            ) -> dict[str, str | list[str]]:
                command_name: str = command.name  # pyright: ignore[reportAny]
                return {
                    "name": command_name,
                    "accessible_by": "Accessible to all members",  # This should trigger warnings
                    "permission_overrides": [],
                    "channel_restrictions": [],
                }

            with patch.object(
                self.permission_checker,
                "_analyze_enhanced_command_permissions",
                side_effect=mock_enhanced_analysis,
            ):
                with patch.object(
                    self.permission_checker,
                    "_analyze_integration_permissions",
                    new_callable=AsyncMock,
                ) as mock_integration:
                    mock_integration.return_value = {
                        "global_roles_access": "Not configured (all members)",
                        "global_channels_access": "None (all channels)",
                    }

                    with patch(
                        "src.tgraph_bot.bot.permission_checker.logger"
                    ) as mock_logger:
                        await self.permission_checker.check_slash_command_permissions(
                            self.mock_guild
                        )

                        # Should log security warnings for ALL admin commands
                        warning_calls = [
                            call
                            for call in mock_logger.warning.call_args_list  # pyright: ignore[reportAny]
                            if "Security warnings" in str(call)  # pyright: ignore[reportAny]
                        ]
                        assert len(warning_calls) >= 1

                        # Check that all three admin commands generated warnings
                        all_warning_calls = mock_logger.warning.call_args_list  # pyright: ignore[reportAny]
                        warning_messages = [str(call) for call in all_warning_calls]  # pyright: ignore[reportAny]

                        config_warning_found = any(
                            "/config" in msg for msg in warning_messages
                        )
                        update_graphs_warning_found = any(
                            "/update_graphs" in msg for msg in warning_messages
                        )
                        test_scheduler_warning_found = any(
                            "/test_scheduler" in msg for msg in warning_messages
                        )

                        assert config_warning_found, (
                            "Expected warning for /config command"
                        )
                        assert update_graphs_warning_found, (
                            "Expected warning for /update_graphs command"
                        )
                        assert test_scheduler_warning_found, (
                            "Expected warning for /test_scheduler command"
                        )

    async def test_check_slash_command_permissions_with_warnings(self) -> None:
        """Test checking slash command permissions with security warnings."""
        # Setup mock bot permissions
        permissions = MagicMock()
        permissions.send_messages = True
        permissions.embed_links = True
        permissions.attach_files = True
        permissions.read_message_history = True
        permissions.manage_messages = True
        permissions.use_application_commands = True
        self.mock_guild.me.guild_permissions = permissions  # pyright: ignore[reportAny]

        # Setup mock commands with security issue
        mock_local_command = MagicMock()
        mock_local_command.name = "update_graphs"
        mock_local_commands = [mock_local_command]

        mock_api_command = MagicMock()
        mock_api_command.name = "update_graphs"
        mock_api_command.default_member_permissions = None
        mock_api_commands = [mock_api_command]

        self.mock_bot.tree.get_commands = MagicMock(return_value=mock_local_commands)  # pyright: ignore[reportAny]
        self.mock_bot.tree.fetch_commands = AsyncMock(return_value=mock_api_commands)  # pyright: ignore[reportAny]

        with patch("src.tgraph_bot.bot.permission_checker.logger") as mock_logger:
            await self.permission_checker.check_slash_command_permissions(
                self.mock_guild
            )

            # Should log the permission table
            mock_logger.info.assert_called()  # pyright: ignore[reportAny]
            # Should log security warnings
            mock_logger.warning.assert_called()  # pyright: ignore[reportAny]

    async def test_log_permission_status_no_guilds(self) -> None:
        """Test logging permission status when bot is in no guilds."""
        self.mock_bot.guilds = []

        with patch("src.tgraph_bot.bot.permission_checker.logger") as mock_logger:
            await self.permission_checker.log_permission_status()

            mock_logger.warning.assert_called_with(  # pyright: ignore[reportAny]
                "Bot is not in any guilds - cannot check permissions"
            )

    async def test_log_permission_status_multiple_guilds(self) -> None:
        """Test logging permission status for multiple guilds."""
        guild1 = MagicMock(spec=discord.Guild)
        guild1.name = "Guild 1"
        guild2 = MagicMock(spec=discord.Guild)
        guild2.name = "Guild 2"
        self.mock_bot.guilds = [guild1, guild2]

        # Setup permissions for both guilds
        for guild in [guild1, guild2]:
            permissions = MagicMock()
            permissions.send_messages = True
            permissions.embed_links = True
            permissions.attach_files = True
            permissions.read_message_history = True
            permissions.manage_messages = True
            permissions.use_application_commands = True
            guild.me.guild_permissions = permissions  # pyright: ignore[reportAny]

        self.mock_bot.tree.get_commands = MagicMock(return_value=[])  # pyright: ignore[reportAny]
        self.mock_bot.tree.fetch_commands = AsyncMock(return_value=[])  # pyright: ignore[reportAny]

        with patch("src.tgraph_bot.bot.permission_checker.logger") as mock_logger:
            await self.permission_checker.log_permission_status()

            # Should log info about checking permissions
            info_calls = [
                call
                for call in mock_logger.info.call_args_list  # pyright: ignore[reportAny]
                if "Checking permissions across" in str(call)  # pyright: ignore[reportAny]
            ]
            assert len(info_calls) == 1
            assert "2 guild(s)" in str(info_calls[0])  # pyright: ignore[reportAny]

    def test_get_permission_help_text(self) -> None:
        """Test getting permission help text."""
        help_text = self.permission_checker.get_permission_help_text()

        assert "Discord Permission Setup Guide" in help_text
        assert "Bot Permissions:" in help_text
        assert "Slash Command Permissions:" in help_text
        assert "Send Messages" in help_text
        assert "Manage Server" in help_text
        assert "Security Notes:" in help_text

    async def test_get_slash_commands_with_rate_limiting(self) -> None:
        """Test getting slash commands with rate limiting retry logic."""
        # Create mock commands
        mock_command = MagicMock()
        mock_command.name = "test_command"
        mock_command.id = 123456789
        mock_commands = [mock_command]

        # Mock rate limit error on first call, success on second
        rate_limit_error = discord.HTTPException(
            response=MagicMock(status=429, headers={"Retry-After": "0.1"}),
            message="Rate limited",
        )

        self.mock_bot.tree.fetch_commands = AsyncMock(  # pyright: ignore[reportAny]
            side_effect=[rate_limit_error, mock_commands]
        )

        result = await self.permission_checker.get_slash_commands(self.mock_guild)

        assert len(result) == 1
        assert result[0].name == "test_command"
        # Should have been called twice due to retry
        assert self.mock_bot.tree.fetch_commands.call_count == 2  # pyright: ignore[reportAny]

    async def test_get_slash_commands_max_retries_exceeded(self) -> None:
        """Test getting slash commands when max retries are exceeded."""
        # Mock rate limit error on all calls
        rate_limit_error = discord.HTTPException(
            response=MagicMock(status=429, headers={"Retry-After": "0.1"}),
            message="Rate limited",
        )

        self.mock_bot.tree.fetch_commands = AsyncMock(side_effect=rate_limit_error)  # pyright: ignore[reportAny]

        result = await self.permission_checker.get_slash_commands(self.mock_guild)

        # Should return empty list after max retries
        assert result == []
        # Should have been called 3 times (initial + 2 retries)
        assert self.mock_bot.tree.fetch_commands.call_count == 3  # pyright: ignore[reportAny]

    async def test_get_slash_commands_direct_api_fetch(self) -> None:
        """Test getting slash commands directly from Discord API."""
        # Create mock commands
        mock_command = MagicMock()
        mock_command.name = "direct_api_command"
        mock_command.id = 987654321
        mock_commands = [mock_command]

        # Mock successful API fetch
        self.mock_bot.tree.fetch_commands = AsyncMock(return_value=mock_commands)  # pyright: ignore[reportAny]

        result = await self.permission_checker.get_slash_commands(self.mock_guild)

        assert len(result) == 1
        assert result[0].name == "direct_api_command"
        self.mock_bot.tree.fetch_commands.assert_called_once_with(guild=self.mock_guild)  # pyright: ignore[reportAny]

    async def test_get_slash_commands_global_commands(self) -> None:
        """Test getting global slash commands (no guild specified)."""
        # Create mock global commands
        mock_command = MagicMock()
        mock_command.name = "global_command"
        mock_command.id = 111222333
        mock_commands = [mock_command]

        # Mock successful API fetch for global commands
        self.mock_bot.tree.fetch_commands = AsyncMock(return_value=mock_commands)  # pyright: ignore[reportAny]

        result = await self.permission_checker.get_slash_commands(guild=None)

        assert len(result) == 1
        assert result[0].name == "global_command"
        self.mock_bot.tree.fetch_commands.assert_called_once_with()  # pyright: ignore[reportAny]

    async def test_get_slash_commands_http_error_non_rate_limit(self) -> None:
        """Test getting slash commands with non-rate-limit HTTP error."""
        # Mock non-rate-limit HTTP error
        http_error = discord.HTTPException(
            response=MagicMock(status=500), message="Internal server error"
        )

        self.mock_bot.tree.fetch_commands = AsyncMock(side_effect=http_error)  # pyright: ignore[reportAny]

        with patch("src.tgraph_bot.bot.permission_checker.logger") as mock_logger:
            result = await self.permission_checker.get_slash_commands(self.mock_guild)

            # Should return empty list and log warning
            assert result == []
            mock_logger.warning.assert_called()  # pyright: ignore[reportAny]

    async def test_get_slash_commands_unexpected_error(self) -> None:
        """Test getting slash commands with unexpected error."""
        # Mock unexpected error
        unexpected_error = ValueError("Unexpected error")

        self.mock_bot.tree.fetch_commands = AsyncMock(side_effect=unexpected_error)  # pyright: ignore[reportAny]

        with patch("src.tgraph_bot.bot.permission_checker.logger") as mock_logger:
            result = await self.permission_checker.get_slash_commands(self.mock_guild)

            # Should return empty list and log error
            assert result == []
            mock_logger.error.assert_called()  # pyright: ignore[reportAny]

    async def test_get_slash_commands_empty_response(self) -> None:
        """Test getting slash commands when API returns empty list."""
        # Mock empty response
        self.mock_bot.tree.fetch_commands = AsyncMock(return_value=[])  # pyright: ignore[reportAny]

        result = await self.permission_checker.get_slash_commands(self.mock_guild)

        assert result == []
        self.mock_bot.tree.fetch_commands.assert_called_once_with(guild=self.mock_guild)  # pyright: ignore[reportAny]

    async def test_check_slash_command_permissions_combines_global_and_guild(
        self,
    ) -> None:
        """Test that check_slash_command_permissions combines global and guild commands."""
        # Mock guild commands
        mock_guild_command = MagicMock()
        mock_guild_command.name = "guild_command"
        mock_guild_command.id = 111
        mock_guild_command.default_member_permissions = None

        # Mock global commands
        mock_global_command = MagicMock()
        mock_global_command.name = "global_command"
        mock_global_command.id = 222
        mock_global_command.default_member_permissions = None

        # Mock bot permissions
        mock_permissions = MagicMock()
        mock_permissions.send_messages = True
        mock_permissions.embed_links = True
        mock_permissions.attach_files = True
        mock_permissions.manage_messages = True
        mock_permissions.manage_guild = True

        # Setup mocks
        self.permission_checker.check_bot_permissions = AsyncMock(
            return_value=mock_permissions
        )

        # Mock fetch_commands to return different results for guild vs global
        async def mock_fetch_commands(
            guild: discord.Guild | None = None,
        ) -> list[MagicMock]:
            if guild is None:
                return [mock_global_command]  # Global commands
            else:
                return [mock_guild_command]  # Guild commands

        self.mock_bot.tree.fetch_commands = AsyncMock(side_effect=mock_fetch_commands)  # pyright: ignore[reportAny]

        # Mock the sync status check
        with patch.object(
            self.permission_checker,
            "_check_command_sync_status",
            new_callable=AsyncMock,
        ) as mock_sync_check:
            mock_sync_check.return_value = {
                "local_commands_count": 2,
                "api_commands_count": 2,
                "local_command_names": ["guild_command", "global_command"],
                "api_command_names": ["guild_command", "global_command"],
                "sync_needed": False,
            }

            # Call the method
            with patch("src.tgraph_bot.bot.permission_checker.logger") as mock_logger:
                await self.permission_checker.check_slash_command_permissions(
                    self.mock_guild
                )

                # Verify that both guild and global commands were fetched
                # Now calls fetch_commands 3 times: guild commands, global commands, and integration analysis
                assert self.mock_bot.tree.fetch_commands.call_count >= 2  # pyright: ignore[reportAny]

                # Verify logging shows command registration info
                info_calls = [str(call) for call in mock_logger.info.call_args_list]  # pyright: ignore[reportAny]

                # The optimized version should log command availability
                found_availability_log = any(
                    "commands available:" in call for call in info_calls
                )
                assert found_availability_log, (
                    f"Expected availability log not found in: {info_calls}"
                )

    async def test_analyze_enhanced_command_permissions_default_access(self) -> None:
        """Test enhanced command permission analysis for default access patterns."""
        # Mock command with default permissions
        command = MagicMock()
        command.name = "about"
        command.default_member_permissions = None

        # Mock no permission overrides
        command.fetch_permissions = AsyncMock(return_value=None)

        result = await self.permission_checker._analyze_enhanced_command_permissions(  # pyright: ignore[reportPrivateUsage]
            command, self.mock_guild
        )

        assert result["name"] == "about"
        assert result["accessible_by"] == "Accessible to all members"
        assert result["permission_overrides"] == []
        assert result["channel_restrictions"] == []

    async def test_analyze_enhanced_command_permissions_admin_only(self) -> None:
        """Test enhanced command permission analysis for commands with no Integration overrides."""
        # Mock command with manage_guild permission requirement (bot developer setting)
        permissions = MagicMock()
        permissions.manage_guild = True
        command = MagicMock()
        command.name = "config"
        command.default_member_permissions = permissions

        # Mock no Integration permission overrides from server admin
        command.fetch_permissions = AsyncMock(return_value=None)

        result = await self.permission_checker._analyze_enhanced_command_permissions(  # pyright: ignore[reportPrivateUsage]
            command, self.mock_guild
        )

        assert result["name"] == "config"
        # Should show Integration settings, not bot developer's default permissions
        assert result["accessible_by"] == "Accessible to all members"
        assert result["permission_overrides"] == []

    async def test_analyze_enhanced_command_permissions_with_role_overrides(
        self,
    ) -> None:
        """Test enhanced command permission analysis with role-based overrides."""
        # Mock command with default permissions
        permissions = MagicMock()
        permissions.manage_guild = True
        command = MagicMock()
        command.name = "update_graphs"
        command.default_member_permissions = permissions

        # Mock permission overrides with role allowances
        mock_role_permission = MagicMock()
        mock_role_permission.type = discord.AppCommandPermissionType.role
        mock_role_permission.id = 123456789
        mock_role_permission.permission = True

        mock_guild_permissions = MagicMock()
        mock_guild_permissions.permissions = [mock_role_permission]
        command.fetch_permissions = AsyncMock(return_value=mock_guild_permissions)

        # Mock guild role lookup
        mock_role = MagicMock()
        mock_role.name = "Staff"
        mock_role.id = 123456789
        self.mock_guild.get_role = MagicMock(return_value=mock_role)

        result = await self.permission_checker._analyze_enhanced_command_permissions(  # pyright: ignore[reportPrivateUsage]
            command, self.mock_guild
        )

        assert result["name"] == "update_graphs"
        assert len(result["permission_overrides"]) == 1
        assert "Staff (Allowed)" in result["permission_overrides"][0]

    async def test_analyze_enhanced_command_permissions_with_user_overrides(
        self,
    ) -> None:
        """Test enhanced command permission analysis with user-based overrides."""
        command = MagicMock()
        command.name = "my_stats"
        command.default_member_permissions = None

        # Mock permission overrides with user restrictions
        mock_user_permission = MagicMock()
        mock_user_permission.type = discord.AppCommandPermissionType.user
        mock_user_permission.id = 987654321
        mock_user_permission.permission = False

        mock_guild_permissions = MagicMock()
        mock_guild_permissions.permissions = [mock_user_permission]
        command.fetch_permissions = AsyncMock(return_value=mock_guild_permissions)

        # Mock guild member lookup
        mock_member = MagicMock()
        mock_member.display_name = "BlockedUser"
        mock_member.id = 987654321
        self.mock_guild.get_member = MagicMock(return_value=mock_member)

        result = await self.permission_checker._analyze_enhanced_command_permissions(  # pyright: ignore[reportPrivateUsage]
            command, self.mock_guild
        )

        assert result["name"] == "my_stats"
        assert len(result["permission_overrides"]) == 1
        assert "BlockedUser (Denied)" in result["permission_overrides"][0]

    async def test_analyze_enhanced_command_permissions_with_channel_overrides(
        self,
    ) -> None:
        """Test enhanced command permission analysis with channel-based overrides."""
        command = MagicMock()
        command.name = "uptime"
        command.default_member_permissions = None

        # Mock permission overrides with channel restrictions
        mock_channel_permission = MagicMock()
        mock_channel_permission.type = discord.AppCommandPermissionType.channel
        mock_channel_permission.id = 555666777
        mock_channel_permission.permission = True

        mock_guild_permissions = MagicMock()
        mock_guild_permissions.permissions = [mock_channel_permission]
        command.fetch_permissions = AsyncMock(return_value=mock_guild_permissions)

        # Mock guild channel lookup
        mock_channel = MagicMock()
        mock_channel.name = "bot-commands"
        mock_channel.id = 555666777
        self.mock_guild.get_channel = MagicMock(return_value=mock_channel)

        result = await self.permission_checker._analyze_enhanced_command_permissions(  # pyright: ignore[reportPrivateUsage]
            command, self.mock_guild
        )

        assert result["name"] == "uptime"
        assert len(result["channel_restrictions"]) == 1
        assert "#bot-commands" in result["channel_restrictions"][0]

    async def test_analyze_enhanced_command_permissions_fetch_error(self) -> None:
        """Test enhanced command permission analysis when fetching permissions fails."""
        command = MagicMock()
        command.name = "test_command"
        command.default_member_permissions = None

        # Mock permission fetch failure
        command.fetch_permissions = AsyncMock(
            side_effect=discord.HTTPException(MagicMock(status=403), "Forbidden")
        )

        result = await self.permission_checker._analyze_enhanced_command_permissions(  # pyright: ignore[reportPrivateUsage]
            command, self.mock_guild
        )

        assert result["name"] == "test_command"
        assert result["accessible_by"] == "Accessible to all members"
        assert result["permission_overrides"] == []
        assert result["channel_restrictions"] == []

    def test_format_enhanced_permission_table(self) -> None:
        """Test formatting enhanced permission information into a table."""
        # Set up a proper guild name for the mock
        self.mock_guild.name = "Test Guild"

        bot_permissions = {
            "send_messages": True,
            "embed_links": False,
            "attach_files": True,
        }

        enhanced_command_analyses: list[dict[str, str | list[str]]] = [
            {
                "name": "about",
                "accessible_by": "Accessible to all members",
                "permission_overrides": [],
                "channel_restrictions": [],
            },
            {
                "name": "config",
                "accessible_by": "@everyone (Denied), Plex Admin (Allowed)",
                "permission_overrides": ["Staff (Allowed)", "Moderator (Allowed)"],
                "channel_restrictions": ["#admin-only"],
            },
        ]

        result = self.permission_checker._format_enhanced_permission_table(  # pyright: ignore[reportPrivateUsage]
            self.mock_guild, bot_permissions, enhanced_command_analyses
        )

        assert "Test Guild" in result
        assert "🤖 Bot Permissions" in result  # Updated to new format
        assert "✅ Granted" in result  # Check for detailed permission status
        assert "❌ Missing" in result  # Check for detailed permission status
        assert "⚙️ Integration Access Control" in result  # Updated to new format
        assert "/about" in result
        assert "/config" in result
        assert "Accessible to all members" in result
        assert "@everyone (Denied), Plex Admin (Allowed)" in result

    def test_format_enhanced_permission_table_alignment(self) -> None:
        """Test that the enhanced permission table has proper alignment."""
        # Set up a proper guild name for the mock
        self.mock_guild.name = "NoobSkateCrew"

        bot_permissions = {
            "send_messages": True,
            "embed_links": True,
            "attach_files": True,
            "read_message_history": True,
            "manage_messages": True,
            "use_application_commands": True,
        }

        enhanced_command_analyses: list[dict[str, str | list[str]]] = [
            {
                "name": "about",
                "accessible_by": "Accessible to all members",
                "permission_overrides": [],
                "channel_restrictions": [],
            },
            {
                "name": "config",
                "accessible_by": "@everyone (Denied), Plex Admin (Allowed)",
                "permission_overrides": ["Staff (Allowed)"],
                "channel_restrictions": ["#plex-stats-graphs (Allowed)"],
            },
        ]

        result = self.permission_checker._format_enhanced_permission_table(  # pyright: ignore[reportPrivateUsage]
            self.mock_guild, bot_permissions, enhanced_command_analyses
        )

        lines = result.split("\n")

        # Import unicodedata for visual width calculation
        import unicodedata

        def visual_width(text: str) -> int:
            """Calculate the visual width of text accounting for wide characters."""
            width = 0
            for char in text:
                if unicodedata.east_asian_width(char) in ("F", "W"):
                    width += 2  # Full-width or wide characters
                elif unicodedata.combining(char):
                    width += 0  # Combining characters don't add width
                else:
                    width += 1  # Normal characters
            return width

        # Check that all lines have exactly the same VISUAL width
        expected_visual_width = 80
        for i, line in enumerate(lines):
            if line.strip():  # Skip empty lines
                actual_visual_width = visual_width(line)
                assert actual_visual_width == expected_visual_width, (
                    f"Line {i + 1} has incorrect visual width: {actual_visual_width} (expected {expected_visual_width})\nLine: '{line}'"
                )

        # Verify specific content is present and properly formatted
        assert "🔐 Permission Status for NoobSkateCrew" in result
        assert "🤖 Bot Permissions" in result  # Updated to new format
        assert "⚙️ Integration Access Control" in result  # Updated to new format
        assert "Accessible to all members" in result
        assert "@everyone (Denied), Plex Admin (Allowed)" in result

    async def test_analyze_integration_permissions_no_restrictions(self) -> None:
        """Test integration permissions analysis when no restrictions are set."""
        # Mock empty command list
        self.mock_bot.tree.fetch_commands = AsyncMock(return_value=[])  # pyright: ignore[reportAny]

        result = await self.permission_checker._analyze_integration_permissions(  # pyright: ignore[reportPrivateUsage]
            self.mock_guild
        )

        assert result["global_roles_access"] == "Not configured (all members)"
        assert result["global_channels_access"] == "None (all channels)"

    async def test_analyze_integration_permissions_with_restrictions(self) -> None:
        """Test integration permissions analysis with role and channel restrictions."""
        # Mock command with permissions
        mock_command = MagicMock()
        mock_command.name = "test_command"

        # Mock permission restrictions
        mock_role_permission = MagicMock()
        mock_role_permission.type = discord.AppCommandPermissionType.role
        mock_role_permission.id = self.mock_guild.default_role.id  # pyright: ignore[reportAny] # @everyone
        mock_role_permission.permission = False  # Denied

        mock_channel_permission = MagicMock()
        mock_channel_permission.type = discord.AppCommandPermissionType.channel
        mock_channel_permission.id = 123456789
        mock_channel_permission.permission = True  # Allowed

        mock_guild_permissions = MagicMock()
        mock_guild_permissions.permissions = [
            mock_role_permission,
            mock_channel_permission,
        ]
        mock_command.fetch_permissions = AsyncMock(return_value=mock_guild_permissions)

        # Mock channel lookup
        mock_channel = MagicMock()
        mock_channel.name = "bot-commands"
        self.mock_guild.get_channel = MagicMock(return_value=mock_channel)

        # Mock fetch_commands to return our test command
        self.mock_bot.tree.fetch_commands = AsyncMock(return_value=[mock_command])  # pyright: ignore[reportAny]

        result = await self.permission_checker._analyze_integration_permissions(  # pyright: ignore[reportPrivateUsage]
            self.mock_guild
        )

        assert result["global_roles_access"] == "Restricted from @everyone"
        assert "#bot-commands (Allowed)" in result["global_channels_access"]

    async def test_analyze_integration_permissions_fetch_error(self) -> None:
        """Test integration permissions analysis when Discord API fails."""
        # Mock API failure
        self.mock_bot.tree.fetch_commands = AsyncMock(  # pyright: ignore[reportAny]
            side_effect=discord.Forbidden(MagicMock(status=403), "Forbidden")
        )

        result = await self.permission_checker._analyze_integration_permissions(  # pyright: ignore[reportPrivateUsage]
            self.mock_guild
        )

        assert result["global_roles_access"] == "Unable to fetch (need Manage Server)"
        assert (
            result["global_channels_access"] == "Unable to fetch (need Manage Server)"
        )

    async def test_check_slash_command_permissions_optimized_api_calls(self) -> None:
        """Test that optimized permission checking minimizes Discord API calls."""
        # Setup mock bot permissions
        permissions = MagicMock()
        permissions.send_messages = True
        permissions.embed_links = True
        permissions.attach_files = True
        permissions.read_message_history = True
        permissions.manage_messages = True
        permissions.use_application_commands = True
        self.mock_guild.me.guild_permissions = permissions  # pyright: ignore[reportAny]

        # Create mock commands
        mock_guild_cmd = MagicMock()
        mock_guild_cmd.name = "guild_command"
        mock_guild_cmd.default_member_permissions = None
        mock_guild_cmd.fetch_permissions = AsyncMock(return_value=None)

        mock_global_cmd = MagicMock()
        mock_global_cmd.name = "global_command"
        mock_global_cmd.default_member_permissions = None
        mock_global_cmd.fetch_permissions = AsyncMock(return_value=None)

        # Track API call counts
        fetch_commands_call_count = 0

        async def mock_fetch_commands(
            guild: discord.Guild | None = None,
        ) -> list[MagicMock]:
            nonlocal fetch_commands_call_count
            fetch_commands_call_count += 1
            if guild is None:
                return [mock_global_cmd]  # Global commands
            else:
                return [mock_guild_cmd]  # Guild commands

        self.mock_bot.tree.fetch_commands = AsyncMock(side_effect=mock_fetch_commands)  # pyright: ignore[reportAny]

        with patch("src.tgraph_bot.bot.permission_checker.logger"):
            await self.permission_checker.check_slash_command_permissions(
                self.mock_guild
            )

        # Optimized version should make fewer API calls than the original
        # Original made 5+ calls: guild commands, global commands, guild sync, global sync, integration analysis
        # Optimized should make only 2-3 calls: guild commands, global commands, and potentially integration
        assert fetch_commands_call_count <= 3, (
            f"Too many API calls: {fetch_commands_call_count} (expected <= 3)"
        )

    async def test_concurrent_permission_analysis(self) -> None:
        """Test that command permission analysis can be done concurrently."""
        import asyncio
        from unittest.mock import patch

        # Setup mock bot permissions
        permissions = MagicMock()
        permissions.send_messages = True
        permissions.embed_links = True
        permissions.attach_files = True
        permissions.read_message_history = True
        permissions.manage_messages = True
        permissions.use_application_commands = True
        self.mock_guild.me.guild_permissions = permissions  # pyright: ignore[reportAny]

        # Create multiple mock commands
        mock_commands: list[MagicMock] = []
        for i in range(5):  # Create 5 commands to test concurrency
            mock_cmd = MagicMock()
            mock_cmd.name = f"command_{i}"
            mock_cmd.default_member_permissions = None

            # Add delay to permission fetching to test concurrency
            async def delayed_fetch_permissions(guild: discord.Guild) -> None:  # pyright: ignore[reportUnusedParameter]
                await asyncio.sleep(0.01)  # Small delay
                return None

            mock_cmd.fetch_permissions = AsyncMock(
                side_effect=delayed_fetch_permissions
            )
            mock_commands.append(mock_cmd)

        # Mock command fetching
        self.mock_bot.tree.fetch_commands = AsyncMock(return_value=mock_commands)  # pyright: ignore[reportAny]

        # Measure execution time
        import time

        start_time = time.time()

        with patch("src.tgraph_bot.bot.permission_checker.logger"):
            await self.permission_checker.check_slash_command_permissions(
                self.mock_guild
            )

        end_time = time.time()
        execution_time = end_time - start_time

        # With concurrency, 5 commands with 0.01s delay each should take much less than 0.05s total
        # Allow some overhead but ensure it's significantly faster than sequential execution
        assert execution_time < 0.05, (
            f"Execution took too long: {execution_time}s (expected < 0.05s)"
        )

    async def test_cached_command_data_reuse(self) -> None:
        """Test that command data is cached and reused to avoid redundant API calls."""
        # Setup mock bot permissions
        permissions = MagicMock()
        permissions.send_messages = True
        permissions.embed_links = True
        permissions.attach_files = True
        permissions.read_message_history = True
        permissions.manage_messages = True
        permissions.use_application_commands = True
        self.mock_guild.me.guild_permissions = permissions  # pyright: ignore[reportAny]

        # Create mock command
        mock_cmd = MagicMock()
        mock_cmd.name = "test_command"
        mock_cmd.default_member_permissions = None
        mock_cmd.fetch_permissions = AsyncMock(return_value=None)

        # Track how many times fetch_commands is called
        fetch_commands_calls: list[discord.Guild | None] = []

        async def track_fetch_commands(
            guild: discord.Guild | None = None,
        ) -> list[MagicMock]:
            fetch_commands_calls.append(guild)
            if guild is None:
                return []  # No global commands
            else:
                return [mock_cmd]  # Guild command

        self.mock_bot.tree.fetch_commands = AsyncMock(side_effect=track_fetch_commands)  # pyright: ignore[reportAny]

        with patch("src.tgraph_bot.bot.permission_checker.logger"):
            await self.permission_checker.check_slash_command_permissions(
                self.mock_guild
            )

        # Verify that each unique API call (guild vs global) is made only once
        guild_calls = sum(1 for call in fetch_commands_calls if call is not None)
        global_calls = sum(1 for call in fetch_commands_calls if call is None)

        assert guild_calls == 1, (
            f"Guild commands fetched {guild_calls} times (expected 1)"
        )
        assert global_calls == 1, (
            f"Global commands fetched {global_calls} times (expected 1)"
        )

    def test_format_enhanced_permission_table_with_integrations(self) -> None:
        """Test formatting enhanced permission table with integration analysis."""
        # Set up a proper guild name for the mock
        self.mock_guild.name = "Test Guild"

        bot_permissions = {
            "send_messages": True,
            "embed_links": True,
            "attach_files": True,
        }

        enhanced_command_analyses: list[dict[str, str | list[str]]] = [
            {
                "name": "about",
                "accessible_by": "Accessible to all members",
                "permission_overrides": [],
                "channel_restrictions": [],
            },
        ]

        integration_analysis = {
            "global_roles_access": "Admin (Allowed), Moderator (Allowed)",
            "global_channels_access": "#bot-commands (Allowed)",
        }

        result = self.permission_checker._format_enhanced_permission_table(  # pyright: ignore[reportPrivateUsage]
            self.mock_guild,
            bot_permissions,
            enhanced_command_analyses,
            integration_analysis,
        )

        assert "Test Guild" in result
        assert "🤖 Bot Permissions" in result  # Updated to new format
        assert "⚙️ Integration Access Control" in result  # Updated to new format
        assert "Global Roles & Members" in result
        assert "Admin (Allowed), Moderator (Allowed)" in result
        assert "Global Channel Restrictions" in result
        assert "#bot-commands (Allowed)" in result
        assert "/about" in result

    def test_format_enhanced_permission_table_alphabetizes_commands(self) -> None:
        """Test that commands are displayed in alphabetical order."""
        # Set up a proper guild name for the mock
        self.mock_guild.name = "Test Guild"

        bot_permissions = {
            "send_messages": True,
            "embed_links": True,
            "attach_files": True,
        }

        # Create commands in non-alphabetical order
        enhanced_command_analyses: list[dict[str, str | list[str]]] = [
            {
                "name": "update_graphs",
                "accessible_by": "Accessible to all members",
                "permission_overrides": [],
                "channel_restrictions": [],
            },
            {
                "name": "about",
                "accessible_by": "Accessible to all members",
                "permission_overrides": [],
                "channel_restrictions": [],
            },
            {
                "name": "config",
                "accessible_by": "Accessible to all members",
                "permission_overrides": [],
                "channel_restrictions": [],
            },
        ]

        result = self.permission_checker._format_enhanced_permission_table(  # pyright: ignore[reportPrivateUsage]
            self.mock_guild, bot_permissions, enhanced_command_analyses
        )

        # Commands should appear in alphabetical order: about, config, update_graphs
        about_index = result.find("/about")
        config_index = result.find("/config")
        update_graphs_index = result.find("/update_graphs")

        assert about_index < config_index < update_graphs_index
