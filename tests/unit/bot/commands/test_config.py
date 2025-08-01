"""
Tests for configuration command functionality.

This module tests the /config command group including /config view and /config edit
commands with proper validation, error handling, and Discord integration.

Note: Basic initialization and type validation tests have been consolidated
in tests.unit.bot.test_cog_base_functionality to eliminate redundancy.
"""

from unittest.mock import patch

import discord
import pytest

from src.tgraph_bot.bot.commands.config import ConfigCog
from src.tgraph_bot.config.schema import TGraphBotConfig
from src.tgraph_bot.main import TGraphBot
from tests.utils.cog_helpers import create_mock_bot_with_config
from tests.utils.test_helpers import (
    create_mock_interaction,
    create_temp_config_file,
)


class TestConfigCog:
    """Test cases for the ConfigCog class."""

    @pytest.fixture
    def mock_bot(self, base_config: TGraphBotConfig) -> TGraphBot:
        """Create a mock TGraphBot instance."""
        return create_mock_bot_with_config(base_config)

    @pytest.fixture
    def config_cog(self, mock_bot: TGraphBot) -> ConfigCog:
        """Create a ConfigCog instance for testing."""
        return ConfigCog(mock_bot)

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
    async def test_config_view_success(self, config_cog: ConfigCog) -> None:
        """Test successful configuration viewing."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_view", user_id=123456, username="TestUser"
        )

        # Call the method using the callback (need to pass cog as first argument)
        _ = await config_cog.config_view.callback(config_cog, mock_interaction)  # pyright: ignore[reportArgumentType]

        # Verify interaction response was called
        mock_interaction.response.send_message.assert_called_once()  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

        # Get the embed from the call
        call_args = mock_interaction.response.send_message.call_args  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue,reportUnknownVariableType]
        embed: discord.Embed = call_args[1]["embed"]  # pyright: ignore[reportUnknownVariableType]

        assert embed.title == "🔧 Bot Configuration"  # pyright: ignore[reportUnknownMemberType]
        assert embed.color == discord.Color.blue()  # pyright: ignore[reportUnknownMemberType]
        assert (
            len(embed.fields) >= 3  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
        )  # Should have multiple fields

    @pytest.mark.asyncio
    async def test_config_view_error(self, config_cog: ConfigCog) -> None:
        """Test configuration viewing with error."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_view", user_id=123456, username="TestUser"
        )

        # Mock the config manager to raise an exception
        with patch.object(
            config_cog.tgraph_bot.config_manager,
            "get_current_config",
            side_effect=RuntimeError("Test error"),
        ):
            _ = await config_cog.config_view.callback(config_cog, mock_interaction)  # pyright: ignore[reportArgumentType]

        # Verify error response was sent via interaction
        mock_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_invalid_setting(self, config_cog: ConfigCog) -> None:
        """Test configuration editing with invalid setting."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_edit", user_id=123456, username="TestUser"
        )

        _ = await config_cog.config_edit.callback(  # pyright: ignore[reportUnknownVariableType]
            config_cog,
            mock_interaction,
            key="INVALID_SETTING",  # pyright: ignore[reportCallIssue]
            value="value",
        )

        # Verify error response was sent via interaction
        mock_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_invalid_value(self, config_cog: ConfigCog) -> None:
        """Test configuration editing with invalid value."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_edit", user_id=123456, username="TestUser"
        )

        _ = await config_cog.config_edit.callback(  # pyright: ignore[reportUnknownVariableType]
            config_cog,
            mock_interaction,
            key="automation.scheduling.update_days",  # pyright: ignore[reportCallIssue]
            value="not_a_number",
        )

        # Verify error response was sent via interaction
        mock_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_validation_error(self, config_cog: ConfigCog) -> None:
        """Test configuration editing with validation error."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_edit", user_id=123456, username="TestUser"
        )

        # Try to set automation.scheduling.update_days to an invalid value (outside range)
        _ = await config_cog.config_edit.callback(  # pyright: ignore[reportUnknownVariableType]
            config_cog,
            mock_interaction,
            key="automation.scheduling.update_days",  # pyright: ignore[reportCallIssue]
            value="999",
        )

        # Verify error response was sent via interaction
        mock_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_no_config_file(self, config_cog: ConfigCog) -> None:
        """Test configuration editing when no config file path is available."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_edit", user_id=123456, username="TestUser"
        )

        # Mock the config manager's config_file_path to be None
        with (
            patch.object(
                config_cog.tgraph_bot.config_manager, "config_file_path", None
            ),
            patch(
                "src.tgraph_bot.utils.discord.command_utils.safe_interaction_response"
            ) as mock_safe_response,
        ):
            _ = await config_cog.config_edit.callback(  # pyright: ignore[reportUnknownVariableType]
                config_cog,
                mock_interaction,
                key="automation.scheduling.update_days",  # pyright: ignore[reportCallIssue]
                value="14",
            )

        # Verify error response was sent through the new error handling system
        mock_safe_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_edit_success(
        self, config_cog: ConfigCog, base_config: TGraphBotConfig
    ) -> None:
        """Test configuration editing with nested structure - should succeed for nested keys."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_edit", user_id=123456, username="TestUser"
        )

        # Create a temporary config file using centralized utility
        with create_temp_config_file() as config_path:
            # Mock the config manager's config_file_path
            with (
                patch.object(
                    config_cog.tgraph_bot.config_manager,
                    "config_file_path",
                    config_path,
                ),
                patch.object(
                    config_cog.tgraph_bot.config_manager,
                    "get_current_config",
                    return_value=base_config,
                ),
                patch(
                    "src.tgraph_bot.config.manager.ConfigManager.save_config"
                ) as mock_save,
                patch.object(
                    config_cog.tgraph_bot.config_manager, 
                    "update_runtime_config"
                ) as mock_update_runtime,
            ):
                # The config command now supports nested structure properly
                # So it should succeed with valid nested keys
                _ = await config_cog.config_edit.callback(  # pyright: ignore[reportUnknownVariableType]
                    config_cog,
                    mock_interaction,
                    key="automation.scheduling.update_days",  # pyright: ignore[reportCallIssue]
                    value="14",
                )

                # Verify save was called since the nested key exists and is valid
                mock_save.assert_called_once()
                mock_update_runtime.assert_called_once()

                # Verify success response was sent
                mock_interaction.response.send_message.assert_called_once()  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

    @pytest.mark.asyncio
    async def test_config_edit_save_error(self, config_cog: ConfigCog) -> None:
        """Test configuration editing when save operation fails."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_edit", user_id=123456, username="TestUser"
        )

        # Create a temporary config file using centralized utility
        with create_temp_config_file() as config_path:
            # Mock the config manager's config_file_path and save to raise an exception
            with (
                patch.object(
                    config_cog.tgraph_bot.config_manager,
                    "config_file_path",
                    config_path,
                ),
                patch(
                    "src.tgraph_bot.config.manager.ConfigManager.save_config",
                    side_effect=OSError("Save failed"),
                ),
                patch(
                    "src.tgraph_bot.utils.discord.command_utils.safe_interaction_response"
                ) as mock_safe_response,
            ):
                _ = await config_cog.config_edit.callback(  # pyright: ignore[reportUnknownVariableType]
                    config_cog,
                    mock_interaction,
                    key="automation.scheduling.update_days",  # pyright: ignore[reportCallIssue]
                    value="14",
                )

                # Verify error response was sent through the new error handling system
                mock_safe_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_view_with_specific_key(self, config_cog: ConfigCog) -> None:
        """Test configuration viewing with specific key."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_view", user_id=123456, username="TestUser"
        )

        # Test viewing a specific key
        _ = await config_cog.config_view.callback(  # pyright: ignore[reportUnknownVariableType]
            config_cog,
            mock_interaction,
            key="automation.scheduling.update_days",  # pyright: ignore[reportCallIssue]
        )

        # Verify response was sent
        mock_interaction.response.send_message.assert_called_once()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]

        # Get the embed that was sent
        call_args = mock_interaction.response.send_message.call_args  # pyright: ignore[reportAttributeAccessIssue,reportUnknownVariableType,reportUnknownMemberType]
        embed = call_args[1]["embed"]  # pyright: ignore[reportUnknownVariableType]

        # Verify the embed contains the specific key information
        assert "automation.scheduling.update_days" in embed.title  # pyright: ignore[reportUnknownMemberType]
        assert embed.fields[0].name == "Current Value"  # pyright: ignore[reportUnknownMemberType]

    @pytest.mark.asyncio
    async def test_config_view_with_invalid_key(self, config_cog: ConfigCog) -> None:
        """Test configuration viewing with invalid key."""
        # Create mock interaction using standardized utility
        mock_interaction = create_mock_interaction(
            command_name="config_view", user_id=123456, username="TestUser"
        )

        # Test viewing an invalid key
        _ = await config_cog.config_view.callback(  # pyright: ignore[reportUnknownVariableType]
            config_cog,
            mock_interaction,
            key="INVALID_KEY",  # pyright: ignore[reportCallIssue]
        )

        # Verify response was sent
        mock_interaction.response.send_message.assert_called_once()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]

        # Get the embed that was sent
        call_args = mock_interaction.response.send_message.call_args  # pyright: ignore[reportAttributeAccessIssue,reportUnknownVariableType,reportUnknownMemberType]
        embed = call_args[1]["embed"]  # pyright: ignore[reportUnknownVariableType]

        # Verify the embed shows an error
        assert "Configuration Key Not Found" in embed.title  # pyright: ignore[reportUnknownMemberType]
        assert "INVALID_KEY" in embed.description  # pyright: ignore[reportUnknownMemberType]

    @pytest.mark.asyncio
    async def test_config_key_autocomplete(self, config_cog: ConfigCog) -> None:
        """Test configuration key autocomplete functionality."""
        # Create mock interaction
        mock_interaction = create_mock_interaction(
            command_name="config_autocomplete", user_id=123456, username="TestUser"
        )

        # Test autocomplete with no input
        choices = await config_cog._config_key_autocomplete(mock_interaction, "")  # pyright: ignore[reportPrivateUsage]

        # Should return all available keys (limited to 25)
        assert len(choices) <= 25
        assert all(choice.name in config_cog._get_config_keys() for choice in choices)  # pyright: ignore[reportPrivateUsage]

        # Test autocomplete with partial input
        choices = await config_cog._config_key_autocomplete(mock_interaction, "automation")  # pyright: ignore[reportPrivateUsage]

        # Should return filtered keys
        assert all("automation" in choice.name for choice in choices)
        assert len(choices) > 0
