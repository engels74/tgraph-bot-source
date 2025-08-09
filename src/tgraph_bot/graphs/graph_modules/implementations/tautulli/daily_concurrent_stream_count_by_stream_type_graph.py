"""
Daily concurrent stream count by stream type graph for TGraph Bot.

This module inherits from BaseGraph and uses the Seaborn library to implement
the logic to plot peak concurrent stream counts separated by stream type
(transcode decision). This allows users to see the maximum number of simultaneous
streams for direct play, transcode, and copy streams on a daily basis.
"""

import logging
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, override

import pandas as pd
from matplotlib.axes import Axes

from ...utils.annotation_helper import AnnotationHelper
from ...core.base_graph import BaseGraph
from ...data.data_processor import data_processor
from ...utils.utils import (
    ProcessedRecords,
    ConcurrentStreamAggregates,
    calculate_concurrent_streams_by_date,
    get_stream_type_display_info,
)
from ...visualization.visualization_mixin import VisualizationMixin

if TYPE_CHECKING:
    from .....config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class DailyConcurrentStreamCountByStreamTypeGraph(BaseGraph, VisualizationMixin):
    """Graph showing peak concurrent stream counts per day separated by stream type."""

    def __init__(
        self,
        config: "TGraphBotConfig | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None,
    ) -> None:
        """
        Initialize the daily concurrent stream count by stream type graph.

        Args:
            config: Configuration object containing graph settings
            width: Figure width in inches
            height: Figure height in inches
            dpi: Dots per inch for the figure
            background_color: Background color for the graph (overrides config if provided)
        """
        super().__init__(
            config=config,
            width=width,
            height=height,
            dpi=dpi,
            background_color=background_color,
        )
        self.annotation_helper: AnnotationHelper = AnnotationHelper(self)

    @override
    def get_title(self) -> str:
        """
        Get the title for this graph type.

        Returns:
            The graph title with timeframe information
        """
        return self.get_enhanced_title_with_timeframe(
            "Daily Concurrent Stream Count by Stream Type"
        )

    def _filter_records_by_time_range(
        self, records: ProcessedRecords, time_range_days: int
    ) -> ProcessedRecords:
        """
        Filter processed records to respect the time_range_days configuration.

        Args:
            records: List of processed play history records
            time_range_days: Number of days to keep (from today backwards)

        Returns:
            Filtered list of records within the specified time range
        """
        if not records or time_range_days <= 0:
            return records

        # Calculate cutoff date (time_range_days ago from today)
        cutoff_date = datetime.now() - timedelta(days=time_range_days)

        # Filter records to only include those within the time range
        filtered_records = [
            record
            for record in records
            if "datetime" in record and record["datetime"] >= cutoff_date
        ]

        logger.info(
            f"Filtered {len(records)} records down to {len(filtered_records)} records within {time_range_days} days"
        )
        return filtered_records

    def _setup_aligned_date_axis(
        self, ax: Axes, sorted_dates: list[str], num_dates: int
    ) -> None:
        """
        Setup the date axis with proper alignment between labels and grid lines.

        Args:
            ax: The matplotlib axes to configure
            sorted_dates: List of sorted date strings
            num_dates: Total number of dates
        """

        # Determine optimal labeling strategy based on number of dates
        if num_dates <= 30:
            # For time_range_days=30 or less: Show every date for perfect alignment
            interval = 1
            date_format = "%m/%d"
        elif num_dates <= 60:
            # Two months: Show every 2-3 days
            interval = max(1, num_dates // 20)  # Show ~20 labels max
            date_format = "%m/%d"
        elif num_dates <= 90:
            # Three months: Show every 3-4 days
            interval = max(1, num_dates // 20)  # Show ~20 labels max
            date_format = "%m/%d"
        elif num_dates <= 180:
            # Six months: Show weekly intervals
            interval = max(1, num_dates // 25)  # Show ~25 labels max
            date_format = "%m/%d"
        else:
            # More than six months: Use year-month format with monthly intervals
            interval = max(1, num_dates // 24)  # Show ~24 labels max
            date_format = "%Y-%m"

        # For better alignment, manually set the tick positions and labels
        # Calculate which dates to show based on the interval
        selected_indices = list(range(0, num_dates, interval))

        # Ensure we always include the last date if it's not already included
        if selected_indices and selected_indices[-1] != num_dates - 1:
            selected_indices.append(num_dates - 1)

        # Set the tick positions to align perfectly with data points
        ax.set_xticks([i for i in selected_indices])  # pyright: ignore[reportAny] # matplotlib method returns Any

        # Set the tick labels using the selected dates
        selected_dates = [sorted_dates[i] for i in selected_indices]
        selected_date_objects = [pd.to_datetime(date) for date in selected_dates]

        # Format the labels
        formatted_labels = [
            date_obj.strftime(date_format) for date_obj in selected_date_objects
        ]
        ax.set_xticklabels(formatted_labels)  # pyright: ignore[reportAny] # matplotlib method returns Any

        # Rotate labels for better readability
        _ = ax.tick_params(axis="x", rotation=45)  # pyright: ignore[reportUnknownMemberType]

        logger.debug(
            f"Configured date axis with {len(selected_indices)} labels for {num_dates} data points"
        )

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """
        Generate the daily concurrent stream count by stream type graph using the provided data.

        Args:
            data: Dictionary containing play history data from Tautulli API
                 Expected structure: {'data': [list of play records]}

        Returns:
            Path to the generated graph image file

        Raises:
            ValueError: If data is invalid or missing required fields
        """
        logger.info("Generating daily concurrent stream count by stream type graph")

        try:
            # Step 1: Extract and process play history data using DataProcessor
            _, processed_records = data_processor.extract_and_process_play_history(data)

            # Step 2: Extract time range configuration
            time_range_days = self.get_time_range_days_from_config()
            logger.info(f"Using time_range_days configuration: {time_range_days} days")

            # Step 3: Filter records to respect time_range_days configuration
            filtered_records = self._filter_records_by_time_range(
                processed_records, time_range_days
            )
            processed_records = filtered_records

            # Step 4: Setup figure with styling using combined utility
            _, ax = self.setup_figure_with_styling()

            # Step 5: Configure grid styling (explicit for line plots)
            self.configure_seaborn_style_with_grid()
            if self.get_grid_enabled():
                # For line plots, explicitly enable grid on the axes
                ax.grid(True, alpha=0.7, linewidth=0.5)  # pyright: ignore[reportUnknownMemberType] # matplotlib method with **kwargs
            else:
                ax.grid(False)  # pyright: ignore[reportUnknownMemberType] # matplotlib method with **kwargs

            # Step 6: Generate concurrent stream visualization
            if processed_records:
                self._generate_concurrent_stream_visualization(ax, processed_records)
            else:
                # Show message that no stream data is available
                self._generate_no_stream_data_visualization(ax)

            # Step 7: Finalize and save using combined utility
            output_path = self.finalize_and_save_figure(
                graph_type="daily_concurrent_stream_count_by_stream_type", user_id=None
            )
            return output_path

        except Exception as e:
            logger.exception(
                f"Error generating daily concurrent stream count by stream type graph: {e}"
            )
            raise
        finally:
            self.cleanup()

    def _generate_concurrent_stream_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate concurrent stream visualization showing peak concurrent streams by type.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Calculate concurrent streams by date using the utility function
        concurrent_data = calculate_concurrent_streams_by_date(
            processed_records, separate_by_stream_type=True
        )

        if not concurrent_data:
            self.handle_empty_data_with_message(
                ax, "No concurrent stream data available for the selected time range."
            )
            return

        # Prepare data for plotting by stream type
        stream_type_data = self._prepare_stream_type_concurrent_data(concurrent_data)

        if not stream_type_data:
            self.handle_empty_data_with_message(
                ax, "No concurrent stream data available for the selected time range."
            )
            return

        # Get all dates for consistent x-axis
        all_dates: set[str] = set()
        for _, date_data in stream_type_data.items():
            all_dates.update(date_data.keys())

        if not all_dates:
            self.handle_empty_data_with_message(
                ax, "No data available for the selected time range."
            )
            return

        # Sort dates for proper timeline
        sorted_dates: list[str] = sorted(all_dates)

        # Get stream type display info
        stream_type_info = get_stream_type_display_info()

        # Plot each stream type separately
        stream_types_plotted: list[str] = []
        for stream_type, date_data in stream_type_data.items():
            if not date_data:
                continue

            # Prepare data for this stream type
            counts = [date_data.get(date, 0) for date in sorted_dates]

            # Skip if no data for this stream type
            if all(count == 0 for count in counts):
                continue

            # Get display information
            display_info = stream_type_info.get(
                stream_type, {"display_name": stream_type.title(), "color": "#1f77b4"}
            )
            label = display_info["display_name"]
            color = display_info["color"]

            # Create the plot using numerical x-axis for better control
            import numpy as np

            x_positions = np.arange(len(sorted_dates))
            _ = ax.plot(  # pyright: ignore[reportUnknownMemberType] # matplotlib method
                x_positions,
                counts,
                marker="o",
                linewidth=3,
                markersize=8,
                label=label,
                color=color,
                markerfacecolor=color,
                markeredgecolor="white",
                markeredgewidth=1.5,
                alpha=0.8,
            )

            stream_types_plotted.append(stream_type)

        if not stream_types_plotted:
            self.handle_empty_data_with_message(
                ax, "No concurrent stream data available for the selected time range."
            )
            return

        # Customize the plot
        self.setup_title_and_axes_with_ax(
            ax, xlabel="Date", ylabel="Peak Concurrent Streams"
        )

        # Setup aligned date axis
        num_dates = len(sorted_dates)
        self._setup_aligned_date_axis(ax, sorted_dates, num_dates)

        # Add legend
        _ = ax.legend(  # pyright: ignore[reportUnknownMemberType]
            loc="best",
            frameon=True,
            fancybox=True,
            shadow=True,
            framealpha=0.9,
            fontsize=12,
        )

        # Add line value annotations if enabled
        # Collect all data points from all plotted lines
        all_x_data: list[float] = []
        all_y_data: list[float] = []

        for stream_type in stream_types_plotted:
            if stream_type in stream_type_data:
                date_data = stream_type_data[stream_type]
                counts = [date_data.get(date, 0) for date in sorted_dates]
                x_positions = list(range(len(sorted_dates)))

                # Add data points from this line
                all_x_data.extend(x_positions)
                all_y_data.extend(counts)

        if all_x_data and all_y_data:
            self.annotation_helper.annotate_line_points(
                ax=ax,
                config_key="graphs.appearance.annotations.enabled_on.daily_concurrent_stream_count_by_stream_type",
                x_data=all_x_data,
                y_data=all_y_data,
                ha="center",
                va="bottom",
                offset_y=2,
            )

        # Add peak annotations if enabled (separate feature)
        if self.is_peak_annotations_enabled():
            self._add_peak_annotations(ax, stream_type_data, sorted_dates)

        logger.info(
            f"Created concurrent stream count graph with {len(stream_types_plotted)} stream types and {num_dates} data points"
        )

    def _generate_no_stream_data_visualization(self, ax: Axes) -> None:
        """
        Generate visualization when no stream data is available.

        Args:
            ax: The matplotlib axes to plot on
        """
        self.handle_empty_data_with_message(
            ax,
            "No concurrent stream data available.\nThis graph requires Tautulli API data with duration and timing information.",
        )

    def _prepare_stream_type_concurrent_data(
        self, concurrent_data: ConcurrentStreamAggregates
    ) -> dict[str, dict[str, int]]:
        """
        Prepare concurrent stream data organized by stream type and date.

        Args:
            concurrent_data: List of concurrent stream records from calculate_concurrent_streams_by_date

        Returns:
            Dictionary mapping stream types to date-count dictionaries
        """
        stream_type_data: dict[str, dict[str, int]] = {}

        for record in concurrent_data:
            date_str = str(record["date"])
            stream_breakdown = record.get("stream_type_breakdown", {})

            for stream_type, count in stream_breakdown.items():
                if stream_type not in stream_type_data:
                    stream_type_data[stream_type] = {}

                stream_type_data[stream_type][date_str] = int(count)

        # Fill missing dates with zeros for all stream types for consistency
        if stream_type_data:
            all_dates: set[str] = set()
            for date_data in stream_type_data.values():
                all_dates.update(date_data.keys())

            for stream_type in stream_type_data:
                for date_str in all_dates:
                    if date_str not in stream_type_data[stream_type]:
                        stream_type_data[stream_type][date_str] = 0

        return stream_type_data

    def _add_peak_annotations(
        self,
        ax: Axes,
        stream_type_data: dict[str, dict[str, int]],
        sorted_dates: list[str],
    ) -> None:
        """
        Add peak annotations for stream type concurrent data.

        Args:
            ax: The matplotlib axes to add annotations to
            stream_type_data: Dictionary of stream type data by date
            sorted_dates: List of sorted date strings
        """
        stream_type_info = get_stream_type_display_info()

        for stream_type, date_data in stream_type_data.items():
            if not date_data:
                continue

            counts: list[int] = [date_data.get(date, 0) for date in sorted_dates]
            if all(count == 0 for count in counts):
                continue

            max_count: int = max(counts)
            if max_count > 0:
                max_idx = counts.index(max_count)

                # Get label for this stream type
                display_info = stream_type_info.get(
                    stream_type, {"display_name": stream_type.title()}
                )
                label = display_info["display_name"]

                self.annotation_helper.annotate_peak_value(
                    ax,
                    x=float(max_idx),
                    y=float(max_count),
                    value=max_count,
                    label_prefix=f"{label} Peak",
                )
