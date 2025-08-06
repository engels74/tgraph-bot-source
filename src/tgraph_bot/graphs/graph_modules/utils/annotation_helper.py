"""
AnnotationHelper utility for TGraph Bot graph modules.

This module provides standardized annotation methods for graph visualizations,
consolidating common annotation patterns found across graph implementations.
It eliminates DRY violations by providing reusable annotation functionality.
"""

import logging
from collections.abc import Sequence
from typing import Protocol, cast, runtime_checkable

from matplotlib.axes import Axes
from matplotlib.patches import Rectangle

logger = logging.getLogger(__name__)


@runtime_checkable
class AnnotationProtocol(Protocol):
    """
    Protocol defining the interface for objects that can use annotation helpers.

    This protocol ensures that classes using AnnotationHelper have the necessary
    configuration access methods for annotation styling and positioning.
    """

    def get_config_value(self, key: str, default: object = None) -> object:
        """Get a configuration value with optional default."""
        ...

    def get_annotation_font_size(self) -> int:
        """Get the font size to use for annotations."""
        ...

    def get_annotation_color(self) -> str:
        """Get the color to use for annotations."""
        ...

    def get_annotation_outline_color(self) -> str:
        """Get the outline color for annotations."""
        ...

    def is_annotation_outline_enabled(self) -> bool:
        """Check if annotation outlines are enabled."""
        ...

    def get_peak_annotation_color(self) -> str:
        """Get the background color for peak annotations."""
        ...

    def get_peak_annotation_text_color(self) -> str:
        """Get the text color for peak annotations."""
        ...

    def is_peak_annotations_enabled(self) -> bool:
        """Check if peak annotations are enabled."""
        ...


