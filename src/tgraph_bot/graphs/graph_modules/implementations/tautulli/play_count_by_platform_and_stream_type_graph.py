"""
Play count by platform and stream type graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot play counts
by platform with stream type breakdown. This helps users understand which
platforms are being used and how they handle different stream types.
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
    aggregate_by_platform_and_stream_type,
    get_stream_type_display_info,
)
from ...visualization.visualization_mixin import VisualizationMixin

if TYPE_CHECKING:
    from .....config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class PlayCountByPlatformAndStreamTypeGraph(BaseGraph, VisualizationMixin):
    """Graph showing play counts by platform with stream type breakdown."""

    def __init__(
        self,
        config: "TGraphBotConfig | None" = None,
        width: int = 14,
        height: int = 10,
        dpi: int = 100,
        background_color: str | None = None,
    ) -> None:
        """
        Initialize the play count by platform and stream type graph.

        Args:
            config: Configuration object containing graph settings
            width: Figure width in inches (larger for stacked bars)
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
        return self.get_enhanced_title_with_timeframe(
            "Play Count by Platform and Stream Type"
        )

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """
        Generate the play count by platform and stream type graph using the provided data.

        Args:
            data: Dictionary containing play history data from Tautulli API
                 Expected structure: {'data': [list of play records]}

        Returns:
            Path to the generated graph image file

        Raises:
            ValueError: If data is invalid or missing required fields
        """
        logger.info("Generating play count by platform and stream type graph")

        try:
            # Step 1: Extract and process play history data using DataProcessor
            _, processed_records = data_processor.extract_and_process_play_history(data)

            # Step 2: Setup figure with styling using combined utility
            _, ax = self.setup_figure_with_styling()

            # Step 3: Configure styling for bar charts
            self.configure_seaborn_style_with_grid()

            # Step 4: Generate platform and stream type visualization
            if processed_records:
                self._generate_platform_stream_type_visualization(ax, processed_records)
            else:
                # Show message that no data is available
                self._generate_no_data_visualization(ax)

            # Step 5: Finalize and save using combined utility
            output_path = self.finalize_and_save_figure(
                graph_type="play_count_by_platform_and_stream_type", user_id=None
            )
            return output_path

        except Exception as e:
            logger.exception(
                f"Error generating play count by platform and stream type graph: {e}"
            )
            raise
        finally:
            self.cleanup()

    def _generate_platform_stream_type_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate platform and stream type visualization showing stacked bars by platform.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Aggregate data by platform and stream type (limit to top 10 platforms)
        platform_stream_data = aggregate_by_platform_and_stream_type(
            processed_records, limit=10
        )

        if not platform_stream_data:
            self.handle_empty_data_with_message(
                ax,
                "No platform and stream type data available for the selected time range.",
            )
            return

        # Prepare data for stacked bar chart
        platforms = list(platform_stream_data.keys())

        if not platforms:
            self.handle_empty_data_with_message(
                ax,
                "No platform and stream type data available for the selected time range.",
            )
            return

        # Get all unique stream types across all platforms
        all_stream_types = set()
        for stream_aggregates in platform_stream_data.values():
            for stream_record in stream_aggregates:
                all_stream_types.add(stream_record["stream_type"])

        stream_types = sorted(all_stream_types)

        if not stream_types:
            self.handle_empty_data_with_message(
                ax, "No stream type data available for the selected time range."
            )
            return

        # Get stream type display info for colors and labels
        stream_type_info = get_stream_type_display_info()

        # Prepare data matrix for stacked bars
        data_matrix = []
        colors = []
        labels = []

        for stream_type in stream_types:
            # Get counts for this stream type across all platforms
            counts = []
            for platform in platforms:
                platform_data = platform_stream_data[platform]
                count = 0
                for record in platform_data:
                    if record["stream_type"] == stream_type:
                        count = record["play_count"]
                        break
                counts.append(count)

            data_matrix.append(counts)

            # Get display info for this stream type
            display_info = stream_type_info.get(
                stream_type, {"display_name": stream_type.title(), "color": "#1f77b4"}
            )
            colors.append(display_info["color"])
            labels.append(display_info["display_name"])

        # Create stacked horizontal bar chart (better for platform names)
        y_positions = np.arange(len(platforms))

        # Calculate cumulative positions for stacking
        left_positions = np.zeros(len(platforms))
        bars_list = []

        for i, (counts, color, label) in enumerate(zip(data_matrix, colors, labels)):
            bars = ax.barh(  # pyright: ignore[reportUnknownMemberType] # matplotlib method
                y_positions,
                counts,
                left=left_positions,
                color=color,
                alpha=0.8,
                label=label,
                edgecolor="white",
                linewidth=0.8,
            )
            bars_list.append(bars)
            left_positions += np.array(counts)

        # Customize the plot
        self.setup_title_and_axes_with_ax(ax, xlabel="Play Count", ylabel="Platform")

        # Set y-axis labels and positioning
        ax.set_yticks(y_positions)  # pyright: ignore[reportAny] # matplotlib method returns Any

        # Format platform names for better display
        formatted_platforms = [
            self._format_platform_name(platform) for platform in platforms
        ]
        ax.set_yticklabels(formatted_platforms)  # pyright: ignore[reportAny] # matplotlib method returns Any

        # Invert y-axis so top platform is at top
        ax.invert_yaxis()  # pyright: ignore[reportUnknownMemberType] # matplotlib method

        # Add value annotations on bars if enabled (using basic horizontal bar annotation)
        self.annotation_helper.annotate_horizontal_bar_patches(
            ax=ax,
            config_key="graphs.appearance.annotations.enabled_on.play_count_by_platform_and_stream_type",
            offset_x_ratio=0.01,
            ha="left",
            va="center",
            fontweight="normal",
            min_value_threshold=1.0,
        )

        # Add legend for stream types
        _ = ax.legend(  # pyright: ignore[reportUnknownMemberType]
            loc="lower right",
            frameon=True,
            fancybox=True,
            shadow=True,
            framealpha=0.9,
            fontsize=10,
        )

        # Add grid for better readability
        if self.get_grid_enabled():
            ax.grid(True, axis="x", alpha=0.3, linewidth=0.5)  # pyright: ignore[reportUnknownMemberType] # matplotlib method with **kwargs
        else:
            ax.grid(False)  # pyright: ignore[reportUnknownMemberType] # matplotlib method with **kwargs

        # Optimize layout
        ax.margins(y=0.01)  # pyright: ignore[reportUnknownMemberType] # matplotlib method with **kwargs

        logger.info(
            f"Created platform and stream type graph with {len(platforms)} platforms and {len(stream_types)} stream types"
        )

    def _generate_no_data_visualization(self, ax: Axes) -> None:
        """
        Generate visualization when no data is available.

        Args:
            ax: The matplotlib axes to plot on
        """
        self.handle_empty_data_with_message(
            ax,
            "No platform and stream type data available.\nThis graph requires Tautulli API data with platform and transcode decision information.",
        )

    def _format_platform_name(self, platform: str) -> str:
        """
        Format platform name for better display.

        Args:
            platform: Raw platform string

        Returns:
            Formatted platform name
        """
        if not platform or platform == "unknown":
            return "Unknown Platform"

        # Common platform name cleanups
        platform_mapping = {
            "Plex Web": "Plex Web",
            "Plex for Android": "Android",
            "Plex for iOS": "iOS",
            "Plex for Apple TV": "Apple TV",
            "Plex for Roku": "Roku",
            "Plex for Xbox": "Xbox",
            "Plex for PlayStation": "PlayStation",
            "Plex Media Player": "Desktop Player",
            "Plex for Smart TV": "Smart TV",
            "Plex for Chromecast": "Chromecast",
        }

        # Try exact match first
        if platform in platform_mapping:
            return platform_mapping[platform]

        # Try partial matches for variations
        for key, value in platform_mapping.items():
            if key.lower() in platform.lower():
                return value

        # Return cleaned up version
        return platform.replace("Plex for ", "").replace("Plex ", "")
