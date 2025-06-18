"""
Tests for configuration command functionality.

This module tests the /config command group including /config view and /config edit
commands with proper validation, error handling, and Discord integration.
"""

from unittest.mock import patch

import discord
import pytest
from discord.ext import commands


from bot.commands.config import ConfigCog
from config.schema import TGraphBotConfig
from main import TGraphBot
from tests.utils.test_helpers import create_config_manager_with_config, create_mock_interaction, create_temp_config_file


class TestConfigCog:
    """Test cases for the ConfigCog class."""

    @pytest.fixture
    def mock_bot(self, base_config: TGraphBotConfig) -> TGraphBot:
        """Create a mock TGraphBot instance."""
        config_manager = create_config_manager_with_config(base_config)
        bot = TGraphBot(config_manager)
        return bot

    @pytest.fixture
    def config_cog(self, mock_bot: TGraphBot) -> ConfigCog:
        """Create a ConfigCog instance for testing."""
        return ConfigCog(mock_bot)



    def test_init(self, mock_bot: TGraphBot) -> None:
        """Test ConfigCog initialization."""
        cog = ConfigCog(mock_bot)
        assert cog.bot is mock_bot
        assert isinstance(cog.tgraph_bot, TGraphBot)

    def test_tgraph_bot_property_with_wrong_bot_type(self) -> None:
        """Test tgraph_bot property with wrong bot type."""
        regular_bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

        # The ConfigCog constructor will fail when trying to access tgraph_bot
        with pytest.raises(TypeError, match="Expected TGraphBot instance"):
            _ = ConfigCog(regular_bot)

    def test_convert_config_value_string(self, config_cog: ConfigCog) -> None:
        """Test string value conversion."""
        result = config_cog._convert_config_value("test_value", str)  # pyright: ignore[reportPrivateUsage]
        assert result == "test_value"
        assert isinstance(result, str)

    def test_convert_config_value_int(self, config_cog: ConfigCog) -> None:
        """Test integer value conversion."""
        result = config_cog._convert_config_value("42", int)  # pyright: ignore[reportPrivateUsage]
        assert result == 42
        assert isinstance(result, int)

    def test_convert_config_value_int_invalid(self, config_cog: ConfigCog) -> None:
        """Test invalid integer value conversion."""
        with pytest.raises(ValueError, match="'not_a_number' is not a valid integer"):
            _ = config_cog._convert_config_value("not_a_number", int)  # pyright: ignore[reportPrivateUsage]

    def test_convert_config_value_bool_true(self, config_cog: ConfigCog) -> None:
        """Test boolean true value conversion."""
        true_values = ["true", "yes", "1", "on", "enabled", "TRUE", "YES"]
        for value in true_values:
            result = config_cog._convert_config_value(value, bool)  # pyright: ignore[reportPrivateUsage]
            assert result is True

    def test_convert_config_value_bool_false(self, config_cog: ConfigCog) -> None:
        """Test boolean false value conversion."""
        false_values = ["false", "no", "0", "off", "disabled", "FALSE", "NO"]
        for value in false_values:
            result = config_cog._convert_config_value(value, bool)  # pyright: ignore[reportPrivateUsage]
            assert result is False

    def test_convert_config_value_bool_invalid(self, config_cog: ConfigCog) -> None:
        """Test invalid boolean value conversion."""
        with pytest.raises(ValueError, match="'maybe' is not a valid boolean"):
            _ = config_cog._convert_config_value("maybe", bool)  # pyright: ignore[reportPrivateUsage]

    def test_convert_config_value_float(self, config_cog: ConfigCog) -> None:
        """Test float value conversion."""
        result = config_cog._convert_config_value("3.14", float)  # pyright: ignore[reportPrivateUsage]
        assert result == 3.14
        assert isinstance(result, float)

    def test_convert_config_value_float_invalid(self, config_cog: ConfigCog) -> None:
        """Test invalid float value conversion."""
        with pytest.raises(ValueError, match="'not_a_float' is not a valid number"):
            _ = config_cog._convert_config_value("not_a_float", float)  # pyright: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_config_view_success(
        self,
        config_cog: ConfigCog
    ) -> None:
        """Test successful configuration viewing."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_view",
            user_id=123456,
            username="TestUser"
        )
        
        # Call the method directly using the callback
        _ = await config_cog.config_view.callback(config_cog, mock_interaction)  # pyright: ignore[reportCallIssue,reportUnknownVariableType]

        # Verify interaction response was called
        mock_interaction.response.send_message.assert_called_once()  # pyright: ignore[reportAny]

        # Get the embed from the call
        call_args = mock_interaction.response.send_message.call_args  # pyright: ignore[reportAny]
        embed = call_args[1]['embed']  # pyright: ignore[reportAny]

        assert embed.title == "🔧 Bot Configuration"  # pyright: ignore[reportAny]
        assert embed.color == discord.Color.blue()  # pyright: ignore[reportAny]
        assert len(embed.fields) >= 3  # Should have multiple fields  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_config_view_error(
        self,
        config_cog: ConfigCog
    ) -> None:
        """Test configuration viewing with error."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_view",
            user_id=123456,
            username="TestUser"
        )
        
        # Mock the config manager to raise an exception
        with patch.object(config_cog.tgraph_bot.config_manager, 'get_current_config', side_effect=RuntimeError("Test error")), \
             patch('utils.command_utils.safe_interaction_response') as mock_safe_response:
            _ = await config_cog.config_view.callback(config_cog, mock_interaction)  # pyright: ignore[reportCallIssue,reportUnknownVariableType]

        # Verify error response was sent through the new error handling system
        mock_safe_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_invalid_setting(
        self,
        config_cog: ConfigCog
    ) -> None:
        """Test configuration editing with invalid setting."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_edit",
            user_id=123456,
            username="TestUser"
        )
        
        with patch('utils.command_utils.safe_interaction_response') as mock_safe_response:
            _ = await config_cog.config_edit.callback(config_cog, mock_interaction, "INVALID_SETTING", "value")  # pyright: ignore[reportCallIssue,reportUnknownVariableType]

        # Verify error response was sent through the new error handling system
        mock_safe_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_invalid_value(
        self,
        config_cog: ConfigCog
    ) -> None:
        """Test configuration editing with invalid value."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_edit",
            user_id=123456,
            username="TestUser"
        )
        
        with patch('utils.command_utils.safe_interaction_response') as mock_safe_response:
            _ = await config_cog.config_edit.callback(config_cog, mock_interaction, "UPDATE_DAYS", "not_a_number")  # pyright: ignore[reportCallIssue,reportUnknownVariableType]

        # Verify error response was sent through the new error handling system
        mock_safe_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_validation_error(
        self,
        config_cog: ConfigCog
    ) -> None:
        """Test configuration editing with validation error."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_edit",
            user_id=123456,
            username="TestUser"
        )
        
        # Try to set UPDATE_DAYS to an invalid value (outside range)
        with patch('utils.command_utils.safe_interaction_response') as mock_safe_response:
            _ = await config_cog.config_edit.callback(config_cog, mock_interaction, "UPDATE_DAYS", "999")  # pyright: ignore[reportCallIssue,reportUnknownVariableType]

        # Verify error response was sent through the new error handling system
        mock_safe_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_no_config_file(
        self,
        config_cog: ConfigCog
    ) -> None:
        """Test configuration editing when no config file path is available."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_edit",
            user_id=123456,
            username="TestUser"
        )
        
        # Mock the config manager's config_file_path to be None
        with patch.object(config_cog.tgraph_bot.config_manager, 'config_file_path', None), \
             patch('utils.command_utils.safe_interaction_response') as mock_safe_response:
            _ = await config_cog.config_edit.callback(config_cog, mock_interaction, "UPDATE_DAYS", "14")  # pyright: ignore[reportCallIssue,reportUnknownVariableType]

        # Verify error response was sent through the new error handling system
        mock_safe_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_success(
        self,
        config_cog: ConfigCog,
        base_config: TGraphBotConfig
    ) -> None:
        """Test successful configuration editing."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_edit",
            user_id=123456,
            username="TestUser"
        )
        
        # Create a temporary config file using centralized utility
        with create_temp_config_file() as config_path:
            # Mock the config manager's config_file_path
            with patch.object(config_cog.tgraph_bot.config_manager, 'config_file_path', config_path), \
                 patch.object(config_cog.tgraph_bot.config_manager, 'get_current_config', return_value=base_config), \
                 patch('config.manager.ConfigManager.save_config') as mock_save:

                _ = await config_cog.config_edit.callback(config_cog, mock_interaction, "UPDATE_DAYS", "14")  # pyright: ignore[reportCallIssue,reportUnknownVariableType]

                # Verify save was called
                mock_save.assert_called_once()

                # Verify success response was sent
                mock_interaction.response.send_message.assert_called_once()  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_config_edit_save_error(
        self, 
        config_cog: ConfigCog
    ) -> None:
        """Test configuration editing when save operation fails."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_edit",
            user_id=123456,
            username="TestUser"
        )
        
        # Create a temporary config file using centralized utility
        with create_temp_config_file() as config_path:
            # Mock the config manager's config_file_path and save to raise an exception
            with patch.object(config_cog.tgraph_bot.config_manager, 'config_file_path', config_path), \
                 patch('config.manager.ConfigManager.save_config', side_effect=OSError("Save failed")), \
                 patch('utils.command_utils.safe_interaction_response') as mock_safe_response:

                _ = await config_cog.config_edit.callback(config_cog, mock_interaction, "UPDATE_DAYS", "14")  # pyright: ignore[reportCallIssue,reportUnknownVariableType]

                # Verify error response was sent through the new error handling system
                mock_safe_response.assert_called_once()
