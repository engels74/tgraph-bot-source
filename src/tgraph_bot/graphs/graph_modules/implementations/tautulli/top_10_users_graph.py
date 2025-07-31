"""
Top 10 users graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot the top 10 users.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, override

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes

from ...utils.annotation_helper import AnnotationHelper
from ...core.base_graph import BaseGraph
from ...data.data_processor import data_processor
from ...utils.utils import (
    ProcessedRecords,
    aggregate_top_users,
    aggregate_top_users_separated,
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
        self.annotation_helper: AnnotationHelper = AnnotationHelper(self)

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

            # Step 2: Setup figure with styling using combined utility
            _, ax = self.setup_figure_with_styling()

            # Step 3: Configure grid styling
            self.configure_seaborn_style_with_grid()

            # Step 4: Generate visualization based on configuration
            if self.get_media_type_separation_enabled():
                if self.get_stacked_bar_charts_enabled():
                    self._generate_stacked_visualization(ax, processed_records)
                else:
                    self._generate_separated_visualization(ax, processed_records)
            else:
                self._generate_combined_visualization(ax, processed_records)

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

    def _generate_combined_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate combined visualization showing all users without media type separation.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        import pandas as pd
        import seaborn as sns

        # Aggregate top users data
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

        if top_users:
            # Convert to pandas DataFrame for easier plotting
            df = pd.DataFrame(top_users)

            # Get user-configured palette or default color
            user_palette, fallback_color = self.get_palette_or_default_color()

            if user_palette:
                # Use the configured palette with hue to apply different colors to each bar
                _ = sns.barplot(  # pyright: ignore[reportUnknownMemberType] # seaborn method overloads
                    data=df,
                    x="play_count",
                    y="username",
                    hue="username",
                    palette=user_palette,
                    legend=False,
                    ax=ax,
                    orient="h",
                )
            else:
                # Use default single color when no palette is configured
                _ = sns.barplot(  # pyright: ignore[reportUnknownMemberType] # seaborn method overloads
                    data=df,
                    x="play_count",
                    y="username",
                    color=fallback_color,
                    ax=ax,
                    orient="h",
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
            self.annotation_helper.annotate_horizontal_bar_patches(
                ax=ax,
                config_key="ANNOTATE_TOP_10_USERS",
                offset_x_ratio=0.01,
                ha="left",
                va="center",
                fontweight="normal",
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

    def _generate_separated_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate separated visualization showing Movies and TV Series users separately.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Aggregate data by media type with user separation
        censor_usernames = self.should_censor_usernames()
        separated_data = aggregate_top_users_separated(
            processed_records, limit=10, censor=censor_usernames
        )

        if not separated_data:
            self.handle_empty_data_with_message(
                ax, "No user data available for the selected time range."
            )
            return

        # Prepare data for plotting - combine all users from all media types
        all_users: list[dict[str, str | int]] = []
        media_type_mapping: dict[str, str] = {}  # username -> media_type for coloring

        for media_type, users_list in separated_data.items():
            if not users_list:
                continue

            for user_data in users_list:
                username = user_data["username"]
                play_count = user_data["play_count"]

                # Create combined entry
                combined_entry = {
                    "username": username,
                    "play_count": play_count,
                    "media_type": media_type,
                }
                all_users.append(combined_entry)
                media_type_mapping[str(username)] = str(media_type)

        if not all_users:
            self.handle_empty_data_with_message(
                ax, "No user data available for the selected time range."
            )
            return

        # Sort by play count and take top 10 overall
        all_users.sort(key=lambda x: int(x["play_count"]), reverse=True)
        top_users = all_users[:10]

        # Create DataFrame for plotting
        df = pd.DataFrame(top_users)

        # Create color mapping based on media types
        colors: list[str] = []
        for _, row in df.iterrows():
            media_type = str(row["media_type"])  # pyright: ignore[reportAny] # pandas row access
            _, color = self.get_media_type_display_info(media_type)
            colors.append(color)

        # Add color column to DataFrame for hue mapping
        df["color"] = colors

        # Get unique colors to avoid palette size warnings
        unique_colors = list(
            dict.fromkeys(colors)
        )  # Preserves order while removing duplicates

        # Create horizontal bar plot
        _ = sns.barplot(  # pyright: ignore[reportUnknownMemberType]
            data=df,
            x="play_count",
            y="username",
            hue="color",
            palette=unique_colors,
            ax=ax,
            orient="h",
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

        # Create legend for media types
        media_types_present = list(set(str(user["media_type"]) for user in top_users))
        if len(media_types_present) > 1:
            self.create_separated_legend(ax, media_types_present)

        # Add value labels on bars if enabled
        self.annotation_helper.annotate_horizontal_bar_patches(
            ax=ax,
            config_key="ANNOTATE_TOP_10_USERS",
            offset_x_ratio=0.01,
            ha="left",
            va="center",
            fontweight="normal",
        )

        logger.info(
            f"Created separated top 10 users graph with {len(top_users)} users across {len(media_types_present)} media types"
        )

    def _generate_stacked_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate stacked visualization showing Movies and TV Series users in stacked bars.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Aggregate data by media type with user separation
        censor_usernames = self.should_censor_usernames()
        separated_data = aggregate_top_users_separated(
            processed_records, limit=10, censor=censor_usernames
        )

        if not separated_data:
            self.handle_empty_data_with_message(
                ax, "No user data available for the selected time range."
            )
            return

        # Get all unique users across all media types
        all_usernames: set[str] = set()
        for users_list in separated_data.values():
            for user_data in users_list:
                all_usernames.add(str(user_data["username"]))

        if not all_usernames:
            self.handle_empty_data_with_message(
                ax, "No user data available for the selected time range."
            )
            return

        # Create user play count matrix for stacking
        user_data_matrix: dict[str, dict[str, int]] = {}
        for username in all_usernames:
            user_data_matrix[username] = {}
            total_plays = 0

            # Get play counts for each media type
            for media_type, users_list in separated_data.items():
                user_plays = 0
                for user_data in users_list:
                    if str(user_data["username"]) == username:
                        user_plays = int(user_data["play_count"])
                        break
                user_data_matrix[username][media_type] = user_plays
                total_plays += user_plays

            user_data_matrix[username]["total"] = total_plays

        # Sort users by total play count and take top 10
        sorted_users = sorted(
            user_data_matrix.items(), key=lambda x: x[1]["total"], reverse=True
        )[:10]

        if not sorted_users:
            self.handle_empty_data_with_message(
                ax, "No user data available for the selected time range."
            )
            return

        # Prepare data for stacked horizontal bars
        usernames = [user[0] for user in sorted_users]
        media_types = [
            mt
            for mt in separated_data.keys()
            if any(user[1][mt] > 0 for user in sorted_users)
        ]

        if not media_types:
            self.handle_empty_data_with_message(
                ax, "No user data available for the selected time range."
            )
            return

        # Create stacked horizontal bars
        y_positions = np.arange(len(usernames))
        left_positions = np.zeros(len(usernames))

        for media_type in media_types:
            counts = [sorted_users[i][1][media_type] for i in range(len(usernames))]

            # Only create bars for media types with data
            if any(count > 0 for count in counts):
                label, color = self.get_media_type_display_info(media_type)

                _ = ax.barh(  # pyright: ignore[reportUnknownMemberType]
                    y_positions,
                    counts,
                    left=left_positions,
                    label=label,
                    color=color,
                    alpha=0.8,
                )

                left_positions += np.array(counts)

        # Customize the plot
        self.setup_standard_title_and_axes(
            title=self.get_title(),
            xlabel="Play Count",
            ylabel="Username",
            title_fontsize=18,
            label_fontsize=12,
        )

        # Set y-axis ticks to show usernames
        ax.set_yticks(y_positions)  # pyright: ignore[reportAny] # matplotlib stubs incomplete
        ax.set_yticklabels(usernames)  # pyright: ignore[reportAny] # matplotlib stubs incomplete

        # Add legend
        if len(media_types) > 1:
            _ = ax.legend(  # pyright: ignore[reportUnknownMemberType]
                loc="best",
                frameon=True,
                fancybox=True,
                shadow=True,
                framealpha=0.9,
                fontsize=12,
            )

        # Add value annotations if enabled (for total values)
        if self.get_config_value("ANNOTATE_TOP_10_USERS", False):
            for i, (username, data) in enumerate(sorted_users):
                total = data["total"]
                if total > 0:
                    _ = ax.annotate(  # pyright: ignore[reportUnknownMemberType]
                        str(total),
                        (total, i),
                        ha="left",
                        va="center",
                        fontweight="normal",
                        xytext=(3, 0),
                        textcoords="offset points",
                    )

        logger.info(
            f"Created stacked top 10 users graph with {len(usernames)} users across {len(media_types)} media types"
        )
