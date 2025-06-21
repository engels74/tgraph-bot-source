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
    handle_empty_data,
)

if TYPE_CHECKING:
    from config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class PlayCountByMonthGraph(BaseGraph):
    """Graph showing play counts by month."""

    def __init__(
        self,
        config: "TGraphBotConfig | dict[str, object] | None" = None,
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

    def _process_monthly_tautulli_data(self, monthly_data: Mapping[str, object]) -> dict[str, int]:
        """
        Process monthly play data from Tautulli's get_plays_per_month API endpoint.
        
        Args:
            monthly_data: Raw data from Tautulli's get_plays_per_month endpoint
            
        Returns:
            Dictionary mapping month strings to total play counts
        """
        logger.debug(f"Processing Tautulli monthly data: {monthly_data}")
        
        month_counts: dict[str, int] = {}
        
        # The Tautulli API returns categories (months) and series (media types with data arrays)
        categories = monthly_data.get('categories', [])
        series = monthly_data.get('series', [])
        
        if not isinstance(categories, list) or not isinstance(series, list):
            logger.warning("Invalid monthly data structure from Tautulli API")
            return month_counts
            
        # Initialize months with zero counts
        for month in categories:  # pyright: ignore[reportUnknownVariableType]
            if isinstance(month, str):
                month_counts[month] = 0
        
        # Sum up plays across all media types for each month
        for media_series in series:  # pyright: ignore[reportUnknownVariableType]
            if isinstance(media_series, dict):
                data_array = media_series.get('data', [])  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                if isinstance(data_array, list):
                    for i, count in enumerate(data_array):  # pyright: ignore[reportUnknownVariableType]
                        if i < len(categories) and isinstance(count, (int, float)):
                            month_key = categories[i]  # pyright: ignore[reportUnknownVariableType]
                            if isinstance(month_key, str):
                                month_counts[month_key] = month_counts.get(month_key, 0) + int(count)
        
        logger.debug(f"Processed {len(month_counts)} months with data: {month_counts}")
        return month_counts

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
            is_valid, error_msg = validate_graph_data(data, ['monthly_plays'])
            if not is_valid:
                raise ValueError(f"Invalid graph data: {error_msg}")

            # Step 2: Process monthly play data from Tautulli API
            monthly_data_raw = data.get('monthly_plays', {})
            logger.info(f"Processing monthly play data: {monthly_data_raw}")

            # Step 3: Process the monthly data structure from Tautulli
            if isinstance(monthly_data_raw, dict):
                month_counts = self._process_monthly_tautulli_data(monthly_data_raw)
            else:
                logger.warning("Monthly data is not a dictionary, using empty data")
                month_counts = {}
            
            if month_counts:
                logger.info(f"Processed data for {len(month_counts)} months")
            else:
                logger.warning("No valid monthly data found, using empty data")
                month_data = handle_empty_data('month')
                if isinstance(month_data, dict):
                    month_counts = month_data
                else:
                    month_counts = {}

            # Step 4: Setup figure and axes
            _, ax = self.setup_figure()

            # Step 5: Configure Seaborn styling
            if self.get_grid_enabled():
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
                color = self.get_tv_color()
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
                annotate_enabled = self.get_config_value('ANNOTATE_PLAY_COUNT_BY_MONTH', False)
                if annotate_enabled:
                    numeric_values = list(month_counts.values())
                    max_count = max(numeric_values) if numeric_values else 1
                    for i, (month, count) in enumerate(sorted_months):
                        if count > 0:
                            self.add_bar_value_annotation(
                                ax,
                                x=i,
                                y=count,
                                value=count,
                                ha='center',
                                va='bottom',
                                offset_y=max_count * 0.01,
                                fontweight='bold'
                            )
            else:
                # Handle empty data case
                _ = ax.text(0.5, 0.5, "No data available for monthly play counts",  # pyright: ignore[reportUnknownMemberType]
                           ha='center', va='center', transform=ax.transAxes, fontsize=16)
                _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]

            # Adjust layout to prevent label cutoff
            if self.figure is not None:
                self.figure.tight_layout()

            # Save the figure using base class utility method
            output_path = self.save_figure(
                graph_type="play_count_by_month",
                user_id=None
            )

            logger.info(f"Play count by month graph saved to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.exception(f"Error generating play count by month graph: {e}")
            raise
        finally:
            self.cleanup()
