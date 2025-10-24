"""Top users graph generator.

This module implements the TopUsersGraph generator that creates
horizontal bar charts showing top N users by play count.

Requirements: 5.5, 5.6, 18.5
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure

from tgraph_bot.config.models import GraphAppearanceConfig, GraphConfig, TopGraphConfig
from tgraph_bot.graphs.data import StreamRecord, aggregate_by_user


@dataclass(slots=True)
class TopUsersGraph:
    """Generates top users graph.

    This graph shows the top N users by play count using horizontal bars.
    Respects privacy settings for username display.

    Uses dataclass with slots for memory efficiency.

    Requirements:
        - 5.5: Use seaborn for enhanced aesthetics
        - 5.6: Support top users graph type
        - 18.5: Implement using sns.barplot() for horizontal bars with user limit
    """

    def generate(
        self,
        data: list[StreamRecord],
        *,
        config: GraphConfig,
        appearance: GraphAppearanceConfig,
    ) -> Figure:
        """Generate top users horizontal bar chart.

        Creates a horizontal bar chart showing the top N users by play count.
        Users are sorted by count (descending) and limited to the configured maximum.

        Args:
            data: List of stream records to visualize
            config: Graph-specific configuration (limit, palette, etc.)
            appearance: Visual styling configuration (colors, dimensions, seaborn, etc.)

        Returns:
            Matplotlib Figure object with the generated graph

        Requirements:
            - 5.5: Use seaborn barplot
            - 5.6: Generate top users graph
            - 18.5: Use sns.barplot() for horizontal bars with user limit
        """
        # Cast config to TopGraphConfig (it should be TopGraphConfig for this graph type)
        if not isinstance(config, TopGraphConfig):
            msg = "TopUsersGraph requires TopGraphConfig"
            raise TypeError(msg)
        top_config = config

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

        # Aggregate by user
        aggregated = aggregate_by_user(data)

        # Limit to top N
        limited = dict(list(aggregated.items())[: top_config.limit])

        if not limited:
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

        # Prepare data for plotting (reverse for top-to-bottom display)
        users = list(reversed(list(limited.keys())))
        counts = list(reversed(list(limited.values())))

        # Get color from palette or use default
        if top_config.palette:
            from tgraph_bot.graphs.styling import GraphStyling

            styling = GraphStyling()
            colors = styling.get_palette(top_config.palette, n_colors=1)
            color = colors[0] if colors else appearance.colors.movie
        else:
            color = appearance.colors.movie

        # Create horizontal bar chart
        _ = sns.barplot(
            x=counts,
            y=users,
            ax=ax,
            color=color,
            orient="h",
        )

        # Set labels and title
        _ = ax.set_xlabel("Play Count", fontsize=12)  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
        _ = ax.set_ylabel("User", fontsize=12)  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
        _ = ax.set_title(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
            f"Top {len(limited)} Users", fontsize=14, fontweight="bold"
        )

        # Apply grid settings
        if appearance.grid.enabled:
            _ = ax.grid(True, alpha=appearance.grid.alpha, axis="x")  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
        else:
            _ = ax.grid(False)  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs

        # Apply background color
        _ = fig.patch.set_facecolor(appearance.colors.background)
        _ = ax.set_facecolor(appearance.colors.background)

        # Tight layout to prevent label cutoff
        _ = fig.tight_layout()

        return fig

