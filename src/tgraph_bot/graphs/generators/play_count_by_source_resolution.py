"""Play count by source resolution graph generator.

This module implements the PlayCountBySourceResolutionGraph generator that creates
bar charts showing play counts by source resolution with configurable grouping.

Requirements: 17.1, 17.2, 17.3, 17.4
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure

from tgraph_bot.config.models import GraphAppearanceConfig, GraphConfig
from tgraph_bot.graphs.data import StreamRecord, aggregate_by_resolution


@dataclass(slots=True)
class PlayCountBySourceResolutionGraph:
    """Generates play count by source resolution graph.

    This graph shows play counts by source resolution (original media quality)
    with configurable grouping (standard, detailed, simplified).

    Uses dataclass with slots for memory efficiency.

    Requirements:
        - 17.1: Extract resolution data from stream records
        - 17.2: Group resolutions into standard categories
        - 17.3: Display exact resolution values in detailed mode
        - 17.4: Group into broad categories in simplified mode
    """

    def generate(
        self,
        data: list[StreamRecord],
        *,
        config: GraphConfig,
        appearance: GraphAppearanceConfig,
        resolution_grouping: str = "standard",
    ) -> Figure:
        """Generate play count by source resolution bar chart.

        Creates a bar chart showing play counts by source resolution.
        Resolution grouping can be "standard", "detailed", or "simplified".

        Args:
            data: List of stream records to visualize
            config: Graph-specific configuration (palette, annotations, etc.)
            appearance: Visual styling configuration (colors, dimensions, seaborn, etc.)
            resolution_grouping: Grouping mode - "standard", "detailed", or "simplified"

        Returns:
            Matplotlib Figure object with the generated graph

        Requirements:
            - 17.1: Extract resolution data
            - 17.2: Group resolutions based on mode
        """
        # Create figure with configured dimensions
        fig, ax = plt.subplots(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
            figsize=(appearance.dimensions.width, appearance.dimensions.height)
        )

        # Handle empty data
        if not data:
            _ = ax.text(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
                0.5,
                0.5,
                "No data available",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=14,
            )
            _ = ax.set_xlim(0, 1)
            _ = ax.set_ylim(0, 1)
            return fig

        # Aggregate by source resolution with grouping
        aggregated = aggregate_by_resolution(
            data,
            resolution_field="source_resolution",
            grouping=resolution_grouping,
        )

        if not aggregated:
            _ = ax.text(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
                0.5,
                0.5,
                "No data available",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=14,
            )
            _ = ax.set_xlim(0, 1)
            _ = ax.set_ylim(0, 1)
            return fig

        # Prepare data for plotting
        resolutions = list(aggregated.keys())
        counts = list(aggregated.values())

        # Get color from palette or use default
        if config.palette:
            from tgraph_bot.graphs.styling import GraphStyling

            styling = GraphStyling()
            colors = styling.get_palette(config.palette, n_colors=len(resolutions))
        else:
            # Use single color for all bars
            colors = [appearance.colors.movie] * len(resolutions)

        # Create bar chart using countplot-style visualization
        # Note: seaborn's countplot requires raw data, so we use barplot instead
        _ = sns.barplot(
            x=resolutions,
            y=counts,
            ax=ax,
            palette=colors if len(colors) == len(resolutions) else None,
            hue=resolutions if len(colors) == len(resolutions) else None,
            legend=False,
        )

        # Add annotations if enabled
        if config.annotations_enabled:
            for idx, count in enumerate(counts):
                _ = ax.text(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
                    idx,
                    count,
                    str(count),
                    ha="center",
                    va="bottom",
                    fontsize=appearance.annotations.font_size,
                    color=appearance.annotations.color,
                )

        # Set labels and title
        _ = ax.set_xlabel("Source Resolution", fontsize=12)
        _ = ax.set_ylabel("Play Count", fontsize=12)
        
        title_suffix = {
            "standard": "(Standard Grouping)",
            "detailed": "(Detailed)",
            "simplified": "(Simplified)",
        }.get(resolution_grouping, "")
        
        _ = ax.set_title(
            f"Play Count by Source Resolution {title_suffix}",
            fontsize=14,
            fontweight="bold",
        )

        # Apply grid if enabled
        if appearance.grid.enabled:
            _ = ax.grid(True, alpha=appearance.grid.alpha, axis="y")

        # Rotate x-axis labels for better readability
        _ = plt.setp(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
            ax.get_xticklabels(),
            rotation=45,
            ha="right",
        )

        # Tight layout to prevent label cutoff
        _ = fig.tight_layout()  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs

        return fig

