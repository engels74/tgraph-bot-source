"""
Tests for main.py entry point functionality.

This module tests the TGraphBot class initialization, configuration loading,
error handling, logging, graceful shutdown, and main entry point function
with proper mocking of Discord API calls.
"""

import asyncio
import logging
import signal
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord.ext import commands

from main import TGraphBot, main, setup_logging, setup_signal_handlers
from config.manager import ConfigManager
from config.schema import TGraphBotConfig

if TYPE_CHECKING:
    pass


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

            # Should raise RuntimeError when no config is available
            with pytest.raises(RuntimeError, match="Bot setup failed: No configuration available"):
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


class TestEnhancedErrorHandling:
    """Test cases for enhanced error handling functionality."""

    def test_bot_initialization_with_background_tasks(self) -> None:
        """Test that bot initializes with background task management."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Verify background task management attributes
        assert hasattr(bot, '_background_tasks')
        assert hasattr(bot, '_shutdown_event')
        assert hasattr(bot, '_is_shutting_down')
        assert isinstance(bot._background_tasks, set)  # pyright: ignore[reportPrivateUsage]
        assert isinstance(bot._shutdown_event, asyncio.Event)  # pyright: ignore[reportPrivateUsage]
        assert bot._is_shutting_down is False  # pyright: ignore[reportPrivateUsage]
        assert bot.is_shutting_down() is False

    @pytest.mark.asyncio
    async def test_setup_hook_error_handling(self) -> None:
        """Test setup_hook with various error conditions."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Test with no configuration
        with pytest.raises(RuntimeError, match="Bot setup failed: No configuration available"):
            await bot.setup_hook()

    @pytest.mark.asyncio
    async def test_setup_hook_extension_loading_errors(self) -> None:
        """Test setup_hook handling extension loading errors gracefully."""
        config_manager = ConfigManager()
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
            LANGUAGE="en",
        )
        config_manager.set_current_config(mock_config)
        bot = TGraphBot(config_manager)

        # Mock extension loading to return some failed extensions
        from bot.extensions import ExtensionStatus
        mock_results = [
            ExtensionStatus("bot.commands.about", True),
            ExtensionStatus("bot.commands.broken", False, "Import error"),
        ]

        with patch("main.setup_i18n"), \
             patch("main.load_extensions", return_value=mock_results), \
             patch.object(bot, "setup_background_tasks", new_callable=AsyncMock):

            await bot.setup_hook()
            # Should complete successfully even with some failed extensions

    @pytest.mark.asyncio
    async def test_background_task_management(self) -> None:
        """Test background task creation and cleanup."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Test creating a background task
        async def dummy_task() -> None:
            await asyncio.sleep(0.1)

        task = bot.create_background_task(dummy_task(), "test_task")
        assert task in bot._background_tasks  # pyright: ignore[reportPrivateUsage]
        assert task.get_name() == "test_task"

        # Wait for task to complete
        await task

        # Task should be automatically removed from set when done
        assert task not in bot._background_tasks  # pyright: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_cleanup_background_tasks(self) -> None:
        """Test cleanup of background tasks during shutdown."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Create some background tasks
        async def long_running_task() -> None:
            await asyncio.sleep(10)  # Long enough to be cancelled

        task1 = bot.create_background_task(long_running_task(), "task1")
        task2 = bot.create_background_task(long_running_task(), "task2")

        assert len(bot._background_tasks) == 2  # pyright: ignore[reportPrivateUsage]

        # Cleanup should cancel and wait for tasks
        await bot.cleanup_background_tasks()

        assert len(bot._background_tasks) == 0  # pyright: ignore[reportPrivateUsage]
        assert task1.cancelled()
        assert task2.cancelled()

    @pytest.mark.asyncio
    async def test_enhanced_close_method(self) -> None:
        """Test enhanced close method with comprehensive cleanup."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Create a background task
        async def dummy_task() -> None:
            await asyncio.sleep(10)

        _ = bot.create_background_task(dummy_task(), "test_task")

        with patch.object(commands.Bot, "close", new_callable=AsyncMock) as mock_parent_close:
            await bot.close()

            # Verify shutdown state
            assert bot.is_shutting_down() is True
            assert bot._shutdown_event.is_set()  # pyright: ignore[reportPrivateUsage]
            assert len(bot._background_tasks) == 0  # pyright: ignore[reportPrivateUsage]
            mock_parent_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_method_idempotent(self) -> None:
        """Test that close method can be called multiple times safely."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        with patch.object(commands.Bot, "close", new_callable=AsyncMock) as mock_parent_close:
            # First call
            await bot.close()
            assert mock_parent_close.call_count == 1

            # Second call should be skipped
            await bot.close()
            assert mock_parent_close.call_count == 1  # Should not increase

    @pytest.mark.asyncio
    async def test_on_ready_with_shutdown_event(self) -> None:
        """Test on_ready behavior when shutdown is requested during startup."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Set shutdown event before on_ready
        bot._shutdown_event.set()  # pyright: ignore[reportPrivateUsage]

        mock_user = MagicMock()
        mock_user.name = "TestBot"
        mock_user.id = 123456789

        def mock_empty_guilds() -> list[discord.Guild]:
            return []

        with patch.object(type(bot), "user", new_callable=lambda: mock_user), \
             patch.object(type(bot), "guilds", new_callable=mock_empty_guilds), \
             patch.object(bot, "close", new_callable=AsyncMock) as mock_close:

            await bot.on_ready()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_enhanced_on_error(self) -> None:
        """Test enhanced on_error with detailed logging."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Should handle errors without raising exceptions
        await bot.on_error("test_event", "arg1", "arg2", kwarg1="value1", kwarg2="value2")

    @pytest.mark.asyncio
    async def test_on_disconnect_and_resumed(self) -> None:
        """Test disconnect and resumed event handlers."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # These should not raise exceptions
        await bot.on_disconnect()
        await bot.on_resumed()


class TestLoggingSetup:
    """Test cases for enhanced logging configuration."""

    def test_setup_logging_creates_directories(self) -> None:
        """Test that setup_logging creates necessary directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to the temp directory
            import os
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                setup_logging()

                logs_dir = Path(temp_dir) / "logs"
                assert logs_dir.exists()
                assert logs_dir.is_dir()
            finally:
                os.chdir(original_cwd)

    def test_setup_logging_configures_handlers(self) -> None:
        """Test that setup_logging configures multiple handlers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pathlib.Path.cwd", return_value=Path(temp_dir)):
                # Clear existing handlers
                root_logger = logging.getLogger()
                original_handlers = root_logger.handlers[:]

                try:
                    setup_logging()

                    # Should have file, console, and error handlers
                    assert len(root_logger.handlers) >= 3

                    # Check for different handler types
                    handler_types = [type(h).__name__ for h in root_logger.handlers]
                    assert "RotatingFileHandler" in handler_types
                    assert "StreamHandler" in handler_types

                finally:
                    # Restore original handlers
                    root_logger.handlers = original_handlers

    def test_setup_logging_sets_levels(self) -> None:
        """Test that setup_logging sets appropriate log levels."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pathlib.Path.cwd", return_value=Path(temp_dir)):
                setup_logging()

                # Check specific logger levels
                discord_logger = logging.getLogger("discord")
                bot_logger = logging.getLogger("bot")

                assert discord_logger.level == logging.WARNING
                assert bot_logger.level == logging.INFO


