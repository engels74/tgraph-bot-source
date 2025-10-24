"""Daily play count graph generator.

This module implements the DailyPlayCountGraph generator that creates
line charts showing play counts over time with optional media type separation.

Requirements: 5.5, 5.6, 18.1
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure

from tgraph_bot.config.models import GraphAppearanceConfig, GraphConfig
from tgraph_bot.graphs.data import StreamRecord, aggregate_by_date


@dataclass(slots=True)
class DailyPlayCountGraph:
    """Generates daily play count over time graph.

    This graph shows the number of plays per day over the configured time period.
    Uses seaborn lineplot for cleaner multi-line charts when media type separation
    is enabled.

    Uses dataclass with slots for memory efficiency.

    Requirements:
        - 5.5: Use seaborn for enhanced aesthetics
        - 5.6: Support daily play count graph type
        - 18.1: Implement using sns.lineplot() for cleaner multi-line charts
    """

    def generate(
        self,
        data: list[StreamRecord],
        *,
        config: GraphConfig,
        appearance: GraphAppearanceConfig,
    ) -> Figure:
        """Generate daily play count line chart.

        Creates a line chart showing play counts by date. If media type separation
        is enabled, creates separate lines for movies and TV shows.

        Args:
            data: List of stream records to visualize
            config: Graph-specific configuration (media type separation, palette, etc.)
            appearance: Visual styling configuration (colors, dimensions, seaborn, etc.)

        Returns:
            Matplotlib Figure object with the generated graph

        Requirements:
            - 5.5: Use seaborn lineplot for cleaner multi-line charts
            - 5.6: Generate daily play count graph
            - 18.1: Use sns.lineplot() for multi-line charts
        """
        # Create figure with configured dimensions
        fig, ax = plt.subplots(  # matplotlib incomplete stubs
            figsize=(appearance.dimensions.width, appearance.dimensions.height)
        )

        # Handle empty data
        if not data:
            _ = ax.text(
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

        if config.media_type_separation:
            # Separate data by media type
            movie_data = [r for r in data if r.media_type == "movie"]
            tv_data = [r for r in data if r.media_type == "tv"]

            # Aggregate each type
            movie_agg = aggregate_by_date(movie_data)
            tv_agg = aggregate_by_date(tv_data)

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

            # Plot movies
            if movie_agg:
                dates = list(movie_agg.keys())
                counts = list(movie_agg.values())
                _ = sns.lineplot(
                    x=dates,
                    y=counts,
                    ax=ax,
                    color=movie_color,
                    label="Movies",
                    marker="o",
                    linewidth=2,
                )

            # Plot TV shows
            if tv_agg:
                dates = list(tv_agg.keys())
                counts = list(tv_agg.values())
                _ = sns.lineplot(
                    x=dates,
                    y=counts,
                    ax=ax,
                    color=tv_color,
                    label="TV Shows",
                    marker="s",
                    linewidth=2,
                )

            # Add legend
            _ = ax.legend()

        else:
            # Aggregate all data together
            aggregated = aggregate_by_date(data)

            if aggregated:
                dates = list(aggregated.keys())
                counts = list(aggregated.values())

                # Get color from palette or use default
                if config.palette:
                    from tgraph_bot.graphs.styling import GraphStyling

                    styling = GraphStyling()
                    colors = styling.get_palette(config.palette, n_colors=1)
                    color = colors[0] if colors else appearance.colors.movie
                else:
                    color = appearance.colors.movie

                _ = sns.lineplot(
                    x=dates,
                    y=counts,
                    ax=ax,
                    color=color,
                    marker="o",
                    linewidth=2,
                )

        # Set labels and title
        _ = ax.set_xlabel("Date", fontsize=12)
        _ = ax.set_ylabel("Play Count", fontsize=12)
        _ = ax.set_title(
            "Daily Play Count", fontsize=14, fontweight="bold"
        )

        # Apply grid settings
        if appearance.grid.enabled:
            _ = ax.grid(True, alpha=appearance.grid.alpha)
        else:
            _ = ax.grid(False)

        # Rotate x-axis labels for better readability
        _ = plt.setp(
            ax.get_xticklabels(), rotation=45, ha="right"
        )

        # Apply background color
        _ = fig.patch.set_facecolor(appearance.colors.background)
        _ = ax.set_facecolor(appearance.colors.background)

        # Tight layout to prevent label cutoff
        _ = fig.tight_layout()

        return fig

