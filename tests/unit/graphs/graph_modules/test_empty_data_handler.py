"""
Tests for the EmptyDataHandler utility.

This module provides comprehensive test coverage for the EmptyDataHandler class,
ensuring that all empty data handling functionality works correctly across
different scenarios and edge cases.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


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
        mock_ax.text.assert_called_once_with(  # pyright: ignore[reportAny]
            0.5,
            0.5,
            "No data available\nfor the selected time period",
            ha="center",
            va="center",
            transform=mock_ax.transAxes,  # pyright: ignore[reportAny]
            fontsize=16,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.7),
        )

        # Verify title was not set (default behavior)
        mock_ax.set_title.assert_not_called()  # pyright: ignore[reportAny]

        # Verify axes was not cleared (default behavior)
        mock_ax.clear.assert_not_called()  # pyright: ignore[reportAny]

    def test_display_empty_data_message_with_custom_parameters(self) -> None:
        """Test empty data message display with custom parameters."""
        handler = EmptyDataHandler()
        mock_ax = MagicMock()

        handler.display_empty_data_message(
            mock_ax,
            message="Custom empty message",
            fontsize=20,
            fontweight="normal",
            clear_axes=True,
            set_title=True,
            title="Custom Title",
        )

        # Verify text was called with custom parameters
        mock_ax.text.assert_called_once_with(  # pyright: ignore[reportAny]
            0.5,
            0.5,
            "Custom empty message",
            ha="center",
            va="center",
            transform=mock_ax.transAxes,  # pyright: ignore[reportAny]
            fontsize=20,
            fontweight="normal",
            bbox=dict(
                boxstyle=handler.DEFAULT_BOXSTYLE,
                facecolor=handler.DEFAULT_FACECOLOR,
                alpha=handler.DEFAULT_ALPHA,
            ),
        )

        # Verify title was set
        mock_ax.set_title.assert_called_once_with("Custom Title")  # pyright: ignore[reportAny]

        # Verify axes was cleared
        mock_ax.clear.assert_called_once()  # pyright: ignore[reportAny]

    def test_display_empty_data_message_with_none_axes(self) -> None:
        """Test empty data message display when axes is None."""
        handler = EmptyDataHandler()

        with patch(
            "src.tgraph_bot.graphs.graph_modules.data.empty_data_handler.logger"
        ) as mock_logger:
            handler.display_empty_data_message(None)
            mock_logger.warning.assert_called_once_with(  # pyright: ignore[reportAny]
                "Cannot display empty data message: axes is None"
            )

    @patch("src.tgraph_bot.graphs.graph_modules.data.empty_data_handler.logger")
    def test_display_empty_data_message_logging(self, mock_logger: MagicMock) -> None:
        """Test logging behavior for empty data message display."""
        handler = EmptyDataHandler()
        mock_ax = MagicMock()

        # Test default logging (info message)
        handler.display_empty_data_message(mock_ax)
        mock_logger.info.assert_called_once()  # pyright: ignore[reportAny]

        # Reset mock
        mock_logger.reset_mock()

        # Test disabled logging
        handler.display_empty_data_message(mock_ax, log_message=False)
        mock_logger.info.assert_not_called()  # pyright: ignore[reportAny]

        # Reset mock
        mock_logger.reset_mock()

        # Test warning disabled
        handler.display_empty_data_message(mock_ax, log_warning=False)
        mock_logger.warning.assert_not_called()  # pyright: ignore[reportAny]

    def test_display_localized_empty_data_message_success(self) -> None:
        """Test localized empty data message display with successful message key mapping."""
        handler = EmptyDataHandler()
        mock_ax = MagicMock()

        handler.display_localized_empty_data_message(mock_ax, "platform")

        # Verify text was called with platform message
        mock_ax.text.assert_called_once_with(  # pyright: ignore[reportAny]
            0.5,
            0.5,
            "No platform data available",
            ha="center",
            va="center",
            transform=mock_ax.transAxes,  # pyright: ignore[reportAny]
            fontsize=16,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.7),
        )

    def test_display_localized_empty_data_message_translation_failure(self) -> None:
        """Test localized empty data message display when unknown message key is used."""
        handler = EmptyDataHandler()
        mock_ax = MagicMock()

        # Test with unknown message key - should fallback to default
        handler.display_localized_empty_data_message(mock_ax, "unknown_key")

        # Verify fallback message was used
        mock_ax.text.assert_called_once_with(  # pyright: ignore[reportAny]
            0.5,
            0.5,
            "No data available\nfor the selected time period",
            ha="center",
            va="center",
            transform=mock_ax.transAxes,  # pyright: ignore[reportAny]
            fontsize=16,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.7),
        )

    def test_get_standard_empty_message_known_types(self) -> None:
        """Test getting standard empty messages for known graph types."""
        handler = EmptyDataHandler()

        # Test play data type
        message = handler.get_standard_empty_message("play")
        assert message == "No play data available"

        # Test user data type
        message = handler.get_standard_empty_message("user")
        assert message == "No user data available"

        # Test platform data type
        message = handler.get_standard_empty_message("platform")
        assert message == "No platform data available"

        # Test default fallback for unknown types
        unknown_types = [
            "play_data",
            "daily",
            "monthly",
            "hourly",
            "dayofweek",
            "user_data",
            "users",
            "platform_data",
            "platforms",
        ]
        for graph_type in unknown_types:
            message = handler.get_standard_empty_message(graph_type)
            assert message == "No data available\nfor the selected time period"

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

        # Verify clearing operations were called
        mock_ax.clear.assert_called_once()  # pyright: ignore[reportAny]
        mock_ax.set_xticks.assert_called_once_with([])  # pyright: ignore[reportAny]
        mock_ax.set_yticks.assert_called_once_with([])  # pyright: ignore[reportAny]

        # Verify spines were made invisible
        mock_ax.spines.__getitem__.assert_any_call("top")  # pyright: ignore[reportAny]
        mock_ax.spines.__getitem__.assert_any_call("right")  # pyright: ignore[reportAny]
        mock_ax.spines.__getitem__.assert_any_call("bottom")  # pyright: ignore[reportAny]
        mock_ax.spines.__getitem__.assert_any_call("left")  # pyright: ignore[reportAny]

    def test_clear_axes_for_empty_data_with_none_axes(self) -> None:
        """Test clearing axes when axes is None."""
        handler = EmptyDataHandler()

        with patch(
            "src.tgraph_bot.graphs.graph_modules.data.empty_data_handler.logger"
        ) as mock_logger:
            handler.clear_axes_for_empty_data(None)
            mock_logger.warning.assert_called_once_with(  # pyright: ignore[reportAny]
                "Cannot clear axes for empty data: axes is None"
            )

    def test_default_constants(self) -> None:
        """Test that default constants are properly defined."""
        handler = EmptyDataHandler()

        # Test message constants
        assert (
            handler.DEFAULT_MESSAGE == "No data available\nfor the selected time period"
        )
        assert handler.DEFAULT_PLAY_DATA_MESSAGE == "No play data available"
        assert handler.DEFAULT_USER_DATA_MESSAGE == "No user data available"
        assert handler.DEFAULT_PLATFORM_DATA_MESSAGE == "No platform data available"

        # Test styling constants
        assert handler.DEFAULT_FONTSIZE == 16
        assert handler.DEFAULT_FONTWEIGHT == "bold"
        assert handler.DEFAULT_ALPHA == 0.7
        assert handler.DEFAULT_FACECOLOR == "lightgray"
        assert handler.DEFAULT_BOXSTYLE == "round,pad=0.5"
