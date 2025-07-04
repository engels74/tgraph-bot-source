"""
Top 10 platforms graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot the top 10 platforms.
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
    aggregate_top_platforms,
    handle_empty_data,
)

if TYPE_CHECKING:
    from config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class Top10PlatformsGraph(BaseGraph):
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
            # Step 1: Extract play history data from the full data structure
            play_history_data_raw = data.get("play_history", {})
            if not isinstance(play_history_data_raw, dict):
                raise ValueError("Missing or invalid 'play_history' data in input")

            # Cast to the proper type for type checker
            play_history_data = cast(Mapping[str, object], play_history_data_raw)

            # Step 2: Validate the play history data
            is_valid, error_msg = validate_graph_data(play_history_data, ["data"])
            if not is_valid:
                raise ValueError(f"Invalid play history data: {error_msg}")

            # Step 3: Process play history data
            processed_records = process_play_history_data(play_history_data)
            logger.info(f"Processed {len(processed_records)} play history records")

            # Step 4: Aggregate top platforms data
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

            # Step 5: Setup figure and axes
            _, ax = self.setup_figure()

            # Step 6: Configure Seaborn styling
            if self.get_grid_enabled():
                sns.set_style("whitegrid")
            else:
                sns.set_style("white")

            # Step 6: Prepare data for Seaborn
            if top_platforms:
                # Convert to DataFrame for Seaborn
                df = pd.DataFrame(top_platforms)

                # Step 7: Create horizontal bar plot using Seaborn
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

                # Step 8: Customize the plot
                _ = ax.set_title(  # pyright: ignore[reportUnknownMemberType]
                    self.get_title(), fontsize=18, fontweight="bold", pad=20
                )
                _ = ax.set_xlabel("Play Count", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType]
                _ = ax.set_ylabel("Platform", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType]

                # Adjust tick parameters
                ax.tick_params(axis="x", labelsize=12)  # pyright: ignore[reportUnknownMemberType]
                ax.tick_params(axis="y", labelsize=12)  # pyright: ignore[reportUnknownMemberType]

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
                # Handle empty data case
                _ = ax.text(  # pyright: ignore[reportUnknownMemberType]
                    0.5,
                    0.5,
                    "No platform data available",
                    ha="center",
                    va="center",
                    transform=ax.transAxes,
                    fontsize=16,
                )
                _ = ax.set_title(self.get_title(), fontsize=18, fontweight="bold")  # pyright: ignore[reportUnknownMemberType]

            # Adjust layout to prevent label cutoff
            if self.figure is not None:
                self.figure.tight_layout()

            # Save the figure using base class utility method
            output_path = self.save_figure(graph_type="top_10_platforms", user_id=None)

            logger.info(f"Top 10 platforms graph saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.exception(f"Error generating top 10 platforms graph: {e}")
            raise
        finally:
            self.cleanup()
