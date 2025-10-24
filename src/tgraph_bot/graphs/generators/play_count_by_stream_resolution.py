"""Play count by stream resolution graph generator.

This module implements the PlayCountByStreamResolutionGraph generator that creates
bar charts showing play counts by stream resolution with optional transcoding focus.

Requirements: 17.1, 17.2, 17.3, 17.4, 17.5
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure

from tgraph_bot.config.models import GraphAppearanceConfig, GraphConfig
from tgraph_bot.graphs.data import StreamRecord, aggregate_by_resolution


@dataclass(slots=True)
class PlayCountByStreamResolutionGraph:
    """Generates play count by stream resolution graph.

    This graph shows play counts by stream resolution (delivered quality)
    with configurable grouping and optional transcoding focus emphasis.

    Uses dataclass with slots for memory efficiency.

    Requirements:
        - 17.1: Extract resolution data from stream records
        - 17.2: Group resolutions into standard categories
        - 17.3: Display exact resolution values in detailed mode
        - 17.4: Group into broad categories in simplified mode
        - 17.5: Emphasize transcoded content with distinct visual styling
    """

    def generate(
        self,
        data: list[StreamRecord],
        *,
        config: GraphConfig,
        appearance: GraphAppearanceConfig,
        resolution_grouping: str = "standard",
        transcoding_focus: bool = False,
    ) -> Figure:
        """Generate play count by stream resolution bar chart.

        Creates a bar chart showing play counts by stream resolution.
        Resolution grouping can be "standard", "detailed", or "simplified".
        If transcoding_focus is enabled, transcoded streams are visually emphasized.

        Args:
            data: List of stream records to visualize
            config: Graph-specific configuration (palette, annotations, etc.)
            appearance: Visual styling configuration (colors, dimensions, seaborn, etc.)
            resolution_grouping: Grouping mode - "standard", "detailed", or "simplified"
            transcoding_focus: Whether to emphasize transcoded content

        Returns:
            Matplotlib Figure object with the generated graph

        Requirements:
            - 17.1: Extract resolution data
            - 17.5: Emphasize transcoded content if enabled
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

        if transcoding_focus:
            # Separate transcoded and non-transcoded streams
            transcoded_data = [r for r in data if r.stream_type == "transcode"]
            non_transcoded_data = [r for r in data if r.stream_type != "transcode"]

            # Aggregate both separately
            transcoded_agg = aggregate_by_resolution(
                transcoded_data,
                resolution_field="stream_resolution",
                grouping=resolution_grouping,
            )
            non_transcoded_agg = aggregate_by_resolution(
                non_transcoded_data,
                resolution_field="stream_resolution",
                grouping=resolution_grouping,
            )

            # Get all unique resolutions
            all_resolutions = sorted(
                set(transcoded_agg.keys()) | set(non_transcoded_agg.keys())
            )

            if not all_resolutions:
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

            # Prepare data for stacked bars
            transcoded_counts = [transcoded_agg.get(res, 0) for res in all_resolutions]
            non_transcoded_counts = [
                non_transcoded_agg.get(res, 0) for res in all_resolutions
            ]

            # Create stacked bar chart
            x_pos = range(len(all_resolutions))

            _ = ax.bar(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
                x_pos,
                non_transcoded_counts,
                label="Direct Play / Copy",
                color="#2ecc71",  # Green
            )
            _ = ax.bar(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
                x_pos,
                transcoded_counts,
                bottom=non_transcoded_counts,
                label="Transcoded",
                color="#e74c3c",  # Red (emphasis)
            )

            _ = ax.set_xticks(x_pos)  # pyright: ignore[reportUnknownMemberType]  # matplotlib **kwargs
            _ = ax.set_xticklabels(all_resolutions)  # pyright: ignore[reportUnknownMemberType]  # matplotlib **kwargs
            _ = ax.legend(title="Stream Type", loc="best")  # pyright: ignore[reportUnknownMemberType]  # matplotlib **kwargs

        else:
            # Standard aggregation without transcoding focus
            aggregated = aggregate_by_resolution(
                data,
                resolution_field="stream_resolution",
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

            # Create bar chart
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
        _ = ax.set_xlabel("Stream Resolution", fontsize=12)  # pyright: ignore[reportUnknownMemberType]  # matplotlib **kwargs
        _ = ax.set_ylabel("Play Count", fontsize=12)  # pyright: ignore[reportUnknownMemberType]  # matplotlib **kwargs

        title_suffix = {
            "standard": "(Standard Grouping)",
            "detailed": "(Detailed)",
            "simplified": "(Simplified)",
        }.get(resolution_grouping, "")

        focus_suffix = " - Transcoding Focus" if transcoding_focus else ""

        _ = ax.set_title(  # pyright: ignore[reportUnknownMemberType]  # matplotlib **kwargs
            f"Play Count by Stream Resolution {title_suffix}{focus_suffix}",
            fontsize=14,
            fontweight="bold",
        )

        # Apply grid if enabled
        if appearance.grid.enabled:
            _ = ax.grid(True, alpha=appearance.grid.alpha, axis="y")  # pyright: ignore[reportUnknownMemberType]  # matplotlib **kwargs

        # Rotate x-axis labels for better readability
        _ = plt.setp(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
            ax.get_xticklabels(),
            rotation=45,
            ha="right",
        )

        # Tight layout to prevent label cutoff
        _ = fig.tight_layout()

        return fig
