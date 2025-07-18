"""
Top 10 platforms graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot the top 10 platforms.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, override

import pandas as pd
import seaborn as sns

from ..base_graph import BaseGraph
from ..data_processor import data_processor
from ..visualization_mixin import VisualizationMixin
from ..utils import (
    aggregate_top_platforms,
    handle_empty_data,
)

if TYPE_CHECKING:
    from ....config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class Top10PlatformsGraph(BaseGraph, VisualizationMixin):
    """Graph showing the top 10 platforms by play count."""

    def __init__(
        self,
        config: "TGraphBotConfig | dict[str, object] | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None,
    ) -> None:
        """
        Initialize the top 10 platforms graph.

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
        return self.get_enhanced_title_with_timeframe("Top 10 Platforms")

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """
        Generate the top 10 platforms graph using the provided data.

        Args:
            data: Dictionary containing platform usage data

        Returns:
            Path to the generated graph image file
        """
        logger.info("Generating top 10 platforms graph")

        try:
            # Step 1: Extract and process play history data using DataProcessor
            _, processed_records = data_processor.extract_and_process_play_history(data)

            # Step 2: Aggregate top platforms data
            if processed_records:
                top_platforms = aggregate_top_platforms(processed_records, limit=10)
                logger.info(f"Found {len(top_platforms)} top platforms")
            else:
                logger.warning("No valid records found, using empty data")
                platform_data = handle_empty_data("platforms")
                if isinstance(platform_data, list):
                    top_platforms = platform_data
                else:
                    top_platforms = []

            # Step 3: Setup figure with styling using combined utility
            _, ax = self.setup_figure_with_styling()

            # Step 4: Configure grid styling
            self.configure_seaborn_style_with_grid()

            # Step 5: Create visualization
            if top_platforms:
                # Convert to DataFrame for Seaborn
                df = pd.DataFrame(top_platforms)

                # Create horizontal bar plot using Seaborn
                color = self.get_tv_color()
                _ = sns.barplot(
                    data=df,
                    x="play_count",
                    y="platform",
                    ax=ax,
                    color=color,
                    alpha=0.8,
                    orient="h",
                )

                # Customize the plot
                self.setup_standard_title_and_axes(
                    title=self.get_title(),
                    xlabel="Play Count",
                    ylabel="Platform",
                    title_fontsize=18,
                    label_fontsize=14,
                )

                # Configure tick parameters
                self.configure_tick_parameters(axis="both", labelsize=12)

                # Add value annotations if enabled
                annotate_enabled = self.get_config_value(
                    "ANNOTATE_TOP_10_PLATFORMS", False
                )
                if annotate_enabled:
                    # Get max play count for positioning annotations
                    play_counts: list[int | float] = []
                    for p in top_platforms:
                        count = p.get("play_count", 0)
                        if isinstance(count, (int, float)):
                            play_counts.append(count)
                    max_play_count = max(play_counts) if play_counts else 1
                    for bar in ax.patches:
                        width = bar.get_width()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType,reportUnknownVariableType]
                        if width and width > 0:  # Only annotate non-zero values
                            y_val = bar.get_y() + bar.get_height() / 2.0  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType,reportUnknownVariableType]
                            self.add_bar_value_annotation(
                                ax,
                                x=float(width),  # pyright: ignore[reportUnknownArgumentType]
                                y=float(y_val),  # pyright: ignore[reportUnknownArgumentType]
                                value=int(width),  # pyright: ignore[reportUnknownArgumentType]
                                ha="left",
                                va="center",
                                offset_x=max_play_count * 0.01,
                                fontweight="bold",
                            )
            else:
                # Handle empty data case using mixin utility
                self.display_no_data_message(
                    message="No platform data available"
                )
                # Set title for empty data case
                self.setup_standard_title_and_axes(title=self.get_title())

            # Step 6: Finalize and save using combined utility
            output_path = self.finalize_and_save_figure(graph_type="top_10_platforms", user_id=None)
            return output_path

        except Exception as e:
            logger.exception(f"Error generating top 10 platforms graph: {e}")
            raise
        finally:
            self.cleanup()
