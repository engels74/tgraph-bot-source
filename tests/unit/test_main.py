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
from typing import TYPE_CHECKING, override
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord.ext import commands

from src.tgraph_bot.main import TGraphBot, main, setup_logging, setup_signal_handlers
from src.tgraph_bot.config.manager import ConfigManager
from src.tgraph_bot.config.schema import TGraphBotConfig
from tests.utils.test_helpers import create_config_manager_with_config
from tests.utils.async_helpers import AsyncTestBase, async_mock_context

if TYPE_CHECKING:
    pass


class TestTGraphBot:
    """Test cases for the TGraphBot class."""

    def test_init_with_config_manager(self, minimal_config: TGraphBotConfig) -> None:
        """Test TGraphBot initialization with ConfigManager."""
        config_manager = create_config_manager_with_config(minimal_config)
        
        bot = TGraphBot(config_manager)
        
        assert isinstance(bot, commands.Bot)
        assert bot.config_manager is config_manager
        assert bot.start_time == 0.0
        assert bot.command_prefix == "!"  # pyright: ignore[reportUnknownMemberType]
        assert bot.help_command is None
        
        # Check intents
        assert bot.intents.message_content is False  # Privileged intent not required for slash commands
        assert bot.intents.guilds is True

    @pytest.mark.asyncio
    async def test_setup_hook_with_config(self, base_config: TGraphBotConfig) -> None:
        """Test setup_hook with valid configuration."""
        config_manager = create_config_manager_with_config(base_config)
        
        bot = TGraphBot(config_manager)
        
        # Mock the setup_i18n (synchronous), load_extensions (async), and tree.sync functions
        async with async_mock_context("src.tgraph_bot.main.setup_i18n", new_callable=MagicMock) as mock_setup_i18n, \
                   async_mock_context("src.tgraph_bot.main.load_extensions") as mock_load_extensions:
            
            # Mock the command tree sync
            with patch.object(bot.tree, 'sync', new_callable=AsyncMock) as mock_sync, \
                 patch.object(bot, 'setup_background_tasks', new_callable=AsyncMock) as mock_setup_tasks:
                
                # Mock sync to return some synced commands
                mock_sync.return_value = [MagicMock(), MagicMock(), MagicMock()]  # 3 synced commands
                
                await bot.setup_hook()
                
                # Verify i18n setup was called with correct language
                mock_setup_i18n.assert_called_once_with(base_config.LANGUAGE)
                
                # Verify extensions loading was called with bot instance
                mock_load_extensions.assert_called_once_with(bot)
                
                # Verify command sync was called
                mock_sync.assert_called_once()
                
                # Verify background tasks setup was called
                mock_setup_tasks.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_hook_no_config(self) -> None:
        """Test setup_hook when no configuration is loaded."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Mock the setup_i18n (synchronous), load_extensions (async), and tree.sync functions
        async with async_mock_context("src.tgraph_bot.main.setup_i18n", new_callable=MagicMock) as mock_setup_i18n, \
                   async_mock_context("src.tgraph_bot.main.load_extensions") as mock_load_extensions:
            
            # Mock the command tree sync (shouldn't be called due to early failure)
            with patch.object(bot.tree, 'sync', new_callable=AsyncMock) as mock_sync:

                # Should raise RuntimeError when no config is available
                with pytest.raises(RuntimeError, match="Bot setup failed: No configuration available"):
                    await bot.setup_hook()

                # Verify i18n setup and extensions loading were not called
                mock_setup_i18n.assert_not_called()
                mock_load_extensions.assert_not_called()
                
                # Verify command sync was not called due to early failure
                mock_sync.assert_not_called()

    @pytest.mark.asyncio
    async def test_setup_hook_command_sync_failure(self, base_config: TGraphBotConfig) -> None:
        """Test setup_hook when command sync fails but continues gracefully."""
        config_manager = create_config_manager_with_config(base_config)
        
        bot = TGraphBot(config_manager)
        
        # Mock the setup_i18n (synchronous) and load_extensions (async) functions
        async with async_mock_context("src.tgraph_bot.main.setup_i18n", new_callable=MagicMock) as mock_setup_i18n, \
                   async_mock_context("src.tgraph_bot.main.load_extensions") as mock_load_extensions:
            
            # Mock the command tree sync to fail
            with patch.object(bot.tree, 'sync', new_callable=AsyncMock) as mock_sync, \
                 patch.object(bot, 'setup_background_tasks', new_callable=AsyncMock) as mock_setup_tasks:
                
                # Make sync raise an exception
                mock_sync.side_effect = discord.HTTPException(response=MagicMock(), message="Sync failed")
                
                # Should complete successfully despite sync failure
                await bot.setup_hook()
                
                # Verify other steps still completed
                mock_setup_i18n.assert_called_once_with(base_config.LANGUAGE)
                mock_load_extensions.assert_called_once_with(bot)
                mock_sync.assert_called_once()
                mock_setup_tasks.assert_called_once()

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
        from src.tgraph_bot.bot.extensions import ExtensionStatus
        mock_results = [
            ExtensionStatus("bot.commands.about", True),
            ExtensionStatus("bot.commands.broken", False, "Import error"),
        ]

        with patch("src.tgraph_bot.main.setup_i18n"), \
             patch("src.tgraph_bot.main.load_extensions", return_value=mock_results):
            
            # Mock the command tree sync and background tasks
            with patch.object(bot.tree, 'sync', new_callable=AsyncMock) as mock_sync, \
                 patch.object(bot, 'setup_background_tasks', new_callable=AsyncMock):
                
                # Mock sync to return successful commands
                mock_sync.return_value = [MagicMock()]  # 1 synced command
                
                await bot.setup_hook()
                
                # Should complete successfully even with some failed extensions
                # Verify command sync was still called
                mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_ready_with_user(self) -> None:
        """Test on_ready event handler when user is available."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Create a mock user object using utility
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

        # Mock the parent close method using async utility
        async with async_mock_context("discord.ext.commands.Bot.close") as mock_close:
            await bot.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_discord_connection_intents(self) -> None:
        """Test that Discord intents are properly configured for bot functionality."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)

        # Verify required intents are enabled
        assert bot.intents.message_content is False  # Privileged intent not required for slash commands
        assert bot.intents.guilds is True, "Guilds intent required for server information"

        # Verify bot configuration
        assert bot.command_prefix == "!"  # pyright: ignore[reportUnknownMemberType]
        assert bot.help_command is None, "Custom help command should be used"

    @pytest.mark.asyncio
    async def test_discord_bot_connection_setup(self, comprehensive_config: TGraphBotConfig) -> None:
        """Test that the bot is properly configured for Discord connection."""
        config_manager = create_config_manager_with_config(comprehensive_config)

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

        # Verify bot is configured to use Discord's permissions
        # (This is a structural test - specific permission testing would be in command tests)
        assert hasattr(bot, 'tree'), "Bot should have application command tree"


class TestMainFunction:
    """Test cases for the main() function."""

    @pytest.mark.asyncio
    async def test_main_no_config_file(self) -> None:
        """Test main() when config.yml doesn't exist."""
        from src.tgraph_bot.utils.cli.args import ParsedArgs

        # Mock CLI args
        mock_args = ParsedArgs(
            config_file=Path("data/config/config.yml"),
            data_folder=Path("data"),
            log_folder=Path("data/logs")
        )

        with patch("src.tgraph_bot.main.get_parsed_args", return_value=mock_args), \
             patch("pathlib.Path.exists", return_value=False), \
             patch("sys.exit") as mock_exit:

            await main()
            # sys.exit should be called with 1, but we don't care how many times
            # since the function may call it multiple times in error handling
            mock_exit.assert_called_with(1)

    @pytest.mark.asyncio
    async def test_main_with_config_file(self) -> None:
        """Test main() with valid config file."""
        from src.tgraph_bot.utils.cli.args import ParsedArgs

        # Create a mock config
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )

        # Mock CLI args
        mock_args = ParsedArgs(
            config_file=Path("data/config/config.yml"),
            data_folder=Path("data"),
            log_folder=Path("data/logs")
        )

        with patch("src.tgraph_bot.main.get_parsed_args", return_value=mock_args), \
             patch("pathlib.Path.exists", return_value=True), \
             patch.object(ConfigManager, "load_config", return_value=mock_config):
            
            async with async_mock_context("src.tgraph_bot.main.TGraphBot.start") as mock_start:
                await main()
                mock_start.assert_called_once_with("test_token")

    @pytest.mark.asyncio
    async def test_main_keyboard_interrupt(self) -> None:
        """Test main() handling KeyboardInterrupt."""
        from src.tgraph_bot.utils.cli.args import ParsedArgs

        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )

        # Mock CLI args
        mock_args = ParsedArgs(
            config_file=Path("data/config/config.yml"),
            data_folder=Path("data"),
            log_folder=Path("data/logs")
        )

        with patch("src.tgraph_bot.main.get_parsed_args", return_value=mock_args), \
             patch("pathlib.Path.exists", return_value=True), \
             patch.object(ConfigManager, "load_config", return_value=mock_config):
            
            async with async_mock_context("src.tgraph_bot.main.TGraphBot.start", side_effect=KeyboardInterrupt) as _mock_start, \
                       async_mock_context("src.tgraph_bot.main.TGraphBot.close") as mock_close:
                
                await main()
                mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_exception(self) -> None:
        """Test main() handling general exceptions."""
        from src.tgraph_bot.utils.cli.args import ParsedArgs

        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )

        # Mock CLI args
        mock_args = ParsedArgs(
            config_file=Path("data/config/config.yml"),
            data_folder=Path("data"),
            log_folder=Path("data/logs")
        )

        with patch("src.tgraph_bot.main.get_parsed_args", return_value=mock_args), \
             patch("pathlib.Path.exists", return_value=True), \
             patch.object(ConfigManager, "load_config", return_value=mock_config), \
             patch("sys.exit") as mock_exit:
            
            async with async_mock_context("src.tgraph_bot.main.TGraphBot.start", side_effect=Exception("Test error")) as _mock_start, \
                       async_mock_context("src.tgraph_bot.main.TGraphBot.close") as mock_close:
                
                await main()
                mock_close.assert_called_once()
                mock_exit.assert_called_once_with(1)


