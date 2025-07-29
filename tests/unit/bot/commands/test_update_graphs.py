"""
Tests for update graphs command functionality.

This module tests the /update_graphs command including cleanup functionality,
graph generation, error handling, and proper integration with Discord channels.

Note: Basic initialization and type validation tests have been consolidated
in tests.unit.bot.test_cog_base_functionality to eliminate redundancy.
"""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from src.tgraph_bot.bot.commands.update_graphs import UpdateGraphsCog
from src.tgraph_bot.config.schema import TGraphBotConfig
from src.tgraph_bot.main import TGraphBot
from tests.utils.cog_helpers import create_mock_bot_with_config
from tests.utils.test_helpers import (
    create_mock_channel,
    create_mock_interaction,
    create_mock_message,
)


class TestUpdateGraphsCog:
    """Test cases for the UpdateGraphsCog class."""

    @pytest.fixture
    def mock_bot(self, base_config: TGraphBotConfig) -> TGraphBot:
        """Create a mock TGraphBot instance."""
        return create_mock_bot_with_config(base_config)

    @pytest.fixture
    def update_graphs_cog(self, mock_bot: TGraphBot) -> UpdateGraphsCog:
        """Create an UpdateGraphsCog instance for testing."""
        return UpdateGraphsCog(mock_bot)

    @pytest.mark.asyncio
    async def test_update_graphs_success_with_cleanup(
        self, update_graphs_cog: UpdateGraphsCog
    ) -> None:
        """Test successful update graphs command with message cleanup."""
        # Create mock interaction
        mock_interaction = create_mock_interaction(
            command_name="update_graphs", user_id=123456, username="TestAdmin"
        )

        # Create mock channel
        mock_channel = create_mock_channel(name="test-channel")

        with (
            patch.object(
                update_graphs_cog.config_helper,
                "validate_discord_channel",
                return_value=mock_channel,
            ),
            patch.object(
                update_graphs_cog, "_cleanup_bot_messages", new_callable=AsyncMock
            ) as mock_cleanup,
            patch(
                "src.tgraph_bot.bot.commands.update_graphs.GraphManager"
            ) as mock_graph_manager_class,
            patch.object(
                update_graphs_cog,
                "_post_graphs_to_channel",
                new_callable=AsyncMock,
                return_value=3,
            ) as mock_post,
        ):
            # Setup GraphManager mock
            mock_graph_manager = AsyncMock()
            mock_graph_manager.generate_all_graphs.return_value = [  # pyright: ignore[reportAny]
                "graph1.png",
                "graph2.png",
                "graph3.png",
            ]
            mock_graph_manager_class.return_value.__aenter__.return_value = (  # pyright: ignore[reportAny]
                mock_graph_manager
            )
            mock_graph_manager_class.return_value.__aexit__.return_value = None  # pyright: ignore[reportAny]

            # Execute the command
            _ = await update_graphs_cog.update_graphs.callback(  # pyright: ignore[reportUnknownVariableType]
                update_graphs_cog,
                mock_interaction,  # pyright: ignore[reportCallIssue]
            )

            # Verify the cleanup → generate → post sequence
            mock_cleanup.assert_called_once_with(mock_channel)
            mock_graph_manager.generate_all_graphs.assert_called_once()  # pyright: ignore[reportAny]
            mock_post.assert_called_once_with(
                mock_channel, ["graph1.png", "graph2.png", "graph3.png"]
            )

            # Verify multiple ephemeral responses were sent (initial + completion)
            assert mock_interaction.response.send_message.call_count >= 2  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
            # All calls should be ephemeral with delete_after
            call_args_list = mock_interaction.response.send_message.call_args_list  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue,reportUnknownVariableType]
            for call in call_args_list:  # pyright: ignore[reportUnknownVariableType]
                kwargs = call.kwargs  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
                assert kwargs["ephemeral"] is True
                assert kwargs["delete_after"] == 30.0

    @pytest.mark.asyncio
    async def test_update_graphs_cleanup_failure(
        self, update_graphs_cog: UpdateGraphsCog
    ) -> None:
        """Test update graphs command when cleanup fails."""
        # Create mock interaction
        mock_interaction = create_mock_interaction(
            command_name="update_graphs", user_id=123456, username="TestAdmin"
        )

        # Create mock channel
        mock_channel = create_mock_channel(name="test-channel")

        with (
            patch.object(
                update_graphs_cog.config_helper,
                "validate_discord_channel",
                return_value=mock_channel,
            ),
            patch.object(
                update_graphs_cog,
                "_cleanup_bot_messages",
                new_callable=AsyncMock,
                side_effect=Exception("Cleanup failed"),
            ) as mock_cleanup,
            patch.object(
                update_graphs_cog, "handle_command_error"
            ) as mock_error_handler,
        ):
            # Execute the command
            _ = await update_graphs_cog.update_graphs.callback(  # pyright: ignore[reportUnknownVariableType]
                update_graphs_cog,
                mock_interaction,  # pyright: ignore[reportCallIssue]
            )

            # Verify cleanup was attempted
            mock_cleanup.assert_called_once_with(mock_channel)

            # Verify error handling was called
            mock_error_handler.assert_called_once()
            args = mock_error_handler.call_args[0]  # pyright: ignore[reportAny]
            assert args[0] == mock_interaction
            assert isinstance(args[1], Exception)
            assert args[2] == "update_graphs"

    @pytest.mark.asyncio
    async def test_update_graphs_no_graphs_generated(
        self, update_graphs_cog: UpdateGraphsCog
    ) -> None:
        """Test update graphs command when no graphs are generated."""
        # Create mock interaction
        mock_interaction = create_mock_interaction(
            command_name="update_graphs", user_id=123456, username="TestAdmin"
        )

        # Create mock channel
        mock_channel = create_mock_channel(name="test-channel")

        with (
            patch.object(
                update_graphs_cog.config_helper,
                "validate_discord_channel",
                return_value=mock_channel,
            ),
            patch.object(
                update_graphs_cog, "_cleanup_bot_messages", new_callable=AsyncMock
            ) as mock_cleanup,
            patch(
                "src.tgraph_bot.bot.commands.update_graphs.GraphManager"
            ) as mock_graph_manager_class,
            patch.object(
                update_graphs_cog, "_post_graphs_to_channel", new_callable=AsyncMock
            ) as mock_post,
        ):
            # Setup GraphManager mock to return empty list
            mock_graph_manager = AsyncMock()
            mock_graph_manager.generate_all_graphs.return_value = []  # pyright: ignore[reportAny]
            mock_graph_manager_class.return_value.__aenter__.return_value = (  # pyright: ignore[reportAny]
                mock_graph_manager
            )
            mock_graph_manager_class.return_value.__aexit__.return_value = None  # pyright: ignore[reportAny]

            # Execute the command
            _ = await update_graphs_cog.update_graphs.callback(  # pyright: ignore[reportUnknownVariableType]
                update_graphs_cog,
                mock_interaction,  # pyright: ignore[reportCallIssue]
            )

            # Verify cleanup was performed and generation attempted, but not posting
            mock_cleanup.assert_called_once_with(mock_channel)
            mock_graph_manager.generate_all_graphs.assert_called_once()  # pyright: ignore[reportAny]
            mock_post.assert_not_called()

            # Should send ephemeral warning messages (initial + warning)
            assert mock_interaction.response.send_message.call_count >= 2  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_success(
        self, update_graphs_cog: UpdateGraphsCog
    ) -> None:
        """Test successful cleanup of bot messages."""
        # Create mock channel
        mock_channel = create_mock_channel(name="test-channel")

        # Create mock bot user
        mock_bot_user = MagicMock()
        mock_bot_user.id = 123456789

        # Create mock messages - some from bot, some from users
        mock_bot_message1 = create_mock_message(
            message_id="msg1", author_id=123456789, is_bot=True
        )
        mock_bot_message2 = create_mock_message(
            message_id="msg2", author_id=123456789, is_bot=True
        )
        mock_user_message = create_mock_message(
            message_id="user_msg", author_id=987654321, is_bot=False
        )

        # Mock the async iterator for channel history
        async def mock_history(
            *_args: object, **_kwargs: object
        ) -> AsyncIterator[discord.Message]:
            for message in [mock_bot_message1, mock_user_message, mock_bot_message2]:
                yield message

        mock_channel.history = mock_history

        with patch.object(
            type(update_graphs_cog.bot), "user", new_callable=lambda: mock_bot_user
        ):
            await update_graphs_cog._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]

            # Should only delete bot's messages
            mock_bot_message1.delete.assert_called_once()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
            mock_bot_message2.delete.assert_called_once()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
            mock_user_message.delete.assert_not_called()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_no_manage_permissions(
        self, update_graphs_cog: UpdateGraphsCog
    ) -> None:
        """Test cleanup when bot lacks manage messages permission."""
        mock_channel = create_mock_channel(
            name="test-channel", permissions={"manage_messages": False}
        )

        mock_bot_user = MagicMock()
        mock_bot_user.id = 123456789

        # Create mock bot message
        mock_bot_message = create_mock_message(
            message_id="msg1", author_id=123456789, is_bot=True
        )

        async def mock_history(
            *_args: object, **_kwargs: object
        ) -> AsyncIterator[discord.Message]:
            for message in [mock_bot_message]:
                yield message

        mock_channel.history = mock_history

        with patch.object(
            type(update_graphs_cog.bot), "user", new_callable=lambda: mock_bot_user
        ):
            await update_graphs_cog._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]

            # Should still attempt to delete bot's own messages
            mock_bot_message.delete.assert_called_once()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_forbidden_error(
        self, update_graphs_cog: UpdateGraphsCog
    ) -> None:
        """Test cleanup when delete operation is forbidden."""
        mock_channel = MagicMock(spec=discord.TextChannel)
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
        mock_bot_message.delete = AsyncMock(
            side_effect=discord.Forbidden(response=MagicMock(), message="Forbidden")
        )

        async def mock_history(
            *_args: object, **_kwargs: object
        ) -> AsyncIterator[MagicMock]:
            for message in [mock_bot_message]:
                yield message

        mock_channel.history = mock_history

        with patch.object(
            type(update_graphs_cog.bot), "user", new_callable=lambda: mock_bot_user
        ):
            # Should not raise exception, just log warning
            await update_graphs_cog._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]

            mock_bot_message.delete.assert_called_once()  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_rate_limiting(
        self, update_graphs_cog: UpdateGraphsCog
    ) -> None:
        """Test cleanup with rate limiting (429 error)."""
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.name = "test-channel"

        mock_bot_user = MagicMock()
        mock_bot_user.id = 123456789

        mock_guild_member = MagicMock()
        mock_guild_member.permissions_for.return_value.manage_messages = True  # pyright: ignore[reportAny]
        mock_channel.guild.me = mock_guild_member  # pyright: ignore[reportAny]

        # Create mock bot message that raises rate limit error
        mock_rate_limit_error = discord.HTTPException(
            response=MagicMock(), message="Rate limited"
        )
        mock_rate_limit_error.status = 429
        # Add retry_after attribute to the mock
        setattr(mock_rate_limit_error, "retry_after", 2.0)

        mock_bot_message = MagicMock()
        mock_bot_message.author.id = 123456789  # pyright: ignore[reportAny]
        mock_bot_message.id = "msg1"
        mock_bot_message.delete = AsyncMock(side_effect=mock_rate_limit_error)

        async def mock_history(
            *_args: object, **_kwargs: object
        ) -> AsyncIterator[MagicMock]:
            yield mock_bot_message

        mock_channel.history = mock_history

        with (
            patch.object(
                type(update_graphs_cog.bot), "user", new_callable=lambda: mock_bot_user
            ),
            patch(
                "src.tgraph_bot.bot.commands.update_graphs.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep,
        ):
            await update_graphs_cog._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]

            mock_bot_message.delete.assert_called_once()  # pyright: ignore[reportAny]
            # Should sleep for retry_after duration
            mock_sleep.assert_called_with(2.0)

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_not_found_error(
        self, update_graphs_cog: UpdateGraphsCog
    ) -> None:
        """Test cleanup when message is already deleted (NotFound error)."""
        mock_channel = MagicMock(spec=discord.TextChannel)
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
        mock_bot_message.delete = AsyncMock(
            side_effect=discord.NotFound(response=MagicMock(), message="Not found")
        )

        async def mock_history(
            *_args: object, **_kwargs: object
        ) -> AsyncIterator[MagicMock]:
            for message in [mock_bot_message]:
                yield message

        mock_channel.history = mock_history

        with patch.object(
            type(update_graphs_cog.bot), "user", new_callable=lambda: mock_bot_user
        ):
            # Should not raise exception for NotFound
            await update_graphs_cog._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]

            mock_bot_message.delete.assert_called_once()  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_rate_limit_protection(
        self, update_graphs_cog: UpdateGraphsCog
    ) -> None:
        """Test cleanup with automatic rate limit protection."""
        mock_channel = MagicMock(spec=discord.TextChannel)
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

        async def mock_history(
            *_args: object, **_kwargs: object
        ) -> AsyncIterator[MagicMock]:
            for message in mock_messages:
                yield message

        mock_channel.history = mock_history

        with (
            patch.object(
                type(update_graphs_cog.bot), "user", new_callable=lambda: mock_bot_user
            ),
            patch(
                "src.tgraph_bot.bot.commands.update_graphs.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep,
        ):
            await update_graphs_cog._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]

            # All messages should be deleted
            for mock_message in mock_messages:
                mock_message.delete.assert_called_once()  # pyright: ignore[reportAny]

            # Should sleep after every 5 deletions (rate limit protection)
            mock_sleep.assert_called_with(1.0)

    @pytest.mark.asyncio
    async def test_update_graphs_on_cooldown(
        self, update_graphs_cog: UpdateGraphsCog
    ) -> None:
        """Test update graphs command when on cooldown."""
        # Create mock interaction
        mock_interaction = create_mock_interaction(
            command_name="update_graphs", user_id=123456, username="TestAdmin"
        )

        with patch.object(
            update_graphs_cog, "check_cooldowns", return_value=(True, 30.0)
        ):
            _ = await update_graphs_cog.update_graphs.callback(  # pyright: ignore[reportUnknownVariableType]
                update_graphs_cog,
                mock_interaction,  # pyright: ignore[reportCallIssue]
            )

            # Should send cooldown message and return early
            mock_interaction.response.send_message.assert_called_once()  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
            # Should not proceed to graph generation
            assert mock_interaction.followup.send.call_count == 0  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

    @pytest.mark.asyncio
    async def test_update_graphs_partial_success(
        self, update_graphs_cog: UpdateGraphsCog
    ) -> None:
        """Test update graphs command with partial success (some graphs fail to post)."""
        # Create mock interaction
        mock_interaction = create_mock_interaction(
            command_name="update_graphs", user_id=123456, username="TestAdmin"
        )

        # Create mock channel
        mock_channel = create_mock_channel(name="test-channel")

        with (
            patch.object(
                update_graphs_cog.config_helper,
                "validate_discord_channel",
                return_value=mock_channel,
            ),
            patch.object(
                update_graphs_cog, "_cleanup_bot_messages", new_callable=AsyncMock
            ),
            patch(
                "src.tgraph_bot.bot.commands.update_graphs.GraphManager"
            ) as mock_graph_manager_class,
            patch.object(
                update_graphs_cog,
                "_post_graphs_to_channel",
                new_callable=AsyncMock,
                return_value=2,
            ) as mock_post,
        ):
            # Setup GraphManager mock with 3 graphs but only 2 post successfully
            mock_graph_manager = AsyncMock()
            mock_graph_manager.generate_all_graphs.return_value = [  # pyright: ignore[reportAny]
                "graph1.png",
                "graph2.png",
                "graph3.png",
            ]
            mock_graph_manager_class.return_value.__aenter__.return_value = (  # pyright: ignore[reportAny]
                mock_graph_manager
            )
            mock_graph_manager_class.return_value.__aexit__.return_value = None  # pyright: ignore[reportAny]

            # Execute the command
            _ = await update_graphs_cog.update_graphs.callback(  # pyright: ignore[reportUnknownVariableType]
                update_graphs_cog,
                mock_interaction,  # pyright: ignore[reportCallIssue]
            )

            # Verify ephemeral warning messages were sent (initial + partial success warning)
            assert mock_interaction.response.send_message.call_count >= 2  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
            # Should have called post with all 3 graphs
            mock_post.assert_called_once_with(
                mock_channel, ["graph1.png", "graph2.png", "graph3.png"]
            )
