"""
Tests for update graphs command functionality.

This module tests the /update_graphs command including cleanup functionality,
graph generation, error handling, and proper integration with Discord channels.
"""

from unittest.mock import AsyncMock, patch, MagicMock
from collections.abc import AsyncIterator

import discord
import pytest
from discord.ext import commands

from src.tgraph_bot.bot.commands.update_graphs import UpdateGraphsCog
from src.tgraph_bot.config.schema import TGraphBotConfig
from src.tgraph_bot.main import TGraphBot
from tests.utils.test_helpers import (
    create_config_manager_with_config,
    create_mock_interaction,
)


class TestUpdateGraphsCog:
    """Test cases for the UpdateGraphsCog class."""

    @pytest.fixture
    def mock_bot(self, base_config: TGraphBotConfig) -> TGraphBot:
        """Create a mock TGraphBot instance."""
        config_manager = create_config_manager_with_config(base_config)
        bot = TGraphBot(config_manager)
        return bot

    @pytest.fixture
    def update_graphs_cog(self, mock_bot: TGraphBot) -> UpdateGraphsCog:
        """Create an UpdateGraphsCog instance for testing."""
        return UpdateGraphsCog(mock_bot)

    def test_init(self, mock_bot: TGraphBot) -> None:
        """Test UpdateGraphsCog initialization."""
        cog = UpdateGraphsCog(mock_bot)
        assert cog.bot is mock_bot
        assert isinstance(cog.tgraph_bot, TGraphBot)
        assert cog.cooldown_config is not None
        assert hasattr(cog, "config_helper")

    def test_tgraph_bot_property_with_wrong_bot_type(self) -> None:
        """Test tgraph_bot property with wrong bot type."""
        regular_bot = commands.Bot(
            command_prefix="!", intents=discord.Intents.default()
        )

        def mock_init(self: UpdateGraphsCog, bot: commands.Bot) -> None:
            """Mock initialization that just sets the bot attribute."""
            setattr(self, "bot", bot)

        # Mock the initialization to avoid accessing tgraph_bot during __init__
        with (
            patch("src.tgraph_bot.bot.commands.update_graphs.ConfigurationHelper"),
            patch.object(UpdateGraphsCog, "__init__", mock_init),
        ):
            # Create the cog (this should succeed)
            cog = UpdateGraphsCog(regular_bot)

            # Accessing tgraph_bot property should raise TypeError
            with pytest.raises(TypeError, match="Expected TGraphBot instance"):
                cog.tgraph_bot  # Don't assign to _ to avoid type warning

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
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.name = "test-channel"

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
            patch("src.tgraph_bot.bot.commands.update_graphs.ProgressCallbackManager"),
        ):
            # Setup GraphManager mock
            mock_graph_manager = AsyncMock()
            mock_graph_manager.generate_all_graphs.return_value = [
                "graph1.png",
                "graph2.png",
                "graph3.png",
            ]  # pyright: ignore[reportAny]
            mock_graph_manager_class.return_value.__aenter__.return_value = (
                mock_graph_manager  # pyright: ignore[reportAny]
            )
            mock_graph_manager_class.return_value.__aexit__.return_value = None  # pyright: ignore[reportAny]

            # Execute the command
            _ = await update_graphs_cog.update_graphs.callback(  # pyright: ignore[reportUnknownVariableType]
                update_graphs_cog, mock_interaction  # pyright: ignore[reportCallIssue]
            )

            # Verify the cleanup → generate → post sequence
            mock_cleanup.assert_called_once_with(mock_channel)
            mock_graph_manager.generate_all_graphs.assert_called_once()  # pyright: ignore[reportAny]
            mock_post.assert_called_once_with(
                mock_channel, ["graph1.png", "graph2.png", "graph3.png"]
            )

            # Verify interaction responses were sent
            mock_interaction.response.send_message.assert_called_once()  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
            assert mock_interaction.followup.send.call_count >= 1  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

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
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.name = "test-channel"

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
                update_graphs_cog, mock_interaction  # pyright: ignore[reportCallIssue]
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
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.name = "test-channel"

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
            patch("src.tgraph_bot.bot.commands.update_graphs.ProgressCallbackManager"),
        ):
            # Setup GraphManager mock to return empty list
            mock_graph_manager = AsyncMock()
            mock_graph_manager.generate_all_graphs.return_value = []  # pyright: ignore[reportAny]
            mock_graph_manager_class.return_value.__aenter__.return_value = (
                mock_graph_manager  # pyright: ignore[reportAny]
            )
            mock_graph_manager_class.return_value.__aexit__.return_value = None  # pyright: ignore[reportAny]

            # Execute the command
            _ = await update_graphs_cog.update_graphs.callback(  # pyright: ignore[reportUnknownVariableType]
                update_graphs_cog, mock_interaction  # pyright: ignore[reportCallIssue]
            )

            # Verify cleanup was performed and generation attempted, but not posting
            mock_cleanup.assert_called_once_with(mock_channel)
            mock_graph_manager.generate_all_graphs.assert_called_once()  # pyright: ignore[reportAny]
            mock_post.assert_not_called()

            # Should send a warning message
            assert mock_interaction.followup.send.call_count >= 1  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_success(
        self, update_graphs_cog: UpdateGraphsCog
    ) -> None:
        """Test successful cleanup of bot messages."""
        # Create mock channel
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.name = "test-channel"

        # Create mock guild and permissions
        mock_guild_member = MagicMock()
        mock_guild_member.permissions_for.return_value.manage_messages = True  # pyright: ignore[reportAny]
        mock_channel.guild.me = mock_guild_member  # pyright: ignore[reportAny]

        # Create mock bot user
        mock_bot_user = MagicMock()
        mock_bot_user.id = 123456789

        # Create mock messages - some from bot, some from users
        mock_bot_message1 = MagicMock()
        mock_bot_message1.author.id = (
            123456789  # Bot's message  # pyright: ignore[reportAny]
        )
        mock_bot_message1.id = "msg1"
        mock_bot_message1.delete = AsyncMock()

        mock_bot_message2 = MagicMock()
        mock_bot_message2.author.id = (
            123456789  # Bot's message  # pyright: ignore[reportAny]
        )
        mock_bot_message2.id = "msg2"
        mock_bot_message2.delete = AsyncMock()

        mock_user_message = MagicMock()
        mock_user_message.author.id = (
            987654321  # User's message  # pyright: ignore[reportAny]
        )
        mock_user_message.id = "user_msg"
        mock_user_message.delete = AsyncMock()

        # Mock the async iterator for channel history
        async def mock_history(
            *_args: object, **_kwargs: object
        ) -> AsyncIterator[MagicMock]:
            for message in [mock_bot_message1, mock_user_message, mock_bot_message2]:
                yield message

        mock_channel.history = mock_history

        with patch.object(
            type(update_graphs_cog.bot), "user", new_callable=lambda: mock_bot_user
        ):
            await update_graphs_cog._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]

            # Should only delete bot's messages
            mock_bot_message1.delete.assert_called_once()  # pyright: ignore[reportAny]
            mock_bot_message2.delete.assert_called_once()  # pyright: ignore[reportAny]
            mock_user_message.delete.assert_not_called()  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_cleanup_bot_messages_no_manage_permissions(
        self, update_graphs_cog: UpdateGraphsCog
    ) -> None:
        """Test cleanup when bot lacks manage messages permission."""
        mock_channel = MagicMock(spec=discord.TextChannel)
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

        async def mock_history(
            *_args: object, **_kwargs: object
        ) -> AsyncIterator[MagicMock]:
            for message in [mock_bot_message]:
                yield message

        mock_channel.history = mock_history

        with patch.object(
            type(update_graphs_cog.bot), "user", new_callable=lambda: mock_bot_user
        ):
            await update_graphs_cog._cleanup_bot_messages(mock_channel)  # pyright: ignore[reportPrivateUsage]

            # Should still attempt to delete bot's own messages
            mock_bot_message.delete.assert_called_once()  # pyright: ignore[reportAny]

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
                update_graphs_cog, mock_interaction  # pyright: ignore[reportCallIssue]
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
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.name = "test-channel"

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
            patch("src.tgraph_bot.bot.commands.update_graphs.ProgressCallbackManager"),
        ):
            # Setup GraphManager mock with 3 graphs but only 2 post successfully
            mock_graph_manager = AsyncMock()
            mock_graph_manager.generate_all_graphs.return_value = [
                "graph1.png",
                "graph2.png",
                "graph3.png",
            ]  # pyright: ignore[reportAny]
            mock_graph_manager_class.return_value.__aenter__.return_value = (
                mock_graph_manager  # pyright: ignore[reportAny]
            )
            mock_graph_manager_class.return_value.__aexit__.return_value = None  # pyright: ignore[reportAny]

            # Execute the command
            _ = await update_graphs_cog.update_graphs.callback(  # pyright: ignore[reportUnknownVariableType]
                update_graphs_cog, mock_interaction  # pyright: ignore[reportCallIssue]
            )

            # Verify partial success warning was sent
            assert mock_interaction.followup.send.call_count >= 1  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
            # Should have called post with all 3 graphs
            mock_post.assert_called_once_with(
                mock_channel, ["graph1.png", "graph2.png", "graph3.png"]
            )
