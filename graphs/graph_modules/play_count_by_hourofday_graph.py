"""
Play count by hour of day graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot play counts
by hour of the day.
"""

import logging
from typing import TYPE_CHECKING, override

import pandas as pd
import seaborn as sns

from .base_graph import BaseGraph
from .utils import (
    validate_graph_data,
    process_play_history_data,
    aggregate_by_hour_of_day,
    handle_empty_data,
)

if TYPE_CHECKING:
    from config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class PlayCountByHourOfDayGraph(BaseGraph):
    """Graph showing play counts by hour of the day."""

    def __init__(
        self,
        config: "TGraphBotConfig | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None
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
            background_color=background_color
        )

    @override
    def get_title(self) -> str:
        """
        Get the title for this graph type.

        Returns:
            The graph title
        """
        return "Play Count by Hour of Day"

    @override
    def generate(self, data: dict[str, object]) -> str:
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
            # Step 1: Validate input data
            is_valid, error_msg = validate_graph_data(data, ['data'])
            if not is_valid:
                raise ValueError(f"Invalid data for hour of day graph: {error_msg}")

            # Step 2: Process raw play history data
            try:
                processed_records = process_play_history_data(data)
                logger.info(f"Processed {len(processed_records)} play history records")
            except Exception as e:
                logger.error(f"Error processing play history data: {e}")
                processed_records = []

            # Step 3: Aggregate data by hour of day
            if processed_records:
                hourly_counts = aggregate_by_hour_of_day(processed_records)
                logger.info(f"Aggregated data for {len(hourly_counts)} hours")
            else:
                logger.warning("No valid records found, using empty data")
                hourly_data = handle_empty_data('hour_of_day')
                if isinstance(hourly_data, dict):
                    # Convert string keys back to int for consistency
                    hourly_counts = {int(k): v for k, v in hourly_data.items()}
                else:
                    hourly_counts = {hour: 0 for hour in range(24)}

            # Step 4: Setup figure and axes
            _, ax = self.setup_figure()

            # Step 5: Configure Seaborn styling
            if self.config and self.config.ENABLE_GRAPH_GRID:
                sns.set_style("whitegrid")
            else:
                sns.set_style("white")

            # Step 6: Create visualization
            if any(isinstance(count, int) and count > 0 for count in hourly_counts.values()):
                # Convert to pandas DataFrame for easier plotting
                hours = list(range(24))
                counts = [hourly_counts.get(hour, 0) for hour in hours]

                df = pd.DataFrame({
                    'hour': hours,
                    'play_count': counts
                })

                # Create bar plot
                _ = sns.barplot(
                    data=df,
                    x='hour',
                    y='play_count',
                    ax=ax,
                    palette='viridis'
                )

                # Customize the plot
                _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold', pad=20)  # pyright: ignore[reportUnknownMemberType]
                _ = ax.set_xlabel('Hour of Day', fontsize=12)  # pyright: ignore[reportUnknownMemberType]
                _ = ax.set_ylabel('Play Count', fontsize=12)  # pyright: ignore[reportUnknownMemberType]

                # Set x-axis ticks to show all hours
                _ = ax.set_xticks(range(0, 24, 2))  # pyright: ignore[reportUnknownMemberType]
                _ = ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 2)])  # pyright: ignore[reportUnknownMemberType]

                logger.info(f"Created hour of day graph with data for 24 hours")

            else:
                # Handle empty data case
                _ = ax.text(0.5, 0.5, "No play data available\nfor the selected time period",  # pyright: ignore[reportUnknownMemberType]
                           ha='center', va='center', transform=ax.transAxes, fontsize=16)
                _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]
                logger.warning("Generated empty hour of day graph due to no data")

            # Step 7: Improve layout and save
            if self.figure is not None:
                self.figure.tight_layout()

            # Save the figure using base class utility method
            output_path = self.save_figure(
                graph_type="play_count_by_hourofday",
                user_id=None
            )

            logger.info(f"Hour of day graph saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.exception(f"Error generating play count by hour of day graph: {e}")
            raise
        finally:
            self.cleanup()
