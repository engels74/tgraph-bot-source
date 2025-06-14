"""
Play count by month graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot play counts
by month.
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
    aggregate_by_month,
    handle_empty_data,
)

if TYPE_CHECKING:
    from config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class PlayCountByMonthGraph(BaseGraph):
    """Graph showing play counts by month."""

    def __init__(
        self,
        config: "TGraphBotConfig | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None
    ) -> None:
        """
        Initialize the play count by month graph.

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
        return "Play Count by Month"

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """
        Generate the play count by month graph using the provided data.
        
        Args:
            data: Dictionary containing play count data by month
            
        Returns:
            Path to the generated graph image file
        """
        logger.info("Generating play count by month graph")
        
        try:
            # Step 1: Validate input data
            is_valid, error_msg = validate_graph_data(data, ['response'])
            if not is_valid:
                raise ValueError(f"Invalid graph data: {error_msg}")

            # Step 2: Process play history data
            processed_records = process_play_history_data(data)
            logger.info(f"Processed {len(processed_records)} play history records")

            # Step 3: Aggregate data by month
            if processed_records:
                month_counts = aggregate_by_month(processed_records)
                logger.info(f"Aggregated data for {len(month_counts)} months")
            else:
                logger.warning("No valid records found, using empty data")
                month_data = handle_empty_data('month')
                if isinstance(month_data, dict):
                    month_counts = month_data
                else:
                    month_counts = {}

            # Step 4: Setup figure and axes
            _, ax = self.setup_figure()

            # Step 5: Configure Seaborn styling
            if self.config and self.config.ENABLE_GRAPH_GRID:
                sns.set_style("whitegrid")
            else:
                sns.set_style("white")

            # Step 6: Prepare data for Seaborn
            if month_counts:
                # Sort months chronologically
                sorted_months = sorted(month_counts.items())
                plot_data: list[dict[str, object]] = []
                for month, count in sorted_months:
                    plot_data.append({'month': month, 'play_count': count})

                # Convert to DataFrame for Seaborn
                df = pd.DataFrame(plot_data)

                # Step 7: Create the line plot using Seaborn (better for time series)
                color = self.config.TV_COLOR if self.config else "#1f77b4"
                _ = sns.lineplot(
                    data=df,
                    x="month",
                    y="play_count",
                    ax=ax,
                    color=color,
                    marker='o',
                    linewidth=2.5,
                    markersize=8
                )

                # Step 8: Customize the plot
                _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold', pad=20)  # pyright: ignore[reportUnknownMemberType]
                _ = ax.set_xlabel("Month", fontsize=14, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]
                _ = ax.set_ylabel("Play Count", fontsize=14, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]

                # Rotate x-axis labels for better readability
                ax.tick_params(axis='x', rotation=45, labelsize=12)  # pyright: ignore[reportUnknownMemberType]
                ax.tick_params(axis='y', labelsize=12)  # pyright: ignore[reportUnknownMemberType]

                # Add value annotations if enabled
                if self.config and getattr(self.config, 'ENABLE_ANNOTATION_OUTLINE', False):
                    numeric_values = list(month_counts.values())
                    max_count = max(numeric_values) if numeric_values else 1
                    for i, (month, count) in enumerate(sorted_months):
                        if count > 0:
                            _ = ax.text(  # pyright: ignore[reportUnknownMemberType]
                                i, count + max_count * 0.01,
                                f'{int(count)}',
                                ha='center', va='bottom', fontsize=10, fontweight='bold'
                            )
            else:
                # Handle empty data case
                _ = ax.text(0.5, 0.5, "No data available for monthly play counts",  # pyright: ignore[reportUnknownMemberType]
                           ha='center', va='center', transform=ax.transAxes, fontsize=16)
                _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]

            # Adjust layout to prevent label cutoff
            if self.figure is not None:
                self.figure.tight_layout()

            # Save the figure
            output_path = "graphs/play_count_by_month.png"
            return self.save_figure(output_path)
            
        except Exception as e:
            logger.exception(f"Error generating play count by month graph: {e}")
            raise
        finally:
            self.cleanup()
