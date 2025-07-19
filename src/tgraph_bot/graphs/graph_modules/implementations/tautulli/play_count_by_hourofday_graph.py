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

            # Step 4: Generate visualization
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
            # Convert to pandas DataFrame for easier plotting
            hours = list(range(24))
            counts = [hourly_counts.get(hour, 0) for hour in hours]

            df = pd.DataFrame({"hour": hours, "play_count": counts})

            # Create bar plot
            _ = sns.barplot(  # pyright: ignore[reportUnknownMemberType] # seaborn method overloads
                data=df,
                x="hour",
                y="play_count",
                hue="hour",
                ax=ax,
                palette="viridis",
                legend=False,
            )

            # Customize the plot
            _ = ax.set_title(  # pyright: ignore[reportUnknownMemberType]
                self.get_title(), fontsize=18, fontweight="bold", pad=20
            )
            _ = ax.set_xlabel("Hour of Day", fontsize=12)  # pyright: ignore[reportUnknownMemberType]
            _ = ax.set_ylabel("Play Count", fontsize=12)  # pyright: ignore[reportUnknownMemberType]

            # Set x-axis ticks to show all hours
            _ = ax.set_xticks(range(0, 24, 2))  # pyright: ignore[reportAny] # matplotlib method returns Any
            _ = ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 2)])  # pyright: ignore[reportAny] # matplotlib method returns Any

            # Add bar value annotations if enabled
            self.annotation_helper.annotate_bar_patches(
                ax,
                "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY",
                offset_y=1,
                fontweight="bold",
            )

            logger.info("Created hour of day graph with data for 24 hours")

        else:
            self._handle_empty_data_case(ax)

    def _handle_empty_data_case(self, ax: Axes) -> None:
        """
        Handle the case where no data is available.

        Args:
            ax: The matplotlib axes to display the message on
        """
        self.handle_empty_data_with_message(
            ax, "No play data available\nfor the selected time period"
        )
        logger.warning("Generated empty hour of day graph due to no data")
