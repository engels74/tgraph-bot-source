"""
Top 10 platforms graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot the top 10 platforms.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, override

import numpy as np
from matplotlib.axes import Axes

from ...utils.annotation_helper import AnnotationHelper
from ...core.base_graph import BaseGraph
from ...data.data_processor import data_processor
from ...utils.utils import (
    ProcessedRecords,
    aggregate_top_platforms,
    aggregate_top_platforms_separated,
    handle_empty_data,
)
from ...visualization.visualization_mixin import VisualizationMixin

if TYPE_CHECKING:
    from .....config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class Top10PlatformsGraph(BaseGraph, VisualizationMixin):
    """Graph showing the top 10 platforms by play count."""

    def __init__(
        self,
        config: "TGraphBotConfig | None" = None,
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
        self.annotation_helper: AnnotationHelper = AnnotationHelper(self)

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
                graph_type="top_10_platforms", user_id=None
            )
            return output_path

        except Exception as e:
            logger.exception(f"Error generating top 10 platforms graph: {e}")
            raise
        finally:
            self.cleanup()

    def _generate_combined_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate combined visualization showing all platforms without media type separation.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        import pandas as pd
        import seaborn as sns

        # Aggregate top platforms data
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

        if top_platforms:
            # Convert to DataFrame for Seaborn
            df = pd.DataFrame(top_platforms)

            # Get user-configured palette or default color
            user_palette, fallback_color = self.get_palette_or_default_color()

            if user_palette:
                # Use palette with hue for multiple colors
                _ = sns.barplot(  # pyright: ignore[reportUnknownMemberType] # seaborn method overloads
                    data=df,
                    x="play_count",
                    y="platform",
                    hue="platform",
                    palette=user_palette,
                    legend=False,
                    ax=ax,
                    alpha=0.8,
                    orient="h",
                )
            else:
                # Use single default color
                _ = sns.barplot(  # pyright: ignore[reportUnknownMemberType] # seaborn method overloads
                    data=df,
                    x="play_count",
                    y="platform",
                    ax=ax,
                    color=fallback_color,
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
            self.annotation_helper.annotate_horizontal_bar_patches(
                ax,
                "ANNOTATE_TOP_10_PLATFORMS",
                offset_x_ratio=0.01,
                ha="left",
                va="center",
                fontweight="bold",
            )
        else:
            # Handle empty data case using mixin utility
            self.display_no_data_message(message="No platform data available")
            # Set title for empty data case
            self.setup_standard_title_and_axes(title=self.get_title())

    def _generate_separated_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate separated visualization showing Movies and TV Series platforms separately.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        import pandas as pd
        import seaborn as sns

        # Aggregate data by media type with platform separation
        separated_data = aggregate_top_platforms_separated(processed_records, limit=10)

        if not separated_data:
            self.handle_empty_data_with_message(
                ax, "No platform data available for the selected time range."
            )
            return

        # Prepare data for plotting - combine all platforms from all media types
        all_platforms: list[dict[str, str | int]] = []

        for media_type, platforms_list in separated_data.items():
            if not platforms_list:
                continue

            for platform_data in platforms_list:
                platform_name = platform_data["platform"]
                play_count = platform_data["play_count"]

                # Create combined entry
                combined_entry = {
                    "platform": platform_name,
                    "play_count": play_count,
                    "media_type": media_type,
                }
                all_platforms.append(combined_entry)

        if not all_platforms:
            self.handle_empty_data_with_message(
                ax, "No platform data available for the selected time range."
            )
            return

        # Sort by play count and take top 10 overall
        all_platforms.sort(key=lambda x: int(x["play_count"]), reverse=True)
        top_platforms = all_platforms[:10]

        # Create DataFrame for plotting
        df = pd.DataFrame(top_platforms)

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
            y="platform",
            hue="color",
            palette=unique_colors,
            ax=ax,
            orient="h",
            alpha=0.8,
            legend=False,
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

        # Create legend for media types
        media_types_present = list(
            set(str(platform["media_type"]) for platform in top_platforms)
        )
        if len(media_types_present) > 1:
            self.create_separated_legend(ax, media_types_present)

        # Add value annotations if enabled
        self.annotation_helper.annotate_horizontal_bar_patches(
            ax,
            "ANNOTATE_TOP_10_PLATFORMS",
            offset_x_ratio=0.01,
            ha="left",
            va="center",
            fontweight="bold",
        )

        logger.info(
            f"Created separated top 10 platforms graph with {len(top_platforms)} platforms across {len(media_types_present)} media types"
        )

    def _generate_stacked_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate stacked visualization showing Movies and TV Series platforms in stacked bars.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Aggregate data by media type with platform separation
        separated_data = aggregate_top_platforms_separated(processed_records, limit=10)

        if not separated_data:
            self.handle_empty_data_with_message(
                ax, "No platform data available for the selected time range."
            )
            return

        # Get all unique platforms across all media types
        all_platform_names: set[str] = set()
        for platforms_list in separated_data.values():
            for platform_data in platforms_list:
                all_platform_names.add(str(platform_data["platform"]))

        if not all_platform_names:
            self.handle_empty_data_with_message(
                ax, "No platform data available for the selected time range."
            )
            return

        # Create platform play count matrix for stacking
        platform_data_matrix: dict[str, dict[str, int]] = {}
        for platform_name in all_platform_names:
            platform_data_matrix[platform_name] = {}
            total_plays = 0

            # Get play counts for each media type
            for media_type, platforms_list in separated_data.items():
                platform_plays = 0
                for platform_data in platforms_list:
                    if str(platform_data["platform"]) == platform_name:
                        platform_plays = int(platform_data["play_count"])
                        break
                platform_data_matrix[platform_name][media_type] = platform_plays
                total_plays += platform_plays

            platform_data_matrix[platform_name]["total"] = total_plays

        # Sort platforms by total play count and take top 10
        sorted_platforms = sorted(
            platform_data_matrix.items(), key=lambda x: x[1]["total"], reverse=True
        )[:10]

        if not sorted_platforms:
            self.handle_empty_data_with_message(
                ax, "No platform data available for the selected time range."
            )
            return

        # Prepare data for stacked horizontal bars
        platform_names = [platform[0] for platform in sorted_platforms]
        media_types = [
            mt
            for mt in separated_data.keys()
            if any(platform[1][mt] > 0 for platform in sorted_platforms)
        ]

        if not media_types:
            self.handle_empty_data_with_message(
                ax, "No platform data available for the selected time range."
            )
            return

        # Create stacked horizontal bars
        y_positions = np.arange(len(platform_names))
        left_positions = np.zeros(len(platform_names))

        for media_type in media_types:
            counts = [
                sorted_platforms[i][1][media_type] for i in range(len(platform_names))
            ]

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
            ylabel="Platform",
            title_fontsize=18,
            label_fontsize=14,
        )

        # Configure tick parameters
        self.configure_tick_parameters(axis="both", labelsize=12)

        # Set y-axis ticks to show platform names
        ax.set_yticks(y_positions)  # pyright: ignore[reportAny] # matplotlib stubs incomplete
        ax.set_yticklabels(platform_names)  # pyright: ignore[reportAny] # matplotlib stubs incomplete

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
        if self.get_config_value("ANNOTATE_TOP_10_PLATFORMS", False):
            for i, (platform_name, data) in enumerate(sorted_platforms):
                total = data["total"]
                if total > 0:
                    _ = ax.annotate(  # pyright: ignore[reportUnknownMemberType]
                        str(total),
                        (total, i),
                        ha="left",
                        va="center",
                        fontweight="bold",
                        xytext=(3, 0),
                        textcoords="offset points",
                    )

        logger.info(
            f"Created stacked top 10 platforms graph with {len(platform_names)} platforms across {len(media_types)} media types"
        )
