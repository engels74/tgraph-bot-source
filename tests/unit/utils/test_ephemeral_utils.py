"""
Test cases for ephemeral message utilities.

This module tests the ephemeral message auto-deletion utilities to ensure they
properly handle Discord interaction responses with the delete_after parameter.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, call

from tests.utils.test_helpers import create_mock_interaction


class TestEphemeralUtils:
    """Test cases for ephemeral message utilities."""

    @pytest.mark.asyncio
    async def test_send_ephemeral_with_deletion_default_params(self) -> None:
        """Test sending ephemeral message with default 60-second deletion."""
        # Import here to avoid circular import during module loading
        from src.tgraph_bot.utils.discord.ephemeral_utils import send_ephemeral_with_deletion
        
        interaction = create_mock_interaction()
        content = "Test ephemeral message"
        
        # Execute the function
        await send_ephemeral_with_deletion(interaction, content=content)
        
        # Verify interaction.response.send_message was called with correct parameters
        send_message_mock = interaction.response.send_message
        send_message_mock.assert_called_once_with(  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
            content=content,
            ephemeral=True,
            delete_after=60.0
        )

    @pytest.mark.asyncio
    async def test_send_ephemeral_with_deletion_custom_timeout(self) -> None:
        """Test sending ephemeral message with custom deletion timeout."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import send_ephemeral_with_deletion
        
        interaction = create_mock_interaction()
        content = "Test ephemeral message"
        custom_timeout = 120.0
        
        # Execute the function
        await send_ephemeral_with_deletion(interaction, content=content, delete_after=custom_timeout)
        
        # Verify interaction.response.send_message was called with custom timeout
        send_message_mock = interaction.response.send_message
        send_message_mock.assert_called_once_with(  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
            content=content,
            ephemeral=True,
            delete_after=custom_timeout
        )

    @pytest.mark.asyncio
    async def test_send_ephemeral_with_deletion_with_embed(self) -> None:
        """Test sending ephemeral message with embed and auto-deletion."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import send_ephemeral_with_deletion
        
        interaction = create_mock_interaction()
        embed = MagicMock()  # Mock Discord embed
        
        # Execute the function
        await send_ephemeral_with_deletion(interaction, embed=embed)
        
        # Verify interaction.response.send_message was called with embed
        send_message_mock = interaction.response.send_message
        send_message_mock.assert_called_once_with(  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
            embed=embed,
            ephemeral=True,
            delete_after=60.0
        )

    @pytest.mark.asyncio
    async def test_send_ephemeral_with_deletion_with_all_params(self) -> None:
        """Test sending ephemeral message with all parameters."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import send_ephemeral_with_deletion
        
        interaction = create_mock_interaction()
        content = "Test content"
        embed = MagicMock()
        view = MagicMock()
        
        # Execute the function
        await send_ephemeral_with_deletion(
            interaction, 
            content=content, 
            embed=embed, 
            view=view,
            delete_after=45.0
        )
        
        # Verify interaction.response.send_message was called with all parameters
        send_message_mock = interaction.response.send_message
        send_message_mock.assert_called_once_with(  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
            content=content,
            embed=embed,
            view=view,
            ephemeral=True,
            delete_after=45.0
        )

    @pytest.mark.asyncio
    async def test_send_ephemeral_with_deletion_response_already_sent_now_works(self) -> None:
        """Test that the fix prevents TypeError when followup.send receives delete_after."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import send_ephemeral_with_deletion
        
        interaction = create_mock_interaction(is_response_done=True)
        content = "Test ephemeral message"
        
        # Mock followup.send to return a message (normal successful behavior)
        mock_message = MagicMock()
        mock_message.delete = AsyncMock()
        followup_mock = AsyncMock(return_value=mock_message)
        interaction.followup.send = followup_mock
        
        # This should now work without raising TypeError
        await send_ephemeral_with_deletion(interaction, content=content)
        
        # Verify followup.send was called WITHOUT the delete_after parameter
        followup_mock.assert_called_once_with(
            content=content,
            ephemeral=True
        )

    @pytest.mark.asyncio
    async def test_send_ephemeral_with_deletion_followup_with_manual_deletion(self) -> None:
        """Test expected behavior: followup messages use manual deletion instead of delete_after."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import send_ephemeral_with_deletion
        
        interaction = create_mock_interaction(is_response_done=True)
        content = "Test ephemeral message"
        
        # Mock followup.send to return a message object that can be deleted
        mock_message = MagicMock()
        mock_message.delete = AsyncMock()
        followup_mock = AsyncMock(return_value=mock_message)
        interaction.followup.send = followup_mock
        
        # Execute the function
        await send_ephemeral_with_deletion(interaction, content=content, delete_after=30.0)
        
        # Verify followup.send was called WITHOUT delete_after parameter
        followup_mock.assert_called_once_with(
            content=content,
            ephemeral=True
        )
        
        # Verify response.send_message was not called
        send_message_mock = interaction.response.send_message
        send_message_mock.assert_not_called()  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

    @pytest.mark.asyncio
    async def test_send_ephemeral_with_deletion_error_handling(self) -> None:
        """Test error handling when Discord API call fails."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import send_ephemeral_with_deletion
        
        interaction = create_mock_interaction()
        
        # Mock interaction to raise an exception
        interaction.response.send_message.side_effect = Exception("Discord API error")  # pyright: ignore[reportAttributeAccessIssue]
        
        # Verify the exception is propagated
        with pytest.raises(Exception, match="Discord API error"):
            await send_ephemeral_with_deletion(interaction, content="Test")

    @pytest.mark.asyncio
    async def test_edit_ephemeral_with_deletion_default_params(self) -> None:
        """Test editing ephemeral message with default 60-second deletion."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import edit_ephemeral_with_deletion
        
        interaction = create_mock_interaction()
        content = "Updated ephemeral message"
        
        # Mock edit_original_response method
        edit_mock = AsyncMock()
        interaction.edit_original_response = edit_mock
        
        # Execute the function
        await edit_ephemeral_with_deletion(interaction, content=content)
        
        # Verify interaction.edit_original_response was called with correct parameters
        edit_mock.assert_called_once_with(
            content=content,
            delete_after=60.0
        )

    @pytest.mark.asyncio
    async def test_edit_ephemeral_with_deletion_custom_timeout(self) -> None:
        """Test editing ephemeral message with custom deletion timeout."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import edit_ephemeral_with_deletion
        
        interaction = create_mock_interaction()
        embed = MagicMock()
        custom_timeout = 90.0
        
        # Mock edit_original_response method
        edit_mock = AsyncMock()
        interaction.edit_original_response = edit_mock
        
        # Execute the function
        await edit_ephemeral_with_deletion(interaction, embed=embed, delete_after=custom_timeout)
        
        # Verify interaction.edit_original_response was called with custom timeout
        edit_mock.assert_called_once_with(
            embed=embed,
            delete_after=custom_timeout
        )

    @pytest.mark.asyncio
    async def test_edit_ephemeral_with_deletion_all_params(self) -> None:
        """Test editing ephemeral message with all parameters."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import edit_ephemeral_with_deletion
        
        interaction = create_mock_interaction()
        content = "Updated content"
        embed = MagicMock()
        view = MagicMock()
        
        # Mock edit_original_response method
        edit_mock = AsyncMock()
        interaction.edit_original_response = edit_mock
        
        # Execute the function
        await edit_ephemeral_with_deletion(
            interaction, 
            content=content, 
            embed=embed, 
            view=view,
            delete_after=30.0
        )
        
        # Verify interaction.edit_original_response was called with all parameters
        edit_mock.assert_called_once_with(
            content=content,
            embed=embed,
            view=view,
            delete_after=30.0
        )

    @pytest.mark.asyncio
    async def test_edit_ephemeral_with_deletion_error_handling(self) -> None:
        """Test error handling when edit original response fails."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import edit_ephemeral_with_deletion
        
        interaction = create_mock_interaction()
        
        # Mock edit_original_response to raise an exception
        edit_mock = AsyncMock()
        edit_mock.side_effect = Exception("Edit failed")
        interaction.edit_original_response = edit_mock
        
        # Verify the exception is propagated
        with pytest.raises(Exception, match="Edit failed"):
            await edit_ephemeral_with_deletion(interaction, content="Test")


class TestEphemeralUtilsConstants:
    """Test cases for ephemeral utilities constants and configuration."""

    def test_default_deletion_timeout_constant(self) -> None:
        """Test that the default deletion timeout constant is correctly set."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import DEFAULT_EPHEMERAL_DELETION_TIMEOUT
        
        # Verify the default timeout is 60 seconds
        assert DEFAULT_EPHEMERAL_DELETION_TIMEOUT == 60.0
        assert isinstance(DEFAULT_EPHEMERAL_DELETION_TIMEOUT, float)

    def test_deletion_timeout_validation(self) -> None:
        """Test validation of deletion timeout parameter."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import send_ephemeral_with_deletion
        
        interaction = create_mock_interaction()
        
        # Test with negative timeout - should raise ValueError
        with pytest.raises(ValueError, match="delete_after must be positive"):
            import asyncio
            asyncio.run(send_ephemeral_with_deletion(interaction, content="Test", delete_after=-1.0))

    def test_deletion_timeout_zero_handling(self) -> None:
        """Test handling of zero deletion timeout."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import send_ephemeral_with_deletion
        
        interaction = create_mock_interaction()
        
        # Test with zero timeout - should raise ValueError
        with pytest.raises(ValueError, match="delete_after must be positive"):
            import asyncio
            asyncio.run(send_ephemeral_with_deletion(interaction, content="Test", delete_after=0.0))


