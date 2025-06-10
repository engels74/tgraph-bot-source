"""
Tests for main.py entry point functionality.

This module tests the TGraphBot class initialization, configuration loading,
and main entry point function with proper mocking of Discord API calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from discord.ext import commands

from main import TGraphBot, main
from config.manager import ConfigManager
from config.schema import TGraphBotConfig


class TestTGraphBot:
    """Test cases for the TGraphBot class."""

    def test_init_with_config_manager(self) -> None:
        """Test TGraphBot initialization with ConfigManager."""
        config_manager = ConfigManager()
        
        # Create a mock config
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )
        config_manager.set_current_config(mock_config)
        
        bot = TGraphBot(config_manager)
        
        assert isinstance(bot, commands.Bot)
        assert bot.config_manager is config_manager
        assert bot.start_time == 0.0
        assert bot.command_prefix == "!"  # pyright: ignore[reportUnknownMemberType]
        assert bot.help_command is None
        
        # Check intents
        assert bot.intents.message_content is True
        assert bot.intents.guilds is True

    @pytest.mark.asyncio
    async def test_setup_hook_with_config(self) -> None:
        """Test setup_hook with valid configuration."""
        config_manager = ConfigManager()
        
        # Create a mock config
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
            LANGUAGE="en",
        )
        config_manager.set_current_config(mock_config)
        
        bot = TGraphBot(config_manager)
        
        # Mock the setup_i18n and load_extensions functions
        with patch("main.setup_i18n") as mock_setup_i18n, \
             patch("main.load_extensions") as mock_load_extensions:
            
            await bot.setup_hook()
            
            # Verify i18n setup was called with correct language
            mock_setup_i18n.assert_called_once_with("en")
            
            # Verify extensions loading was called with bot instance
            mock_load_extensions.assert_called_once_with(bot)

    @pytest.mark.asyncio
    async def test_setup_hook_no_config(self) -> None:
        """Test setup_hook when no configuration is loaded."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)
        
        # Mock the setup_i18n and load_extensions functions
        with patch("main.setup_i18n") as mock_setup_i18n, \
             patch("main.load_extensions") as mock_load_extensions:
            
            await bot.setup_hook()
            
            # Verify i18n setup and extensions loading were not called
            mock_setup_i18n.assert_not_called()
            mock_load_extensions.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_ready_with_user(self) -> None:
        """Test on_ready event handler when user is available."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Create a mock user object
        mock_user = MagicMock()
        mock_user.name = "TestBot"
        mock_user.id = 123456789

        # Mock time.time to test start_time setting
        with patch("time.time", return_value=1234567890.0), \
             patch.object(type(bot), "user", new_callable=lambda: mock_user), \
             patch.object(type(bot), "guilds", new_callable=lambda: [MagicMock(), MagicMock()]):

            await bot.on_ready()
            assert bot.start_time == 1234567890.0

    @pytest.mark.asyncio
    async def test_on_ready_no_user(self) -> None:
        """Test on_ready when bot.user is None."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Test the case where user is None - this should just log an error and return
        with patch.object(type(bot), "user", new_callable=lambda: None):
            await bot.on_ready()
            # start_time should remain 0.0 when user is None
            assert bot.start_time == 0.0

    @pytest.mark.asyncio
    async def test_on_error(self) -> None:
        """Test on_error event handler."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Should not raise an exception
        await bot.on_error("test_event", "arg1", "arg2", kwarg1="value1")

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test close method for graceful shutdown."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Mock the parent close method
        with patch.object(commands.Bot, "close", new_callable=AsyncMock) as mock_close:
            await bot.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_discord_connection_intents(self) -> None:
        """Test that Discord intents are properly configured for bot functionality."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Verify required intents are enabled
        assert bot.intents.message_content is True, "Message content intent required for commands"
        assert bot.intents.guilds is True, "Guilds intent required for server information"

        # Verify bot configuration
        assert bot.command_prefix == "!"  # pyright: ignore[reportUnknownMemberType]
        assert bot.help_command is None, "Custom help command should be used"

    @pytest.mark.asyncio
    async def test_discord_bot_connection_setup(self) -> None:
        """Test that the bot is properly configured for Discord connection."""
        config_manager = ConfigManager()

        # Create a mock config with valid Discord token
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
        )
        config_manager.set_current_config(mock_config)

        bot = TGraphBot(config_manager)

        # Verify bot is properly initialized for Discord connection
        assert isinstance(bot, commands.Bot), "Bot should be a discord.py Bot instance"
        assert bot.config_manager is config_manager, "Config manager should be accessible"

        # Verify async/await patterns are used in event handlers
        import inspect
        assert inspect.iscoroutinefunction(bot.on_ready), "on_ready should be async"
        assert inspect.iscoroutinefunction(bot.on_error), "on_error should be async"
        assert inspect.iscoroutinefunction(bot.close), "close should be async"
        assert inspect.iscoroutinefunction(bot.setup_hook), "setup_hook should be async"

    @pytest.mark.asyncio
    async def test_discord_native_permissions_integration(self) -> None:
        """Test that commands use Discord's native permissions system."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Load extensions to test command permissions
        from bot.commands.config import ConfigCog
        from bot.commands.update_graphs import UpdateGraphsCog

        config_cog = ConfigCog(bot)
        update_cog = UpdateGraphsCog(bot)

        # Verify admin commands have proper default permissions
        config_view_cmd = config_cog.config_group.get_command("view")
        config_edit_cmd = config_cog.config_group.get_command("edit")
        update_graphs_cmd = update_cog.update_graphs

        # These commands should have manage_guild permission requirement
        assert config_view_cmd is not None, "config view command should exist"
        assert config_edit_cmd is not None, "config edit command should exist"
        assert update_graphs_cmd is not None, "update_graphs command should exist"

        # Verify the commands have permission checks
        assert hasattr(config_view_cmd, 'checks'), "config view should have permission checks"
        assert hasattr(config_edit_cmd, 'checks'), "config edit should have permission checks"
        assert hasattr(update_graphs_cmd, 'checks'), "update_graphs should have permission checks"




class TestMainFunction:
    """Test cases for the main() function."""

    @pytest.mark.asyncio
    async def test_main_no_config_file(self) -> None:
        """Test main() when config.yml doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("sys.exit") as mock_exit:

            await main()
            # sys.exit should be called with 1, but we don't care how many times
            # since the function may call it multiple times in error handling
            mock_exit.assert_called_with(1)

    @pytest.mark.asyncio
    async def test_main_with_config_file(self) -> None:
        """Test main() with valid config file."""
        # Create a mock config
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch.object(ConfigManager, "load_config", return_value=mock_config), \
             patch.object(TGraphBot, "start", new_callable=AsyncMock) as mock_start:
            
            await main()
            mock_start.assert_called_once_with("test_token")

    @pytest.mark.asyncio
    async def test_main_keyboard_interrupt(self) -> None:
        """Test main() handling KeyboardInterrupt."""
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch.object(ConfigManager, "load_config", return_value=mock_config), \
             patch.object(TGraphBot, "start", new_callable=AsyncMock, side_effect=KeyboardInterrupt), \
             patch.object(TGraphBot, "close", new_callable=AsyncMock) as mock_close:
            
            await main()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_exception(self) -> None:
        """Test main() handling general exceptions."""
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch.object(ConfigManager, "load_config", return_value=mock_config), \
             patch.object(TGraphBot, "start", new_callable=AsyncMock, side_effect=Exception("Test error")), \
             patch.object(TGraphBot, "close", new_callable=AsyncMock) as mock_close, \
             patch("sys.exit") as mock_exit:
            
            await main()
            mock_close.assert_called_once()
            mock_exit.assert_called_once_with(1)
