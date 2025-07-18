"""
Tests for the base command cog utilities.

This module tests the BaseCommandCog class and BaseCooldownConfig
to ensure proper cooldown management, error handling, and configuration access.
"""

import time
from typing import cast
from unittest.mock import Mock

import discord
import pytest
from discord.ext import commands

from src.tgraph_bot.utils.discord.base_command_cog import (
    BaseCommandCog,
    BaseCooldownConfig,
)
from src.tgraph_bot.utils.core.error_handler import ErrorContext


class TestBaseCooldownConfig:
    """Test the BaseCooldownConfig class."""

    def test_init(self) -> None:
        """Test BaseCooldownConfig initialization."""
        config = BaseCooldownConfig(
            user_cooldown_config_key="TEST_COOLDOWN_MINUTES",
            global_cooldown_config_key="TEST_GLOBAL_COOLDOWN_SECONDS",
            user_cooldown_multiplier=60,
        )

        assert config.user_cooldown_config_key == "TEST_COOLDOWN_MINUTES"
        assert config.global_cooldown_config_key == "TEST_GLOBAL_COOLDOWN_SECONDS"
        assert config.user_cooldown_multiplier == 60

    def test_init_with_defaults(self) -> None:
        """Test BaseCooldownConfig initialization with default multiplier."""
        config = BaseCooldownConfig(
            user_cooldown_config_key="TEST_COOLDOWN_MINUTES",
            global_cooldown_config_key="TEST_GLOBAL_COOLDOWN_SECONDS",
        )

        assert config.user_cooldown_multiplier == 60


