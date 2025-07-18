"""
Visualization mixin for common matplotlib and seaborn operations.

This module provides a mixin class that consolidates common visualization patterns
used across all graph implementations in the TGraph Bot system. It addresses
DRY violations by extracting repeated matplotlib setup, seaborn styling,
and common visualization patterns into reusable methods.
"""

import logging
from typing import TYPE_CHECKING, Any, Protocol, Literal

import matplotlib.axes
import seaborn as sns

if TYPE_CHECKING:
    from ...config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class VisualizationProtocol(Protocol):
    """Protocol defining the interface required by VisualizationMixin."""

    config: "TGraphBotConfig | dict[str, Any] | None"
    axes: matplotlib.axes.Axes | None
    figure: Any

    def get_grid_enabled(self) -> bool:
        """Check if grid should be enabled for this graph."""
        ...

    def get_title(self) -> str:
        """Get the title for this graph."""
        ...

    def setup_figure(self) -> tuple[Any, Any]:
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
        _ = self.axes.set_title(
            display_title,
            fontsize=title_fontsize,
            fontweight="bold",
            pad=title_pad,
        )

        # Set axis labels if provided
        if xlabel is not None:
            _ = self.axes.set_xlabel(xlabel, fontsize=label_fontsize)
        if ylabel is not None:
            _ = self.axes.set_ylabel(ylabel, fontsize=label_fontsize)

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

        _ = self.axes.text(
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            transform=self.axes.transAxes,
            fontsize=fontsize,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=alpha),
        )

    def setup_figure_with_seaborn_grid(self: VisualizationProtocol) -> tuple[Any, Any]:
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

    def configure_standard_grid(self: VisualizationProtocol, alpha: float = 0.3) -> None:
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

        self.axes.grid(True, alpha=alpha)

    def setup_bar_chart_annotations(
        self: VisualizationProtocol,
        bars: Any,
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
            height = bar.get_height()
            _ = self.axes.annotate(
                format_string.format(value),
                xy=(bar.get_x() + bar.get_width() / 2, height),
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
        sns.set_palette(palette)

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

        self.axes.tick_params(axis=axis, labelsize=labelsize, rotation=rotation)

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

        _ = self.axes.legend(
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
        _ = self.axes.set_xticks([])
        _ = self.axes.set_yticks([])

    def setup_time_series_axes(
        self: VisualizationProtocol,
        xlabel: str = "Date",
        ylabel: str = "Count",
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
        if self.axes is not None:
            # Set title
            display_title = self.get_title()
            _ = self.axes.set_title(display_title, fontsize=18, fontweight="bold", pad=20)
            
            # Set axis labels
            if xlabel is not None:
                _ = self.axes.set_xlabel(xlabel, fontsize=12)
            if ylabel is not None:
                _ = self.axes.set_ylabel(ylabel, fontsize=12)
            
            # Configure tick parameters
            self.axes.tick_params(axis="x", rotation=rotation)

        # Format x-axis dates if matplotlib dates are being used
        try:
            import matplotlib.dates as mdates

            self.axes.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
        except ImportError:
            logger.warning("matplotlib.dates not available for date formatting")