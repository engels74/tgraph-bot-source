"""
Visualization mixin for common matplotlib and seaborn operations.

This module provides a mixin class that consolidates common visualization patterns
used across all graph implementations in the TGraph Bot system. It addresses
DRY violations by extracting repeated matplotlib setup, seaborn styling,
and common visualization patterns into reusable methods.
"""

import logging
from typing import TYPE_CHECKING, Literal, Protocol
from collections.abc import Sequence

import matplotlib.axes
import matplotlib.figure
import seaborn as sns

if TYPE_CHECKING:
    from ....config.schema import TGraphBotConfig

# Suppress matplotlib categorical units warnings early
# These warnings occur when seaborn/matplotlib detects numeric-looking strings
_matplotlib_category_logger = logging.getLogger("matplotlib.category")
_matplotlib_category_logger.setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class VisualizationProtocol(Protocol):
    """Protocol defining the interface required by VisualizationMixin."""

    config: "TGraphBotConfig | dict[str, object] | None"
    axes: matplotlib.axes.Axes | None
    figure: matplotlib.figure.Figure | None

    def get_grid_enabled(self) -> bool:
        """Check if grid should be enabled for this graph."""
        ...

    def get_tv_color(self) -> str:
        """Get the configured TV color."""
        ...

    def get_movie_color(self) -> str:
        """Get the configured movie color."""
        ...

    def get_title(self) -> str:
        """Get the title for this graph."""
        ...

    def setup_figure(self) -> tuple[matplotlib.figure.Figure, matplotlib.axes.Axes]:
        """Set up matplotlib figure and axes."""
        ...


