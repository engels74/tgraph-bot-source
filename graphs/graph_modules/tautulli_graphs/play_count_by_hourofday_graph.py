"""
Play count by hour of day graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot play counts
by hour of the day, resulting in a cleaner implementation and superior visual output.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, override, cast

import pandas as pd
import seaborn as sns

from ..base_graph import BaseGraph
from ..utils import (
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
            # Step 1: Extract play history data from the full data structure
            play_history_data_raw = data.get("play_history", {})
            if not isinstance(play_history_data_raw, dict):
                raise ValueError("Missing or invalid 'play_history' data in input")

            # Cast to the proper type for type checker
            play_history_data = cast(Mapping[str, object], play_history_data_raw)

            # Step 2: Validate the play history data
            is_valid, error_msg = validate_graph_data(play_history_data, ["data"])
            if not is_valid:
                raise ValueError(
                    f"Invalid play history data for hour of day graph: {error_msg}"
                )

            # Step 3: Process raw play history data
            try:
                processed_records = process_play_history_data(play_history_data)
                logger.info(f"Processed {len(processed_records)} play history records")
            except Exception as e:
                logger.error(f"Error processing play history data: {e}")
                processed_records = []

            # Step 4: Aggregate data by hour of day
            if processed_records:
                hourly_counts = aggregate_by_hour_of_day(processed_records)
                logger.info(f"Aggregated data for {len(hourly_counts)} hours")
            else:
                logger.warning("No valid records found, using empty data")
                hourly_data = handle_empty_data("hour_of_day")
                if isinstance(hourly_data, dict):
                    # Convert string keys back to int for consistency
                    hourly_counts = {int(k): v for k, v in hourly_data.items()}
                else:
                    hourly_counts = {hour: 0 for hour in range(24)}

            # Step 5: Setup figure and axes
            _, ax = self.setup_figure()

            # Step 6: Configure Seaborn styling
            if self.get_grid_enabled():
                sns.set_style("whitegrid")
            else:
                sns.set_style("white")

            # Step 7: Create visualization
            if any(count > 0 for count in hourly_counts.values()):
                # Convert to pandas DataFrame for easier plotting
                hours = list(range(24))
                counts = [hourly_counts.get(hour, 0) for hour in hours]

                df = pd.DataFrame({"hour": hours, "play_count": counts})

                # Create bar plot
                _ = sns.barplot(
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
                _ = ax.set_xticks(range(0, 24, 2))  # pyright: ignore[reportUnknownMemberType]
                _ = ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 2)])  # pyright: ignore[reportUnknownMemberType]

                # Add bar value annotations if enabled
                annotate_enabled = self.get_config_value(
                    "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY", False
                )
                if annotate_enabled:
                    # Get all bar patches and annotate them
                    for patch in ax.patches:
                        height = patch.get_height()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType,reportUnknownVariableType]
                        if height and height > 0:  # Only annotate non-zero values
                            x_val = patch.get_x() + patch.get_width() / 2  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType,reportUnknownVariableType]
                            self.add_bar_value_annotation(
                                ax,
                                x=float(x_val),  # pyright: ignore[reportUnknownArgumentType]
                                y=float(height),  # pyright: ignore[reportUnknownArgumentType]
                                value=int(height),  # pyright: ignore[reportUnknownArgumentType]
                                ha="center",
                                va="bottom",
                                offset_y=1,
                                fontweight="bold",
                            )

                logger.info("Created hour of day graph with data for 24 hours")

            else:
                # Handle empty data case
                _ = ax.text(  # pyright: ignore[reportUnknownMemberType]
                    0.5,
                    0.5,
                    "No play data available\nfor the selected time period",
                    ha="center",
                    va="center",
                    transform=ax.transAxes,
                    fontsize=16,
                )
                _ = ax.set_title(self.get_title(), fontsize=18, fontweight="bold")  # pyright: ignore[reportUnknownMemberType]
                logger.warning("Generated empty hour of day graph due to no data")

            # Step 8: Improve layout and save
            if self.figure is not None:
                self.figure.tight_layout()

            # Save the figure using base class utility method
            output_path = self.save_figure(
                graph_type="play_count_by_hourofday", user_id=None
            )

            logger.info(f"Hour of day graph saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.exception(f"Error generating play count by hour of day graph: {e}")
            raise
        finally:
            self.cleanup()
