"""Top platforms graph generator.

This module implements the TopPlatformsGraph generator that creates
horizontal bar charts showing top N platforms with optional grouping.

Requirements: 5.5, 5.6, 18.4
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure

from tgraph_bot.config.models import GraphAppearanceConfig, GraphConfig, TopGraphConfig
from tgraph_bot.graphs.data import StreamRecord, aggregate_by_platform


@dataclass(slots=True)
class TopPlatformsGraph:
    """Generates top platforms graph.

    This graph shows the top N platforms by play count using horizontal bars.
    Supports platform grouping (e.g., "Plex for Android" and "Plex for Android TV"
    become "Android").

    Uses dataclass with slots for memory efficiency.

    Requirements:
        - 5.5: Use seaborn for enhanced aesthetics
        - 5.6: Support top platforms graph type
        - 18.4: Implement using sns.barplot() for horizontal bars with platform limit and grouping
    """

    def generate(
        self,
        data: list[StreamRecord],
        *,
        config: GraphConfig,
        appearance: GraphAppearanceConfig,
    ) -> Figure:
        """Generate top platforms horizontal bar chart.

        Creates a horizontal bar chart showing the top N platforms by play count.
        Platforms are sorted by count (descending) and limited to the configured maximum.

        Args:
            data: List of stream records to visualize
            config: Graph-specific configuration (limit, palette, etc.)
            appearance: Visual styling configuration (colors, dimensions, seaborn, etc.)

        Returns:
            Matplotlib Figure object with the generated graph

        Requirements:
            - 5.5: Use seaborn barplot
            - 5.6: Generate top platforms graph
            - 18.4: Use sns.barplot() for horizontal bars with platform limit
        """
        # Cast config to TopGraphConfig (it should be TopGraphConfig for this graph type)
        if not isinstance(config, TopGraphConfig):
            msg = "TopPlatformsGraph requires TopGraphConfig"
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

        # Aggregate by platform
        aggregated = aggregate_by_platform(data)

        # Apply grouping (simplify platform names)
        grouped = self._group_platforms(aggregated)

        # Limit to top N
        limited = dict(list(grouped.items())[: top_config.limit])

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
        platforms = list(reversed(list(limited.keys())))
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
            y=platforms,
            ax=ax,
            color=color,
            orient="h",
        )

        # Set labels and title
        _ = ax.set_xlabel("Play Count", fontsize=12)  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
        _ = ax.set_ylabel("Platform", fontsize=12)  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
        _ = ax.set_title(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
            f"Top {len(limited)} Platforms", fontsize=14, fontweight="bold"
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

    def _group_platforms(
        self, aggregated: dict[str, int]
    ) -> dict[str, int]:
        """Group similar platform names.

        Simplifies platform names by grouping similar variants:
        - "Plex for Android" and "Plex for Android TV" -> "Android"
        - "Plex for iOS" and "Plex for iPhone" -> "iOS"
        - "Plex Web" -> "Web"
        - etc.

        Args:
            aggregated: Dictionary mapping platform names to counts

        Returns:
            Dictionary with grouped platform names and summed counts

        Requirements:
            - 18.4: Group similar platform names
        """
        grouped: dict[str, int] = {}

        for platform, count in aggregated.items():
            # Simplify platform name
            simplified = self._simplify_platform_name(platform)
            grouped[simplified] = grouped.get(simplified, 0) + count

        # Sort by count descending
        return dict(sorted(grouped.items(), key=lambda x: x[1], reverse=True))

    def _simplify_platform_name(self, platform: str) -> str:
        """Simplify a platform name.

        Args:
            platform: Original platform name

        Returns:
            Simplified platform name

        Requirements:
            - 18.4: Simplify platform names for grouping
        """
        platform_lower = platform.lower()

        # Android variants
        if "android" in platform_lower:
            return "Android"

        # iOS variants
        if "ios" in platform_lower or "iphone" in platform_lower or "ipad" in platform_lower:
            return "iOS"

        # Web variants
        if "web" in platform_lower:
            return "Web"

        # Roku variants
        if "roku" in platform_lower:
            return "Roku"

        # Apple TV variants
        if "apple tv" in platform_lower or "appletv" in platform_lower:
            return "Apple TV"

        # Fire TV variants
        if "fire tv" in platform_lower or "firetv" in platform_lower:
            return "Fire TV"

        # Xbox variants
        if "xbox" in platform_lower:
            return "Xbox"

        # PlayStation variants
        if "playstation" in platform_lower or "ps4" in platform_lower or "ps5" in platform_lower:
            return "PlayStation"

        # Windows variants
        if "windows" in platform_lower:
            return "Windows"

        # macOS variants
        if "macos" in platform_lower or "mac" in platform_lower:
            return "macOS"

        # Linux variants
        if "linux" in platform_lower:
            return "Linux"

        # Default: return original
        return platform