class AnnotationHelper:
    """
    Utility class providing standardized annotation methods for graph visualizations.

    This class consolidates common annotation patterns found across graph implementations,
    eliminating code duplication and providing consistent annotation behavior.

    Features:
    - Bar value annotations with configurable positioning
    - Peak value annotations with custom styling
    - Stacked bar segment annotations
    - Horizontal bar annotations
    - Configurable text formatting and styling
    """

    def __init__(self, graph: AnnotationProtocol) -> None:
        """
        Initialize the AnnotationHelper with a graph instance.

        Args:
            graph: Graph instance that implements AnnotationProtocol
        """
        self.graph: AnnotationProtocol = graph

    def annotate_bar_patches(
        self,
        ax: Axes,
        config_key: str,
        offset_y: float = 1.0,
        ha: str = "center",
        va: str = "bottom",
        fontweight: str = "bold",
        min_value_threshold: float = 0.0,
    ) -> None:
        """
        Annotate all bar patches in an axes with their values.

        This method implements the common pattern of iterating through ax.patches
        and adding value annotations to each bar.

        Args:
            ax: Matplotlib axes containing bar patches
            config_key: Configuration key to check if annotations are enabled
            offset_y: Y-offset for annotation positioning
            ha: Horizontal alignment for text
            va: Vertical alignment for text
            fontweight: Font weight for text
            min_value_threshold: Minimum value to annotate (skip smaller values)
        """
        annotate_enabled = self.graph.get_config_value(config_key, False)
        if not annotate_enabled:
            return

        try:
            for patch in ax.patches:  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType] # matplotlib patches not typed
                # Most bar chart patches are Rectangle instances with these methods
                if (
                    hasattr(patch, "get_height")  # pyright: ignore[reportUnknownArgumentType] # matplotlib patch typing
                    and hasattr(patch, "get_x")  # pyright: ignore[reportUnknownArgumentType] # matplotlib patch typing
                    and hasattr(patch, "get_width")  # pyright: ignore[reportUnknownArgumentType] # matplotlib patch typing
                ):
                    rect_patch = cast(Rectangle, patch)
                    height = rect_patch.get_height()
                    if height and height > min_value_threshold:
                        x_val = rect_patch.get_x() + rect_patch.get_width() / 2
                        self._add_text_annotation(
                            ax,
                            x=float(x_val),
                            y=float(height),
                            value=int(height),
                            ha=ha,
                            va=va,
                            offset_y=offset_y,
                            fontweight=fontweight,
                        )
        except Exception as e:
            logger.warning(f"Failed to annotate bar patches: {e}")

    def annotate_horizontal_bar_patches(
        self,
        ax: Axes,
        config_key: str,
        offset_x_ratio: float = 0.01,
        ha: str = "left",
        va: str = "center",
        fontweight: str = "normal",
        min_value_threshold: float = 0.0,
    ) -> None:
        """
        Annotate horizontal bar patches with their values.

        This method handles the specific case of horizontal bar charts where
        the value is represented by the bar width rather than height.

        Args:
            ax: Matplotlib axes containing horizontal bar patches
            config_key: Configuration key to check if annotations are enabled
            offset_x_ratio: X-offset as ratio of maximum value
            ha: Horizontal alignment for text
            va: Vertical alignment for text
            fontweight: Font weight for text
            min_value_threshold: Minimum value to annotate
        """
        annotate_enabled = self.graph.get_config_value(config_key, False)
        if not annotate_enabled:
            return

        try:
            # Calculate max width for offset positioning
            max_width = 0.0
            for patch in ax.patches:  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType] # matplotlib patches not typed
                if hasattr(patch, "get_width"):  # pyright: ignore[reportUnknownArgumentType] # matplotlib patch typing
                    rect_patch = cast(Rectangle, patch)
                    width = rect_patch.get_width()
                    if width and width > max_width:
                        max_width = float(width)

            offset_x = max_width * offset_x_ratio

            for patch in ax.patches:  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType] # matplotlib patches not typed
                if (
                    hasattr(patch, "get_width")  # pyright: ignore[reportUnknownArgumentType] # matplotlib patch typing
                    and hasattr(patch, "get_y")  # pyright: ignore[reportUnknownArgumentType] # matplotlib patch typing
                    and hasattr(patch, "get_height")  # pyright: ignore[reportUnknownArgumentType] # matplotlib patch typing
                ):
                    rect_patch = cast(Rectangle, patch)
                    width = rect_patch.get_width()
                    if width and width > min_value_threshold:
                        y_val = rect_patch.get_y() + rect_patch.get_height() / 2
                        self._add_text_annotation(
                            ax,
                            x=float(width),
                            y=float(y_val),
                            value=int(width),
                            ha=ha,
                            va=va,
                            offset_x=offset_x,
                            fontweight=fontweight,
                        )
        except Exception as e:
            logger.warning(f"Failed to annotate horizontal bar patches: {e}")

    def annotate_stacked_bar_segments(
        self,
        ax: Axes,
        config_key: str,
        bar_containers: Sequence[tuple[object, str, object]],
        categories: Sequence[str],
        include_totals: bool = True,
        segment_fontsize: int = 9,
        total_fontsize: int = 11,
    ) -> None:
        """
        Annotate stacked bar chart segments and optionally totals.

        This method handles the complex case of stacked bar charts where each
        segment needs annotation and optionally a total at the top.

        Args:
            ax: Matplotlib axes containing stacked bars
            config_key: Configuration key to check if annotations are enabled
            bar_containers: List of (bars, media_type, values) tuples
            categories: List of category names for x-axis positioning
            include_totals: Whether to include total annotations at top
            segment_fontsize: Font size for segment annotations
            total_fontsize: Font size for total annotations
        """
        annotate_enabled = self.graph.get_config_value(config_key, False)
        if not annotate_enabled:
            return

        try:
            for i, _ in enumerate(categories):
                cumulative_height = 0.0

                # Annotate each segment
                for bars, media_type, values in bar_containers:
                    # Avoid unused variable warnings
                    _ = bars
                    _ = media_type
                    if hasattr(values, "__getitem__"):
                        indexable_values = cast("Sequence[float]", values)
                        value = float(indexable_values[i])
                    else:
                        value = 0.0
                    if value > 0:
                        # Position annotation in the middle of this segment
                        self._add_text_annotation(
                            ax,
                            x=float(i),
                            y=cumulative_height + value / 2,
                            value=int(value),
                            ha="center",
                            va="center",
                            fontsize=segment_fontsize,
                            fontweight="normal",
                        )
                    cumulative_height += value

                # Add total annotation at the top if requested
                if include_totals and cumulative_height > 0:
                    self._add_text_annotation(
                        ax,
                        x=float(i),
                        y=cumulative_height,
                        value=int(cumulative_height),
                        ha="center",
                        va="bottom",
                        offset_y=2,
                        fontsize=total_fontsize,
                        fontweight="bold",
                    )
        except Exception as e:
            logger.warning(f"Failed to annotate stacked bar segments: {e}")

    def annotate_peak_value(
        self,
        ax: Axes,
        x: float,
        y: float,
        value: int | float,
        label_prefix: str = "Peak",
        offset_x: float = 10,
        offset_y: float = 10,
    ) -> None:
        """
        Add a peak value annotation with arrow and styled box.

        This method creates a prominent annotation for highlighting peak values
        with customizable styling and positioning.

        Args:
            ax: Matplotlib axes to add annotation to
            x: X-coordinate of the peak
            y: Y-coordinate of the peak
            value: Peak value to display
            label_prefix: Text prefix for the annotation
            offset_x: X-offset for annotation positioning
            offset_y: Y-offset for annotation positioning
        """
        if not self.graph.is_peak_annotations_enabled():
            return

        try:
            _ = ax.annotate(  # pyright: ignore[reportUnknownMemberType] # matplotlib annotate typing
                f"{label_prefix}: {value}",
                xy=(x, y),
                xytext=(offset_x, offset_y),
                textcoords="offset points",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor=self.graph.get_peak_annotation_color(),
                    edgecolor="black",
                    alpha=0.9,
                ),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
                color=self.graph.get_peak_annotation_text_color(),
                fontweight="bold",
            )
        except Exception as e:
            logger.warning(f"Failed to add peak annotation: {e}")

    def annotate_stacked_horizontal_bar_segments(
        self,
        ax: Axes,
        config_key: str,
        bar_containers: "Sequence[tuple[object, str, object]]",
        categories: "Sequence[str]",
        include_totals: bool = True,
        segment_fontsize: int = 9,
        total_fontsize: int = 11,
        segment_ha: str = "center",
        total_ha: str = "left",
        total_offset_x_ratio: float = 0.02,
    ) -> None:
        """
        Annotate stacked horizontal bar chart segments and optionally totals.

        This method handles the complex case of stacked horizontal bar charts where each
        segment needs annotation and optionally a total at the end of the bar.

        Args:
            ax: Matplotlib axes containing stacked horizontal bars
            config_key: Configuration key to check if annotations are enabled
            bar_containers: List of (bars, media_type, values) tuples
            categories: List of category names for y-axis positioning
            include_totals: Whether to include total annotations at end
            segment_fontsize: Font size for segment annotations
            total_fontsize: Font size for total annotations
            segment_ha: Horizontal alignment for segment text
            total_ha: Horizontal alignment for total text
            total_offset_x_ratio: X-offset ratio for total annotations
        """
        annotate_enabled = self.graph.get_config_value(config_key, False)
        if not annotate_enabled:
            return

        try:
            # Calculate maximum total width for offset positioning
            max_total_width = 0.0
            for i, _ in enumerate(categories):
                cumulative_width = 0.0
                for _, _, values in bar_containers:
                    if hasattr(values, "__getitem__"):
                        indexable_values = cast("Sequence[float]", values)
                        value = float(indexable_values[i])
                    else:
                        value = 0.0
                    cumulative_width += value
                if cumulative_width > max_total_width:
                    max_total_width = cumulative_width

            total_offset_x = max_total_width * total_offset_x_ratio

            for i, _ in enumerate(categories):
                cumulative_width = 0.0

                # Annotate each segment
                for _, media_type, values in bar_containers:
                    # Avoid unused variable warnings
                    _ = media_type
                    if hasattr(values, "__getitem__"):
                        indexable_values = cast("Sequence[float]", values)
                        value = float(indexable_values[i])
                    else:
                        value = 0.0
                    if value > 0:
                        # Position annotation in the middle of this segment
                        self._add_text_annotation(
                            ax,
                            x=cumulative_width + value / 2,
                            y=float(i),
                            value=int(value),
                            ha=segment_ha,
                            va="center",
                            fontsize=segment_fontsize,
                            fontweight="normal",
                        )
                    cumulative_width += value

                # Add total annotation at the end if requested
                if include_totals and cumulative_width > 0:
                    self._add_text_annotation(
                        ax,
                        x=cumulative_width,
                        y=float(i),
                        value=int(cumulative_width),
                        ha=total_ha,
                        va="center",
                        offset_x=total_offset_x,
                        fontsize=total_fontsize,
                        fontweight="bold",
                    )
        except Exception as e:
            logger.warning(f"Failed to annotate stacked horizontal bar segments: {e}")

    def annotate_line_points(
        self,
        ax: Axes,
        config_key: str,
        x_data: "Sequence[float]",
        y_data: "Sequence[float]",
        offset_y: float = 2.0,
        offset_x: float = 0.0,
        ha: str = "center",
        va: str = "bottom",
        fontweight: str = "normal",
        min_value_threshold: float = 0.0,
    ) -> None:
        """
        Annotate line graph data points with their values.

        This method handles annotation of line graphs where data points are represented
        by x,y coordinates rather than bar patches.

        Args:
            ax: Matplotlib axes containing line graph
            config_key: Configuration key to check if annotations are enabled
            x_data: X-coordinates of the data points
            y_data: Y-coordinates of the data points (values to annotate)
            offset_y: Y-offset for annotation positioning
            offset_x: X-offset for annotation positioning
            ha: Horizontal alignment for text
            va: Vertical alignment for text
            fontweight: Font weight for text
            min_value_threshold: Minimum value to annotate (skip smaller values)
        """
        annotate_enabled = self.graph.get_config_value(config_key, False)
        if not annotate_enabled:
            return

        try:
            # Ensure both sequences have the same length
            if len(x_data) != len(y_data):
                logger.warning(
                    "x_data and y_data must have the same length for line annotation"
                )
                return

            # Annotate each data point
            for x, y in zip(x_data, y_data):
                # Skip values below threshold
                if y and y > min_value_threshold:
                    self._add_text_annotation(
                        ax,
                        x=float(x),
                        y=float(y),
                        value=int(y) if isinstance(y, float) and y.is_integer() else y,
                        ha=ha,
                        va=va,
                        offset_x=offset_x,
                        offset_y=offset_y,
                        fontweight=fontweight,
                    )
        except Exception as e:
            logger.warning(f"Failed to annotate line points: {e}")

    def _add_text_annotation(
        self,
        ax: Axes,
        x: float,
        y: float,
        value: int | float,
        ha: str = "center",
        va: str = "bottom",
        offset_x: float = 0,
        offset_y: float = 0,
        fontsize: int | None = None,
        fontweight: str = "normal",
    ) -> None:
        """
        Add a text annotation with consistent styling.

        This is the core method that handles the actual text placement with
        proper styling, outline effects, and positioning.

        Args:
            ax: Matplotlib axes to add annotation to
            x: X-coordinate for annotation
            y: Y-coordinate for annotation
            value: Value to display
            ha: Horizontal alignment
            va: Vertical alignment
            offset_x: X-offset from position
            offset_y: Y-offset from position
            fontsize: Font size (uses config default if None)
            fontweight: Font weight
        """
        try:
            # Use config-based font size if not specified
            if fontsize is None:
                fontsize = self.graph.get_annotation_font_size()

            # Format the value for display
            if isinstance(value, float) and value.is_integer():
                text = str(int(value))
            else:
                text = str(value)

            # Calculate actual position with offsets
            actual_x = x + offset_x
            actual_y = y + offset_y

            if self.graph.is_annotation_outline_enabled():
                # Add text with outline for better readability
                from matplotlib import patheffects

                _ = ax.text(  # pyright: ignore[reportUnknownMemberType]
                    actual_x,
                    actual_y,
                    text,
                    ha=ha,
                    va=va,
                    fontsize=fontsize,
                    fontweight=fontweight,
                    color="white",
                    path_effects=[
                        patheffects.Stroke(
                            linewidth=3,
                            foreground=self.graph.get_annotation_outline_color(),
                        ),
                        patheffects.Normal(),
                    ],
                )
            else:
                # Add text without outline
                _ = ax.text(  # pyright: ignore[reportUnknownMemberType]
                    actual_x,
                    actual_y,
                    text,
                    ha=ha,
                    va=va,
                    fontsize=fontsize,
                    fontweight=fontweight,
                    color=self.graph.get_annotation_color(),
                )
        except Exception as e:
            logger.warning(f"Failed to add text annotation: {e}")
