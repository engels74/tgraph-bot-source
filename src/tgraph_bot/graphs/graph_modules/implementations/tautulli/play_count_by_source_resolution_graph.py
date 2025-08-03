"""
Play count by source resolution graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot play counts 
by source resolution (original file resolution). This helps users understand
what resolutions their content is stored in and which resolutions are most popular.
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
    aggregate_by_resolution,
    filter_records_by_stream_type,
    get_available_stream_types,
)
from ...visualization.visualization_mixin import VisualizationMixin

if TYPE_CHECKING:
    from .....config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class PlayCountBySourceResolutionGraph(BaseGraph, VisualizationMixin):
    """Graph showing play counts by source resolution (original file resolution)."""

    def __init__(
        self,
        config: "TGraphBotConfig | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None,
    ) -> None:
        """
        Initialize the play count by source resolution graph.

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
        return self.get_enhanced_title_with_timeframe("Play Count by Source Resolution")

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """
        Generate the play count by source resolution graph using the provided data.

        Args:
            data: Dictionary containing play history data from Tautulli API
                 Expected structure: {'data': [list of play records]}

        Returns:
            Path to the generated graph image file

        Raises:
            ValueError: If data is invalid or missing required fields
        """
        logger.info("Generating play count by source resolution graph")

        try:
            # Step 1: Extract and process play history data with resolution metadata lookup
            import asyncio
            
            # Use run_until_complete to handle both cases (existing loop or not)
            try:
                # Try to get existing loop
                loop = asyncio.get_running_loop()
                # Create a new task in the existing loop
                task = loop.create_task(
                    data_processor.extract_and_process_play_history_with_resolution(data)
                )
                # For sync context, we need to create a new thread to run this
                import concurrent.futures
                import threading
                
                def run_in_new_loop():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            data_processor.extract_and_process_play_history_with_resolution(data)
                        )
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_new_loop)
                    _, processed_records = future.result()
                    
            except RuntimeError:
                # No event loop running, we can use asyncio.run
                _, processed_records = asyncio.run(
                    data_processor.extract_and_process_play_history_with_resolution(data)
                )

            # Step 2: Setup figure with styling using combined utility
            _, ax = self.setup_figure_with_styling()

            # Step 3: Configure styling for bar charts
            self.configure_seaborn_style_with_grid()

            # Step 4: Apply stream type filtering if configured
            filtered_records = self._apply_stream_type_filtering(processed_records)

            # Step 5: Generate resolution visualization
            if filtered_records:
                self._generate_resolution_visualization(ax, filtered_records)
            else:
                # Show message that no data is available
                self._generate_no_data_visualization(ax)

            # Step 5: Finalize and save using combined utility
            output_path = self.finalize_and_save_figure(
                graph_type="play_count_by_source_resolution", user_id=None
            )
            return output_path

        except Exception as e:
            logger.exception(f"Error generating play count by source resolution graph: {e}")
            raise
        finally:
            self.cleanup()

    def _apply_stream_type_filtering(self, processed_records: ProcessedRecords) -> ProcessedRecords:
        """
        Apply stream type filtering to processed records based on configuration.

        This method allows filtering by specific stream types (direct play, copy, transcode)
        to focus the resolution analysis on particular streaming scenarios.

        Args:
            processed_records: List of processed play history records

        Returns:
            Filtered list of records based on stream type configuration
        """
        # Check if stream type filtering is configured
        # For now, we'll include all stream types by default
        # This can be extended to read from configuration in the future

        # Get available stream types in the data
        available_types = get_available_stream_types(processed_records)

        if not available_types:
            logger.warning("No stream type data available in records")
            return processed_records

        logger.info(f"Available stream types: {', '.join(available_types)}")

        # For now, include all stream types (no filtering)
        # Future enhancement: Add configuration option to filter specific types
        # Example: filter_records_by_stream_type(processed_records, ["direct play", "copy"])

        filtered_records = filter_records_by_stream_type(
            processed_records,
            stream_types=None,  # Include all types
            exclude_unknown=True  # Exclude unknown stream types for cleaner data
        )

        logger.info(f"Stream type filtering: {len(filtered_records)} records after filtering (excluded unknown types)")

        return filtered_records

    def _generate_resolution_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate resolution visualization showing play counts by source resolution.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Aggregate data by source resolution
        resolution_aggregates = aggregate_by_resolution(
            processed_records, resolution_field="video_resolution"
        )

        if not resolution_aggregates:
            self.handle_empty_data_with_message(
                ax, "No source resolution data available.\nThis may indicate:\n• Tautulli is not collecting resolution data\n• No media has been played recently\n• Resolution fields are not available in your Tautulli version"
            )
            return

        # Limit to top 15 resolutions for readability
        top_resolutions = resolution_aggregates[:15]
        
        if not top_resolutions:
            self.handle_empty_data_with_message(
                ax, "No source resolution data available for the selected time range."
            )
            return

        # Prepare data for plotting
        resolutions = [res["resolution"] for res in top_resolutions]
        counts = [res["play_count"] for res in top_resolutions]

        # Format resolution labels for better display
        formatted_resolutions = [self._format_resolution_label(res) for res in resolutions]

        # Create color palette based on resolution quality
        colors = [self._get_resolution_color(res) for res in resolutions]

        # Create horizontal bar chart (better for resolution labels)
        y_positions = np.arange(len(formatted_resolutions))
        bars = ax.barh(  # pyright: ignore[reportUnknownMemberType] # matplotlib method
            y_positions,
            counts,
            color=colors,
            alpha=0.8,
            edgecolor="white",
            linewidth=1.2,
        )

        # Customize the plot
        self.setup_title_and_axes_with_ax(
            ax, 
            xlabel="Play Count", 
            ylabel="Source Resolution"
        )

        # Set y-axis labels and positioning
        ax.set_yticks(y_positions)  # pyright: ignore[reportAny] # matplotlib method returns Any
        ax.set_yticklabels(formatted_resolutions)  # pyright: ignore[reportAny] # matplotlib method returns Any
        
        # Invert y-axis so highest resolution is at top
        ax.invert_yaxis()  # pyright: ignore[reportUnknownMemberType] # matplotlib method

        # Add value annotations on bars if enabled
        self.annotation_helper.annotate_horizontal_bar_patches(
            ax=ax,
            config_key="graphs.appearance.annotations.enabled_on.play_count_by_source_resolution",
            offset_x_ratio=0.01,
            ha="left",
            va="center",
            fontweight="bold",
        )

        # Add grid for better readability
        if self.get_grid_enabled():
            ax.grid(True, axis="x", alpha=0.3, linewidth=0.5)  # pyright: ignore[reportUnknownMemberType] # matplotlib method with **kwargs
        else:
            ax.grid(False)  # pyright: ignore[reportUnknownMemberType] # matplotlib method with **kwargs

        # Optimize layout
        ax.margins(y=0.01)  # pyright: ignore[reportUnknownMemberType] # matplotlib method with **kwargs

        logger.info(f"Created source resolution graph with {len(top_resolutions)} resolutions")

    def _generate_no_data_visualization(self, ax: Axes) -> None:
        """
        Generate visualization when no data is available.

        Args:
            ax: The matplotlib axes to plot on
        """
        self.handle_empty_data_with_message(
            ax, "No source resolution data available.\nThis graph requires Tautulli API data with video resolution information.\nCheck your Tautulli configuration and ensure media is being played."
        )

    def _format_resolution_label(self, resolution: str) -> str:
        """
        Format resolution label for better display.

        Args:
            resolution: Raw resolution string (e.g., "1920x1080")

        Returns:
            Formatted resolution label with common names
        """
        if resolution == "unknown" or not resolution:
            return "Unknown (No resolution data from Tautulli)"
        
        # Common resolution mappings
        resolution_names = {
            "3840x2160": "4K UHD (3840×2160)",
            "4096x2160": "4K DCI (4096×2160)", 
            "2560x1440": "1440p (2560×1440)",
            "1920x1080": "1080p (1920×1080)",
            "1680x1050": "WSXGA+ (1680×1050)",
            "1600x900": "HD+ (1600×900)",
            "1366x768": "WXGA (1366×768)",
            "1280x720": "720p (1280×720)",
            "1024x768": "XGA (1024×768)",
            "854x480": "FWVGA (854×480)",
            "720x480": "NTSC (720×480)",
            "720x576": "PAL (720×576)",
        }
        
        return resolution_names.get(resolution, resolution)

    def _get_resolution_color(self, resolution: str) -> str:
        """
        Get color for resolution based on quality tier.

        Args:
            resolution: Resolution string

        Returns:
            Color code for the resolution
        """
        if resolution == "unknown" or not resolution:
            return "#95a5a6"  # Gray for unknown
        
        # Extract height for categorization
        try:
            if "x" in resolution:
                height = int(resolution.split("x")[1])
            else:
                height = 0
        except (ValueError, IndexError):
            height = 0

        # Color by quality tier
        if height >= 2160:  # 4K+
            return "#e74c3c"  # Red - highest quality
        elif height >= 1440:  # 1440p
            return "#f39c12"  # Orange - high quality
        elif height >= 1080:  # 1080p
            return "#27ae60"  # Green - standard HD
        elif height >= 720:   # 720p
            return "#3498db"  # Blue - HD
        elif height >= 480:   # SD
            return "#9b59b6"  # Purple - standard definition
        else:
            return "#95a5a6"  # Gray - unknown/low quality

