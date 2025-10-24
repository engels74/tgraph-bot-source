"""Play count by hour of day graph generator.

This module implements the PlayCountByHourOfDayGraph generator that creates
bar charts showing play counts by hour of day with optional stacking.

Requirements: 5.5, 5.6, 18.3
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.figure import Figure

from tgraph_bot.config.models import GraphAppearanceConfig, GraphConfig
from tgraph_bot.graphs.data import StreamRecord, aggregate_by_hour


@dataclass(slots=True)
class PlayCountByHourOfDayGraph:
    """Generates play count by hour of day graph.

    This graph shows the number of plays for each hour of the day (0-23).
    Uses seaborn barplot with optional stacking for media type separation.

    Uses dataclass with slots for memory efficiency.

    Requirements:
        - 5.5: Use seaborn for enhanced aesthetics
        - 5.6: Support play count by hour of day graph type
        - 18.3: Implement using sns.barplot() with stacked option
    """

    def generate(
        self,
        data: list[StreamRecord],
        *,
        config: GraphConfig,
        appearance: GraphAppearanceConfig,
    ) -> Figure:
        """Generate play count by hour of day bar chart.

        Creates a bar chart showing play counts for each hour (0-23).
        If media type separation and stacking are enabled, creates stacked bars.

        Args:
            data: List of stream records to visualize
            config: Graph-specific configuration (media type separation, stacked, etc.)
            appearance: Visual styling configuration (colors, dimensions, seaborn, etc.)

        Returns:
            Matplotlib Figure object with the generated graph

        Requirements:
            - 5.5: Use seaborn barplot
            - 5.6: Generate play count by hour of day graph
            - 18.3: Use sns.barplot() with stacked option
        """
        # Create figure with configured dimensions
        fig, ax = plt.subplots(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
            figsize=(appearance.dimensions.width, appearance.dimensions.height)
        )

        hours = list(range(24))

        if config.media_type_separation and config.stacked:
            # Separate data by media type
            movie_data = [r for r in data if r.media_type == "movie"]
            tv_data = [r for r in data if r.media_type == "tv"]

            # Aggregate each type
            movie_agg = aggregate_by_hour(movie_data)
            tv_agg = aggregate_by_hour(tv_data)

            # Get colors from palette or use base colors
            if config.palette:
                from tgraph_bot.graphs.styling import GraphStyling

                styling = GraphStyling()
                colors = styling.get_palette(config.palette, n_colors=2)
                movie_color = colors[0] if len(colors) >= 1 else appearance.colors.movie
                tv_color = colors[1] if len(colors) >= 2 else appearance.colors.tv
            else:
                movie_color = appearance.colors.movie
                tv_color = appearance.colors.tv

            # Prepare data for stacked bars
            movie_counts = [movie_agg[hour] for hour in hours]
            tv_counts = [tv_agg[hour] for hour in hours]

            x = np.arange(len(hours))
            width = 0.8

            # Create stacked bars
            _ = ax.bar(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
                x, movie_counts, width, label="Movies", color=movie_color
            )
            _ = ax.bar(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
                x,
                tv_counts,
                width,
                bottom=movie_counts,
                label="TV Shows",
                color=tv_color,
            )

            _ = ax.set_xticks(x)  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
            _ = ax.set_xticklabels([str(h) for h in hours])  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
            _ = ax.legend()  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs

        else:
            # Aggregate all data together
            aggregated = aggregate_by_hour(data)
            counts = [aggregated[hour] for hour in hours]

            # Get color from palette or use default
            if config.palette:
                from tgraph_bot.graphs.styling import GraphStyling

                styling = GraphStyling()
                colors = styling.get_palette(config.palette, n_colors=1)
                color = colors[0] if colors else appearance.colors.movie
            else:
                color = appearance.colors.movie

            # Create bar chart
            _ = sns.barplot(
                x=hours,
                y=counts,
                ax=ax,
                color=color,
            )

        # Set labels and title
        _ = ax.set_xlabel("Hour of Day", fontsize=12)  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
        _ = ax.set_ylabel("Play Count", fontsize=12)  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
        _ = ax.set_title(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
            "Play Count by Hour of Day", fontsize=14, fontweight="bold"
        )

        # Apply grid settings
        if appearance.grid.enabled:
            _ = ax.grid(True, alpha=appearance.grid.alpha, axis="y")  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
        else:
            _ = ax.grid(False)  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs

        # Apply background color
        _ = fig.patch.set_facecolor(appearance.colors.background)
        _ = ax.set_facecolor(appearance.colors.background)

        # Tight layout to prevent label cutoff
        _ = fig.tight_layout()

        return fig
