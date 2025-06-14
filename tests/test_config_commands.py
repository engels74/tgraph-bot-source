"""
Tests for configuration command functionality.

This module tests the /config command group including /config view and /config edit
commands with proper validation, error handling, and Discord integration.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord.ext import commands


from bot.commands.config import ConfigCog
from config.manager import ConfigManager
from config.schema import TGraphBotConfig
from main import TGraphBot


class TestConfigCog:
    """Test cases for the ConfigCog class."""

    @pytest.fixture
    def mock_config(self) -> TGraphBotConfig:
        """Create a mock configuration for testing."""
        return TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token",
            CHANNEL_ID=123456789012345678,
            UPDATE_DAYS=7,
            LANGUAGE="en",
            CENSOR_USERNAMES=True,
            ENABLE_GRAPH_GRID=False,
        )

    @pytest.fixture
    def mock_config_manager(self, mock_config: TGraphBotConfig) -> ConfigManager:
        """Create a mock configuration manager."""
        config_manager = ConfigManager()
        config_manager.set_current_config(mock_config)
        return config_manager

    @pytest.fixture
    def mock_bot(self, mock_config_manager: ConfigManager) -> TGraphBot:
        """Create a mock TGraphBot instance."""
        bot = TGraphBot(mock_config_manager)
        return bot

    @pytest.fixture
    def config_cog(self, mock_bot: TGraphBot) -> ConfigCog:
        """Create a ConfigCog instance for testing."""
        return ConfigCog(mock_bot)

    @pytest.fixture
    def mock_interaction(self) -> MagicMock:
        """Create a mock Discord interaction."""
        interaction = MagicMock(spec=discord.Interaction)
        interaction.response = AsyncMock()
        interaction.followup = AsyncMock()
        interaction.user = MagicMock()
        return interaction

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
        config_cog: ConfigCog,
        mock_interaction: MagicMock
    ) -> None:
        """Test successful configuration viewing."""
        # Call the method directly using the callback
        _ = await config_cog.config_view.callback(config_cog, mock_interaction)  # pyright: ignore[reportCallIssue]

        # Verify interaction response was called
        mock_interaction.response.send_message.assert_called_once()

        # Get the embed from the call
        call_args = mock_interaction.response.send_message.call_args
        embed = call_args[1]['embed']

        assert embed.title == "🔧 Bot Configuration"
        assert embed.color == discord.Color.blue()
        assert len(embed.fields) >= 3  # Should have multiple fields

    @pytest.mark.asyncio
    async def test_config_view_error(
        self,
        config_cog: ConfigCog,
        mock_interaction: MagicMock
    ) -> None:
        """Test configuration viewing with error."""
        # Mock the config manager to raise an exception
        with patch.object(config_cog.tgraph_bot.config_manager, 'get_current_config', side_effect=RuntimeError("Test error")), \
             patch('utils.command_utils.safe_interaction_response') as mock_safe_response:
            _ = await config_cog.config_view.callback(config_cog, mock_interaction)  # pyright: ignore[reportCallIssue]

        # Verify error response was sent through the new error handling system
        mock_safe_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_invalid_setting(
        self,
        config_cog: ConfigCog,
        mock_interaction: MagicMock
    ) -> None:
        """Test configuration editing with invalid setting."""
        with patch('utils.command_utils.safe_interaction_response') as mock_safe_response:
            _ = await config_cog.config_edit.callback(config_cog, mock_interaction, "INVALID_SETTING", "value")  # pyright: ignore[reportCallIssue]

        # Verify error response was sent through the new error handling system
        mock_safe_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_invalid_value(
        self,
        config_cog: ConfigCog,
        mock_interaction: MagicMock
    ) -> None:
        """Test configuration editing with invalid value."""
        with patch('utils.command_utils.safe_interaction_response') as mock_safe_response:
            _ = await config_cog.config_edit.callback(config_cog, mock_interaction, "UPDATE_DAYS", "not_a_number")  # pyright: ignore[reportCallIssue]

        # Verify error response was sent through the new error handling system
        mock_safe_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_validation_error(
        self,
        config_cog: ConfigCog,
        mock_interaction: MagicMock
    ) -> None:
        """Test configuration editing with validation error."""
        # Try to set UPDATE_DAYS to an invalid value (outside range)
        with patch('utils.command_utils.safe_interaction_response') as mock_safe_response:
            _ = await config_cog.config_edit.callback(config_cog, mock_interaction, "UPDATE_DAYS", "999")  # pyright: ignore[reportCallIssue]

        # Verify error response was sent through the new error handling system
        mock_safe_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_no_config_file(
        self,
        config_cog: ConfigCog,
        mock_interaction: MagicMock
    ) -> None:
        """Test configuration editing when config file doesn't exist."""
        with patch('pathlib.Path.exists', return_value=False), \
             patch('utils.command_utils.safe_interaction_response') as mock_safe_response:
            _ = await config_cog.config_edit.callback(config_cog, mock_interaction, "UPDATE_DAYS", "14")  # pyright: ignore[reportCallIssue]

        # Verify error response was sent through the new error handling system
        mock_safe_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_success(
        self,
        config_cog: ConfigCog,
        mock_interaction: MagicMock,
        _mock_config: TGraphBotConfig
    ) -> None:
        """Test successful configuration editing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            
            # Write initial config
            _ = temp_file.write("UPDATE_DAYS: 7\nLANGUAGE: en\n")
            temp_file.flush()
            
            try:
                with patch('pathlib.Path.exists', return_value=True), \
                     patch('bot.commands.config.Path', return_value=temp_path), \
                     patch.object(ConfigManager, 'save_config') as mock_save:

                    _ = await config_cog.config_edit.callback(config_cog, mock_interaction, "UPDATE_DAYS", "14")  # pyright: ignore[reportCallIssue]
                
                # Verify success response was sent
                mock_interaction.response.send_message.assert_called_once()
                call_args = mock_interaction.response.send_message.call_args
                embed = call_args[1]['embed']
                
                assert embed.title == "✅ Configuration Updated"
                assert embed.color == discord.Color.green()
                
                # Verify save was called
                mock_save.assert_called_once()
                
            finally:
                temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_config_edit_save_error(
        self, 
        config_cog: ConfigCog, 
        mock_interaction: MagicMock
    ) -> None:
        """Test configuration editing with save error."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch.object(ConfigManager, 'save_config', side_effect=Exception("Save failed")), \
             patch('utils.command_utils.safe_interaction_response') as mock_safe_response:

            _ = await config_cog.config_edit.callback(config_cog, mock_interaction, "UPDATE_DAYS", "14")  # pyright: ignore[reportCallIssue]

        # Verify error response was sent through the new error handling system
        mock_safe_response.assert_called_once()
