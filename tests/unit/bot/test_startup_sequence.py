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
from typing import cast

import discord
import pytest

from src.tgraph_bot.bot.startup_sequence import StartupSequence, TGraphBotProtocol
from src.tgraph_bot.config.manager import ConfigManager
from src.tgraph_bot.config.schema import TGraphBotConfig


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create a mock bot instance for testing."""
    bot = MagicMock(spec=TGraphBotProtocol)

    # Properly type the user mock
    user_mock = MagicMock(spec=discord.ClientUser)
    user_mock.id = 123456789
    bot.user = user_mock

    # Properly type the config manager mock
    config_manager_mock = MagicMock(spec=ConfigManager)
    bot.config_manager = config_manager_mock

    # Properly type the update tracker mock
    update_tracker_mock = MagicMock()
    bot.update_tracker = update_tracker_mock

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
    return StartupSequence(cast(TGraphBotProtocol, mock_bot))


class TestStartupSequence:
    """Test the StartupSequence class."""

    @pytest.mark.asyncio
    async def test_startup_sequence_initialization(
        self, startup_sequence: StartupSequence, mock_bot: MagicMock
    ) -> None:
        """Test that StartupSequence initializes correctly."""
        assert startup_sequence.bot == mock_bot
        assert startup_sequence.cleanup_completed is False
        assert startup_sequence.initial_post_completed is False

    @pytest.mark.asyncio
    async def test_cleanup_previous_messages_success(
        self,
        startup_sequence: StartupSequence,
        mock_bot: MagicMock,
        mock_config: TGraphBotConfig,
    ) -> None:
        """Test successful message cleanup."""
        # Setup mocks with proper types
        config_manager_mock = cast(MagicMock, mock_bot.config_manager)
        config_manager_mock.get_current_config.return_value = mock_config  # pyright: ignore[reportAny]

        # Create mock channel with proper spec
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_guild = MagicMock(spec=discord.Guild)
        mock_member = MagicMock(spec=discord.Member)
        mock_permissions = MagicMock(spec=discord.Permissions)
        mock_permissions.manage_messages = True

        mock_channel.guild = mock_guild
        mock_guild.me = mock_member
        mock_channel.permissions_for.return_value = mock_permissions  # pyright: ignore[reportAny]

        # Create mock messages with proper specs
        bot_message = MagicMock(spec=discord.Message)
        bot_message_author = MagicMock(spec=discord.User)
        bot_message_author.id = mock_bot.user.id  # pyright: ignore[reportAny]
        bot_message.author = bot_message_author
        bot_message.delete = AsyncMock()

        other_message = MagicMock(spec=discord.Message)
        other_message_author = MagicMock(spec=discord.User)
        other_message_author.id = 999999999  # Different user
        other_message.author = other_message_author

        # Mock history method with proper typing
        async def mock_history(
            limit: int | None = None,  # pyright: ignore[reportUnusedParameter] # required for discord.py API compatibility
        ) -> AsyncGenerator[MagicMock, None]:
            for msg in [bot_message, other_message]:
                yield msg

        mock_channel.history = mock_history
        get_channel_mock = cast(MagicMock, mock_bot.get_channel)
        get_channel_mock.return_value = mock_channel

        # Run cleanup
        await startup_sequence.cleanup_previous_messages()

        # Verify
        assert startup_sequence.cleanup_completed is True
        bot_message.delete.assert_called_once()  # pyright: ignore[reportAny]
        get_channel_mock.assert_called_once_with(mock_config.CHANNEL_ID)

    @pytest.mark.asyncio
    async def test_cleanup_previous_messages_no_channel(
        self,
        startup_sequence: StartupSequence,
        mock_bot: MagicMock,
        mock_config: TGraphBotConfig,
    ) -> None:
        """Test cleanup when channel is not found."""
        config_manager_mock = cast(MagicMock, mock_bot.config_manager)
        config_manager_mock.get_current_config.return_value = mock_config  # pyright: ignore[reportAny]

        get_channel_mock = cast(MagicMock, mock_bot.get_channel)
        get_channel_mock.return_value = None

        await startup_sequence.cleanup_previous_messages()

        # Should still mark as completed even if channel not found
        assert startup_sequence.cleanup_completed is False

    @pytest.mark.asyncio
    async def test_cleanup_handles_rate_limits(
        self,
        startup_sequence: StartupSequence,
        mock_bot: MagicMock,
        mock_config: TGraphBotConfig,
    ) -> None:
        """Test that cleanup handles Discord rate limits properly."""
        # Setup mocks with proper types
        config_manager_mock = cast(MagicMock, mock_bot.config_manager)
        config_manager_mock.get_current_config.return_value = mock_config  # pyright: ignore[reportAny]

        # Create mock channel with proper spec
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_guild = MagicMock(spec=discord.Guild)
        mock_member = MagicMock(spec=discord.Member)
        mock_permissions = MagicMock(spec=discord.Permissions)
        mock_permissions.manage_messages = True

        mock_channel.guild = mock_guild
        mock_guild.me = mock_member
        mock_channel.permissions_for.return_value = mock_permissions  # pyright: ignore[reportAny]

        # Create mock message with rate limit error
        bot_message = MagicMock(spec=discord.Message)
        bot_message_author = MagicMock(spec=discord.User)
        bot_message_author.id = mock_bot.user.id  # pyright: ignore[reportAny]
        bot_message.author = bot_message_author

        # Simulate rate limit error
        mock_response = MagicMock()
        mock_response.status = 429
        rate_limit_error = discord.HTTPException(mock_response, "rate limited")
        # Use setattr to add retry_after for testing
        setattr(rate_limit_error, "retry_after", 0.1)  # Short delay for testing
        bot_message.delete = AsyncMock(side_effect=rate_limit_error)

        # Mock history with proper typing
        async def mock_history(
            limit: int | None = None,  # pyright: ignore[reportUnusedParameter] # required for discord.py API compatibility
        ) -> AsyncGenerator[MagicMock, None]:
            yield bot_message

        mock_channel.history = mock_history
        get_channel_mock = cast(MagicMock, mock_bot.get_channel)
        get_channel_mock.return_value = mock_channel

        # Run cleanup
        await startup_sequence.cleanup_previous_messages()

        # Should handle the rate limit gracefully and still complete cleanup
        bot_message.delete.assert_called()  # pyright: ignore[reportAny]
        assert startup_sequence.cleanup_completed is True

    @pytest.mark.asyncio
    async def test_post_initial_graphs_success(
        self,
        startup_sequence: StartupSequence,
        mock_bot: MagicMock,
        mock_config: TGraphBotConfig,
    ) -> None:
        """Test successful initial graph posting."""
        # Setup mocks with proper types
        config_manager_mock = cast(MagicMock, mock_bot.config_manager)
        config_manager_mock.get_current_config.return_value = mock_config  # pyright: ignore[reportAny]

        # Create mock channel with proper spec
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.send = AsyncMock()

        get_channel_mock = cast(MagicMock, mock_bot.get_channel)
        get_channel_mock.return_value = mock_channel

        # Mock GraphManager
        with patch(
            "src.tgraph_bot.bot.startup_sequence.GraphManager"
        ) as mock_graph_manager_class:
            mock_graph_manager = AsyncMock()
            mock_graph_manager.__aenter__.return_value = mock_graph_manager  # pyright: ignore[reportAny]
            mock_graph_manager.generate_all_graphs.return_value = [  # pyright: ignore[reportAny]
                "/tmp/graph1.png",
                "/tmp/graph2.png",
            ]
            mock_graph_manager_class.return_value = mock_graph_manager

            # Mock file utilities
            with patch(
                "src.tgraph_bot.bot.startup_sequence.validate_file_for_discord"
            ) as mock_validate:
                with patch(
                    "src.tgraph_bot.bot.startup_sequence.create_discord_file_safe"
                ) as mock_create_file:
                    with patch(
                        "src.tgraph_bot.bot.startup_sequence.create_graph_specific_embed"
                    ) as mock_create_embed:
                        # Setup file validation
                        mock_validation = MagicMock()
                        mock_validation.valid = True
                        mock_validate.return_value = mock_validation

                        # Setup Discord file creation
                        mock_create_file.return_value = MagicMock(spec=discord.File)

                        # Setup embed creation
                        mock_create_embed.return_value = MagicMock(spec=discord.Embed)

                        # Create test files
                        with patch("pathlib.Path.exists", return_value=True):
                            await startup_sequence.post_initial_graphs()

        # Verify
        assert startup_sequence.initial_post_completed is True
        send_mock = cast(AsyncMock, mock_channel.send)
        assert send_mock.call_count == 2  # Two graphs posted

    @pytest.mark.asyncio
    async def test_update_scheduler_state(
        self, startup_sequence: StartupSequence, mock_bot: MagicMock
    ) -> None:
        """Test scheduler state update."""
        # Mark initial post as completed
        startup_sequence.initial_post_completed = True

        # Setup update tracker mocks with proper types
        mock_state = MagicMock()
        mock_state_manager = MagicMock()

        update_tracker_mock = cast(MagicMock, mock_bot.update_tracker)
        update_tracker_mock._state = mock_state
        update_tracker_mock._state_manager = mock_state_manager
        update_tracker_mock.get_next_update_time.return_value = datetime.now()  # pyright: ignore[reportAny]

        # Run scheduler update
        await startup_sequence.update_scheduler_state()

        # Verify state was updated
        assert mock_state.last_update is not None  # pyright: ignore[reportAny]
        mock_state_manager.save_state.assert_called_once()  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_update_scheduler_state_uses_local_timezone(
        self, startup_sequence: StartupSequence, mock_bot: MagicMock
    ) -> None:
        """Test that scheduler state update converts UTC time to local timezone."""
        from zoneinfo import ZoneInfo
        from tgraph_bot.bot.update_tracker import get_local_timezone

        # Mark initial post as completed
        startup_sequence.initial_post_completed = True

        # Setup update tracker mocks with proper types
        mock_state = MagicMock()
        mock_state_manager = MagicMock()

        update_tracker_mock = cast(MagicMock, mock_bot.update_tracker)
        update_tracker_mock._state = mock_state
        update_tracker_mock._state_manager = mock_state_manager
        update_tracker_mock.get_next_update_time.return_value = datetime.now()  # pyright: ignore[reportAny]

        # Mock discord.utils.utcnow to return a known UTC time
        with patch("discord.utils.utcnow") as mock_utcnow:
            from datetime import timezone

            known_utc_time = datetime(2025, 7, 18, 12, 0, 0, tzinfo=timezone.utc)
            mock_utcnow.return_value = known_utc_time

            # Run scheduler update
            await startup_sequence.update_scheduler_state()

            # Verify that the assigned time is in local timezone, not UTC
            assigned_time = mock_state.last_update  # pyright: ignore[reportAny]
            assert assigned_time is not None

            # The assigned time should be the UTC time converted to local timezone
            expected_local_time = known_utc_time.astimezone(get_local_timezone())
            assert assigned_time == expected_local_time

            # Verify the timezone is local, not UTC
            assert assigned_time.tzinfo is not None  # pyright: ignore[reportAny]
            assert isinstance(assigned_time.tzinfo, ZoneInfo)  # pyright: ignore[reportAny]
            assert str(assigned_time.tzinfo) == str(get_local_timezone())
            assert assigned_time.tzinfo != timezone.utc

    @pytest.mark.asyncio
    async def test_update_scheduler_state_skips_if_no_graphs(
        self, startup_sequence: StartupSequence
    ) -> None:
        """Test that scheduler state update is skipped if no graphs were posted."""
        startup_sequence.initial_post_completed = False

        # Should return early without errors
        await startup_sequence.update_scheduler_state()

    @pytest.mark.asyncio
    async def test_full_startup_sequence(
        self, startup_sequence: StartupSequence
    ) -> None:
        """Test the complete startup sequence run."""
        # Mock all the individual methods
        startup_sequence.cleanup_previous_messages = AsyncMock()
        startup_sequence.post_initial_graphs = AsyncMock()
        startup_sequence.update_scheduler_state = AsyncMock()

        # Run the full sequence
        await startup_sequence.run()

        # Verify all steps were called
        cleanup_mock = startup_sequence.cleanup_previous_messages
        post_graphs_mock = startup_sequence.post_initial_graphs
        update_state_mock = startup_sequence.update_scheduler_state

        cleanup_mock.assert_called_once()
        post_graphs_mock.assert_called_once()
        update_state_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_sequence_continues_on_error(
        self, startup_sequence: StartupSequence
    ) -> None:
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
        post_graphs_mock = startup_sequence.post_initial_graphs
        update_state_mock = startup_sequence.update_scheduler_state

        post_graphs_mock.assert_called_once()
        update_state_mock.assert_called_once()

    def test_is_completed(self, startup_sequence: StartupSequence) -> None:
        """Test the is_completed method."""
        assert startup_sequence.is_completed() is False

        startup_sequence.cleanup_completed = True
        assert startup_sequence.is_completed() is False

        startup_sequence.initial_post_completed = True
        assert startup_sequence.is_completed() is True