class TestEnhancedErrorHandling(AsyncTestBase):
    """Test cases for enhanced error handling functionality using async test base."""

    @override
    def setup_method(self) -> None:
        """Set up test method with async utilities."""
        super().setup_method()

    @override
    def teardown_method(self) -> None:
        """Clean up after test method."""
        super().teardown_method()

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

        async with async_mock_context("discord.ext.commands.Bot.close") as mock_parent_close:
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

        async with async_mock_context("discord.ext.commands.Bot.close") as mock_parent_close:
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
        from src.tgraph_bot.utils.cli.paths import get_path_config

        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up PathConfig to use temp directory
            path_config = get_path_config()
            logs_dir = Path(temp_dir) / "data" / "logs"
            path_config.set_paths(
                config_file=Path(temp_dir) / "data" / "config" / "config.yml",
                data_folder=Path(temp_dir) / "data",
                log_folder=logs_dir
            )

            setup_logging()

            assert logs_dir.exists()
            assert logs_dir.is_dir()

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
        
        # Mock bot.close as an async function
        bot.close = AsyncMock()

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
        from src.tgraph_bot.utils.cli.args import ParsedArgs

        # Mock CLI args
        mock_args = ParsedArgs(
            config_file=Path("data/config/config.yml"),
            data_folder=Path("data"),
            log_folder=Path("data/logs")
        )

        with patch("src.tgraph_bot.main.get_parsed_args", return_value=mock_args), \
             patch("src.tgraph_bot.main.setup_logging") as mock_setup_logging, \
             patch("pathlib.Path.exists", return_value=False), \
             patch("sys.exit"):

            # Mock UpdateTracker to prevent background task issues
            mock_update_tracker = MagicMock()
            mock_update_tracker.stop_scheduler = AsyncMock()
            
            with patch("src.tgraph_bot.bot.update_tracker.UpdateTracker", return_value=mock_update_tracker):
                # Create a proper mock for TGraphBot with async close method
                mock_bot_class = MagicMock()
                mock_bot_instance = MagicMock()
                mock_bot_instance.close = AsyncMock()
                # Properly type the is_shutting_down method
                mock_is_shutting_down = MagicMock(return_value=False)
                mock_bot_instance.is_shutting_down = mock_is_shutting_down
                mock_bot_instance.update_tracker = mock_update_tracker
                mock_bot_class.return_value = mock_bot_instance
                
                with patch("src.tgraph_bot.main.TGraphBot", mock_bot_class):
                    await main()
                    mock_setup_logging.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_with_signal_handlers(self) -> None:
        """Test that main() sets up signal handlers."""
        from src.tgraph_bot.utils.cli.args import ParsedArgs

        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )

        # Mock CLI args
        mock_args = ParsedArgs(
            config_file=Path("data/config/config.yml"),
            data_folder=Path("data"),
            log_folder=Path("data/logs")
        )

        with patch("src.tgraph_bot.main.get_parsed_args", return_value=mock_args), \
             patch("src.tgraph_bot.main.setup_logging"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch.object(ConfigManager, "load_config", return_value=mock_config), \
             patch("src.tgraph_bot.main.setup_signal_handlers") as mock_setup_signals:

            # Create a proper mock for TGraphBot with async methods
            mock_bot_class = MagicMock()
            mock_bot_instance = MagicMock()
            mock_bot_instance.start = AsyncMock()
            mock_bot_instance.close = AsyncMock()
            # Properly type the is_shutting_down method
            mock_is_shutting_down = MagicMock(return_value=False)
            mock_bot_instance.is_shutting_down = mock_is_shutting_down
            mock_bot_class.return_value = mock_bot_instance
            
            with patch("src.tgraph_bot.main.TGraphBot", mock_bot_class):
                await main()
                mock_setup_signals.assert_called_once()
                # Mock's assert methods aren't properly typed in unittest.mock
                mock_bot_instance.start.assert_called_once_with("test_token")  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_main_discord_login_failure(self) -> None:
        """Test main() handling Discord login failures."""
        import discord
        from src.tgraph_bot.utils.cli.args import ParsedArgs

        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="invalid_token",
            CHANNEL_ID=123456789,
        )

        # Mock CLI args
        mock_args = ParsedArgs(
            config_file=Path("data/config/config.yml"),
            data_folder=Path("data"),
            log_folder=Path("data/logs")
        )

        with patch("src.tgraph_bot.main.get_parsed_args", return_value=mock_args), \
             patch("src.tgraph_bot.main.setup_logging"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch.object(ConfigManager, "load_config", return_value=mock_config), \
             patch("src.tgraph_bot.main.setup_signal_handlers"), \
             patch.object(TGraphBot, "start", new_callable=AsyncMock,
                         side_effect=discord.LoginFailure("Invalid token")), \
             patch("sys.exit") as mock_exit:

            await main()
            mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_main_discord_http_exception(self) -> None:
        """Test main() handling Discord HTTP exceptions."""
        import discord
        from src.tgraph_bot.utils.cli.args import ParsedArgs

        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )

        # Mock CLI args
        mock_args = ParsedArgs(
            config_file=Path("data/config/config.yml"),
            data_folder=Path("data"),
            log_folder=Path("data/logs")
        )

        with patch("src.tgraph_bot.main.get_parsed_args", return_value=mock_args), \
             patch("src.tgraph_bot.main.setup_logging"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch.object(ConfigManager, "load_config", return_value=mock_config), \
             patch("src.tgraph_bot.main.setup_signal_handlers"), \
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

        with patch("src.tgraph_bot.main.setup_logging"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch.object(ConfigManager, "load_config", return_value=mock_config), \
             patch("src.tgraph_bot.main.setup_signal_handlers"), \
             patch.object(TGraphBot, "start", new_callable=AsyncMock,
                         side_effect=Exception("Test error")), \
             patch.object(TGraphBot, "close", new_callable=AsyncMock) as mock_close, \
             patch.object(TGraphBot, "is_shutting_down", return_value=False), \
             patch("sys.exit"):

            await main()
            # Bot should be closed in finally block
            mock_close.assert_called()


class TestAutomatedGraphUpdate(AsyncTestBase):
    """Test cases for the automated graph update functionality."""

    @override
    def setup_method(self) -> None:
        """Set up test method with async utilities."""
        super().setup_method()

    @override
    def teardown_method(self) -> None:
        """Clean up after test method."""
        super().teardown_method()

    @pytest.mark.asyncio
    async def test_automated_graph_update_success(self, base_config: TGraphBotConfig) -> None:
        """Test successful automated graph update with new 3-step process."""
        config_manager = create_config_manager_with_config(base_config)
        bot = TGraphBot(config_manager)
        
        # Create mock TextChannel - proper Discord mock
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.name = "test-channel"
        
        # Mock bot user
        mock_user = MagicMock()
        mock_user.id = 123456789
        
        with patch.object(bot, 'get_channel', return_value=mock_channel), \
             patch.object(type(bot), 'user', new_callable=lambda: mock_user), \
             patch.object(bot, '_cleanup_bot_messages', new_callable=AsyncMock) as mock_cleanup, \
             patch('src.tgraph_bot.graphs.graph_manager.GraphManager') as mock_graph_manager_class, \
             patch.object(bot, '_post_graphs_to_channel', new_callable=AsyncMock, return_value=3) as mock_post:
            
            # Setup GraphManager mock
            mock_graph_manager = AsyncMock()
            mock_graph_manager.generate_all_graphs.return_value = ['graph1.png', 'graph2.png', 'graph3.png']  # pyright: ignore[reportAny]
            mock_graph_manager_class.return_value.__aenter__.return_value = mock_graph_manager  # pyright: ignore[reportAny]
            mock_graph_manager_class.return_value.__aexit__.return_value = None  # pyright: ignore[reportAny]
            
            # Testing protected method _automated_graph_update is intentional - it's a key internal method
            await bot._automated_graph_update()  # pyright: ignore[reportPrivateUsage]
            
            # Verify the 3-step process: Cleanup → Generate → Post
            mock_cleanup.assert_called_once_with(mock_channel)
            mock_graph_manager.generate_all_graphs.assert_called_once_with(  # pyright: ignore[reportAny]
                max_retries=3,
                timeout_seconds=300.0
            )
            mock_post.assert_called_once_with(mock_channel, ['graph1.png', 'graph2.png', 'graph3.png'])

    @pytest.mark.asyncio
    async def test_automated_graph_update_channel_not_found(self, base_config: TGraphBotConfig) -> None:
        """Test automated graph update when channel is not found."""
        config_manager = create_config_manager_with_config(base_config)
        bot = TGraphBot(config_manager)
        
        with patch.object(bot, 'get_channel', return_value=None), \
             patch.object(bot, '_cleanup_bot_messages', new_callable=AsyncMock) as mock_cleanup, \
             patch('src.tgraph_bot.graphs.graph_manager.GraphManager') as mock_graph_manager_class:
            
            # Testing protected method _automated_graph_update is intentional - it's a key internal method
            await bot._automated_graph_update()  # pyright: ignore[reportPrivateUsage]
            
            # Should not proceed with cleanup or graph generation
            mock_cleanup.assert_not_called()
            mock_graph_manager_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_automated_graph_update_wrong_channel_type(self, base_config: TGraphBotConfig) -> None:
        """Test automated graph update when channel is not a text channel."""
        config_manager = create_config_manager_with_config(base_config)
        bot = TGraphBot(config_manager)
        
        # Create a voice channel mock (not a TextChannel)
        mock_channel = MagicMock(spec=discord.VoiceChannel)
        mock_channel.name = "voice-channel"
        
        with patch.object(bot, 'get_channel', return_value=mock_channel), \
             patch.object(bot, '_cleanup_bot_messages', new_callable=AsyncMock) as mock_cleanup:
            
            # Testing protected method _automated_graph_update is intentional - it's a key internal method
            await bot._automated_graph_update()  # pyright: ignore[reportPrivateUsage]
            
            # Should not proceed with cleanup or graph generation
            mock_cleanup.assert_not_called()

    @pytest.mark.asyncio
    async def test_automated_graph_update_cleanup_error(self, base_config: TGraphBotConfig) -> None:
        """Test automated graph update when cleanup fails."""
        config_manager = create_config_manager_with_config(base_config)
        bot = TGraphBot(config_manager)
        
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.name = "test-channel"
        mock_user = MagicMock()
        mock_user.id = 123456789
        
        with patch.object(bot, 'get_channel', return_value=mock_channel), \
             patch.object(type(bot), 'user', new_callable=lambda: mock_user), \
             patch.object(bot, '_cleanup_bot_messages', new_callable=AsyncMock, side_effect=Exception("Cleanup failed")) as mock_cleanup:
            
            # Should raise the cleanup error
            with pytest.raises(Exception, match="Cleanup failed"):
                # Testing protected method _automated_graph_update is intentional - it's a key internal method
                await bot._automated_graph_update()  # pyright: ignore[reportPrivateUsage]
            
            mock_cleanup.assert_called_once_with(mock_channel)

    @pytest.mark.asyncio
    async def test_automated_graph_update_no_graphs_generated(self, base_config: TGraphBotConfig) -> None:
        """Test automated graph update when no graphs are generated."""
        config_manager = create_config_manager_with_config(base_config)
        bot = TGraphBot(config_manager)
        
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.name = "test-channel"
        mock_user = MagicMock()
        mock_user.id = 123456789
        
        with patch.object(bot, 'get_channel', return_value=mock_channel), \
             patch.object(type(bot), 'user', new_callable=lambda: mock_user), \
             patch.object(bot, '_cleanup_bot_messages', new_callable=AsyncMock) as mock_cleanup, \
             patch('src.tgraph_bot.graphs.graph_manager.GraphManager') as mock_graph_manager_class, \
             patch.object(bot, '_post_graphs_to_channel', new_callable=AsyncMock) as mock_post:
            
            # Setup GraphManager mock to return empty list
            mock_graph_manager = AsyncMock()
            mock_graph_manager.generate_all_graphs = AsyncMock(return_value=[])
            mock_graph_manager_class.return_value.__aenter__ = AsyncMock(return_value=mock_graph_manager)  # pyright: ignore[reportAny]
            mock_graph_manager_class.return_value.__aexit__ = AsyncMock(return_value=None)  # pyright: ignore[reportAny]
            
            # Testing protected method _automated_graph_update is intentional - it's a key internal method
            await bot._automated_graph_update()  # pyright: ignore[reportPrivateUsage]
            
            # Should cleanup and attempt generation, but not post
            mock_cleanup.assert_called_once_with(mock_channel)
            mock_graph_manager.generate_all_graphs.assert_called_once()  # pyright: ignore[reportAny]
            mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_automated_graph_update_graph_generation_error(self, base_config: TGraphBotConfig) -> None:
        """Test automated graph update when graph generation fails."""
        config_manager = create_config_manager_with_config(base_config)
        bot = TGraphBot(config_manager)
        
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.name = "test-channel"
        mock_user = MagicMock()
        mock_user.id = 123456789
        
        with patch.object(bot, 'get_channel', return_value=mock_channel), \
             patch.object(type(bot), 'user', new_callable=lambda: mock_user), \
             patch.object(bot, '_cleanup_bot_messages', new_callable=AsyncMock) as mock_cleanup, \
             patch('src.tgraph_bot.graphs.graph_manager.GraphManager') as mock_graph_manager_class:
            
            # Setup GraphManager mock to raise exception
            mock_graph_manager = AsyncMock()
            mock_graph_manager.generate_all_graphs = AsyncMock(side_effect=Exception("Graph generation failed"))
            mock_graph_manager_class.return_value.__aenter__ = AsyncMock(return_value=mock_graph_manager)  # pyright: ignore[reportAny]
            mock_graph_manager_class.return_value.__aexit__ = AsyncMock(return_value=None)  # pyright: ignore[reportAny]
            
            # Should raise the graph generation error
            with pytest.raises(Exception, match="Graph generation failed"):
                # Testing protected method _automated_graph_update is intentional - it's a key internal method
                await bot._automated_graph_update()  # pyright: ignore[reportPrivateUsage]
            
            # Should have cleaned up first
            mock_cleanup.assert_called_once_with(mock_channel)


class TestCleanupBotMessages(AsyncTestBase):
    """Test cases for the cleanup bot messages functionality."""

    @override
    def setup_method(self) -> None:
        """Set up test method with async utilities."""
        super().setup_method()

    @override
    def teardown_method(self) -> None:
        """Clean up after test method."""
        super().teardown_method()

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_success(self) -> None:
        """Test successful cleanup of bot messages."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)
        
        # Create mock channel and messages
        mock_channel = MagicMock()
        mock_channel.name = "test-channel"
        
        # Create mock bot user
        mock_bot_user = MagicMock()
        mock_bot_user.id = 123456789
        
        # Create mock guild and permissions
        mock_guild_member = MagicMock()
        mock_guild_member.permissions_for.return_value.manage_messages = True  # pyright: ignore[reportAny]
        mock_channel.guild.me = mock_guild_member  # pyright: ignore[reportAny]
        
        # Create mock messages - some from bot, some from users
        mock_bot_message1 = MagicMock()
        mock_bot_message1.author.id = 123456789  # Bot's message  # pyright: ignore[reportAny]
        mock_bot_message1.id = "msg1"
        mock_bot_message1.delete = AsyncMock()
        
        mock_bot_message2 = MagicMock()
        mock_bot_message2.author.id = 123456789  # Bot's message  # pyright: ignore[reportAny]
        mock_bot_message2.id = "msg2"
        mock_bot_message2.delete = AsyncMock()
        
        mock_user_message = MagicMock()
        mock_user_message.author.id = 987654321  # User's message  # pyright: ignore[reportAny]
        mock_user_message.id = "user_msg"
        mock_user_message.delete = AsyncMock()
        
        # Mock the async iterator for channel history
        async def mock_history(*args: object, **kwargs: object) -> AsyncIterator[MagicMock]:  # pyright: ignore[reportUnusedParameter]
            for message in [mock_bot_message1, mock_user_message, mock_bot_message2]:
                yield message
        
        mock_channel.history = mock_history
        
        with patch.object(type(bot), 'user', new_callable=lambda: mock_bot_user):
            # Testing protected method _cleanup_bot_messages is intentional - it's a key internal method
            await bot._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]
            
            # Should only delete bot's messages
            mock_bot_message1.delete.assert_called_once()  # pyright: ignore[reportAny]
            mock_bot_message2.delete.assert_called_once()  # pyright: ignore[reportAny]
            mock_user_message.delete.assert_not_called()  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_no_manage_permissions(self) -> None:
        """Test cleanup when bot lacks manage messages permission."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)
        
        mock_channel = MagicMock()
        mock_channel.name = "test-channel"
        
        mock_bot_user = MagicMock()
        mock_bot_user.id = 123456789
        
        # Mock guild member without manage_messages permission
        mock_guild_member = MagicMock()
        mock_guild_member.permissions_for.return_value.manage_messages = False  # pyright: ignore[reportAny]
        mock_channel.guild.me = mock_guild_member  # pyright: ignore[reportAny]
        
        # Create mock bot message
        mock_bot_message = MagicMock()
        mock_bot_message.author.id = 123456789  # pyright: ignore[reportAny]
        mock_bot_message.id = "msg1"
        mock_bot_message.delete = AsyncMock()
        
        async def mock_history(*args: object, **kwargs: object) -> AsyncIterator[MagicMock]:  # pyright: ignore[reportUnusedParameter]
            for message in [mock_bot_message]:
                yield message
        
        mock_channel.history = mock_history
        
        with patch.object(type(bot), 'user', new_callable=lambda: mock_bot_user):
            # Testing protected method _cleanup_bot_messages is intentional - it's a key internal method
            await bot._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]
            
            # Should still attempt to delete bot's own messages
            mock_bot_message.delete.assert_called_once()  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_forbidden_error(self) -> None:
        """Test cleanup when delete operation is forbidden."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)
        
        mock_channel = MagicMock()
        mock_channel.name = "test-channel"
        
        mock_bot_user = MagicMock()
        mock_bot_user.id = 123456789
        
        mock_guild_member = MagicMock()
        mock_guild_member.permissions_for.return_value.manage_messages = True  # pyright: ignore[reportAny]
        mock_channel.guild.me = mock_guild_member  # pyright: ignore[reportAny]
        
        # Create mock bot message that raises Forbidden when deleted
        mock_bot_message = MagicMock()
        mock_bot_message.author.id = 123456789  # pyright: ignore[reportAny]
        mock_bot_message.id = "msg1"
        mock_bot_message.delete = AsyncMock(side_effect=discord.Forbidden(response=MagicMock(), message="Forbidden"))
        
        async def mock_history(*args: object, **kwargs: object) -> AsyncIterator[MagicMock]:  # pyright: ignore[reportUnusedParameter]
            for message in [mock_bot_message]:
                yield message
        
        mock_channel.history = mock_history
        
        with patch.object(type(bot), 'user', new_callable=lambda: mock_bot_user):
            # Should not raise exception, just log warning
            # Testing protected method _cleanup_bot_messages is intentional - it's a key internal method
            await bot._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]
            
            mock_bot_message.delete.assert_called_once()  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_rate_limiting(self) -> None:
        """Test cleanup with rate limiting (429 error)."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)
        
        mock_channel = MagicMock()
        mock_channel.name = "test-channel"
        
        mock_bot_user = MagicMock()
        mock_bot_user.id = 123456789
        
        mock_guild_member = MagicMock()
        mock_guild_member.permissions_for.return_value.manage_messages = True  # pyright: ignore[reportAny]
        mock_channel.guild.me = mock_guild_member  # pyright: ignore[reportAny]
        
        # Create mock bot message that raises rate limit error
        mock_rate_limit_error = discord.HTTPException(response=MagicMock(), message="Rate limited")
        mock_rate_limit_error.status = 429
        # Add retry_after attribute to the mock
        setattr(mock_rate_limit_error, 'retry_after', 2.0)
        
        mock_bot_message = MagicMock()
        mock_bot_message.author.id = 123456789  # pyright: ignore[reportAny]
        mock_bot_message.id = "msg1"
        mock_bot_message.delete = AsyncMock(side_effect=mock_rate_limit_error)
        
        async def mock_history(*args: object, **kwargs: object) -> AsyncIterator[MagicMock]:  # pyright: ignore[reportUnusedParameter]
            for message in [mock_bot_message]:
                yield message
        
        mock_channel.history = mock_history
        
        with patch.object(type(bot), 'user', new_callable=lambda: mock_bot_user), \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            # Testing protected method _cleanup_bot_messages is intentional - it's a key internal method
            await bot._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]
            
            mock_bot_message.delete.assert_called_once()  # pyright: ignore[reportAny]
            # Should sleep for retry_after duration
            mock_sleep.assert_called_with(2.0)

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_not_found_error(self) -> None:
        """Test cleanup when message is already deleted (NotFound error)."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)
        
        mock_channel = MagicMock()
        mock_channel.name = "test-channel"
        
        mock_bot_user = MagicMock()
        mock_bot_user.id = 123456789
        
        mock_guild_member = MagicMock()
        mock_guild_member.permissions_for.return_value.manage_messages = True  # pyright: ignore[reportAny]
        mock_channel.guild.me = mock_guild_member  # pyright: ignore[reportAny]
        
        # Create mock bot message that raises NotFound when deleted
        mock_bot_message = MagicMock()
        mock_bot_message.author.id = 123456789  # pyright: ignore[reportAny]
        mock_bot_message.id = "msg1"

        # Create AsyncMock that properly raises NotFound
        delete_mock = AsyncMock()
        delete_mock.side_effect = discord.NotFound(response=MagicMock(), message="Not found")
        mock_bot_message.delete = delete_mock
        
        async def mock_history(*args: object, **kwargs: object) -> AsyncIterator[MagicMock]:  # pyright: ignore[reportUnusedParameter]
            for message in [mock_bot_message]:
                yield message
        
        mock_channel.history = mock_history
        
        with patch.object(type(bot), 'user', new_callable=lambda: mock_bot_user):
            # Should not raise exception for NotFound
            # Testing protected method _cleanup_bot_messages is intentional - it's a key internal method
            await bot._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]

            # Verify the delete method was called
            delete_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_rate_limit_protection(self) -> None:
        """Test cleanup with automatic rate limit protection."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)
        
        mock_channel = MagicMock()
        mock_channel.name = "test-channel"
        
        mock_bot_user = MagicMock()
        mock_bot_user.id = 123456789
        
        mock_guild_member = MagicMock()
        mock_guild_member.permissions_for.return_value.manage_messages = True  # pyright: ignore[reportAny]
        mock_channel.guild.me = mock_guild_member  # pyright: ignore[reportAny]
        
        # Create multiple bot messages to test rate limiting
        mock_messages: list[MagicMock] = []
        for i in range(7):  # More than 5 to trigger rate limit protection
            mock_message = MagicMock()
            mock_message.author.id = 123456789  # pyright: ignore[reportAny]
            mock_message.id = f"msg{i}"
            mock_message.delete = AsyncMock()
            mock_messages.append(mock_message)
        
        async def mock_history(*args: object, **kwargs: object) -> AsyncIterator[MagicMock]:  # pyright: ignore[reportUnusedParameter]
            for message in mock_messages:
                yield message
        
        mock_channel.history = mock_history
        
        with patch.object(type(bot), 'user', new_callable=lambda: mock_bot_user), \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            # Testing protected method _cleanup_bot_messages is intentional - it's a key internal method
            await bot._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]
            
            # All messages should be deleted
            for mock_message in mock_messages:
                mock_message.delete.assert_called_once()  # pyright: ignore[reportAny]
            
            # Should sleep after every 5 deletions (rate limit protection)
            mock_sleep.assert_called_with(1.0)

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_general_exception(self) -> None:
        """Test cleanup when a general exception occurs."""
        config_manager = ConfigManager()
        bot = TGraphBot(config_manager)
        
        mock_channel = MagicMock()
        mock_channel.name = "test-channel"
        
        mock_bot_user = MagicMock()
        mock_bot_user.id = 123456789
        
        # Mock history to raise an exception
        mock_channel.history = MagicMock(side_effect=Exception("Database error"))
        
        with patch.object(type(bot), 'user', new_callable=lambda: mock_bot_user):
            # Should raise the general exception
            with pytest.raises(Exception, match="Database error"):
                # Testing protected method _cleanup_bot_messages is intentional - it's a key internal method
                await bot._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]
