"""
Empty data handler utility for graph modules.

This module provides a centralized utility for handling empty data scenarios
across all graph implementations. It consolidates the various empty data
handling patterns found in the codebase into a single, reusable utility.

The EmptyDataHandler eliminates DRY violations by providing:
- Standardized empty data message display
- Configurable message content and styling
- Localization support for user-facing messages
- Integration with matplotlib axes and visualization patterns
- Consistent logging for empty data scenarios

Usage Examples:
    Basic usage with default message:
        >>> handler = EmptyDataHandler()
        >>> handler.display_empty_data_message(ax)

    Custom message with styling:
        >>> handler = EmptyDataHandler()
        >>> handler.display_empty_data_message(
        ...     ax, 
        ...     message="No user data available",
        ...     fontsize=18,
        ...     alpha=0.8
        ... )

    With localization:
        >>> handler = EmptyDataHandler()
        >>> handler.display_localized_empty_data_message(
        ...     ax,
        ...     message_key="no_play_data_available",
        ...     time_period="selected time period"
        ... )
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, final

from ...i18n import translate

if TYPE_CHECKING:
    from matplotlib.axes import Axes

logger = logging.getLogger(__name__)


class AxesProtocol(Protocol):
    """Protocol for matplotlib axes objects."""
    
    def text(
        self,
        x: float,
        y: float,
        s: str,
        *,
        ha: str = "center",
        va: str = "center",
        transform: object = None,
        fontsize: int = 14,
        fontweight: str = "normal",
        bbox: dict[str, object] | None = None,
    ) -> object:
        """Add text to the axes."""
        ...
    
    def set_title(
        self,
        label: str,
        *,
        fontsize: int = 12,
        fontweight: str = "normal",
    ) -> object:
        """Set the title of the axes."""
        ...
    
    def clear(self) -> None:
        """Clear the axes."""
        ...
    
    def set_xlim(self, left: float, right: float) -> None:
        """Set x-axis limits."""
        ...
    
    def set_ylim(self, bottom: float, top: float) -> None:
        """Set y-axis limits."""
        ...
    
    def set_xticks(self, ticks: list[float]) -> None:
        """Set x-axis tick locations."""
        ...
    
    def set_yticks(self, ticks: list[float]) -> None:
        """Set y-axis tick locations."""
        ...
    
    @property
    def transAxes(self) -> object:
        """Transform for axes coordinates."""
        ...


@final
class EmptyDataHandler:
    """
    Centralized utility for handling empty data scenarios in graph generation.
    
    This class consolidates the various empty data handling patterns found across
    graph implementations, providing a standardized approach to displaying
    user-friendly messages when no data is available.
    
    The handler supports:
    - Customizable message content and styling
    - Localization through the i18n system
    - Integration with matplotlib axes
    - Consistent logging patterns
    - Configurable visual styling options
    """
    
    # Default message constants
    DEFAULT_MESSAGE = "No data available\nfor the selected time period"
    DEFAULT_PLAY_DATA_MESSAGE = "No play data available\nfor the selected time period"
    DEFAULT_USER_DATA_MESSAGE = "No user data available\nfor the selected time period"
    DEFAULT_PLATFORM_DATA_MESSAGE = "No platform data available"
    
    # Default styling constants
    DEFAULT_FONTSIZE = 16
    DEFAULT_FONTWEIGHT = "bold"
    DEFAULT_ALPHA = 0.7
    DEFAULT_FACECOLOR = "lightgray"
    DEFAULT_BOXSTYLE = "round,pad=0.5"
    
    def __init__(self) -> None:
        """Initialize the EmptyDataHandler."""
        pass
    
    def display_empty_data_message(
        self,
        ax: Axes | AxesProtocol | None,
        message: str | None = None,
        *,
        fontsize: int | None = None,
        fontweight: str | None = None,
        alpha: float | None = None,
        facecolor: str | None = None,
        boxstyle: str | None = None,
        clear_axes: bool = False,
        set_title: str | None = None,
        log_warning: bool = True,
        log_message: str | None = None,
    ) -> None:
        """
        Display a standardized empty data message on the provided axes.
        
        This method consolidates the empty data display patterns found across
        graph implementations, providing consistent styling and behavior.
        
        Args:
            ax: The matplotlib axes to display the message on
            message: Custom message to display (uses default if None)
            fontsize: Font size for the message text
            fontweight: Font weight for the message text
            alpha: Transparency level for the message box background
            facecolor: Background color for the message box
            boxstyle: Style for the message box border
            clear_axes: Whether to clear axes content before displaying message
            set_title: Optional title to set on the axes
            log_warning: Whether to log a warning message
            log_message: Custom log message (uses default if None)
        """
        if ax is None:
            logger.warning("Cannot display empty data message: axes is None")
            return
        
        # Use default values if not provided
        message = message or self.DEFAULT_MESSAGE
        fontsize = fontsize or self.DEFAULT_FONTSIZE
        fontweight = fontweight or self.DEFAULT_FONTWEIGHT
        alpha = alpha or self.DEFAULT_ALPHA
        facecolor = facecolor or self.DEFAULT_FACECOLOR
        boxstyle = boxstyle or self.DEFAULT_BOXSTYLE
        
        # Clear axes if requested (some implementations need this)
        if clear_axes:
            ax.clear()
        
        # Display the message with consistent styling
        _ = ax.text(  # pyright: ignore[reportUnknownMemberType]
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=fontsize,
            fontweight=fontweight,
            bbox=dict(boxstyle=boxstyle, facecolor=facecolor, alpha=alpha),
        )

        # Set title if provided
        if set_title:
            _ = ax.set_title(set_title, fontsize=18, fontweight="bold")  # pyright: ignore[reportUnknownMemberType]
        
        # Log warning if requested
        if log_warning:
            log_msg = log_message or f"Generated empty graph due to no data: {message}"
            logger.warning(log_msg)
    
    def display_localized_empty_data_message(
        self,
        ax: Axes | AxesProtocol | None,
        message_key: str,
        *,
        fontsize: int | None = None,
        fontweight: str | None = None,
        alpha: float | None = None,
        facecolor: str | None = None,
        boxstyle: str | None = None,
        clear_axes: bool = False,
        set_title: str | None = None,
        log_warning: bool = True,
        log_message: str | None = None,
        **format_kwargs: object,
    ) -> None:
        """
        Display a localized empty data message using the i18n system.
        
        This method provides localization support for empty data messages,
        allowing for internationalized user experiences.
        
        Args:
            ax: The matplotlib axes to display the message on
            message_key: Translation key for the message
            fontsize: Font size for the message text
            fontweight: Font weight for the message text
            alpha: Transparency level for the message box background
            facecolor: Background color for the message box
            boxstyle: Style for the message box border
            clear_axes: Whether to clear axes content before displaying message
            set_title: Optional title to set on the axes
            log_warning: Whether to log a warning message
            log_message: Custom log message (uses default if None)
            **format_kwargs: Additional formatting arguments for translation
        """
        # Translate the message
        try:
            translated_message = translate(message_key, **format_kwargs)
        except Exception as e:
            logger.warning(f"Failed to translate message key '{message_key}': {e}")
            translated_message = self.DEFAULT_MESSAGE
        
        # Use the standard display method with the translated message
        self.display_empty_data_message(
            ax,
            message=translated_message,
            fontsize=fontsize,
            fontweight=fontweight,
            alpha=alpha,
            facecolor=facecolor,
            boxstyle=boxstyle,
            clear_axes=clear_axes,
            set_title=set_title,
            log_warning=log_warning,
            log_message=log_message,
        )
    
    def get_standard_empty_message(self, graph_type: str) -> str:
        """
        Get a standard empty data message for a specific graph type.
        
        This method provides consistent messaging across different graph types
        while allowing for type-specific customization.
        
        Args:
            graph_type: Type of graph (e.g., "play_data", "user_data", "platform_data")
            
        Returns:
            Appropriate empty data message for the graph type
        """
        message_map = {
            "play_data": self.DEFAULT_PLAY_DATA_MESSAGE,
            "user_data": self.DEFAULT_USER_DATA_MESSAGE,
            "platform_data": self.DEFAULT_PLATFORM_DATA_MESSAGE,
            "daily": self.DEFAULT_PLAY_DATA_MESSAGE,
            "monthly": self.DEFAULT_PLAY_DATA_MESSAGE,
            "hourly": self.DEFAULT_PLAY_DATA_MESSAGE,
            "dayofweek": self.DEFAULT_PLAY_DATA_MESSAGE,
            "users": self.DEFAULT_USER_DATA_MESSAGE,
            "platforms": self.DEFAULT_PLATFORM_DATA_MESSAGE,
        }
        
        return message_map.get(graph_type, self.DEFAULT_MESSAGE)
    
    def clear_axes_for_empty_data(self, ax: Axes | AxesProtocol | None) -> None:
        """
        Clear axes content and prepare for empty data display.
        
        This method provides a standardized way to clear axes content
        when displaying empty data messages, ensuring consistent
        empty data presentation across graph implementations.
        
        Args:
            ax: The matplotlib axes to clear
        """
        if ax is None:
            logger.warning("Cannot clear axes: axes is None")
            return
        
        ax.clear()
        _ = ax.set_xlim(0, 1)
        _ = ax.set_ylim(0, 1)
        _ = ax.set_xticks([])  # pyright: ignore[reportUnknownMemberType]
        _ = ax.set_yticks([])  # pyright: ignore[reportUnknownMemberType]
