"""Daily play count by stream type graph generator.

This module implements the DailyPlayCountByStreamTypeGraph generator that creates
line charts showing play counts over time separated by stream type (direct play,
transcode, copy).

Requirements: 16.1, 16.2, 16.5
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure

from tgraph_bot.config.models import GraphAppearanceConfig, GraphConfig
from tgraph_bot.graphs.data import StreamRecord, aggregate_by_date_and_stream_type


@dataclass(slots=True)
class DailyPlayCountByStreamTypeGraph:
    """Generates daily play count by stream type graph.

    This graph shows play counts over time with separate lines for each
    stream type (direct play, transcode, copy).

    Uses dataclass with slots for memory efficiency.

    Requirements:
        - 16.1: Categorize streams as direct play, transcode, or copy
        - 16.2: Render separate visual elements for each stream type
        - 16.5: Support stream type analysis for daily activity
    """

    def generate(
        self,
        data: list[StreamRecord],
        *,
        config: GraphConfig,
        appearance: GraphAppearanceConfig,
    ) -> Figure:
        """Generate daily play count by stream type line chart.

        Creates a line chart showing play counts by date with separate lines
        for each stream type. Uses seaborn lineplot for clean multi-line visualization.

        Args:
            data: List of stream records to visualize
            config: Graph-specific configuration (palette, annotations, etc.)
            appearance: Visual styling configuration (colors, dimensions, seaborn, etc.)

        Returns:
            Matplotlib Figure object with the generated graph

        Requirements:
            - 16.1: Categorize streams by type
            - 16.2: Render separate visual elements for each stream type
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

        # Aggregate data by date and stream type
        aggregated = aggregate_by_date_and_stream_type(data)

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

        # Get all unique stream types
        all_stream_types: set[str] = set()
        for stream_types in aggregated.values():
            all_stream_types.update(stream_types.keys())

        stream_type_list = sorted(all_stream_types)

        # Get colors from palette or use defaults
        if config.palette:
            from tgraph_bot.graphs.styling import GraphStyling

            styling = GraphStyling()
            colors = styling.get_palette(config.palette, n_colors=len(stream_type_list))
        else:
            # Use default colors for stream types
            default_colors = {
                "direct play": "#2ecc71",  # Green
                "transcode": "#e74c3c",  # Red
                "copy": "#3498db",  # Blue
            }
            colors = [
                default_colors.get(st, appearance.colors.movie)
                for st in stream_type_list
            ]

        # Prepare data for each stream type
        dates = list(aggregated.keys())

        for idx, stream_type in enumerate(stream_type_list):
            counts = [aggregated[date].get(stream_type, 0) for date in dates]

            color = colors[idx] if idx < len(colors) else appearance.colors.movie

            _ = sns.lineplot(
                x=dates,
                y=counts,
                ax=ax,
                color=color,
                marker="o",
                linewidth=2,
                label=stream_type.title(),
            )

        # Set labels and title
        _ = ax.set_xlabel("Date", fontsize=12)  # pyright: ignore[reportUnknownMemberType]  # matplotlib **kwargs
        _ = ax.set_ylabel("Play Count", fontsize=12)  # pyright: ignore[reportUnknownMemberType]  # matplotlib **kwargs
        _ = ax.set_title(  # pyright: ignore[reportUnknownMemberType]  # matplotlib **kwargs
            "Daily Play Count by Stream Type", fontsize=14, fontweight="bold"
        )

        # Add legend
        _ = ax.legend(title="Stream Type", loc="best")  # pyright: ignore[reportUnknownMemberType]  # matplotlib **kwargs

        # Apply grid if enabled
        if appearance.grid.enabled:
            _ = ax.grid(True, alpha=appearance.grid.alpha)  # pyright: ignore[reportUnknownMemberType]  # matplotlib **kwargs

        # Rotate x-axis labels for better readability
        _ = plt.setp(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
            ax.get_xticklabels(),
            rotation=45,
            ha="right",
        )

        # Tight layout to prevent label cutoff
        _ = fig.tight_layout()

        return fig
