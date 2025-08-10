"""
Play count by hour of day graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot play counts
by hour of the day, resulting in a cleaner implementation and superior visual output.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, override

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes

from ...utils.annotation_helper import AnnotationHelper
from ...core.base_graph import BaseGraph
from ...data.data_processor import data_processor
from ...utils.utils import (
    ProcessedRecords,
    aggregate_by_hour_of_day,
    aggregate_by_hour_of_day_separated,
)
from ...visualization.visualization_mixin import VisualizationMixin

if TYPE_CHECKING:
    from .....config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class PlayCountByHourOfDayGraph(BaseGraph, VisualizationMixin):
    """Graph showing play counts by hour of the day."""

    def __init__(
        self,
        config: "TGraphBotConfig | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None,
    ) -> None:
        """
        Initialize the play count by hour of day graph.

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
        return self.get_enhanced_title_with_timeframe("Play Count by Hour of Day")

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """
        Generate the play count by hour of day graph using the provided data.

        Args:
            data: Dictionary containing play history data from Tautulli API
                 Expected structure: {'data': [list of play records]}

        Returns:
            Path to the generated graph image file

        Raises:
            ValueError: If data is invalid or missing required fields
        """
        logger.info("Generating play count by hour of day graph")

        try:
            # Step 1: Extract and process play history data using DataProcessor
            _, processed_records = data_processor.extract_and_process_play_history(data)

            # Step 2: Setup figure with styling using combined utility
            _, ax = self.setup_figure_with_styling()

            # Step 3: Configure grid styling
            self.configure_seaborn_style_with_grid()

            # Step 4: Generate visualization based on configuration
            if self.get_media_type_separation_enabled():
                if self.get_stacked_bar_charts_enabled():
                    self._generate_stacked_visualization(ax, processed_records)
                else:
                    self._generate_separated_visualization(ax, processed_records)
            else:
                self._generate_hourly_visualization(ax, processed_records)

            # Step 5: Finalize and save using combined utility
            output_path = self.finalize_and_save_figure(
                graph_type="play_count_by_hourofday", user_id=None
            )
            return output_path

        except Exception as e:
            logger.exception(f"Error generating play count by hour of day graph: {e}")
            raise
        finally:
            self.cleanup()

    def _generate_hourly_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate hourly visualization showing play counts by hour of day.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Aggregate data by hour of day
        if processed_records:
            hourly_counts = aggregate_by_hour_of_day(processed_records)
            logger.info(f"Aggregated data for {len(hourly_counts)} hours")
        else:
            logger.warning("No valid records found, using empty data")
            hourly_counts = {hour: 0 for hour in range(24)}

        # Create visualization
        if any(count > 0 for count in hourly_counts.values()):
            # Create properly typed DataFrame to avoid categorical conversion warning
            hours = list(range(24))
            counts = [hourly_counts.get(hour, 0) for hour in hours]

            # Create DataFrame with explicit numeric types
            df = pd.DataFrame(
                {
                    "hour": hours,  # Keep as int, not string
                    "count": counts,
                }
            )

            # Ensure numeric dtypes to prevent seaborn categorical warning
            df["hour"] = df["hour"].astype(int)
            df["count"] = df["count"].astype(int)

            # Get user-configured palette or default color
            user_palette, fallback_color = self.get_palette_or_default_color()

            if user_palette:
                # Use the configured palette with hue to apply different colors to each bar
                _ = sns.barplot(
                    data=df,
                    x="hour",
                    y="count",
                    hue="hour",
                    palette=user_palette,
                    legend=False,
                    ax=ax,
                )
            else:
                # Use default single color when no palette is configured
                _ = sns.barplot(
                    data=df, x="hour", y="count", color=fallback_color, ax=ax
                )

            # Customize the plot
            self.setup_title_and_axes_with_ax(
                ax, xlabel="Hour of Day", ylabel="Play Count", label_fontsize=12
            )

            # Let seaborn handle x-axis ticks automatically to avoid categorical warnings

            # Add bar value annotations if enabled
            self.annotation_helper.annotate_bar_patches(
                ax,
                "graphs.appearance.annotations.enabled_on.play_count_by_hourofday",
                offset_y=1,
                fontweight="bold",
            )

            # Ensure space for bar annotations with adaptive spacing
            self.annotation_helper.ensure_space_for_vertical_bar_annotations(
                ax=ax,
                offset_ratio=0.05,
                min_padding=0.5,
                max_padding=10.0,
            )

            logger.info("Created hour of day graph with data for 24 hours")

        else:
            self.handle_empty_data_with_message(
                ax, "No data available for the selected time range."
            )
            logger.warning("Generated empty hour of day graph due to no data")

    def _generate_separated_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate separated visualization showing Movies and TV Series separately.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Aggregate data by hour of day with media type separation
        separated_data = aggregate_by_hour_of_day_separated(processed_records)

        if not separated_data:
            self.handle_empty_data_with_message(
                ax, "No data available for the selected time range."
            )
            return

        # Prepare data for plotting
        hours = list(range(24))

        # Plot each media type separately
        media_types_plotted: list[str] = []
        for media_type, media_data in separated_data.items():
            if not media_data:
                continue

            # Prepare data for this media type
            counts = [media_data.get(hour, 0) for hour in hours]

            # Skip if no data for this media type
            if all(count == 0 for count in counts):
                continue

            # Get display information
            label, color = self.get_media_type_display_info(media_type)

            # Create DataFrame for seaborn
            import pandas as pd

            df = pd.DataFrame(
                {
                    "hour": hours,
                    "count": counts,
                }
            )

            # Ensure numeric dtypes to prevent seaborn categorical warning
            df["hour"] = df["hour"].astype(int)
            df["count"] = df["count"].astype(int)

            # Create the bar plot for this media type
            import seaborn as sns

            _ = sns.barplot(
                data=df, x="hour", y="count", color=color, alpha=0.8, ax=ax, label=label
            )

            media_types_plotted.append(media_type)

        if not media_types_plotted:
            self.handle_empty_data_with_message(
                ax, "No data available for the selected time range."
            )
            return

        # Customize the plot
        self.setup_title_and_axes_with_ax(
            ax, xlabel="Hour of Day", ylabel="Play Count", label_fontsize=12
        )

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
        self.annotation_helper.annotate_bar_patches(
            ax,
            "graphs.appearance.annotations.enabled_on.play_count_by_hourofday",
            offset_y=1,
            fontweight="bold",
        )

        # Ensure space for bar annotations with adaptive spacing
        self.annotation_helper.ensure_space_for_vertical_bar_annotations(
            ax=ax,
            offset_ratio=0.05,
            min_padding=0.5,
            max_padding=10.0,
        )

        logger.info(
            f"Created separated hour of day graph with {len(media_types_plotted)} media types"
        )

    def _generate_stacked_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate stacked visualization showing Movies and TV Series in stacked bars.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Aggregate data by hour of day with media type separation
        separated_data = aggregate_by_hour_of_day_separated(processed_records)

        if not separated_data:
            self.handle_empty_data_with_message(
                ax, "No data available for the selected time range."
            )
            return

        # Prepare data for stacked plotting
        hours = list(range(24))
        media_types = list(separated_data.keys())

        if not media_types:
            self.handle_empty_data_with_message(
                ax, "No data available for the selected time range."
            )
            return

        # Create data matrix for stacked bars
        data_matrix: list[list[int]] = []
        labels: list[str] = []
        colors: list[str] = []

        for media_type in media_types:
            media_data = separated_data[media_type]
            counts = [media_data.get(hour, 0) for hour in hours]

            # Only include media types with data
            if any(count > 0 for count in counts):
                data_matrix.append(counts)
                label, color = self.get_media_type_display_info(media_type)
                labels.append(label)
                colors.append(color)

        if not data_matrix:
            self.handle_empty_data_with_message(
                ax, "No data available for the selected time range."
            )
            return

        # Create stacked bar chart
        # Convert hours to numpy array for plotting
        x_positions = np.arange(len(hours))

        # Create stacked bars
        bottom = np.zeros(len(hours), dtype=np.float64)
        for i, (counts, label, color) in enumerate(zip(data_matrix, labels, colors)):
            _ = ax.bar(  # pyright: ignore[reportUnknownMemberType]
                x_positions,
                counts,
                bottom=bottom,
                label=label,
                color=color,
                alpha=0.8,
            )
            bottom += np.array(counts)

        # Customize the plot
        self.setup_title_and_axes_with_ax(
            ax, xlabel="Hour of Day", ylabel="Play Count", label_fontsize=12
        )

        # Set x-axis ticks to show hours
        ax.set_xticks(x_positions)  # pyright: ignore[reportAny] # matplotlib stubs incomplete
        ax.set_xticklabels([str(hour) for hour in hours])  # pyright: ignore[reportAny] # matplotlib stubs incomplete

        # Add legend
        _ = ax.legend(  # pyright: ignore[reportUnknownMemberType]
            loc="best",
            frameon=True,
            fancybox=True,
            shadow=True,
            framealpha=0.9,
            fontsize=12,
        )

        # Add bar value annotations if enabled (for total values)
        # Use AnnotationHelper for consistent styling
        x_data: list[float] = []
        y_data: list[float] = []
        for i, total_value in enumerate(bottom):
            total_int = int(total_value)
            if total_int > 0:
                x_data.append(float(i))
                y_data.append(float(total_value))

        if x_data and y_data:
            self.annotation_helper.annotate_line_points(
                ax=ax,
                config_key="graphs.appearance.annotations.enabled_on.play_count_by_hourofday",
                x_data=x_data,
                y_data=y_data,
                ha="center",
                va="bottom",
                offset_y=1,
                fontweight="bold",
            )

        logger.info(f"Created stacked hour of day graph with {len(labels)} media types")
