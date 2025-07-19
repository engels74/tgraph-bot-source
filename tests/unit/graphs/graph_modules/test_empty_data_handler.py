"""
Tests for the EmptyDataHandler utility.

This module provides comprehensive test coverage for the EmptyDataHandler class,
ensuring that all empty data handling functionality works correctly across
different scenarios and edge cases.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.tgraph_bot.graphs.graph_modules import EmptyDataHandler


class TestEmptyDataHandler:
    """Test cases for the EmptyDataHandler class."""
    
    def test_init(self) -> None:
        """Test EmptyDataHandler initialization."""
        handler = EmptyDataHandler()
        assert handler is not None
    
    def test_display_empty_data_message_with_defaults(self) -> None:
        """Test empty data message display with default parameters."""
        handler = EmptyDataHandler()
        mock_ax = MagicMock()
        
        handler.display_empty_data_message(mock_ax)
        
        # Verify text was called with correct default parameters
        mock_ax.text.assert_called_once_with(
            0.5, 0.5,
            "No data available\nfor the selected time period",
            ha="center", va="center",
            transform=mock_ax.transAxes,
            fontsize=16,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.7)
        )
        
        # Verify title was not set (default behavior)
        mock_ax.set_title.assert_not_called()
        
        # Verify axes was not cleared (default behavior)
        mock_ax.clear.assert_not_called()
    
    def test_display_empty_data_message_with_custom_parameters(self) -> None:
        """Test empty data message display with custom parameters."""
        handler = EmptyDataHandler()
        mock_ax = MagicMock()
        
        handler.display_empty_data_message(
            mock_ax,
            message="Custom empty message",
            fontsize=20,
            fontweight="normal",
            alpha=0.5,
            facecolor="red",
            boxstyle="square,pad=1.0",
            clear_axes=True,
            set_title="Custom Title",
            log_warning=False
        )
        
        # Verify text was called with custom parameters
        mock_ax.text.assert_called_once_with(
            0.5, 0.5,
            "Custom empty message",
            ha="center", va="center",
            transform=mock_ax.transAxes,
            fontsize=20,
            fontweight="normal",
            bbox=dict(boxstyle="square,pad=1.0", facecolor="red", alpha=0.5)
        )
        
        # Verify title was set
        mock_ax.set_title.assert_called_once_with(
            "Custom Title", fontsize=18, fontweight="bold"
        )
        
        # Verify axes was cleared
        mock_ax.clear.assert_called_once()
    
    def test_display_empty_data_message_with_none_axes(self) -> None:
        """Test empty data message display when axes is None."""
        handler = EmptyDataHandler()
        
        with patch('src.tgraph_bot.graphs.graph_modules.data.empty_data_handler.logger') as mock_logger:
            handler.display_empty_data_message(None)
            mock_logger.warning.assert_called_once_with(
                "Cannot display empty data message: axes is None"
            )
    
    @patch('src.tgraph_bot.graphs.graph_modules.data.empty_data_handler.logger')
    def test_display_empty_data_message_logging(self, mock_logger: MagicMock) -> None:
        """Test logging behavior for empty data message display."""
        handler = EmptyDataHandler()
        mock_ax = MagicMock()
        
        # Test default logging
        handler.display_empty_data_message(mock_ax)
        mock_logger.warning.assert_called_once()
        
        # Reset mock
        mock_logger.reset_mock()
        
        # Test custom log message
        handler.display_empty_data_message(
            mock_ax, 
            log_message="Custom log message"
        )
        mock_logger.warning.assert_called_once_with("Custom log message")
        
        # Reset mock
        mock_logger.reset_mock()
        
        # Test disabled logging
        handler.display_empty_data_message(mock_ax, log_warning=False)
        mock_logger.warning.assert_not_called()
    
    @patch('src.tgraph_bot.graphs.graph_modules.data.empty_data_handler.translate')
    def test_display_localized_empty_data_message_success(self, mock_translate: MagicMock) -> None:
        """Test localized empty data message display with successful translation."""
        handler = EmptyDataHandler()
        mock_ax = MagicMock()
        mock_translate.return_value = "Translated message"
        
        handler.display_localized_empty_data_message(
            mock_ax,
            "test_message_key",
            param1="value1",
            param2="value2"
        )
        
        # Verify translation was called with correct parameters
        mock_translate.assert_called_once_with(
            "test_message_key",
            param1="value1",
            param2="value2"
        )
        
        # Verify text was called with translated message
        mock_ax.text.assert_called_once_with(
            0.5, 0.5,
            "Translated message",
            ha="center", va="center",
            transform=mock_ax.transAxes,
            fontsize=16,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.7)
        )
    
    @patch('src.tgraph_bot.graphs.graph_modules.data.empty_data_handler.translate')
    @patch('src.tgraph_bot.graphs.graph_modules.data.empty_data_handler.logger')
    def test_display_localized_empty_data_message_translation_failure(
        self, mock_logger: MagicMock, mock_translate: MagicMock
    ) -> None:
        """Test localized empty data message display when translation fails."""
        handler = EmptyDataHandler()
        mock_ax = MagicMock()
        mock_translate.side_effect = Exception("Translation error")

        handler.display_localized_empty_data_message(
            mock_ax,
            "test_message_key"
        )

        # Verify translation failure was logged (should be called twice - once for translation failure, once for empty data)
        assert mock_logger.warning.call_count == 2  # pyright: ignore[reportUnknownMemberType]

        # Check that the first call was for translation failure
        first_call = mock_logger.warning.call_args_list[0][0][0]  # pyright: ignore[reportUnknownMemberType]
        assert "Failed to translate message key 'test_message_key'" in first_call  # pyright: ignore[reportUnknownArgumentType]

        # Verify fallback message was used
        mock_ax.text.assert_called_once_with(  # pyright: ignore[reportUnknownMemberType]
            0.5, 0.5,
            "No data available\nfor the selected time period",
            ha="center", va="center",
            transform=mock_ax.transAxes,  # pyright: ignore[reportUnknownMemberType]
            fontsize=16,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.7)
        )
    
    def test_get_standard_empty_message_known_types(self) -> None:
        """Test getting standard empty messages for known graph types."""
        handler = EmptyDataHandler()
        
        # Test play data types
        play_data_types = ["play_data", "daily", "monthly", "hourly", "dayofweek"]
        for graph_type in play_data_types:
            message = handler.get_standard_empty_message(graph_type)
            assert message == "No play data available\nfor the selected time period"
        
        # Test user data types
        user_data_types = ["user_data", "users"]
        for graph_type in user_data_types:
            message = handler.get_standard_empty_message(graph_type)
            assert message == "No user data available\nfor the selected time period"
        
        # Test platform data types
        platform_data_types = ["platform_data", "platforms"]
        for graph_type in platform_data_types:
            message = handler.get_standard_empty_message(graph_type)
            assert message == "No platform data available"
    
    def test_get_standard_empty_message_unknown_type(self) -> None:
        """Test getting standard empty message for unknown graph type."""
        handler = EmptyDataHandler()
        
        message = handler.get_standard_empty_message("unknown_type")
        assert message == "No data available\nfor the selected time period"
    
    def test_clear_axes_for_empty_data(self) -> None:
        """Test clearing axes for empty data display."""
        handler = EmptyDataHandler()
        mock_ax = MagicMock()
        
        handler.clear_axes_for_empty_data(mock_ax)
        
        # Verify all clearing operations were called
        mock_ax.clear.assert_called_once()
        mock_ax.set_xlim.assert_called_once_with(0, 1)
        mock_ax.set_ylim.assert_called_once_with(0, 1)
        mock_ax.set_xticks.assert_called_once_with([])
        mock_ax.set_yticks.assert_called_once_with([])
    
    def test_clear_axes_for_empty_data_with_none_axes(self) -> None:
        """Test clearing axes when axes is None."""
        handler = EmptyDataHandler()
        
        with patch('src.tgraph_bot.graphs.graph_modules.data.empty_data_handler.logger') as mock_logger:
            handler.clear_axes_for_empty_data(None)
            mock_logger.warning.assert_called_once_with(
                "Cannot clear axes: axes is None"
            )
    
    def test_default_constants(self) -> None:
        """Test that default constants are properly defined."""
        handler = EmptyDataHandler()
        
        # Test message constants
        assert handler.DEFAULT_MESSAGE == "No data available\nfor the selected time period"
        assert handler.DEFAULT_PLAY_DATA_MESSAGE == "No play data available\nfor the selected time period"
        assert handler.DEFAULT_USER_DATA_MESSAGE == "No user data available\nfor the selected time period"
        assert handler.DEFAULT_PLATFORM_DATA_MESSAGE == "No platform data available"
        
        # Test styling constants
        assert handler.DEFAULT_FONTSIZE == 16
        assert handler.DEFAULT_FONTWEIGHT == "bold"
        assert handler.DEFAULT_ALPHA == 0.7
        assert handler.DEFAULT_FACECOLOR == "lightgray"
        assert handler.DEFAULT_BOXSTYLE == "round,pad=0.5"
