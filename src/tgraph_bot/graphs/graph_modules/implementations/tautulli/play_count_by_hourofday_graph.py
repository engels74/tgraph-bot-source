"""
Play count by hour of day graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot play counts
by hour of the day, resulting in a cleaner implementation and superior visual output.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, override

import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes

from ...utils.annotation_helper import AnnotationHelper
from ...core.base_graph import BaseGraph
from ...data.data_processor import data_processor
from ...utils.utils import (
    ProcessedRecords,
    aggregate_by_hour_of_day,
)
from ...visualization.visualization_mixin import VisualizationMixin

if TYPE_CHECKING:
    from .....config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class PlayCountByHourOfDayGraph(BaseGraph, VisualizationMixin):
    """Graph showing play counts by hour of the day."""

    def __init__(
        self,
        config: "TGraphBotConfig | dict[str, object] | None" = None,
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

            # Step 4: Apply configured palette if set
            self.apply_configured_palette("PLAY_COUNT_BY_HOUROFDAY_PALETTE")

            # Step 5: Generate visualization
            self._generate_hourly_visualization(ax, processed_records)

            # Step 6: Finalize and save using combined utility
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

            # Use seaborn barplot with palette support or consistent color scheme
            # Using single color avoids categorical units warnings that occur with hue="hour"
            tv_color = self.get_tv_color()  # Get consistent color from theme
            
            # Only add color parameter when no palette is configured
            # This allows the configured palette to be used via sns.set_palette()
            palette_config = getattr(self.config, "PLAY_COUNT_BY_HOUROFDAY_PALETTE", "")
            if not palette_config:
                _ = sns.barplot(  # pyright: ignore[reportUnknownMemberType] # seaborn method overloads
                    data=df,
                    x="hour", 
                    y="count",
                    color=tv_color,
                    ax=ax
                )
            else:
                _ = sns.barplot(  # pyright: ignore[reportUnknownMemberType] # seaborn method overloads
                    data=df,
                    x="hour", 
                    y="count",
                    ax=ax
                )

            # Customize the plot
            self.setup_title_and_axes_with_ax(
                ax, xlabel="Hour of Day", ylabel="Play Count", label_fontsize=12
            )

            # Let seaborn handle x-axis ticks automatically to avoid categorical warnings

            # Add bar value annotations if enabled
            self.annotation_helper.annotate_bar_patches(
                ax,
                "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY",
                offset_y=1,
                fontweight="bold",
            )

            logger.info("Created hour of day graph with data for 24 hours")

        else:
            self.handle_empty_data_with_message(
                ax, "No data available for the selected time range."
            )
            logger.warning("Generated empty hour of day graph due to no data")