class VisualizationMixin:
    """
    Mixin class providing common visualization functionality.

    This mixin consolidates common matplotlib and seaborn setup patterns
    that are repeated across all graph implementations. It provides
    standardized methods for:
    - Grid-aware seaborn styling
    - Title and axis configuration
    - Empty data message display
    - Layout finalization

    The mixin requires the implementing class to have certain attributes
    and methods as defined by the VisualizationProtocol.
    """

    def configure_seaborn_style_with_grid(self: VisualizationProtocol) -> None:
        """
        Configure seaborn style with grid awareness.

        This method applies seaborn styling based on the grid configuration,
        using "whitegrid" when grid is enabled and "white" when disabled.
        This pattern is repeated across all Tautulli graph implementations.
        """
        if self.get_grid_enabled():
            sns.set_style("whitegrid")
        else:
            sns.set_style("white")

    def setup_standard_title_and_axes(
        self: VisualizationProtocol,
        title: str | None = None,
        xlabel: str | None = None,
        ylabel: str | None = None,
        title_fontsize: int = 18,
        label_fontsize: int = 12,
        title_pad: int = 20,
    ) -> None:
        """
        Set up standard title and axis labels with consistent formatting.

        This method applies the common title and axis configuration pattern
        used across all graph implementations, with customizable parameters.

        Args:
            title: Graph title (uses get_title() if None)
            xlabel: X-axis label (optional)
            ylabel: Y-axis label (optional)
            title_fontsize: Font size for the title
            label_fontsize: Font size for axis labels
            title_pad: Padding for the title
        """
        if self.axes is None:
            logger.warning("Cannot setup title and axes: axes is None")
            return

        # Set title
        display_title = title if title is not None else self.get_title()
        _ = self.axes.set_title(  # pyright: ignore[reportUnknownMemberType]
            display_title,
            fontsize=title_fontsize,
            fontweight="bold",
            pad=title_pad,
        )

        # Set axis labels if provided
        if xlabel is not None:
            _ = self.axes.set_xlabel(xlabel, fontsize=label_fontsize)  # pyright: ignore[reportUnknownMemberType]
        if ylabel is not None:
            _ = self.axes.set_ylabel(ylabel, fontsize=label_fontsize)  # pyright: ignore[reportUnknownMemberType]

    def setup_title_and_axes_with_ax(
        self: VisualizationProtocol,
        ax: matplotlib.axes.Axes,
        title: str | None = None,
        xlabel: str | None = None,
        ylabel: str | None = None,
        title_fontsize: int = 18,
        label_fontsize: int = 14,
        title_pad: int = 20,
    ) -> None:
        """
        Set up standard title and axis labels with consistent formatting on a specific axes.

        This method applies the same formatting as setup_standard_title_and_axes
        but works with a provided axes object instead of self.axes.

        Args:
            ax: The matplotlib axes to configure
            title: Graph title (uses get_title() if None)
            xlabel: X-axis label (optional)
            ylabel: Y-axis label (optional)
            title_fontsize: Font size for the title
            label_fontsize: Font size for axis labels
            title_pad: Padding for the title
        """
        # Set title
        display_title = title if title is not None else self.get_title()
        _ = ax.set_title(  # pyright: ignore[reportUnknownMemberType]
            display_title,
            fontsize=title_fontsize,
            fontweight="bold",
            pad=title_pad,
        )

        # Set axis labels if provided
        if xlabel is not None:
            _ = ax.set_xlabel(xlabel, fontsize=label_fontsize, fontweight="bold")  # pyright: ignore[reportUnknownMemberType]
        if ylabel is not None:
            _ = ax.set_ylabel(ylabel, fontsize=label_fontsize, fontweight="bold")  # pyright: ignore[reportUnknownMemberType]

    def get_media_type_display_info(
        self: VisualizationProtocol, media_type: str
    ) -> tuple[str, str]:
        """
        Get standardized display name and color for a media type.

        This method consolidates the common pattern of getting media type display
        information with config overrides for TV and movie colors.

        Args:
            media_type: The media type to get info for (e.g., "tv", "movie")

        Returns:
            Tuple of (display_name, color) for the media type
        """
        from ..utils.utils import get_media_type_display_info

        display_info = get_media_type_display_info()

        if media_type in display_info:
            label = display_info[media_type]["display_name"]
            color = display_info[media_type]["color"]

            # Override with config colors if available
            if media_type == "tv":
                color = self.get_tv_color()
            elif media_type == "movie":
                color = self.get_movie_color()

            return label, color
        else:
            # Fallback for unknown media types
            return media_type.title(), "#666666"

    def display_no_data_message(
        self: VisualizationProtocol,
        message: str = "No data available\nfor the selected time period",
        fontsize: int = 16,
        alpha: float = 0.7,
    ) -> None:
        """
        Display a standardized "no data" message on the graph.

        This method provides the common pattern for displaying empty data
        messages that is used across multiple graph implementations.

        Args:
            message: Message to display
            fontsize: Font size for the message
            alpha: Transparency level for the message box
        """
        if self.axes is None:
            logger.warning("Cannot display no data message: axes is None")
            return

        _ = self.axes.text(  # pyright: ignore[reportUnknownMemberType]
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            transform=self.axes.transAxes,
            fontsize=fontsize,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=alpha),
        )

    def setup_figure_with_seaborn_grid(
        self: VisualizationProtocol,
    ) -> tuple[matplotlib.figure.Figure, matplotlib.axes.Axes]:
        """
        Set up figure with grid-aware seaborn styling.

        This method combines figure setup with grid-aware seaborn styling,
        providing a common pattern used across graph implementations.

        Returns:
            Tuple of (figure, axes) objects

        Note:
            This method assumes the implementing class has a setup_figure method.
            The return type is Any to avoid circular dependencies.
        """
        # Call setup_figure method on the implementing class
        figure, axes = self.setup_figure()  # type: ignore[attr-defined]

        # Apply grid-aware seaborn styling
        # Apply the same logic as configure_seaborn_style_with_grid
        if self.get_grid_enabled():
            sns.set_style("whitegrid")
        else:
            sns.set_style("white")

        return figure, axes

    def finalize_plot_layout(self: VisualizationProtocol) -> None:
        """
        Finalize plot layout with standard adjustments.

        This method applies common layout finalization patterns used
        across all graph implementations, including tight_layout.

        Note:
            This method assumes the implementing class has a figure attribute.
        """
        if hasattr(self, "figure") and self.figure is not None:
            self.figure.tight_layout()  # type: ignore[attr-defined]
        else:
            logger.warning("Cannot finalize layout: figure is None or not available")

    def configure_standard_grid(
        self: VisualizationProtocol, alpha: float = 0.3
    ) -> None:
        """
        Configure standard grid settings.

        This method applies common grid configuration used across
        graph implementations for better readability.

        Args:
            alpha: Transparency level for the grid
        """
        if self.axes is None:
            logger.warning("Cannot configure grid: axes is None")
            return

        self.axes.grid(True, alpha=alpha)  # pyright: ignore[reportUnknownMemberType]

    def setup_bar_chart_annotations(
        self: VisualizationProtocol,
        bars: Sequence[object],
        values: list[float],
        format_string: str = "{:.0f}",
        fontsize: int = 10,
        rotation: int = 0,
        ha: str = "center",
        va: str = "bottom",
    ) -> None:
        """
        Set up standardized bar chart value annotations.

        This method provides the common pattern for adding value annotations
        to bar charts, which is used across multiple graph implementations.

        Args:
            bars: Matplotlib bar container object
            values: List of values to annotate
            format_string: Format string for value display
            fontsize: Font size for annotations
            rotation: Text rotation angle
            ha: Horizontal alignment
            va: Vertical alignment
        """
        if self.axes is None:
            logger.warning("Cannot setup bar annotations: axes is None")
            return

        for bar, value in zip(bars, values):
            height = getattr(bar, "get_height", lambda: 0)()
            get_x = getattr(bar, "get_x", lambda: 0)
            get_width = getattr(bar, "get_width", lambda: 1)
            _ = self.axes.annotate(  # pyright: ignore[reportUnknownMemberType]
                format_string.format(value),
                xy=(get_x() + get_width() / 2, height),
                xytext=(0, 3),  # 3 points vertical offset
                textcoords="offset points",
                ha=ha,
                va=va,
                fontsize=fontsize,
                rotation=rotation,
            )

    def apply_seaborn_palette(self, palette: str = "husl") -> None:
        """
        Apply a seaborn color palette.

        This method provides a standardized way to apply seaborn color
        palettes across graph implementations.

        Args:
            palette: Seaborn palette name to apply
        """
        sns.set_palette(palette)  # pyright: ignore[reportUnknownMemberType]

    def apply_configured_palette(self: VisualizationProtocol, config_key: str) -> None:
        """
        Apply a seaborn color palette based on configuration.

        This method checks the configuration for a palette setting and applies it
        if found. This provides a DRY way to handle palette configuration across
        different graph types.

        Args:
            config_key: The configuration key to check for palette setting
        """
        if self.config is None:
            return

        # Handle both TGraphBotConfig objects and dict configs
        palette: object = None
        if isinstance(self.config, dict):
            # Handle dict configs
            palette = self.config.get(config_key)
        else:
            # Handle TGraphBotConfig objects
            palette = getattr(self.config, config_key, None)

        if palette and isinstance(palette, str):
            sns.set_palette(palette)  # pyright: ignore[reportUnknownMemberType]

    def configure_tick_parameters(
        self: VisualizationProtocol,
        axis: Literal["x", "y", "both"] = "both",
        labelsize: int = 10,
        rotation: int = 0,
    ) -> None:
        """
        Configure tick parameters with standard settings.

        This method applies common tick parameter configurations used
        across graph implementations.

        Args:
            axis: Which axis to configure ('x', 'y', or 'both')
            labelsize: Font size for tick labels
            rotation: Rotation angle for tick labels
        """
        if self.axes is None:
            logger.warning("Cannot configure tick parameters: axes is None")
            return

        self.axes.tick_params(axis=axis, labelsize=labelsize, rotation=rotation)  # pyright: ignore[reportUnknownMemberType]

    def setup_legend_with_standard_config(
        self: VisualizationProtocol,
        location: str = "best",
        fontsize: int = 10,
        frameon: bool = True,
        fancybox: bool = True,
        shadow: bool = True,
        framealpha: float = 0.9,
    ) -> None:
        """
        Set up legend with standard configuration.

        This method provides standardized legend configuration used
        across graph implementations that include legends.

        Args:
            location: Legend location
            fontsize: Font size for legend text
            frameon: Whether to draw the legend frame
            fancybox: Whether to use rounded corners
            shadow: Whether to draw a shadow
            framealpha: Legend frame transparency
        """
        if self.axes is None:
            logger.warning("Cannot setup legend: axes is None")
            return

        _ = self.axes.legend(  # pyright: ignore[reportUnknownMemberType]
            loc=location,
            fontsize=fontsize,
            frameon=frameon,
            fancybox=fancybox,
            shadow=shadow,
            framealpha=framealpha,
        )

    def clear_axes_for_empty_data(self: VisualizationProtocol) -> None:
        """
        Clear axes content for empty data display.

        This method provides a standardized way to clear axes content
        when displaying empty data messages, ensuring consistent
        empty data presentation across graph implementations.
        """
        if self.axes is None:
            logger.warning("Cannot clear axes: axes is None")
            return

        self.axes.clear()
        _ = self.axes.set_xlim(0, 1)
        _ = self.axes.set_ylim(0, 1)
        _ = self.axes.set_xticks([])  # pyright: ignore[reportAny] # matplotlib method returns Any
        _ = self.axes.set_yticks([])  # pyright: ignore[reportAny] # matplotlib method returns Any

    def setup_time_series_axes(
        self: VisualizationProtocol,
        xlabel: str | None = "Date",
        ylabel: str | None = "Count",
        date_format: str = "%Y-%m-%d",
        rotation: int = 45,
    ) -> None:
        """
        Set up axes for time series data with standard formatting.

        This method provides standardized time series axis configuration
        used across time-based graph implementations.

        Args:
            xlabel: X-axis label
            ylabel: Y-axis label
            date_format: Date format string
            rotation: Rotation angle for date labels
        """
        if self.axes is None:
            logger.warning("Cannot setup time series axes: axes is None")
            return

        # Apply standard title and axes setup
        # Set title
        display_title = self.get_title()
        _ = self.axes.set_title(  # pyright: ignore[reportUnknownMemberType]
            display_title, fontsize=18, fontweight="bold", pad=20
        )

        # Set axis labels
        if xlabel is not None:
            _ = self.axes.set_xlabel(xlabel, fontsize=12)  # pyright: ignore[reportUnknownMemberType]
        if ylabel is not None:
            _ = self.axes.set_ylabel(ylabel, fontsize=12)  # pyright: ignore[reportUnknownMemberType]

        # Configure tick parameters
        self.axes.tick_params(axis="x", rotation=rotation)  # pyright: ignore[reportUnknownMemberType]

        # Format x-axis dates if matplotlib dates are being used
        try:
            import matplotlib.dates as mdates

            self.axes.xaxis.set_major_formatter(mdates.DateFormatter(date_format))  # pyright: ignore[reportUnknownMemberType]
        except ImportError:
            logger.warning("matplotlib.dates not available for date formatting")
