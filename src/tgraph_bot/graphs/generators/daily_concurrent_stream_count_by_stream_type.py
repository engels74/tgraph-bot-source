"""Daily concurrent stream count by stream type graph generator.

This module implements the DailyConcurrentStreamCountByStreamTypeGraph generator
that creates line charts showing peak concurrent streams over time separated by
stream type (direct play, transcode, copy).

Requirements: 16.1, 16.2, 16.3, 16.4
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure

from tgraph_bot.config.models import GraphAppearanceConfig, GraphConfig
from tgraph_bot.graphs.data import StreamRecord


def calculate_peak_concurrent_streams_by_type(
    records: Sequence[StreamRecord],
) -> dict[date, dict[str, int]]:
    """Calculate peak concurrent streams by date and stream type.

    For each date, determines the maximum number of concurrent streams
    for each stream type. This is a simplified calculation that counts
    streams per hour and finds the peak.

    Args:
        records: Sequence of stream records to analyze

    Returns:
        Dictionary mapping dates to dictionaries of stream type peak counts

    Requirements:
        - 16.3: Calculate peak concurrent streams for each stream type
    """
    if not records:
        return {}

    # Group by date, hour, and stream type
    hourly_counts: dict[date, dict[int, dict[str, int]]] = {}
    
    for record in records:
        record_date = record.timestamp.date()
        hour = record.timestamp.hour
        stream_type = record.stream_type
        
        if record_date not in hourly_counts:
            hourly_counts[record_date] = {}
        if hour not in hourly_counts[record_date]:
            hourly_counts[record_date][hour] = {}
        
        hourly_counts[record_date][hour][stream_type] = (
            hourly_counts[record_date][hour].get(stream_type, 0) + 1
        )

    # Find peak for each date and stream type
    peak_counts: dict[date, dict[str, int]] = {}
    
    for record_date, hours in hourly_counts.items():
        peak_counts[record_date] = {}
        
        # Get all stream types for this date
        all_stream_types: set[str] = set()
        for hour_data in hours.values():
            all_stream_types.update(hour_data.keys())
        
        # Find peak for each stream type
        for stream_type in all_stream_types:
            peak = max(
                hour_data.get(stream_type, 0)
                for hour_data in hours.values()
            )
            peak_counts[record_date][stream_type] = peak

    # Return sorted by date
    return dict(sorted(peak_counts.items()))


@dataclass(slots=True)
class DailyConcurrentStreamCountByStreamTypeGraph:
    """Generates daily concurrent stream count by stream type graph.

    This graph shows peak concurrent streams over time with separate lines
    for each stream type (direct play, transcode, copy). Optionally highlights
    peak values.

    Uses dataclass with slots for memory efficiency.

    Requirements:
        - 16.1: Categorize streams as direct play, transcode, or copy
        - 16.2: Render separate visual elements for each stream type
        - 16.3: Calculate peak concurrent streams for each stream type
        - 16.4: Mark peak usage periods with highlight color
    """

    def generate(
        self,
        data: list[StreamRecord],
        *,
        config: GraphConfig,
        appearance: GraphAppearanceConfig,
    ) -> Figure:
        """Generate daily concurrent stream count by stream type line chart.

        Creates a line chart showing peak concurrent streams by date with separate
        lines for each stream type. Optionally highlights overall peak values.

        Args:
            data: List of stream records to visualize
            config: Graph-specific configuration (palette, peak highlighting, etc.)
            appearance: Visual styling configuration (colors, dimensions, seaborn, etc.)

        Returns:
            Matplotlib Figure object with the generated graph

        Requirements:
            - 16.3: Calculate peak concurrent streams
            - 16.4: Highlight peaks if enabled
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

        # Calculate peak concurrent streams by date and stream type
        peak_data = calculate_peak_concurrent_streams_by_type(data)

        if not peak_data:
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
        for stream_types in peak_data.values():
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

        # Prepare data for each stream type
        dates = list(peak_data.keys())
        
        # Track peak values for highlighting
        peak_values: dict[str, tuple[date, int]] = {}
        
        for idx, stream_type in enumerate(stream_type_list):
            counts = [
                peak_data[date].get(stream_type, 0)
                for date in dates
            ]
            
            # Track peak for this stream type
            if counts:
                max_count = max(counts)
                max_idx = counts.index(max_count)
                peak_values[stream_type] = (dates[max_idx], max_count)
            
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

        # Highlight peaks if enabled
        if config.peak_highlighting_enabled and peak_values:
            for stream_type, (peak_date, peak_count) in peak_values.items():
                # Find the index of the peak date in the dates list
                peak_idx = dates.index(peak_date)
                _ = ax.plot(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
                    peak_idx,
                    peak_count,
                    marker="*",
                    markersize=15,
                    color=appearance.colors.background,
                    markeredgecolor="#FFD700",  # Gold color for peak
                    markeredgewidth=2,
                    zorder=10,
                )

        # Set labels and title
        _ = ax.set_xlabel("Date", fontsize=12)
        _ = ax.set_ylabel("Peak Concurrent Streams", fontsize=12)
        _ = ax.set_title(
            "Daily Peak Concurrent Streams by Stream Type",
            fontsize=14,
            fontweight="bold",
        )
        
        # Add legend
        _ = ax.legend(title="Stream Type", loc="best")

        # Apply grid if enabled
        if appearance.grid.enabled:
            _ = ax.grid(True, alpha=appearance.grid.alpha)

        # Rotate x-axis labels for better readability
        _ = plt.setp(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
            ax.get_xticklabels(),
            rotation=45,
            ha="right",
        )

        # Tight layout to prevent label cutoff
        _ = fig.tight_layout()  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs

        return fig

