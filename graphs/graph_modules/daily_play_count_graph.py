"""
Daily play count graph for TGraph Bot.

This module inherits from BaseGraph and uses the Seaborn library
to implement the logic to plot daily play counts. This approach
simplifies the plotting code and produces a more aesthetically pleasing result.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, override

import pandas as pd
import seaborn as sns

from .base_graph import BaseGraph
from .utils import (
    validate_graph_data,
    process_play_history_data,
    aggregate_by_date,
    handle_empty_data,
)

if TYPE_CHECKING:
    from config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class DailyPlayCountGraph(BaseGraph):
    """Graph showing daily play counts over time."""

    def __init__(
        self,
        config: "TGraphBotConfig | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None
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
            background_color=background_color
        )

    @override
    def get_title(self) -> str:
        """
        Get the title for this graph type.

        Returns:
            The graph title
        """
        return "Daily Play Count"

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
            # Step 1: Validate input data
            is_valid, error_msg = validate_graph_data(data, ['data'])
            if not is_valid:
                raise ValueError(f"Invalid data for daily play count graph: {error_msg}")

            # Step 2: Process raw play history data
            try:
                processed_records = process_play_history_data(data)
                logger.info(f"Processed {len(processed_records)} play history records")
            except Exception as e:
                logger.error(f"Error processing play history data: {e}")
                # Use empty data structure for graceful degradation
                processed_records = []

            # Step 3: Aggregate data by date
            if processed_records:
                daily_counts = aggregate_by_date(processed_records)
                logger.info(f"Aggregated data for {len(daily_counts)} days")
            else:
                logger.warning("No valid records found, using empty data")
                daily_counts = handle_empty_data('daily')
                if not isinstance(daily_counts, dict):
                    daily_counts = {}

            # Step 4: Setup figure and axes
            _, ax = self.setup_figure()

            # Step 5: Configure Seaborn styling
            if self.config and self.config.ENABLE_GRAPH_GRID:
                sns.set_style("whitegrid")
            else:
                sns.set_style("white")

            # Step 6: Create visualization
            if daily_counts:
                # Convert to pandas DataFrame for easier plotting
                dates = list(daily_counts.keys())
                counts = list(daily_counts.values())

                # Create DataFrame
                df = pd.DataFrame({
                    'date': pd.to_datetime(dates),  # pyright: ignore[reportUnknownMemberType]
                    'play_count': counts
                })
                df = df.sort_values('date')  # pyright: ignore[reportUnknownMemberType]

                # Create line plot with markers
                _ = sns.lineplot(
                    data=df,
                    x='date',
                    y='play_count',
                    ax=ax,
                    marker='o',
                    linewidth=2,
                    markersize=6
                )

                # Customize the plot
                _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold', pad=20)  # pyright: ignore[reportUnknownMemberType]
                _ = ax.set_xlabel('Date', fontsize=12)  # pyright: ignore[reportUnknownMemberType]
                _ = ax.set_ylabel('Play Count', fontsize=12)  # pyright: ignore[reportUnknownMemberType]

                # Rotate x-axis labels for better readability
                _ = ax.tick_params(axis='x', rotation=45)  # pyright: ignore[reportUnknownMemberType]

                # Add annotations if enabled
                if self.config and self.config.ANNOTATE_DAILY_PLAY_COUNT:
                    # Convert counts to integers for proper comparison
                    int_counts = [int(c) if isinstance(c, (int, float)) else 0 for c in counts]
                    max_count = max(int_counts)
                    max_date_idx = int_counts.index(max_count)
                    max_date = dates[max_date_idx]

                    # Convert date to timestamp for annotation
                    max_date_ts = pd.to_datetime(max_date)  # pyright: ignore[reportUnknownMemberType]
                    if hasattr(max_date_ts, 'timestamp'):
                        x_coord = float(max_date_ts.timestamp())
                    else:
                        x_coord = float(max_date_idx)

                    _ = ax.annotate(  # pyright: ignore[reportUnknownMemberType]
                        f'Peak: {max_count}',
                        xy=(x_coord, float(max_count)),
                        xytext=(10, 10),
                        textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor=self.config.ANNOTATION_COLOR, alpha=0.7),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
                    )

                logger.info(f"Created daily play count graph with {len(dates)} data points")

            else:
                # Handle empty data case
                _ = ax.text(0.5, 0.5, "No play data available\nfor the selected time period",  # pyright: ignore[reportUnknownMemberType]
                           ha='center', va='center', transform=ax.transAxes, fontsize=16)
                _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]
                logger.warning("Generated empty daily play count graph due to no data")

            # Step 7: Improve layout and save
            if self.figure is not None:
                self.figure.tight_layout()

            # Save the figure using base class utility method
            output_path = self.save_figure(
                graph_type="daily_play_count",
                user_id=None
            )

            logger.info(f"Daily play count graph saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.exception(f"Error generating daily play count graph: {e}")
            raise
        finally:
            self.cleanup()
