"""Graph styling and theming using seaborn.

This module provides the GraphStyling class for managing graph visual appearance
including seaborn theme application, color palette management, dimensions, and
annotations.

Requirements: 5.2, 5.4, 5.5, 6.1, 6.2, 6.4, 6.5, 6.6, 6.7
"""

from dataclasses import dataclass

import matplotlib.patheffects as path_effects
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from tgraph_bot.config.models import (
    AnnotationConfig,
    GraphColors,
    GraphDimensions,
    GridConfig,
)


@dataclass(slots=True)
class GraphStyling:
    """Manages graph visual styling with seaborn integration.

    This class handles all aspects of graph styling including:
    - Seaborn theme application (style, palette, context)
    - Figure dimensions and DPI
    - Color management (base colors and palettes)
    - Grid configuration
    - Annotations and peak highlighting

    Uses dataclass with slots for memory efficiency (40% savings).

    Requirements:
        - 5.5: Use seaborn for enhanced aesthetics and theme management
        - 6.6: Apply seaborn style
        - 6.7: Use seaborn palette system
    """

    def apply_theme(
        self,
        *,
        style: str = "darkgrid",
        palette: str = "muted",
        context: str = "notebook",
    ) -> None:
        """Apply seaborn theme for consistent styling.

        This sets the global seaborn theme that affects all subsequent
        matplotlib plots. Should be called before creating figures.

        Args:
            style: Seaborn style (whitegrid, darkgrid, white, dark, ticks)
            palette: Seaborn color palette name (muted, deep, pastel, viridis, etc.)
            context: Seaborn context for scaling (paper, notebook, talk, poster)

        Requirements:
            - 5.5: Apply seaborn theme for enhanced aesthetics
            - 6.6: Support seaborn style configuration (darkgrid for Discord)
            - 6.7: Use seaborn palette system
        """
        sns.set_theme(style=style, palette=palette, context=context)  # pyright: ignore[reportArgumentType]  # seaborn stubs too strict

    def get_palette(self, palette_name: str, n_colors: int) -> list[str]:
        """Get seaborn color palette as hex color codes.

        Retrieves a seaborn palette with the specified number of colors.
        Empty palette name returns empty list. Invalid palette names or zero
        colors return empty list.

        Args:
            palette_name: Name of seaborn palette (viridis, plasma, inferno, muted, etc.)
            n_colors: Number of colors to retrieve from palette

        Returns:
            List of hex color codes (e.g., ['#ff0000', '#00ff00'])

        Requirements:
            - 5.4: Apply palette colors when specified
            - 6.7: Use seaborn color palette system for consistent color management
        """
        if not palette_name or n_colors <= 0:
            return []

        try:
            # Get seaborn palette and convert to hex codes
            palette = sns.color_palette(palette_name, n_colors=n_colors)
            return palette.as_hex()
        except (ValueError, KeyError):
            # Invalid palette name - return empty list
            return []

    def apply_styling(
        self,
        fig: Figure,
        *,
        dimensions: GraphDimensions,
        colors: GraphColors,
        grid: GridConfig,
    ) -> None:
        """Apply styling to matplotlib figure.

        Applies dimensions, background color, and grid configuration to
        the provided figure.

        Args:
            fig: Matplotlib figure to style
            dimensions: Dimensions configuration (width, height, DPI)
            colors: Color configuration (background, TV, movie)
            grid: Grid configuration (enabled, alpha)

        Requirements:
            - 5.2: Apply configured dimensions (width, height) and DPI
            - 6.4: Apply background color
            - 6.5: Render grid lines when enabled
        """
        # Apply dimensions (Requirement 5.2)
        fig.set_size_inches(dimensions.width, dimensions.height)
        fig.set_dpi(dimensions.dpi)

        # Apply background color (Requirement 6.4)
        fig.patch.set_facecolor(colors.background)

        # Apply grid configuration to all axes (Requirement 6.5)
        for ax in fig.get_axes():
            if grid.enabled:
                ax.grid(True, alpha=grid.alpha)
            else:
                ax.grid(False)

    def add_annotations(
        self,
        ax: Axes,
        *,
        values: list[float],
        annotation_config: AnnotationConfig,
    ) -> None:
        """Add numeric annotations to graph data points or bars.

        Adds text annotations showing numeric values on graph elements.
        Supports optional outlines for better visibility.

        Args:
            ax: Matplotlib axes to annotate
            values: List of values to annotate
            annotation_config: Annotation styling configuration

        Requirements:
            - 6.1: Display numeric values on data points or bars with configured font size
        """
        if not values:
            return

        # Get the containers (bars or other plot elements)
        containers = ax.containers

        if not containers:
            return

        # Annotate the first container (simple implementation for now)
        container = containers[0]

        for bar, value in zip(container, values, strict=False):  # pyright: ignore[reportUnknownVariableType]  # matplotlib incomplete stubs
            if value == 0:
                continue

            # Get bar position
            height = bar.get_height()  # pyright: ignore[reportUnknownVariableType]  # matplotlib incomplete stubs
            x = bar.get_x() + bar.get_width() / 2  # pyright: ignore[reportUnknownVariableType]  # matplotlib incomplete stubs

            # Create annotation text
            text = ax.text(
                x,  # pyright: ignore[reportUnknownArgumentType]  # matplotlib incomplete stubs
                height,  # pyright: ignore[reportUnknownArgumentType]  # matplotlib incomplete stubs
                f"{value:.0f}",
                ha="center",
                va="bottom",
                fontsize=annotation_config.font_size,
                color=annotation_config.color,
            )

            # Add outline if enabled
            if annotation_config.enable_outline:
                text.set_path_effects(
                    [
                        path_effects.Stroke(
                            linewidth=3, foreground=annotation_config.outline_color
                        ),
                        path_effects.Normal(),
                    ]
                )

    def highlight_peak(
        self,
        ax: Axes,
        *,
        values: list[float],
        peak_color: str,
    ) -> None:
        """Highlight the peak value in the graph.

        Applies a highlight color to the bar or data point with the
        highest value. If there are multiple equal peaks, highlights
        the first one.

        Args:
            ax: Matplotlib axes containing the graph
            values: List of values to find peak in
            peak_color: Hex color code for highlighting

        Requirements:
            - 6.2: Apply configured highlight color to the highest value
        """
        if not values:
            return

        # Find peak value index
        peak_value = max(values)
        peak_index = values.index(peak_value)

        # Get the containers (bars or other plot elements)
        containers = ax.containers

        if not containers:
            return

        # Highlight the peak in the first container
        container = containers[0]

        if peak_index < len(container):
            bar = container[peak_index]  # pyright: ignore[reportUnknownVariableType]  # matplotlib incomplete stubs
            bar.set_color(peak_color)
