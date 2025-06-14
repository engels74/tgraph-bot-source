"""
Top 10 users graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot the top 10 users.
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
    aggregate_top_users,
    handle_empty_data,
)

if TYPE_CHECKING:
    from config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class Top10UsersGraph(BaseGraph):
    """Graph showing the top 10 users by play count."""

    def __init__(
        self,
        config: "TGraphBotConfig | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None
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
            background_color=background_color
        )

    @override
    def get_title(self) -> str:
        """
        Get the title for this graph type.

        Returns:
            The graph title
        """
        return "Top 10 Users"

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
            # Step 1: Validate input data
            is_valid, error_msg = validate_graph_data(data, ['data'])
            if not is_valid:
                raise ValueError(f"Invalid data for top 10 users graph: {error_msg}")

            # Step 2: Process raw play history data
            try:
                processed_records = process_play_history_data(data)
                logger.info(f"Processed {len(processed_records)} play history records")
            except Exception as e:
                logger.error(f"Error processing play history data: {e}")
                # Use empty data structure for graceful degradation
                processed_records = []

            # Step 3: Aggregate top users data
            censor_usernames = self.config.CENSOR_USERNAMES if self.config else True

            if processed_records:
                top_users = aggregate_top_users(processed_records, limit=10, censor=censor_usernames)
                logger.info(f"Aggregated top {len(top_users)} users")
            else:
                logger.warning("No valid records found, using empty data")
                top_users_data = handle_empty_data('users')
                if isinstance(top_users_data, list):
                    top_users = top_users_data
                else:
                    top_users = []

            # Step 4: Setup figure and axes
            _, ax = self.setup_figure()

            # Step 5: Configure Seaborn styling
            if self.config and self.config.ENABLE_GRAPH_GRID:
                sns.set_style("whitegrid")
            else:
                sns.set_style("white")

            # Step 6: Create visualization
            if top_users:
                # Convert to pandas DataFrame for easier plotting
                df = pd.DataFrame(top_users)

                # Create horizontal bar plot
                _ = sns.barplot(
                    data=df,
                    x='play_count',
                    y='username',
                    ax=ax,
                    orient='h',
                    palette='viridis'
                )

                # Customize the plot
                _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold', pad=20)  # pyright: ignore[reportUnknownMemberType]
                _ = ax.set_xlabel('Play Count', fontsize=12)  # pyright: ignore[reportUnknownMemberType]
                _ = ax.set_ylabel('Username', fontsize=12)  # pyright: ignore[reportUnknownMemberType]

                # Add value labels on bars if enabled
                if self.config and self.config.ANNOTATE_TOP_10_USERS:
                    max_count = float(max(df['play_count']))  # pyright: ignore[reportUnknownArgumentType]
                    for i, (_, row) in enumerate(df.iterrows()):  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType,reportUnknownArgumentType]
                        play_count = float(row['play_count'])  # pyright: ignore[reportUnknownArgumentType]
                        _ = ax.text(  # pyright: ignore[reportUnknownMemberType]
                            play_count + max_count * 0.01,
                            i,
                            str(int(play_count)),
                            va='center',
                            fontsize=10,
                            color=self.config.ANNOTATION_COLOR
                        )

                logger.info(f"Created top 10 users graph with {len(top_users)} users")

            else:
                # Handle empty data case
                _ = ax.text(0.5, 0.5, "No user data available\nfor the selected time period",  # pyright: ignore[reportUnknownMemberType]
                           ha='center', va='center', transform=ax.transAxes, fontsize=16)
                _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]
                logger.warning("Generated empty top 10 users graph due to no data")

            # Step 7: Improve layout and save
            if self.figure is not None:
                self.figure.tight_layout()

            # Save the figure using base class utility method
            output_path = self.save_figure(
                graph_type="top_10_users",
                user_id=None
            )

            logger.info(f"Top 10 users graph saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.exception(f"Error generating top 10 users graph: {e}")
            raise
        finally:
            self.cleanup()
