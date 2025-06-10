"""
Play count by day of week graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot play counts
by day of the week, resulting in a cleaner implementation and superior visual output.
"""

import logging
from typing import TYPE_CHECKING, override

from .base_graph import BaseGraph

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
    def generate(self, data: dict[str, object]) -> str:
        """
        Generate the play count by day of week graph using the provided data.
        
        Args:
            data: Dictionary containing play count data by day of week
            
        Returns:
            Path to the generated graph image file
        """
        logger.info("Generating play count by day of week graph")
        
        try:
            # Setup figure and axes
            _, ax = self.setup_figure()

            # TODO: Implement actual graph generation using Seaborn
            # This will process the data and create a bar plot showing
            # play counts for each day of the week (Monday through Sunday)

            # Placeholder implementation
            _ = ax.text(0.5, 0.5, "Play Count by Day of Week Graph\n(Not yet implemented)",
                       ha='center', va='center', transform=ax.transAxes, fontsize=16)
            _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold')
            
            # TODO: Apply Seaborn styling
            # sns.set_style("whitegrid")
            # sns.barplot(data=processed_data, x="day_of_week", y="play_count", ax=ax)
            
            # Save the figure
            output_path = "graphs/play_count_by_dayofweek.png"
            return self.save_figure(output_path)
            
        except Exception as e:
            logger.exception(f"Error generating play count by day of week graph: {e}")
            raise
        finally:
            self.cleanup()
