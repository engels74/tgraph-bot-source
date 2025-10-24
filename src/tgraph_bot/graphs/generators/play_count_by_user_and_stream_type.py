"""Play count by user and stream type graph generator.

This module implements the PlayCountByUserAndStreamTypeGraph generator that
creates bar charts showing play counts by user with stream type breakdown
and optional privacy mode.

Requirements: 13.1, 13.3, 13.4, 16.5
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from tgraph_bot.config.models import GraphAppearanceConfig, GraphConfig
from tgraph_bot.graphs.data import (
    StreamRecord,
    aggregate_by_user_and_stream_type,
    anonymize_usernames,
)


@dataclass(slots=True)
class PlayCountByUserAndStreamTypeGraph:
    """Generates play count by user and stream type graph.

    This graph shows play counts by user with stream type breakdown.
    Supports both stacked and grouped bar chart layouts, and privacy mode
    for username anonymization.

    Uses dataclass with slots for memory efficiency.

    Requirements:
        - 13.1: Apply username anonymization when privacy mode enabled
        - 13.3: Maintain consistent anonymized labels
        - 13.4: Map same username to same label
        - 16.5: Support user breakdown by stream type
    """

    def generate(
        self,
        data: list[StreamRecord],
        *,
        config: GraphConfig,
        appearance: GraphAppearanceConfig,
        top_n: int = 10,
        privacy_mode: bool = False,
    ) -> Figure:
        """Generate play count by user and stream type bar chart.

        Creates a bar chart showing play counts by user with stream type
        breakdown. Can be stacked or grouped based on config.stacked.
        Supports privacy mode for username anonymization.

        Args:
            data: List of stream records to visualize
            config: Graph-specific configuration (stacked, palette, etc.)
            appearance: Visual styling configuration (colors, dimensions, seaborn, etc.)
            top_n: Number of top users to display
            privacy_mode: Whether to anonymize usernames

        Returns:
            Matplotlib Figure object with the generated graph

        Requirements:
            - 13.1: Anonymize usernames if privacy mode enabled
            - 16.5: User breakdown by stream type
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

        # Apply privacy mode if enabled
        processed_data = anonymize_usernames(data) if privacy_mode else data

        # Aggregate by user and stream type
        aggregated = aggregate_by_user_and_stream_type(processed_data)

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

        # Limit to top N users
        limited = dict(list(aggregated.items())[:top_n])

        # Get all unique stream types
        all_stream_types: set[str] = set()
        for stream_types in limited.values():
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
                "transcode": "#e74c3c",    # Red
                "copy": "#3498db",         # Blue
            }
            colors = [
                default_colors.get(st, appearance.colors.movie)
                for st in stream_type_list
            ]

        users = list(limited.keys())
        x_pos = np.arange(len(users))

        if config.stacked:
            # Create stacked bar chart
            bottom = np.zeros(len(users))
            
            for idx, stream_type in enumerate(stream_type_list):
                counts = [
                    limited[user].get(stream_type, 0)
                    for user in users
                ]
                
                color = colors[idx] if idx < len(colors) else appearance.colors.movie
                
                _ = ax.bar(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
                    x_pos,
                    counts,
                    bottom=bottom,
                    label=stream_type.title(),
                    color=color,
                )
                
                bottom += np.array(counts)

        else:
            # Create grouped bar chart
            bar_width = 0.8 / len(stream_type_list)
            
            for idx, stream_type in enumerate(stream_type_list):
                counts = [
                    limited[user].get(stream_type, 0)
                    for user in users
                ]
                
                color = colors[idx] if idx < len(colors) else appearance.colors.movie
                offset = (idx - len(stream_type_list) / 2) * bar_width + bar_width / 2
                
                _ = ax.bar(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
                    x_pos + offset,
                    counts,
                    bar_width,
                    label=stream_type.title(),
                    color=color,
                )

        # Set labels and title
        _ = ax.set_xlabel("User", fontsize=12)
        _ = ax.set_ylabel("Play Count", fontsize=12)
        
        layout_type = "Stacked" if config.stacked else "Grouped"
        privacy_suffix = " (Privacy Mode)" if privacy_mode else ""
        _ = ax.set_title(
            f"Play Count by User and Stream Type ({layout_type}){privacy_suffix}",
            fontsize=14,
            fontweight="bold",
        )
        
        _ = ax.set_xticks(x_pos)
        _ = ax.set_xticklabels(users)
        _ = ax.legend(title="Stream Type", loc="best")

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

