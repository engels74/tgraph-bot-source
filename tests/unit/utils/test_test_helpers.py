"""
Test cases for test helper utilities.

This module tests the test helper utilities to ensure they create properly
configured mock objects with correct attributes and error handling.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from tests.utils.test_helpers import (
    create_mock_discord_bot,
    create_mock_interaction,
    create_mock_guild,
    create_mock_user,
)


class TestMockCreationUtilities:
    """Test cases for Discord mock creation utilities."""

    def test_create_mock_discord_bot_defaults(self) -> None:
        """Test creating a mock Discord bot with default values."""
        bot = create_mock_discord_bot()
        
        assert isinstance(bot, MagicMock)
        assert bot.user.id == 123456789
        assert bot.user.name == "TestBot"
        assert len(bot.guilds) == 2
        assert bot.intents.message_content is True
        assert bot.intents.guilds is True
        assert bot.command_prefix == "!"
        assert bot.help_command is None

    def test_create_mock_discord_bot_custom_values(self) -> None:
        """Test creating a mock Discord bot with custom values."""
        bot = create_mock_discord_bot(
            user_id=999888777,
            user_name="CustomBot",
            guild_count=5
        )
        
        assert bot.user.id == 999888777
        assert bot.user.name == "CustomBot"
        assert len(bot.guilds) == 5
        assert all(guild.name.startswith("Test Guild") for guild in bot.guilds)

    def test_create_mock_discord_bot_validation(self) -> None:
        """Test parameter validation for mock Discord bot creation."""
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            _ = create_mock_discord_bot(user_id=0)
        
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            _ = create_mock_discord_bot(user_id=-1)
        
        with pytest.raises(ValueError, match="guild_count must be non-negative"):
            _ = create_mock_discord_bot(guild_count=-1)

    def test_create_mock_user_defaults(self) -> None:
        """Test creating a mock Discord user with default values."""
        user = create_mock_user()
        
        assert isinstance(user, MagicMock)
        assert user.id == 987654321
        assert user.name == "TestUser"
        assert user.display_name == "TestUser"
        assert user.bot is False

    def test_create_mock_user_custom_values(self) -> None:
        """Test creating a mock Discord user with custom values."""
        user = create_mock_user(
            user_id=111222333,
            username="CustomUser",
            display_name="Custom Display",
            bot=True
        )
        
        assert user.id == 111222333
        assert user.name == "CustomUser"
        assert user.display_name == "Custom Display"
        assert user.bot is True

    def test_create_mock_user_validation(self) -> None:
        """Test parameter validation for mock Discord user creation."""
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            _ = create_mock_user(user_id=0)
        
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            _ = create_mock_user(user_id=-1)

    def test_create_mock_guild_defaults(self) -> None:
        """Test creating a mock Discord guild with default values."""
        guild = create_mock_guild()
        
        assert isinstance(guild, MagicMock)
        assert guild.id == 111222333444555666
        assert guild.name == "Test Guild"
        assert guild.owner_id == 777888999000111222
        assert guild.member_count == 100

    def test_create_mock_guild_custom_values(self) -> None:
        """Test creating a mock Discord guild with custom values."""
        guild = create_mock_guild(
            guild_id=999888777666555444,
            name="Custom Guild",
            owner_id=123456789,
            member_count=250
        )
        
        assert guild.id == 999888777666555444
        assert guild.name == "Custom Guild"
        assert guild.owner_id == 123456789
        assert guild.member_count == 250

    def test_create_mock_guild_validation(self) -> None:
        """Test parameter validation for mock Discord guild creation."""
        with pytest.raises(ValueError, match="guild_id must be a positive integer"):
            _ = create_mock_guild(guild_id=0)
        
        with pytest.raises(ValueError, match="owner_id must be a positive integer"):
            _ = create_mock_guild(owner_id=-1)
        
        with pytest.raises(ValueError, match="member_count must be non-negative"):
            _ = create_mock_guild(member_count=-5)

    def test_create_mock_interaction_defaults(self) -> None:
        """Test creating a mock Discord interaction with default values."""
        interaction = create_mock_interaction()
        
        assert isinstance(interaction, MagicMock)
        assert interaction.user.id == 987654321
        assert interaction.user.name == "TestUser"
        assert interaction.guild.id == 111222333444555666
        assert interaction.guild.name == "Test Guild"
        assert interaction.channel.id == 333444555666777888
        assert interaction.command.name == "test_command"
        assert interaction.response.is_done() is False

    def test_create_mock_interaction_custom_values(self) -> None:
        """Test creating a mock Discord interaction with custom values."""
        interaction = create_mock_interaction(
            user_id=555444333,
            username="InteractionUser",
            guild_id=777666555444333222,
            guild_name="Interaction Guild",
            channel_id=999888777666555444,
            command_name="custom_command",
            is_response_done=True
        )
        
        assert interaction.user.id == 555444333
        assert interaction.user.name == "InteractionUser"
        assert interaction.guild.id == 777666555444333222
        assert interaction.guild.name == "Interaction Guild"
        assert interaction.channel.id == 999888777666555444
        assert interaction.command.name == "custom_command"
        assert interaction.response.is_done() is True

    def test_create_mock_interaction_dm(self) -> None:
        """Test creating a mock Discord interaction for DM (no guild)."""
        interaction = create_mock_interaction(guild_id=None)
        
        assert interaction.user.id == 987654321
        assert interaction.guild is None
        assert interaction.channel.id == 333444555666777888

    def test_create_mock_interaction_validation(self) -> None:
        """Test parameter validation for mock Discord interaction creation."""
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            _ = create_mock_interaction(user_id=0)
        
        with pytest.raises(ValueError, match="guild_id must be a positive integer or None"):
            _ = create_mock_interaction(guild_id=0)
        
        with pytest.raises(ValueError, match="channel_id must be a positive integer"):
            _ = create_mock_interaction(channel_id=-1)

    def test_mock_objects_have_async_methods(self) -> None:
        """Test that mock objects have properly configured async methods."""
        interaction = create_mock_interaction()
        
        # Verify async mocks are properly set up
        assert hasattr(interaction.response, 'send_message')
        assert hasattr(interaction.followup, 'send')
        
        # These should be AsyncMock instances (or at least callable)
        assert callable(interaction.response.send_message)
        assert callable(interaction.followup.send) 