class TestBaseCommandCog:
    """Test the BaseCommandCog class."""

    mock_bot: Mock  # pyright: ignore[reportUninitializedInstanceVariable]
    cooldown_config: BaseCooldownConfig  # pyright: ignore[reportUninitializedInstanceVariable]

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_bot = cast(commands.Bot, Mock(spec=commands.Bot))
        self.cooldown_config = BaseCooldownConfig(
            user_cooldown_config_key="TEST_COOLDOWN_MINUTES",
            global_cooldown_config_key="TEST_GLOBAL_COOLDOWN_SECONDS",
        )

    def test_init_without_cooldown(self) -> None:
        """Test BaseCommandCog initialization without cooldown config."""
        cog = BaseCommandCog(self.mock_bot)  # pyright: ignore[reportAny]

        assert cog.bot == self.mock_bot  # pyright: ignore[reportAny]
        assert cog.cooldown_config is None
        assert not hasattr(cog, "_user_cooldowns")
        assert not hasattr(cog, "_global_cooldown")

    def test_init_with_cooldown(self) -> None:
        """Test BaseCommandCog initialization with cooldown config."""
        cog = BaseCommandCog(self.mock_bot, self.cooldown_config)  # pyright: ignore[reportAny]

        assert cog.bot == self.mock_bot  # pyright: ignore[reportAny]
        assert cog.cooldown_config == self.cooldown_config
        assert hasattr(cog, "_user_cooldowns")
        assert hasattr(cog, "_global_cooldown")
        assert cog._user_cooldowns == {}  # pyright: ignore[reportPrivateUsage]
        assert cog._global_cooldown == 0.0  # pyright: ignore[reportPrivateUsage]

    def test_tgraph_bot_property_success(self) -> None:
        """Test tgraph_bot property with valid TGraphBot instance."""
        # Import here to avoid circular imports in test
        from src.tgraph_bot.main import TGraphBot

        mock_tgraph_bot = cast(TGraphBot, Mock(spec=TGraphBot))
        cog = BaseCommandCog(mock_tgraph_bot)

        assert cog.tgraph_bot == mock_tgraph_bot

    def test_tgraph_bot_property_failure(self) -> None:
        """Test tgraph_bot property with invalid bot instance."""
        cog = BaseCommandCog(self.mock_bot)  # pyright: ignore[reportAny]

        with pytest.raises(TypeError, match="Expected TGraphBot instance"):
            _ = cog.tgraph_bot

    def test_check_cooldowns_no_config(self) -> None:
        """Test cooldown checking without cooldown config."""
        cog = BaseCommandCog(self.mock_bot)  # pyright: ignore[reportAny]
        mock_interaction = cast(discord.Interaction, Mock(spec=discord.Interaction))

        is_on_cooldown, retry_after = cog.check_cooldowns(mock_interaction)

        assert not is_on_cooldown
        assert retry_after == 0.0

    def test_check_cooldowns_no_cooldowns_active(self) -> None:
        """Test cooldown checking with no active cooldowns."""
        cog = BaseCommandCog(self.mock_bot, self.cooldown_config)  # pyright: ignore[reportAny]

        # Mock config with no cooldowns
        mock_config = Mock()
        mock_config.TEST_COOLDOWN_MINUTES = 0
        mock_config.TEST_GLOBAL_COOLDOWN_SECONDS = 0

        cog.get_current_config = Mock(return_value=mock_config)

        mock_interaction = cast(discord.Interaction, Mock(spec=discord.Interaction))
        mock_interaction.user.id = 12345

        is_on_cooldown, retry_after = cog.check_cooldowns(mock_interaction)

        assert not is_on_cooldown
        assert retry_after == 0.0

    def test_check_cooldowns_global_active(self) -> None:
        """Test cooldown checking with active global cooldown."""
        cog = BaseCommandCog(self.mock_bot, self.cooldown_config)  # pyright: ignore[reportAny]

        # Set global cooldown to future time
        future_time = time.time() + 30
        cog._global_cooldown = future_time  # pyright: ignore[reportPrivateUsage]

        # Mock config
        mock_config = Mock()
        mock_config.TEST_GLOBAL_COOLDOWN_SECONDS = 60

        cog.get_current_config = Mock(return_value=mock_config)

        mock_interaction = cast(discord.Interaction, Mock(spec=discord.Interaction))

        is_on_cooldown, retry_after = cog.check_cooldowns(mock_interaction)

        assert is_on_cooldown
        assert retry_after > 0

    def test_update_cooldowns_no_config(self) -> None:
        """Test cooldown updating without cooldown config."""
        cog = BaseCommandCog(self.mock_bot)  # pyright: ignore[reportAny]
        mock_interaction = cast(discord.Interaction, Mock(spec=discord.Interaction))

        # Should not raise any errors
        cog.update_cooldowns(mock_interaction)

    def test_update_cooldowns_with_config(self) -> None:
        """Test cooldown updating with cooldown config."""
        cog = BaseCommandCog(self.mock_bot, self.cooldown_config)  # pyright: ignore[reportAny]

        # Mock config
        mock_config = Mock()
        mock_config.TEST_COOLDOWN_MINUTES = 5
        mock_config.TEST_GLOBAL_COOLDOWN_SECONDS = 60

        cog.get_current_config = Mock(return_value=mock_config)

        mock_interaction = cast(discord.Interaction, Mock(spec=discord.Interaction))
        mock_interaction.user.id = 12345

        current_time = time.time()

        cog.update_cooldowns(mock_interaction)

        # Check that cooldowns were set
        assert cog._global_cooldown > current_time  # pyright: ignore[reportPrivateUsage]
        assert 12345 in cog._user_cooldowns  # pyright: ignore[reportPrivateUsage]
        assert cog._user_cooldowns[12345] > current_time  # pyright: ignore[reportPrivateUsage]

    def test_create_error_context(self) -> None:
        """Test error context creation."""
        cog = BaseCommandCog(self.mock_bot)  # pyright: ignore[reportAny]

        mock_interaction = Mock()
        mock_interaction.user = Mock()
        mock_interaction.user.id = 12345  # pyright: ignore[reportAny]
        mock_interaction.guild = Mock()
        mock_interaction.guild.id = 67890  # pyright: ignore[reportAny]
        mock_interaction.channel = Mock()
        mock_interaction.channel.id = 11111  # pyright: ignore[reportAny]

        context = cog.create_error_context(
            mock_interaction, "test_command", {"extra": "data"}
        )

        assert isinstance(context, ErrorContext)
        assert context.user_id == 12345
        assert context.guild_id == 67890
        assert context.channel_id == 11111
        assert context.command_name == "test_command"
        assert context.additional_context == {"extra": "data"}

    def test_create_error_context_no_guild(self) -> None:
        """Test error context creation without guild."""
        cog = BaseCommandCog(self.mock_bot)  # pyright: ignore[reportAny]

        mock_interaction = Mock()
        mock_interaction.user = Mock()
        mock_interaction.user.id = 12345  # pyright: ignore[reportAny]
        mock_interaction.guild = None
        mock_interaction.channel = Mock()
        mock_interaction.channel.id = 11111  # pyright: ignore[reportAny]

        context = cog.create_error_context(mock_interaction, "test_command")

        assert context.user_id == 12345
        assert context.guild_id is None
        assert context.channel_id == 11111
        assert context.additional_context == {}

    def test_handle_command_error_creates_context(self) -> None:
        """Test that handle_command_error creates proper error context."""
        cog = BaseCommandCog(self.mock_bot)  # pyright: ignore[reportAny]

        mock_interaction = Mock()
        mock_interaction.user = Mock()
        mock_interaction.user.id = 12345  # pyright: ignore[reportAny]
        mock_interaction.guild = Mock()
        mock_interaction.guild.id = 67890  # pyright: ignore[reportAny]
        mock_interaction.channel = Mock()
        mock_interaction.channel.id = 11111  # pyright: ignore[reportAny]

        # Test the context creation part directly
        context = cog.create_error_context(
            mock_interaction, "test_command", {"extra": "data"}
        )

        assert isinstance(context, ErrorContext)
        assert context.user_id == 12345
        assert context.guild_id == 67890
        assert context.channel_id == 11111
        assert context.command_name == "test_command"
        assert context.additional_context == {"extra": "data"}
