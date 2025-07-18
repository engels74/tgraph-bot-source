"""
Daily play count graph for TGraph Bot.

This module inherits from BaseGraph and uses the Seaborn library
to implement the logic to plot daily play counts. This approach
simplifies the plotting code and produces a more aesthetically pleasing result.
"""

import logging
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, cast, override

import pandas as pd
from matplotlib.axes import Axes

from ...utils.annotation_helper import AnnotationHelper
from ...core.base_graph import BaseGraph
from ...data.data_processor import data_processor
from ...data.empty_data_handler import EmptyDataHandler
from ...utils.utils import (
    ProcessedRecords,
    aggregate_by_date,
    aggregate_by_date_separated,
    get_media_type_display_info,
    handle_empty_data,
)
from ...visualization.visualization_mixin import VisualizationMixin

if TYPE_CHECKING:
    from .....config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class DailyPlayCountGraph(BaseGraph, VisualizationMixin):
    """Graph showing daily play counts over time."""

    def __init__(
        self,
        config: "TGraphBotConfig | dict[str, object] | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None,
    ) -> None:
        """
        Initialize the daily play count graph.

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
        return self.get_enhanced_title_with_timeframe("Daily Play Count")

    def _filter_records_by_time_range(
        self, records: ProcessedRecords, time_range_days: int
    ) -> ProcessedRecords:
        """
        Filter processed records to respect the TIME_RANGE_DAYS configuration.

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

    def _get_time_range_days_from_config(self) -> int:
        """
        Extract the TIME_RANGE_DAYS value from the graph's configuration.

        Returns:
            Number of days for the time range from config, defaults to 30 if not found
        """
        return self.get_time_range_days_from_config()

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
            # For TIME_RANGE_DAYS=30 or less: Show every date for perfect alignment
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
        selected_date_objects = [pd.to_datetime(date) for date in selected_dates]  # pyright: ignore[reportUnknownMemberType] # pandas method overloads

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
        Generate the daily play count graph using the provided data.

        Args:
            data: Dictionary containing play history data from Tautulli API
                 Expected structure: {'data': [list of play records]}

        Returns:
            Path to the generated graph image file

        Raises:
            ValueError: If data is invalid or missing required fields
        """
        logger.info("Generating daily play count graph")

        try:
            # Step 1: Extract and process play history data using DataProcessor
            _, processed_records = data_processor.extract_and_process_play_history(data)

            # Step 2: Extract time range configuration
            time_range_days = self._get_time_range_days_from_config()
            logger.info(f"Using TIME_RANGE_DAYS configuration: {time_range_days} days")

            # Step 3: Filter records to respect TIME_RANGE_DAYS configuration
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

            # Step 7: Check if media type separation is enabled
            use_separation = self.get_media_type_separation_enabled()

            if use_separation and processed_records:
                # Generate separated visualization
                self._generate_separated_visualization(ax, processed_records)
            else:
                # Generate traditional combined visualization
                self._generate_combined_visualization(ax, processed_records)

            # Step 8: Finalize and save using combined utility
            output_path = self.finalize_and_save_figure(
                graph_type="daily_play_count", user_id=None
            )
            return output_path

        except Exception as e:
            logger.exception(f"Error generating daily play count graph: {e}")
            raise
        finally:
            self.cleanup()

    def _generate_separated_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate separated visualization showing Movies and TV Series separately.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Get time range configuration for consistent date filling
        time_range_days = self._get_time_range_days_from_config()

        # Aggregate data by date with media type separation, filling missing dates
        separated_data = aggregate_by_date_separated(
            processed_records, fill_missing_dates=True, time_range_days=time_range_days
        )
        display_info = get_media_type_display_info()

        if not separated_data:
            self._handle_empty_data_case(ax)
            return

        # Prepare data for plotting
        all_dates: set[str] = set()
        for media_type_data in separated_data.values():
            all_dates.update(media_type_data.keys())

        if not all_dates:
            self._handle_empty_data_case(ax)
            return

        # Sort dates for proper timeline
        sorted_dates: list[str] = sorted(all_dates)

        # Plot each media type separately
        media_types_plotted: list[str] = []
        for media_type, media_data in separated_data.items():
            if not media_data:
                continue

            # Prepare data for this media type
            counts = [media_data.get(date, 0) for date in sorted_dates]

            # Skip if no data for this media type
            if all(count == 0 for count in counts):
                continue

            # Get display information
            if media_type in display_info:
                label = display_info[media_type]["display_name"]
                color = display_info[media_type]["color"]

                # Override with config colors if available
                if media_type == "tv":
                    color = self.get_tv_color()
                elif media_type == "movie":
                    color = self.get_movie_color()
            else:
                label = media_type.title()
                color = "#666666"  # Default gray for unknown types

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

            media_types_plotted.append(media_type)

        if not media_types_plotted:
            self._handle_empty_data_case(ax)
            return

        # Customize the plot
        _ = ax.set_title(self.get_title(), fontsize=18, fontweight="bold", pad=20)  # pyright: ignore[reportUnknownMemberType]
        _ = ax.set_xlabel("Date", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType]
        _ = ax.set_ylabel("Play Count", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType]

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

        # Add bar value annotations if enabled
        annotate_enabled = self.get_config_value("ANNOTATE_DAILY_PLAY_COUNT", False)
        if annotate_enabled:
            # Add value annotations for each data point
            for media_type, media_data in separated_data.items():
                if not media_data or all(count == 0 for count in media_data.values()):
                    continue
                for i, date in enumerate(sorted_dates):
                    count_value = media_data.get(date, 0)
                    if count_value > 0:
                        self.add_bar_value_annotation(
                            ax,
                            x=float(i),
                            y=float(count_value),
                            value=count_value,
                            ha="center",
                            va="bottom",
                            offset_y=2,
                        )

        # Add peak annotations if enabled (separate feature)
        if self.is_peak_annotations_enabled():
            self._add_peak_annotations(ax, separated_data, sorted_dates)

        logger.info(
            f"Created separated daily play count graph with {len(media_types_plotted)} media types and {num_dates} data points"
        )

    def _generate_combined_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate traditional combined visualization (backward compatibility).

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Use traditional aggregation method with date filling
        if processed_records:
            time_range_days = self._get_time_range_days_from_config()
            daily_counts = aggregate_by_date(
                processed_records,
                fill_missing_dates=True,
                time_range_days=time_range_days,
            )
            logger.info(f"Aggregated data for {len(daily_counts)} days")
        else:
            logger.warning("No valid records found, using empty data")
            daily_counts = handle_empty_data("daily")
            if not isinstance(daily_counts, dict):
                daily_counts = {}

        if daily_counts:
            # Convert to lists for plotting
            dates = list(daily_counts.keys())
            counts = list(daily_counts.values())

            # Sort by date
            date_count_pairs = list(zip(dates, counts))
            date_count_pairs.sort(key=lambda x: x[0])
            sorted_dates, sorted_counts = zip(*date_count_pairs)
            sorted_dates = list(sorted_dates)
            sorted_counts = list(sorted_counts)

            # Create line plot with numerical x-axis for better control
            import numpy as np

            x_positions = np.arange(len(sorted_dates))
            _ = ax.plot(  # pyright: ignore[reportUnknownMemberType] # matplotlib method
                x_positions,
                sorted_counts,
                marker="o",
                linewidth=3,
                markersize=8,
                color=self.get_tv_color(),  # Use TV color as default
                markerfacecolor=self.get_tv_color(),
                markeredgecolor="white",
                markeredgewidth=1.5,
                alpha=0.8,
            )

            # Customize the plot
            _ = ax.set_title(self.get_title(), fontsize=18, fontweight="bold", pad=20)  # pyright: ignore[reportUnknownMemberType]
            _ = ax.set_xlabel("Date", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType]
            _ = ax.set_ylabel("Play Count", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType]

            # Setup aligned date axis
            num_dates = len(sorted_dates)
            self._setup_aligned_date_axis(ax, sorted_dates, num_dates)

            # Add bar value annotations if enabled
            self.annotation_helper.annotate_bar_patches(
                ax,
                "ANNOTATE_DAILY_PLAY_COUNT",
                offset_y=2,
            )

            # Add peak annotations if enabled (separate feature)
            if self.is_peak_annotations_enabled():
                # Find peak for annotation
                max_count = cast(int, max(sorted_counts))
                max_idx = sorted_counts.index(max_count)
                self.annotation_helper.annotate_peak_value(
                    ax,
                    x=float(max_idx),
                    y=float(max_count),
                    value=max_count,
                    label_prefix="Peak",
                )

            logger.info(
                f"Created combined daily play count graph with {num_dates} data points"
            )

        else:
            self._handle_empty_data_case(ax)

    def _handle_empty_data_case(self, ax: Axes) -> None:
        """
        Handle the case where no data is available.

        Args:
            ax: The matplotlib axes to display the message on
        """
        empty_data_handler = EmptyDataHandler()
        empty_data_handler.display_empty_data_message(
            ax,
            message="No play data available\nfor the selected time period",
            set_title=self.get_title(),
            log_message="Generated empty daily play count graph due to no data",
        )

    def _add_peak_annotations(
        self,
        ax: Axes,
        separated_data: dict[str, dict[str, int]],
        sorted_dates: list[str],
    ) -> None:
        """
        Add peak annotations for separated data.

        Args:
            ax: The matplotlib axes to add annotations to
            separated_data: Dictionary of separated media type data
            sorted_dates: List of sorted date strings
        """
        display_info = get_media_type_display_info()

        for media_type, media_data in separated_data.items():
            if not media_data:
                continue

            counts: list[int] = [media_data.get(date, 0) for date in sorted_dates]
            if all(count == 0 for count in counts):
                continue

            max_count: int = max(counts)
            if max_count > 0:
                max_idx = counts.index(max_count)

                # Get label for this media type
                label = display_info.get(media_type, {}).get(
                    "display_name", media_type.title()
                )

                self.annotation_helper.annotate_peak_value(
                    ax,
                    x=float(max_idx),
                    y=float(max_count),
                    value=max_count,
                    label_prefix=f"{label} Peak",
                )
