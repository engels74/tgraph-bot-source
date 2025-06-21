"""
Tests for the bot startup sequence module.

This module tests the startup sequence functionality including:
- Message cleanup
- Initial graph posting
- Scheduler state management
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from collections.abc import AsyncGenerator

import discord
import pytest

from bot.startup_sequence import StartupSequence
from config.manager import ConfigManager
from config.schema import TGraphBotConfig


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create a mock bot instance for testing."""
    bot = MagicMock()
    bot.user = MagicMock()
    bot.user.id = 123456789
    bot.config_manager = MagicMock(spec=ConfigManager)
    bot.update_tracker = MagicMock()
    bot._shutdown_event = asyncio.Event()
    bot.get_channel = MagicMock()
    return bot


@pytest.fixture
def mock_config() -> TGraphBotConfig:
    """Create a mock configuration."""
    config = MagicMock(spec=TGraphBotConfig)
    config.CHANNEL_ID = 987654321
    return config


@pytest.fixture
def startup_sequence(mock_bot: MagicMock) -> StartupSequence:
    """Create a StartupSequence instance for testing."""
    return StartupSequence(mock_bot)


class TestStartupSequence:
    """Test the StartupSequence class."""
    
    @pytest.mark.asyncio
    async def test_startup_sequence_initialization(self, startup_sequence: StartupSequence, mock_bot: MagicMock) -> None:
        """Test that StartupSequence initializes correctly."""
        assert startup_sequence.bot == mock_bot
        assert startup_sequence.cleanup_completed is False
        assert startup_sequence.initial_post_completed is False
    
    @pytest.mark.asyncio
    async def test_cleanup_previous_messages_success(self, startup_sequence: StartupSequence, mock_bot: MagicMock, mock_config: TGraphBotConfig) -> None:
        """Test successful message cleanup."""
        # Setup mocks
        mock_bot.config_manager.get_current_config.return_value = mock_config
        
        # Create mock channel
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_guild = MagicMock()
        mock_member = MagicMock()
        mock_permissions = MagicMock()
        mock_permissions.manage_messages = True
        
        mock_channel.guild = mock_guild
        mock_guild.me = mock_member
        mock_channel.permissions_for.return_value = mock_permissions
        
        # Create mock messages
        bot_message = MagicMock()
        bot_message.author.id = mock_bot.user.id
        bot_message.delete = AsyncMock()
        
        other_message = MagicMock()
        other_message.author.id = 999999999  # Different user
        
        # Mock history method with proper typing
        async def mock_history(limit: int | None = None) -> AsyncGenerator[MagicMock, None]:  # pyright: ignore[reportUnusedParameter]
            for msg in [bot_message, other_message]:
                yield msg
        
        mock_channel.history = mock_history
        mock_bot.get_channel.return_value = mock_channel
        
        # Run cleanup
        await startup_sequence.cleanup_previous_messages()
        
        # Verify
        assert startup_sequence.cleanup_completed is True
        bot_message.delete.assert_called_once()
        mock_bot.get_channel.assert_called_once_with(mock_config.CHANNEL_ID)
    
    @pytest.mark.asyncio
    async def test_cleanup_previous_messages_no_channel(self, startup_sequence: StartupSequence, mock_bot: MagicMock, mock_config: TGraphBotConfig) -> None:
        """Test cleanup when channel is not found."""
        mock_bot.config_manager.get_current_config.return_value = mock_config
        mock_bot.get_channel.return_value = None
        
        await startup_sequence.cleanup_previous_messages()
        
        # Should still mark as completed even if channel not found
        assert startup_sequence.cleanup_completed is False
    
    @pytest.mark.asyncio
    async def test_cleanup_handles_rate_limits(self, startup_sequence: StartupSequence, mock_bot: MagicMock, mock_config: TGraphBotConfig) -> None:
        """Test that cleanup handles Discord rate limits properly."""
        # Setup mocks
        mock_bot.config_manager.get_current_config.return_value = mock_config
        
        # Create mock channel
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_guild = MagicMock()
        mock_member = MagicMock()
        mock_permissions = MagicMock()
        mock_permissions.manage_messages = True
        
        mock_channel.guild = mock_guild
        mock_guild.me = mock_member
        mock_channel.permissions_for.return_value = mock_permissions
        
        # Create mock message with rate limit error
        bot_message = MagicMock()
        bot_message.author.id = mock_bot.user.id
        
        # Simulate rate limit error
        mock_response = MagicMock()
        mock_response.status = 429
        rate_limit_error = discord.HTTPException(mock_response, "rate limited")
        # Use setattr to add retry_after for testing
        setattr(rate_limit_error, 'retry_after', 0.1)  # Short delay for testing
        bot_message.delete = AsyncMock(side_effect=rate_limit_error)
        
        # Mock history with proper typing
        async def mock_history(limit: int | None = None) -> AsyncGenerator[MagicMock, None]:  # pyright: ignore[reportUnusedParameter]
            yield bot_message
        
        mock_channel.history = mock_history
        mock_bot.get_channel.return_value = mock_channel
        
        # Run cleanup
        await startup_sequence.cleanup_previous_messages()
        
        # Should handle the rate limit gracefully
        bot_message.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_post_initial_graphs_success(self, startup_sequence: StartupSequence, mock_bot: MagicMock, mock_config: TGraphBotConfig) -> None:
        """Test successful initial graph posting."""
        # Setup mocks
        mock_bot.config_manager.get_current_config.return_value = mock_config
        
        # Create mock channel
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.send = AsyncMock()
        mock_bot.get_channel.return_value = mock_channel
        
        # Mock GraphManager
        with patch('bot.startup_sequence.GraphManager') as mock_graph_manager_class:
            mock_graph_manager = AsyncMock()
            mock_graph_manager.__aenter__.return_value = mock_graph_manager
            mock_graph_manager.generate_all_graphs.return_value = [
                '/tmp/graph1.png',
                '/tmp/graph2.png'
            ]
            mock_graph_manager_class.return_value = mock_graph_manager
            
            # Mock file utilities
            with patch('bot.startup_sequence.validate_file_for_discord') as mock_validate:
                with patch('bot.startup_sequence.create_discord_file_safe') as mock_create_file:
                    with patch('bot.startup_sequence.create_graph_specific_embed') as mock_create_embed:
                        # Setup file validation
                        mock_validation = MagicMock()
                        mock_validation.valid = True
                        mock_validate.return_value = mock_validation
                        
                        # Setup Discord file creation
                        mock_create_file.return_value = MagicMock(spec=discord.File)
                        
                        # Setup embed creation
                        mock_create_embed.return_value = MagicMock(spec=discord.Embed)
                        
                        # Create test files
                        with patch('pathlib.Path.exists', return_value=True):
                            await startup_sequence.post_initial_graphs()
        
        # Verify
        assert startup_sequence.initial_post_completed is True
        assert mock_channel.send.call_count == 2  # Two graphs posted
    
    @pytest.mark.asyncio
    async def test_update_scheduler_state(self, startup_sequence: StartupSequence, mock_bot: MagicMock) -> None:
        """Test scheduler state update."""
        # Mark initial post as completed
        startup_sequence.initial_post_completed = True
        
        # Setup update tracker mocks
        mock_state = MagicMock()
        mock_state_manager = MagicMock()
        mock_bot.update_tracker._state = mock_state
        mock_bot.update_tracker._state_manager = mock_state_manager
        mock_bot.update_tracker.get_next_update_time.return_value = datetime.now()
        
        # Run scheduler update
        await startup_sequence.update_scheduler_state()
        
        # Verify state was updated
        assert mock_state.last_update is not None
        mock_state_manager.save_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_scheduler_state_skips_if_no_graphs(self, startup_sequence: StartupSequence) -> None:
        """Test that scheduler state update is skipped if no graphs were posted."""
        startup_sequence.initial_post_completed = False
        
        # Should return early without errors
        await startup_sequence.update_scheduler_state()
    
    @pytest.mark.asyncio
    async def test_full_startup_sequence(self, startup_sequence: StartupSequence) -> None:
        """Test the complete startup sequence run."""
        # Mock all the individual methods
        startup_sequence.cleanup_previous_messages = AsyncMock()
        startup_sequence.post_initial_graphs = AsyncMock()
        startup_sequence.update_scheduler_state = AsyncMock()
        
        # Run the full sequence
        await startup_sequence.run()
        
        # Verify all steps were called
        startup_sequence.cleanup_previous_messages.assert_called_once()
        startup_sequence.post_initial_graphs.assert_called_once()
        startup_sequence.update_scheduler_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_startup_sequence_continues_on_error(self, startup_sequence: StartupSequence) -> None:
        """Test that startup sequence continues even if steps fail."""
        # Make cleanup fail
        startup_sequence.cleanup_previous_messages = AsyncMock(
            side_effect=Exception("Cleanup failed")
        )
        startup_sequence.post_initial_graphs = AsyncMock()
        startup_sequence.update_scheduler_state = AsyncMock()
        
        # Run should not raise
        await startup_sequence.run()
        
        # Other steps should still be attempted
        startup_sequence.post_initial_graphs.assert_called_once()
        startup_sequence.update_scheduler_state.assert_called_once()
    
    def test_is_completed(self, startup_sequence: StartupSequence) -> None:
        """Test the is_completed method."""
        assert startup_sequence.is_completed() is False
        
        startup_sequence.cleanup_completed = True
        assert startup_sequence.is_completed() is False
        
        startup_sequence.initial_post_completed = True
        assert startup_sequence.is_completed() is True 