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

from typing import TypeGuard


class HasHeight(Protocol):
    def get_height(self) -> float: ...


class HasWidth(Protocol):
    def get_width(self) -> float: ...


def _has_height(obj: object) -> TypeGuard[Rectangle | HasHeight]:
    return isinstance(obj, Rectangle) or hasattr(obj, "get_height")


def _has_width(obj: object) -> TypeGuard[Rectangle | HasWidth]:
    return isinstance(obj, Rectangle) or hasattr(obj, "get_width")

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

    # --- Adaptive spacing helpers -------------------------------------------------

    def ensure_space_for_vertical_bar_annotations(
        self,
        ax: Axes,
        *,
        offset_ratio: float = 0.05,
        min_padding: float = 0.5,
        max_padding: float = 10.0,
        baseline: float = 0.0,
    ) -> None:
        """
        Expand y-limits to provide room for vertical bar value annotations.

        This inspects ax.patches to find the maximum bar height and adds padding
        based on a ratio of that height. Ensures at least min_padding and caps
        at max_padding to avoid runaway limits.
        """
        try:
            max_height = 0.0
            patches_obj = getattr(ax, "patches", [])
            for patch in cast(Sequence[object], patches_obj):
                if _has_height(patch):
                    h = float(patch.get_height())
                    if h > max_height:
                        max_height = h

            if max_height <= 0:
                return

            padding = max(min_padding, min(max_padding, max_height * offset_ratio))
            _ = ax.set_ylim(baseline, max_height + padding)
        except Exception as e:
            logger.debug(f"Failed to ensure vertical bar annotation space: {e}")

    def ensure_space_for_horizontal_bar_annotations(
        self,
        ax: Axes,
        *,
        offset_ratio: float = 0.05,
        min_padding: float = 0.5,
        max_padding: float = 10.0,
        baseline: float = 0.0,
    ) -> None:
        """
        Expand x-limits to provide room for horizontal bar value annotations.
        """
        try:
            max_width = 0.0
            patches_obj = getattr(ax, "patches", [])
            for patch in cast(Sequence[object], patches_obj):
                if _has_width(patch):
                    w = float(patch.get_width())
                    if w > max_width:
                        max_width = w

            if max_width <= 0:
                return

            padding = max(min_padding, min(max_padding, max_width * offset_ratio))
            _ = ax.set_xlim(baseline, max_width + padding)
        except Exception as e:
            logger.debug(f"Failed to ensure horizontal bar annotation space: {e}")

    def ensure_space_for_stacked_vertical_bars(
        self,
        ax: Axes,
        bar_containers: Sequence[tuple[object, str, object]],
        categories: Sequence[str],
        *,
        offset_ratio: float = 0.05,
        min_padding: float = 0.5,
        max_padding: float = 10.0,
        baseline: float = 0.0,
    ) -> None:
        """
        Expand y-limits for stacked vertical bars using category totals.
        """
        try:
            max_total = 0.0
            for i, _ in enumerate(categories):
                cumulative = 0.0
                for _, _media_type, values in bar_containers:
                    _ = _media_type  # avoid unused
                    if hasattr(values, "__getitem__"):
                        try:
                            v = float(cast(Sequence[float], values)[i])
                        except Exception:
                            v = 0.0
                    else:
                        v = 0.0
                    cumulative += v
                if cumulative > max_total:
                    max_total = cumulative

            if max_total <= 0:
                return

            padding = max(min_padding, min(max_padding, max_total * offset_ratio))
            _ = ax.set_ylim(baseline, max_total + padding)
        except Exception as e:
            logger.debug(f"Failed to ensure stacked vertical bar space: {e}")

    def ensure_space_for_line_annotations(
        self,
        ax: Axes,
        y_data: Sequence[float],
        *,
        percentage: float = 0.05,
        min_padding: float = 0.5,
        max_padding: float = 10.0,
        baseline: float = 0.0,
    ) -> None:
        """
        Expand y-limits to include padding for line point annotations using the
        same adaptive offset logic used by annotate_line_points_adaptive.
        """
        try:
            if not y_data:
                return
            y_max = max(y_data)
            offset = self.calculate_adaptive_annotation_offset(
                y_data, percentage=percentage, min_offset=min_padding, max_offset=max_padding
            )
            _ = ax.set_ylim(baseline, float(y_max) + float(offset))
        except Exception as e:
            logger.debug(f"Failed to ensure line annotation space: {e}")

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

    def calculate_adaptive_annotation_offset(
        self,
        y_data: "Sequence[float]",
        percentage: float = 0.05,
        min_offset: float = 0.5,
        max_offset: float = 10.0,
        default_offset: float = 2.0,
    ) -> float:
        """
        Calculate adaptive annotation offset based on data range.

        This method calculates an appropriate Y-offset for annotations based on the
        range of Y-values in the data, ensuring consistent visual spacing regardless
        of the axis scale.

        Args:
            y_data: Y-coordinates of the data points
            percentage: Percentage of data range to use as offset (default: 5%)
            min_offset: Minimum offset value to ensure readability
            max_offset: Maximum offset value to prevent excessive spacing
            default_offset: Default offset for edge cases (empty/single value data)

        Returns:
            Calculated offset value appropriate for the data range
        """
        try:
            # Handle edge cases
            if not y_data or len(y_data) < 2:
                return default_offset

            # Calculate data range
            y_min = min(y_data)
            y_max = max(y_data)
            data_range = y_max - y_min

            # Handle zero or very small ranges
            if data_range <= 0:
                return default_offset

            # Calculate percentage-based offset
            calculated_offset = data_range * percentage

            # Clamp to min/max bounds
            return max(min_offset, min(calculated_offset, max_offset))

        except Exception as e:
            logger.warning(f"Failed to calculate adaptive offset: {e}")
            return default_offset

    def annotate_line_points_adaptive(
        self,
        ax: Axes,
        config_key: str,
        x_data: "Sequence[float]",
        y_data: "Sequence[float]",
        percentage: float = 0.05,
        min_offset: float = 0.5,
        max_offset: float = 10.0,
        offset_x: float = 0.0,
        ha: str = "center",
        va: str = "bottom",
        fontweight: str = "normal",
        min_value_threshold: float = 0.0,
    ) -> None:
        """
        Annotate line graph data points with adaptive Y-offset based on data range.

        This method automatically calculates an appropriate Y-offset based on the
        data range to ensure consistent annotation positioning across different
        graph types and scales.

        Args:
            ax: Matplotlib axes containing line graph
            config_key: Configuration key to check if annotations are enabled
            x_data: X-coordinates of the data points
            y_data: Y-coordinates of the data points (values to annotate)
            percentage: Percentage of data range to use as offset (default: 5%)
            min_offset: Minimum offset value to ensure readability
            max_offset: Maximum offset value to prevent excessive spacing
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
            # Calculate adaptive offset based on data range
            adaptive_offset_y = self.calculate_adaptive_annotation_offset(
                y_data, percentage, min_offset, max_offset
            )

            # Use the existing annotate_line_points method with calculated offset
            self.annotate_line_points(
                ax=ax,
                config_key=config_key,
                x_data=x_data,
                y_data=y_data,
                offset_y=adaptive_offset_y,
                offset_x=offset_x,
                ha=ha,
                va=va,
                fontweight=fontweight,
                min_value_threshold=min_value_threshold,
            )

            logger.debug(
                f"Applied adaptive annotation offset: {adaptive_offset_y:.2f} " +
                f"(data range: {min(y_data) if y_data else 0:.1f}-{max(y_data) if y_data else 0:.1f})"
            )

        except Exception as e:
            logger.warning(f"Failed to annotate line points with adaptive offset: {e}")

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
