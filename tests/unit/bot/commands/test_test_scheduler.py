"""
Tests for test scheduler command functionality.

This module tests the /test_scheduler command including success cases,
error handling, and proper integration with the UpdateTracker system.

Note: Basic initialization and type validation tests have been consolidated
in tests.unit.bot.test_cog_base_functionality to eliminate redundancy.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tgraph_bot.bot.commands.test_scheduler import SchedulerTestCog
from src.tgraph_bot.config.schema import TGraphBotConfig
from src.tgraph_bot.main import TGraphBot
from tests.utils.cog_helpers import create_mock_bot_with_config
from tests.utils.test_helpers import create_mock_interaction


class TestTestSchedulerCog:
    """Test cases for the SchedulerTestCog class."""

    @pytest.fixture
    def mock_bot(self, base_config: TGraphBotConfig) -> TGraphBot:
        """Create a mock TGraphBot instance."""
        return create_mock_bot_with_config(base_config)

    @pytest.fixture
    def test_scheduler_cog(self, mock_bot: TGraphBot) -> SchedulerTestCog:
        """Create a SchedulerTestCog instance for testing."""
        return SchedulerTestCog(mock_bot)

    @pytest.mark.asyncio
    async def test_test_scheduler_success(
        self, test_scheduler_cog: SchedulerTestCog
    ) -> None:
        """Test successful scheduler test execution."""
        # Create mock interaction
        mock_interaction = create_mock_interaction(
            command_name="test_scheduler", user_id=123456, username="TestAdmin"
        )

        # Mock UpdateTracker and its methods
        mock_update_tracker = MagicMock()
        mock_update_tracker.get_scheduler_status.return_value = {  # pyright: ignore[reportAny] # mock object typing
            "is_running": True,
            "last_update": None,
            "next_update": None,
            "config_update_days": 1,
            "config_fixed_time": "00:05",
        }
        mock_update_tracker.get_next_update_time.return_value = None  # pyright: ignore[reportAny] # mock object typing
        mock_update_tracker.get_last_update_time.return_value = None  # pyright: ignore[reportAny] # mock object typing
        mock_update_tracker.force_update = AsyncMock()

        with patch.object(
            test_scheduler_cog.tgraph_bot, "update_tracker", mock_update_tracker
        ):
            # Execute the command
            _ = await test_scheduler_cog.test_scheduler.callback(  # pyright: ignore[reportUnknownVariableType]
                test_scheduler_cog,
                mock_interaction,  # pyright: ignore[reportCallIssue]
            )

            # Verify force_update was called
            mock_update_tracker.force_update.assert_called_once()  # pyright: ignore[reportAny] # mock object typing

            # Verify interaction responses were sent
            mock_interaction.response.send_message.assert_called_once()  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
            assert (
                mock_interaction.followup.send.call_count >= 2  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
            )  # Status and completion messages

    @pytest.mark.asyncio
    async def test_test_scheduler_force_update_failure(
        self, test_scheduler_cog: SchedulerTestCog
    ) -> None:
        """Test scheduler test when force_update fails."""
        # Create mock interaction
        mock_interaction = create_mock_interaction(
            command_name="test_scheduler", user_id=123456, username="TestAdmin"
        )

        # Mock UpdateTracker to raise an exception on force_update
        mock_update_tracker = MagicMock()
        mock_update_tracker.get_scheduler_status.return_value = {  # pyright: ignore[reportAny] # mock object typing
            "is_running": True,
            "last_update": None,
            "next_update": None,
            "config_update_days": 1,
            "config_fixed_time": "00:05",
        }
        mock_update_tracker.get_next_update_time.return_value = None  # pyright: ignore[reportAny] # mock object typing
        mock_update_tracker.get_last_update_time.return_value = None  # pyright: ignore[reportAny] # mock object typing
        mock_update_tracker.force_update = AsyncMock(
            side_effect=RuntimeError("Test scheduler error")
        )

        with (
            patch.object(
                test_scheduler_cog.tgraph_bot, "update_tracker", mock_update_tracker
            ),
            patch.object(
                test_scheduler_cog, "handle_command_error"
            ) as mock_error_handler,
        ):
            # Execute the command
            _ = await test_scheduler_cog.test_scheduler.callback(  # pyright: ignore[reportUnknownVariableType]
                test_scheduler_cog,
                mock_interaction,  # pyright: ignore[reportCallIssue]
            )

            # Verify error handling was called
            mock_error_handler.assert_called_once()
            args = mock_error_handler.call_args[0]  # pyright: ignore[reportAny] # mock object call_args typing
            assert args[0] == mock_interaction
            assert isinstance(args[1], RuntimeError)
            assert args[2] == "test_scheduler"

    @pytest.mark.asyncio
    async def test_test_scheduler_cooldown_active(
        self, test_scheduler_cog: SchedulerTestCog
    ) -> None:
        """Test scheduler test when command is on cooldown."""
        # Create mock interaction
        mock_interaction = create_mock_interaction(
            command_name="test_scheduler", user_id=123456, username="TestAdmin"
        )

        # Mock cooldown check to return active cooldown
        with patch.object(
            test_scheduler_cog, "check_cooldowns", return_value=(True, 300.0)
        ):
            # Execute the command
            _ = await test_scheduler_cog.test_scheduler.callback(  # pyright: ignore[reportUnknownVariableType]
                test_scheduler_cog,
                mock_interaction,  # pyright: ignore[reportCallIssue]
            )

            # Verify cooldown response was sent
            mock_interaction.response.send_message.assert_called_once()  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

            # Get the embed that was sent
            call_args = mock_interaction.response.send_message.call_args  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue,reportUnknownVariableType]
            embed = call_args[1]["embed"]  # pyright: ignore[reportUnknownVariableType]

            # Verify it's a cooldown embed
            assert "Cooldown" in embed.title  # pyright: ignore[reportUnknownMemberType]

    @pytest.mark.asyncio
    async def test_test_scheduler_config_error(
        self, test_scheduler_cog: SchedulerTestCog
    ) -> None:
        """Test scheduler test when config cannot be loaded."""
        # Create mock interaction
        mock_interaction = create_mock_interaction(
            command_name="test_scheduler", user_id=123456, username="TestAdmin"
        )

        # Mock config manager to raise an exception
        with (
            patch.object(
                test_scheduler_cog,
                "get_current_config",
                side_effect=RuntimeError("Config error"),
            ),
            patch.object(
                test_scheduler_cog, "handle_command_error"
            ) as mock_error_handler,
        ):
            # Execute the command
            _ = await test_scheduler_cog.test_scheduler.callback(  # pyright: ignore[reportUnknownVariableType]
                test_scheduler_cog,
                mock_interaction,  # pyright: ignore[reportCallIssue]
            )

            # Verify error handling was called
            mock_error_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_scheduler_embed_content(
        self, test_scheduler_cog: SchedulerTestCog
    ) -> None:
        """Test that the scheduler test produces correctly formatted embeds."""
        # Create mock interaction
        mock_interaction = create_mock_interaction(
            command_name="test_scheduler", user_id=123456, username="TestAdmin"
        )

        # Mock UpdateTracker
        mock_update_tracker = MagicMock()
        mock_update_tracker.get_scheduler_status.return_value = {  # pyright: ignore[reportAny] # mock object typing
            "is_running": True,
            "last_update": None,
            "next_update": None,
            "config_update_days": 1,
            "config_fixed_time": "00:05",
        }
        mock_update_tracker.get_next_update_time.return_value = None  # pyright: ignore[reportAny] # mock object typing
        mock_update_tracker.get_last_update_time.return_value = None  # pyright: ignore[reportAny] # mock object typing
        mock_update_tracker.force_update = AsyncMock()

        with patch.object(
            test_scheduler_cog.tgraph_bot, "update_tracker", mock_update_tracker
        ):
            # Execute the command
            _ = await test_scheduler_cog.test_scheduler.callback(  # pyright: ignore[reportUnknownVariableType]
                test_scheduler_cog,
                mock_interaction,  # pyright: ignore[reportCallIssue]
            )

            # Verify initial response embed
            mock_interaction.response.send_message.assert_called_once()  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
            call_args = mock_interaction.response.send_message.call_args  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue,reportUnknownVariableType]
            initial_embed = call_args[1]["embed"]  # pyright: ignore[reportUnknownVariableType]

            # Check initial embed content
            assert "Scheduler Test Started" in initial_embed.title  # pyright: ignore[reportUnknownMemberType]
            assert (
                "Testing the scheduled update functionality"
                in initial_embed.description  # pyright: ignore[reportUnknownMemberType]
            )

            # Verify followup messages were sent
            assert mock_interaction.followup.send.call_count >= 2  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

    @pytest.mark.asyncio
    async def test_test_scheduler_permissions_check(
        self, test_scheduler_cog: SchedulerTestCog
    ) -> None:
        """Test that the command has proper permission checks."""
        # Verify the command has the correct permissions set
        command = test_scheduler_cog.test_scheduler

        # Check that it requires manage_guild permission
        assert command.default_permissions is not None
        assert command.default_permissions.manage_guild is True

        # Check that it has permission checks
        checks = getattr(command, "checks", [])
        assert len(checks) > 0  # Should have permission checks
