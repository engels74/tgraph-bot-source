"""
Top 10 users graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot the top 10 users.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, override

import pandas as pd
import seaborn as sns

from ...core.base_graph import BaseGraph
from ...data.data_processor import data_processor
from ...utils.utils import (
    aggregate_top_users,
    handle_empty_data,
)
from ...visualization.visualization_mixin import VisualizationMixin

if TYPE_CHECKING:
    from .....config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class Top10UsersGraph(BaseGraph, VisualizationMixin):
    """Graph showing the top 10 users by play count."""

    def __init__(
        self,
        config: "TGraphBotConfig | dict[str, object] | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None,
    ) -> None:
        """
        Initialize the top 10 users graph.

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
        return self.get_enhanced_title_with_timeframe("Top 10 Users")

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """
        Generate the top 10 users graph using the provided data.

        Args:
            data: Dictionary containing play history data from Tautulli API
                 Expected structure: {'data': [list of play records]}

        Returns:
            Path to the generated graph image file

        Raises:
            ValueError: If data is invalid or missing required fields
        """
        logger.info("Generating top 10 users graph")

        try:
            # Step 1: Extract and process play history data using DataProcessor
            _, processed_records = data_processor.extract_and_process_play_history(data)

            # Step 2: Aggregate top users data
            censor_usernames = self.should_censor_usernames()

            if processed_records:
                top_users = aggregate_top_users(
                    processed_records, limit=10, censor=censor_usernames
                )
                logger.info(f"Aggregated top {len(top_users)} users")
            else:
                logger.warning("No valid records found, using empty data")
                top_users_data = handle_empty_data("users")
                if isinstance(top_users_data, list):
                    top_users = top_users_data
                else:
                    top_users = []

            # Step 3: Setup figure with styling using combined utility
            _, ax = self.setup_figure_with_styling()

            # Step 4: Configure grid styling
            self.configure_seaborn_style_with_grid()

            # Step 5: Create visualization
            if top_users:
                # Convert to pandas DataFrame for easier plotting
                df = pd.DataFrame(top_users)

                # Create horizontal bar plot
                _ = sns.barplot(  # pyright: ignore[reportUnknownMemberType] # seaborn method overloads
                    data=df,
                    x="play_count",
                    y="username",
                    hue="username",
                    ax=ax,
                    orient="h",
                    palette="viridis",
                    legend=False,
                )

                # Customize the plot
                self.setup_standard_title_and_axes(
                    title=self.get_title(),
                    xlabel="Play Count",
                    ylabel="Username",
                    title_fontsize=18,
                    label_fontsize=12,
                )

                # Add value labels on bars if enabled
                annotate_enabled = self.get_config_value("ANNOTATE_TOP_10_USERS", False)
                if annotate_enabled:
                    # Get play counts with proper type handling
                    play_counts: list[int | float] = []
                    for user in top_users:
                        count = user.get("play_count", 0)
                        if isinstance(count, (int, float)):
                            play_counts.append(count)
                    max_count = max(play_counts) if play_counts else 1

                    for i, user in enumerate(top_users):
                        count = user.get("play_count", 0)
                        if isinstance(count, (int, float)):
                            play_count = float(count)
                            self.add_bar_value_annotation(
                                ax,
                                x=play_count,
                                y=i,
                                value=int(play_count),
                                ha="left",
                                va="center",
                                offset_x=max_count * 0.01,
                            )

                logger.info(f"Created top 10 users graph with {len(top_users)} users")

            else:
                # Handle empty data case using mixin utility
                self.display_no_data_message(
                    message="No user data available\nfor the selected time period"
                )
                # Set title for empty data case
                self.setup_standard_title_and_axes(title=self.get_title())
                logger.warning("Generated empty top 10 users graph due to no data")

            # Step 6: Finalize and save using combined utility
            output_path = self.finalize_and_save_figure(
                graph_type="top_10_users", user_id=None
            )
            return output_path

        except Exception as e:
            logger.exception(f"Error generating top 10 users graph: {e}")
            raise
        finally:
            self.cleanup()
