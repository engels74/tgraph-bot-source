"""Play count by month graph generator.

This module implements the PlayCountByMonthGraph generator that creates
line charts showing play counts by month with optional media type separation.

Requirements: 5.5, 5.6
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure

from tgraph_bot.config.models import GraphAppearanceConfig, GraphConfig
from tgraph_bot.graphs.data import StreamRecord, aggregate_by_month


@dataclass(slots=True)
class PlayCountByMonthGraph:
    """Generates play count by month graph.

    This graph shows the number of plays per month over the configured time period.
    Uses seaborn lineplot with optional media type separation.

    Uses dataclass with slots for memory efficiency.

    Requirements:
        - 5.5: Use seaborn for enhanced aesthetics
        - 5.6: Support play count by month graph type
    """

    def generate(
        self,
        data: list[StreamRecord],
        *,
        config: GraphConfig,
        appearance: GraphAppearanceConfig,
    ) -> Figure:
        """Generate play count by month line chart.

        Creates a line chart showing play counts by month. If media type separation
        is enabled, creates separate lines for movies and TV shows.

        Args:
            data: List of stream records to visualize
            config: Graph-specific configuration (media type separation, palette, etc.)
            appearance: Visual styling configuration (colors, dimensions, seaborn, etc.)

        Returns:
            Matplotlib Figure object with the generated graph

        Requirements:
            - 5.5: Use seaborn lineplot
            - 5.6: Generate play count by month graph
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

        if config.media_type_separation:
            # Separate data by media type
            movie_data = [r for r in data if r.media_type == "movie"]
            tv_data = [r for r in data if r.media_type == "tv"]

            # Aggregate each type
            movie_agg = aggregate_by_month(movie_data)
            tv_agg = aggregate_by_month(tv_data)

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
            _ = ax.legend()  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs

        else:
            # Aggregate all data together
            aggregated = aggregate_by_month(data)

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
        _ = ax.set_xlabel("Month", fontsize=12)  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
        _ = ax.set_ylabel("Play Count", fontsize=12)  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
        _ = ax.set_title(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
            "Play Count by Month", fontsize=14, fontweight="bold"
        )

        # Apply grid settings
        if appearance.grid.enabled:
            _ = ax.grid(True, alpha=appearance.grid.alpha)  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
        else:
            _ = ax.grid(False)  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs

        # Rotate x-axis labels for better readability
        _ = plt.setp(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
            ax.get_xticklabels(), rotation=45, ha="right"
        )

        # Apply background color
        _ = fig.patch.set_facecolor(appearance.colors.background)
        _ = ax.set_facecolor(appearance.colors.background)

        # Tight layout to prevent label cutoff
        _ = fig.tight_layout()

        return fig
