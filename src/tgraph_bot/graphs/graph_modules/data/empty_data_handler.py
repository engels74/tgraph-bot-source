"""
Empty data handler for TGraph Bot graph generation.

This module provides utilities for handling and displaying empty data scenarios
in graph generation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import matplotlib.axes

logger = logging.getLogger(__name__)


class EmptyDataHandler:
    """Handler for empty data scenarios in graph generation."""

    # Default styling constants
    DEFAULT_FONTSIZE: int = 16
    DEFAULT_FONTWEIGHT: str = "bold"
    DEFAULT_ALPHA: float = 0.7
    DEFAULT_FACECOLOR: str = "lightgray"
    DEFAULT_BOXSTYLE: str = "round,pad=0.5"

    # Default message constants
    DEFAULT_MESSAGE: str = "No data available\nfor the selected time period"
    DEFAULT_PLATFORM_DATA_MESSAGE: str = "No platform data available"
    DEFAULT_PLAY_DATA_MESSAGE: str = "No play data available"
    DEFAULT_USER_DATA_MESSAGE: str = "No user data available"

    def display_empty_data_message(
        self,
        ax: matplotlib.axes.Axes | None,
        message: str | None = None,
        fontsize: int | None = None,
        fontweight: str | None = None,
        set_title: bool = False,
        title: str = "",
        clear_axes: bool = False,
        log_message: bool = True,
        log_warning: bool = True,
    ) -> None:
        """
        Display an empty data message on the given axes.

        Args:
            ax: Matplotlib axes to display the message on
            message: Message to display
            fontsize: Font size for the message
            fontweight: Font weight for the message
            set_title: Whether to set a title on the axes
            title: Title to set if set_title is True
            clear_axes: Whether to clear the axes before displaying message
            log_message: Whether to log informational messages
            log_warning: Whether to log warning messages
        """
        if ax is None:
            if log_warning:
                logger.warning("Cannot display empty data message: axes is None")
            return

        # Use defaults if not provided
        message = message or self.DEFAULT_MESSAGE
        fontsize = fontsize or self.DEFAULT_FONTSIZE
        fontweight = fontweight or self.DEFAULT_FONTWEIGHT

        if log_message:
            logger.info("Displaying empty data message: %s", message)

        if clear_axes:
            ax.clear()

        if set_title and title:
            _ = ax.set_title(title)  # pyright: ignore[reportUnknownMemberType] # matplotlib method

        _ = ax.text(  # pyright: ignore[reportUnknownMemberType] # matplotlib method
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=fontsize,
            fontweight=fontweight,
            bbox=dict(
                boxstyle=self.DEFAULT_BOXSTYLE,
                facecolor=self.DEFAULT_FACECOLOR,
                alpha=self.DEFAULT_ALPHA,
            ),
        )

    def is_data_empty(self, data: object) -> bool:
        """
        Check if data is considered empty for graph generation.

        Args:
            data: Data to check

        Returns:
            True if data is empty, False otherwise
        """
        if data is None:
            return True

        if isinstance(data, (list, dict, str)):
            return len(data) == 0  # pyright: ignore[reportUnknownArgumentType] # validated types above

        return False

    def has_sufficient_data(self, data: object, min_count: int = 1) -> bool:
        """
        Check if data has sufficient entries for graph generation.

        Args:
            data: Data to check
            min_count: Minimum number of entries required

        Returns:
            True if data has sufficient entries, False otherwise
        """
        if self.is_data_empty(data):
            return False

        if isinstance(data, (list, dict)):
            return len(data) >= min_count  # pyright: ignore[reportUnknownArgumentType] # validated types above

        return True

    def display_localized_empty_data_message(
        self,
        ax: matplotlib.axes.Axes,
        message_key: str = "default",
        **kwargs: Any,  # pyright: ignore[reportExplicitAny,reportAny] # flexible kwargs for display parameters
    ) -> None:
        """
        Display a localized empty data message.

        Args:
            ax: Matplotlib axes to display the message on
            message_key: Key to determine which message to display
            **kwargs: Additional arguments passed to display_empty_data_message
        """
        # Map message keys to actual messages
        message_map = {
            "default": self.DEFAULT_MESSAGE,
            "platform": self.DEFAULT_PLATFORM_DATA_MESSAGE,
            "play": self.DEFAULT_PLAY_DATA_MESSAGE,
            "user": self.DEFAULT_USER_DATA_MESSAGE,
        }

        message = message_map.get(message_key, self.DEFAULT_MESSAGE)
        self.display_empty_data_message(ax, message=message, **kwargs)  # pyright: ignore[reportAny] # flexible kwargs for display parameters

    def get_standard_empty_message(self, message_type: str = "default") -> str:
        """
        Get a standard empty data message by type.

        Args:
            message_type: Type of message to retrieve

        Returns:
            The appropriate empty data message
        """
        message_map = {
            "default": self.DEFAULT_MESSAGE,
            "platform": self.DEFAULT_PLATFORM_DATA_MESSAGE,
            "play": self.DEFAULT_PLAY_DATA_MESSAGE,
            "user": self.DEFAULT_USER_DATA_MESSAGE,
        }
        return message_map.get(message_type, self.DEFAULT_MESSAGE)

    def clear_axes_for_empty_data(self, ax: matplotlib.axes.Axes | None) -> None:
        """
        Clear axes in preparation for empty data display.

        Args:
            ax: Matplotlib axes to clear
        """
        if ax is None:
            logger.warning("Cannot clear axes for empty data: axes is None")
            return

        ax.clear()
        _ = ax.set_xticks([])  # pyright: ignore[reportAny] # matplotlib method
        _ = ax.set_yticks([])  # pyright: ignore[reportAny] # matplotlib method
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)
