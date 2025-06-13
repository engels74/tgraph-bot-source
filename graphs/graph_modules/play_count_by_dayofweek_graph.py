"""
Play count by day of week graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot play counts
by day of the week, resulting in a cleaner implementation and superior visual output.
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
    aggregate_by_day_of_week,
    handle_empty_data,
)

if TYPE_CHECKING:
    from config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class PlayCountByDayOfWeekGraph(BaseGraph):
    """Graph showing play counts by day of the week."""

    def __init__(
        self,
        config: "TGraphBotConfig | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None
    ) -> None:
        """
        Initialize the play count by day of week graph.

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
        return "Play Count by Day of Week"

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """
        Generate the play count by day of week graph using the provided data.
        
        Args:
            data: Dictionary containing play count data by day of week
            
        Returns:
            Path to the generated graph image file
        """
        logger.info("Generating play count by day of week graph")
        
        try:
            # Step 1: Validate input data
            is_valid, error_msg = validate_graph_data(data, ['response'])
            if not is_valid:
                raise ValueError(f"Invalid graph data: {error_msg}")

            # Step 2: Process play history data
            processed_records = process_play_history_data(data)
            logger.info(f"Processed {len(processed_records)} play history records")

            # Step 3: Aggregate data by day of week
            if processed_records:
                day_counts = aggregate_by_day_of_week(processed_records)
                logger.info(f"Aggregated data for {len(day_counts)} days")
            else:
                logger.warning("No valid records found, using empty data")
                day_data = handle_empty_data('day_of_week')
                if isinstance(day_data, dict):
                    day_counts = day_data
                else:
                    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    day_counts = {day: 0 for day in day_names}

            # Step 4: Setup figure and axes
            _, ax = self.setup_figure()

            # Step 5: Configure Seaborn styling
            if self.config and self.config.ENABLE_GRAPH_GRID:
                sns.set_style("whitegrid")
            else:
                sns.set_style("white")

            # Step 6: Prepare data for Seaborn
            # Ensure all days are present in correct order
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            plot_data: list[dict[str, object]] = []
            for day in day_order:
                count = day_counts.get(day, 0)
                plot_data.append({'day_of_week': day, 'play_count': count})

            # Convert to DataFrame for Seaborn
            df = pd.DataFrame(plot_data)

            # Step 7: Create the bar plot using Seaborn
            # Use TV_COLOR as the primary color for general graphs
            color = self.config.TV_COLOR if self.config else "#1f77b4"
            _ = sns.barplot(
                data=df,
                x="day_of_week",
                y="play_count",
                ax=ax,
                color=color,
                alpha=0.8
            )

            # Step 8: Customize the plot
            _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold', pad=20)
            _ = ax.set_xlabel("Day of Week", fontsize=14, fontweight='bold')
            _ = ax.set_ylabel("Play Count", fontsize=14, fontweight='bold')

            # Rotate x-axis labels for better readability
            ax.tick_params(axis='x', rotation=45, labelsize=12)
            ax.tick_params(axis='y', labelsize=12)

            # Add value annotations if enabled (check for annotation settings)
            if self.config and getattr(self.config, 'ENABLE_ANNOTATION_OUTLINE', False):
                # Ensure we have numeric values for max calculation
                numeric_values = [v for v in day_counts.values() if isinstance(v, (int, float))]
                max_count = max(numeric_values) if numeric_values else 1
                for bar in ax.patches:  # pyright: ignore[reportUnknownMemberType]
                    # Use type ignores for matplotlib patch attributes
                    height = bar.get_height()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
                    if height and height > 0:  # Only annotate non-zero values
                        _ = ax.text(  # pyright: ignore[reportUnknownMemberType]
                            bar.get_x() + bar.get_width()/2.,  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
                            height + max_count * 0.01,  # pyright: ignore[reportUnknownArgumentType]
                            f'{int(height)}',  # pyright: ignore[reportUnknownArgumentType]
                            ha='center', va='bottom', fontsize=10, fontweight='bold'
                        )

            # Adjust layout to prevent label cutoff
            if self.figure is not None:
                self.figure.tight_layout()

            # Save the figure
            output_path = "graphs/play_count_by_dayofweek.png"
            return self.save_figure(output_path)
            
        except Exception as e:
            logger.exception(f"Error generating play count by day of week graph: {e}")
            raise
        finally:
            self.cleanup()
