"""
Tests for command utility functions in TGraph Bot.

This module tests utility functions for Discord command formatting,
argument parsing, response handling, and interaction management.
"""

from typing import cast
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from src.tgraph_bot.utils.discord.command_utils import (
    check_manage_guild_permission,
    create_cooldown_embed,
    create_error_embed,
    create_info_embed,
    create_success_embed,
    format_command_help,
    format_config_value,
    format_uptime,
    parse_time_string,
    safe_interaction_response,
    send_error_response,
    send_success_response,
    truncate_text,
    validate_channel_id,
    validate_color_hex,
    validate_email,
    validate_positive_integer,
)


class TestEmbedCreation:
    """Test cases for embed creation functions."""

    def test_create_error_embed_default(self) -> None:
        """Test error embed creation with default values."""
        embed = create_error_embed()

        assert embed.title == "Error"
        assert embed.description == "An error occurred"
        assert embed.color == discord.Color.red()
        assert embed.footer.text == "TGraph Bot"

    def test_create_error_embed_custom(self) -> None:
        """Test error embed creation with custom values."""
        embed = create_error_embed(
            title="Custom Error",
            description="Something went wrong",
            color=discord.Color.orange(),
        )

        assert embed.title == "Custom Error"
        assert embed.description == "Something went wrong"
        assert embed.color == discord.Color.orange()

    def test_create_success_embed_default(self) -> None:
        """Test success embed creation with default values."""
        embed = create_success_embed()

        assert embed.title == "Success"
        assert embed.description == "Operation completed successfully"
        assert embed.color == discord.Color.green()
        assert embed.footer.text == "TGraph Bot"

    def test_create_info_embed_default(self) -> None:
        """Test info embed creation with default values."""
        embed = create_info_embed()

        assert embed.title == "Information"
        assert embed.description == ""
        assert embed.color == discord.Color.blue()
        assert embed.footer.text == "TGraph Bot"

    def test_create_cooldown_embed(self) -> None:
        """Test cooldown embed creation."""
        embed = create_cooldown_embed("test_command", 120.5)

        assert embed.title == "Command on Cooldown"
        description = embed.description
        assert description is not None
        assert "test_command" in description
        field_value = embed.fields[0].value
        assert field_value is not None
        assert "2.0 minutes" in field_value