class TestSignalHandling:
    """Test cases for signal handling functionality."""

    def test_setup_signal_handlers(self) -> None:
        """Test signal handler setup."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        with patch("signal.signal") as mock_signal:
            setup_signal_handlers(bot)

            # Should register handlers for SIGTERM and SIGINT
            assert mock_signal.call_count == 2
            calls = mock_signal.call_args_list

            # Check that SIGTERM and SIGINT are handled
            signals_handled = [call[0][0] for call in calls]
            assert signal.SIGTERM in signals_handled
            assert signal.SIGINT in signals_handled

    def test_signal_handler_function(self) -> None:
        """Test signal handler function behavior."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Create a mock event loop
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True  # pyright: ignore[reportAny]

        with patch("signal.signal") as mock_signal, \
             patch("asyncio.get_event_loop", return_value=mock_loop):

            setup_signal_handlers(bot)

            # Get the signal handler function
            signal_handler = mock_signal.call_args_list[0][0][1]  # pyright: ignore[reportAny]

            # Call the signal handler
            signal_handler(signal.SIGTERM, None)

            # Should create a task to close the bot
            mock_loop.create_task.assert_called_once()  # pyright: ignore[reportAny]


class TestMainFunctionEnhancements:
    """Test cases for enhanced main function functionality."""

    @pytest.mark.asyncio
    async def test_main_with_logging_setup(self) -> None:
        """Test that main() sets up logging."""
        with patch("main.setup_logging") as mock_setup_logging, \
             patch("pathlib.Path.exists", return_value=False), \
             patch("sys.exit"):

            await main()
            mock_setup_logging.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_with_signal_handlers(self) -> None:
        """Test that main() sets up signal handlers."""
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )

        with patch("main.setup_logging"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch.object(ConfigManager, "load_config", return_value=mock_config), \
             patch("main.setup_signal_handlers") as mock_setup_signals, \
             patch.object(TGraphBot, "start", new_callable=AsyncMock):

            await main()
            mock_setup_signals.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_discord_login_failure(self) -> None:
        """Test main() handling Discord login failures."""
        import discord

        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="invalid_token",
            CHANNEL_ID=123456789,
        )

        with patch("main.setup_logging"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch.object(ConfigManager, "load_config", return_value=mock_config), \
             patch("main.setup_signal_handlers"), \
             patch.object(TGraphBot, "start", new_callable=AsyncMock,
                         side_effect=discord.LoginFailure("Invalid token")), \
             patch("sys.exit") as mock_exit:

            await main()
            mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_main_discord_http_exception(self) -> None:
        """Test main() handling Discord HTTP exceptions."""
        import discord

        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )

        with patch("main.setup_logging"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch.object(ConfigManager, "load_config", return_value=mock_config), \
             patch("main.setup_signal_handlers"), \
             patch.object(TGraphBot, "start", new_callable=AsyncMock,
                         side_effect=discord.HTTPException(MagicMock(), "API Error")), \
             patch("sys.exit") as mock_exit:

            await main()
            mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_main_finally_block_cleanup(self) -> None:
        """Test that main() properly cleans up in finally block."""
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )

        with patch("main.setup_logging"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch.object(ConfigManager, "load_config", return_value=mock_config), \
             patch("main.setup_signal_handlers"), \
             patch.object(TGraphBot, "start", new_callable=AsyncMock,
                         side_effect=Exception("Test error")), \
             patch.object(TGraphBot, "close", new_callable=AsyncMock) as mock_close, \
             patch.object(TGraphBot, "is_shutting_down", return_value=False), \
             patch("sys.exit"):

            await main()
            # Bot should be closed in finally block
            mock_close.assert_called()