class TestEphemeralUtilsIntegration:
    """Integration test cases for ephemeral utilities."""

    @pytest.mark.asyncio
    async def test_send_and_edit_sequence(self) -> None:
        """Test sequence of sending and then editing an ephemeral message."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import (
            send_ephemeral_with_deletion,
            edit_ephemeral_with_deletion
        )
        
        interaction = create_mock_interaction()
        
        # Mock edit_original_response method
        edit_mock = AsyncMock()
        interaction.edit_original_response = edit_mock
        
        # Send initial ephemeral message
        await send_ephemeral_with_deletion(interaction, content="Initial message")
        
        # Mark response as done after sending
        interaction.response.is_done.return_value = True  # pyright: ignore[reportAttributeAccessIssue]
        
        # Edit the message
        await edit_ephemeral_with_deletion(interaction, content="Updated message")
        
        # Verify both operations were called correctly
        send_message_mock = interaction.response.send_message
        send_message_mock.assert_called_once_with(  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
            content="Initial message",
            ephemeral=True,
            delete_after=60.0
        )
        edit_mock.assert_called_once_with(
            content="Updated message",
            delete_after=60.0
        )

    @pytest.mark.asyncio
    async def test_multiple_followup_sends(self) -> None:
        """Test multiple followup sends with ephemeral deletion."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import send_ephemeral_with_deletion
        
        interaction = create_mock_interaction(is_response_done=True)
        
        # Mock followup to use instead of response
        followup_mock = AsyncMock()
        interaction.followup.send = followup_mock
        
        # Send multiple followup messages
        await send_ephemeral_with_deletion(interaction, content="First followup")
        await send_ephemeral_with_deletion(interaction, content="Second followup")
        
        # Verify both followup calls (without delete_after since it's removed for webhook compatibility)
        expected_calls = [
            call(content="First followup", ephemeral=True),
            call(content="Second followup", ephemeral=True)
        ]
        followup_mock.assert_has_calls(expected_calls)
        assert followup_mock.call_count == 2


class TestEphemeralUtilsParameterValidation:
    """Test cases for parameter validation in ephemeral utilities."""

    @pytest.mark.asyncio
    async def test_send_ephemeral_requires_content_or_embed(self) -> None:
        """Test that send_ephemeral_with_deletion requires content or embed."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import send_ephemeral_with_deletion
        
        interaction = create_mock_interaction()
        
        # Test without content or embed - should raise ValueError
        with pytest.raises(ValueError, match="Must provide either content or embed"):
            await send_ephemeral_with_deletion(interaction)

    @pytest.mark.asyncio
    async def test_edit_ephemeral_allows_empty_parameters(self) -> None:
        """Test that edit_ephemeral_with_deletion allows empty parameters for clearing."""
        from src.tgraph_bot.utils.discord.ephemeral_utils import edit_ephemeral_with_deletion
        
        interaction = create_mock_interaction()
        
        # Mock edit_original_response method
        edit_mock = AsyncMock()
        interaction.edit_original_response = edit_mock
        
        # Test with no content parameters (should work for clearing)
        await edit_ephemeral_with_deletion(interaction)
        
        # Verify edit was called with just delete_after
        edit_mock.assert_called_once_with(delete_after=60.0)