class TestValidationFunctions:
    """Test cases for validation utility functions."""

    def test_validate_email_valid(self) -> None:
        """Test email validation with valid emails."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@example.co.uk",
            "123@test.io",
        ]

        for email in valid_emails:
            assert validate_email(email), f"Email {email} should be valid"

    def test_validate_email_invalid(self) -> None:
        """Test email validation with invalid emails."""
        invalid_emails = [
            "invalid",
            "@example.com",
            "test@",
            "test.example.com",
            "test@.com",
            "",
        ]

        for email in invalid_emails:
            assert not validate_email(email), f"Email {email} should be invalid"

    def test_validate_channel_id_valid(self) -> None:
        """Test channel ID validation with valid IDs."""
        valid_ids = ["123456789012345678", "987654321098765432"]

        for channel_id in valid_ids:
            result = validate_channel_id(channel_id)
            assert result is not None
            assert isinstance(result, int)

    def test_validate_channel_id_invalid(self) -> None:
        """Test channel ID validation with invalid IDs."""
        invalid_ids = ["abc", "123", "", "-123", "0"]

        for channel_id in invalid_ids:
            result = validate_channel_id(channel_id)
            assert result is None

    def test_validate_positive_integer_valid(self) -> None:
        """Test positive integer validation with valid values."""
        assert validate_positive_integer("5") == 5
        assert validate_positive_integer("100", min_value=1, max_value=200) == 100
        assert validate_positive_integer("1", min_value=1) == 1

    def test_validate_positive_integer_invalid(self) -> None:
        """Test positive integer validation with invalid values."""
        assert validate_positive_integer("0") is None
        assert validate_positive_integer("-5") is None
        assert validate_positive_integer("abc") is None
        assert validate_positive_integer("101", max_value=100) is None

    def test_validate_color_hex_valid(self) -> None:
        """Test hex color validation with valid colors."""
        valid_colors = ["#FF0000", "FF0000", "#00FF00", "0000FF", "#FFFFFF"]

        for color in valid_colors:
            assert validate_color_hex(color), f"Color {color} should be valid"

    def test_validate_color_hex_invalid(self) -> None:
        """Test hex color validation with invalid colors."""
        invalid_colors = ["#GG0000", "FF00", "#FF00000", "red", "", "#"]

        for color in invalid_colors:
            assert not validate_color_hex(color), f"Color {color} should be invalid"


class TestFormattingFunctions:
    """Test cases for formatting utility functions."""

    def test_format_config_value_sensitive(self) -> None:
        """Test config value formatting for sensitive keys."""
        assert format_config_value("services.discord.token", "secret") == "***HIDDEN***"
        assert (
            format_config_value("services.tautulli.api_key", "api_key")
            == "***HIDDEN***"
        )

    def test_format_config_value_boolean(self) -> None:
        """Test config value formatting for boolean values."""
        assert format_config_value("ENABLE_FEATURE", True) == "✅ Enabled"
        assert format_config_value("DISABLE_FEATURE", False) == "❌ Disabled"

    def test_format_config_value_none(self) -> None:
        """Test config value formatting for None values."""
        assert format_config_value("OPTIONAL_SETTING", None) == "Not set"

    def test_format_config_value_string(self) -> None:
        """Test config value formatting for string values."""
        assert format_config_value("NAME", "test") == "test"
        assert format_config_value("EMPTY", "") == "Empty"
        assert format_config_value("WHITESPACE", "   ") == "Empty"

    def test_truncate_text_short(self) -> None:
        """Test text truncation with short text."""
        text = "Short text"
        result = truncate_text(text, 100)
        assert result == text

    def test_truncate_text_long(self) -> None:
        """Test text truncation with long text."""
        text = "A" * 100
        result = truncate_text(text, 50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_parse_time_string_valid(self) -> None:
        """Test time string parsing with valid formats."""
        assert parse_time_string("12:30") == (12, 30)
        assert parse_time_string("00:00") == (0, 0)
        assert parse_time_string("23:59") == (23, 59)

    def test_parse_time_string_invalid(self) -> None:
        """Test time string parsing with invalid formats."""
        assert parse_time_string("XX:XX") is None
        assert parse_time_string("25:00") is None
        assert parse_time_string("12:60") is None
        assert parse_time_string("invalid") is None

    def test_format_uptime(self) -> None:
        """Test uptime formatting."""
        assert format_uptime(30) == "30 seconds"
        assert format_uptime(90) == "1 minute, 30 seconds"
        assert format_uptime(3661) == "1 hour, 1 minute, 1 second"
        assert format_uptime(90061) == "1 day, 1 hour, 1 minute, 1 second"


class TestInteractionUtilities:
    """Test cases for interaction utility functions."""

    @pytest.fixture
    def mock_interaction(self) -> discord.Interaction:
        """Create a mock Discord interaction."""
        interaction = MagicMock(spec=discord.Interaction)
        mock_response = MagicMock()
        mock_send_message = AsyncMock()
        mock_response.send_message = mock_send_message
        mock_is_done = MagicMock(return_value=False)
        mock_response.is_done = mock_is_done
        interaction.response = mock_response
        mock_followup = AsyncMock()
        mock_send = AsyncMock()
        mock_followup.send = mock_send
        interaction.followup = mock_followup
        return cast(discord.Interaction, interaction)

    @pytest.mark.asyncio
    async def test_safe_interaction_response_initial(
        self, mock_interaction: discord.Interaction
    ) -> None:
        """Test safe interaction response with initial response."""
        embed = create_info_embed("Test", "Test message")

        result = await safe_interaction_response(
            interaction=mock_interaction, embed=embed, ephemeral=True
        )

        assert result is True
        mock_response = cast(MagicMock, mock_interaction.response)
        mock_send_message = cast(AsyncMock, mock_response.send_message)
        mock_send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_interaction_response_followup(
        self, mock_interaction: discord.Interaction
    ) -> None:
        """Test safe interaction response with followup."""
        mock_response = cast(MagicMock, mock_interaction.response)
        mock_is_done = cast(MagicMock, mock_response.is_done)
        mock_is_done.return_value = True

        result = await safe_interaction_response(
            interaction=mock_interaction, content="Test message", ephemeral=False
        )

        assert result is True
        mock_followup = cast(AsyncMock, mock_interaction.followup)
        mock_send = cast(AsyncMock, mock_followup.send)
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_error_response(
        self, mock_interaction: discord.Interaction
    ) -> None:
        """Test sending error response."""
        result = await send_error_response(
            interaction=mock_interaction,
            title="Test Error",
            description="Test description",
        )

        assert result is True
        mock_response = cast(MagicMock, mock_interaction.response)
        mock_send_message = cast(AsyncMock, mock_response.send_message)
        mock_send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_success_response(
        self, mock_interaction: discord.Interaction
    ) -> None:
        """Test sending success response."""
        result = await send_success_response(
            interaction=mock_interaction,
            title="Test Success",
            description="Test description",
        )

        assert result is True
        mock_response = cast(MagicMock, mock_interaction.response)
        mock_send_message = cast(AsyncMock, mock_response.send_message)
        mock_send_message.assert_called_once()


class TestPermissionUtilities:
    """Test cases for permission utility functions."""

    def test_check_manage_guild_permission_no_guild(self) -> None:
        """Test permission check with no guild."""
        interaction = MagicMock(spec=discord.Interaction)
        interaction.guild = None

        result = check_manage_guild_permission(interaction)
        assert result is False

    def test_check_manage_guild_permission_owner(self) -> None:
        """Test permission check for guild owner."""
        interaction = MagicMock(spec=discord.Interaction)
        mock_guild = MagicMock()
        mock_guild.owner_id = 123456789
        interaction.guild = mock_guild
        mock_user = MagicMock()
        mock_user.id = 123456789
        interaction.user = mock_user

        result = check_manage_guild_permission(interaction)
        assert result is True

    def test_check_manage_guild_permission_member_with_perms(self) -> None:
        """Test permission check for member with manage guild permission."""
        interaction = MagicMock(spec=discord.Interaction)
        mock_guild = MagicMock()
        mock_guild.owner_id = 987654321
        interaction.guild = mock_guild
        mock_user = MagicMock()
        mock_user.id = 123456789
        mock_permissions = MagicMock()
        mock_permissions.manage_guild = True
        mock_user.guild_permissions = mock_permissions
        interaction.user = mock_user

        result = check_manage_guild_permission(interaction)
        assert result is True

    def test_format_command_help(self) -> None:
        """Test command help formatting."""
        embed = format_command_help(
            command_name="test",
            description="Test command",
            usage="/test <arg>",
            examples=["/test example1", "/test example2"],
        )

        assert embed.title == "Command: /test"
        assert embed.description == "Test command"
        assert len(embed.fields) == 2  # Usage and Examples
        assert embed.fields[0].name == "Usage"
        assert embed.fields[1].name == "Examples"
