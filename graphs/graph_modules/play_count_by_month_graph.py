"""
Play count by month graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot play counts
by month, supporting both combined and separated media type visualization.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, override, cast

import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes

from .base_graph import BaseGraph
from .utils import (
    validate_graph_data,
    process_play_history_data,
    aggregate_by_month,
    aggregate_by_month_separated,
    get_media_type_display_info,
    ProcessedRecords,
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

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """
        Generate the play count by month graph using the provided data.

        Args:
            data: Dictionary containing play history data from Tautulli API
                 Expected structure: {'play_history': {'data': [list of play records]}}

        Returns:
            Path to the generated graph image file

        Raises:
            ValueError: If data is invalid or missing required fields
        """
        logger.info("Generating play count by month graph")

        try:
            # Step 1: Extract play history data from the full data structure
            play_history_data_raw = data.get('play_history', {})
            if not isinstance(play_history_data_raw, dict):
                raise ValueError("Missing or invalid 'play_history' data in input")
            
            # Cast to the proper type for type checker
            play_history_data = cast(Mapping[str, object], play_history_data_raw)

            # Step 2: Validate the play history data
            is_valid, error_msg = validate_graph_data(play_history_data, ['data'])
            if not is_valid:
                raise ValueError(f"Invalid play history data for play count by month graph: {error_msg}")

            # Step 3: Process raw play history data
            try:
                processed_records = process_play_history_data(play_history_data)
                logger.info(f"Processed {len(processed_records)} play history records")
            except Exception as e:
                logger.error(f"Error processing play history data: {e}")
                processed_records = []

            # Step 4: Setup figure and axes
            _, ax = self.setup_figure()

            # Step 5: Apply modern Seaborn styling
            self.apply_seaborn_style()

            # Step 6: Check if media type separation is enabled
            use_separation = self.get_media_type_separation_enabled()

            if use_separation and processed_records:
                # Generate separated visualization
                self._generate_separated_visualization(ax, processed_records)
            else:
                # Generate traditional combined visualization
                self._generate_combined_visualization(ax, processed_records)

            # Step 7: Improve layout and save
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

    def _generate_separated_visualization(self, ax: Axes, processed_records: ProcessedRecords) -> None:
        """
        Generate separated visualization showing Movies and TV Series separately.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Aggregate data by month with media type separation
        separated_data = aggregate_by_month_separated(processed_records)
        display_info = get_media_type_display_info()

        if not separated_data:
            self._handle_empty_data_case(ax)
            return

        # Prepare data for plotting
        plot_data: list[dict[str, str | int]] = []
        for media_type, media_data in separated_data.items():
            if not media_data or all(count == 0 for count in media_data.values()):
                continue
                
            for month, count in media_data.items():
                if media_type in display_info:
                    label = display_info[media_type]['display_name']
                    color = display_info[media_type]['color']
                    
                    # Override with config colors if available
                    if media_type == 'tv':
                        color = self.get_tv_color()
                    elif media_type == 'movie':
                        color = self.get_movie_color()
                else:
                    label = media_type.title()
                    color = '#666666'
                
                plot_data.append({
                    'month': month,
                    'count': count,
                    'media_type': label,
                    'color': color
                })

        if not plot_data:
            self._handle_empty_data_case(ax)
            return

        # Create DataFrame for Seaborn
        df = pd.DataFrame(plot_data)

        # Build color mapping and unique media types from the original plot_data
        color_mapping: dict[str, str] = {}
        unique_media_types_set: set[str] = set()
        
        for item in plot_data:
            media_type_key = str(item['media_type'])
            color_key = str(item['color'])
            unique_media_types_set.add(media_type_key)
            if media_type_key not in color_mapping:
                color_mapping[media_type_key] = color_key
        
        # Create ordered list for consistent plotting
        unique_media_types_list: list[str] = sorted(unique_media_types_set)
        colors: list[str] = [color_mapping[mt] for mt in unique_media_types_list]

        # Sort months chronologically for proper x-axis ordering
        df['month_sort'] = pd.to_datetime(df['month'], format='%Y-%m')  # pyright: ignore[reportUnknownMemberType] # pandas stubs incomplete
        df = df.sort_values('month_sort')  # pyright: ignore[reportUnknownMemberType] # pandas stubs incomplete
        
        # Create grouped bar plot
        _ = sns.barplot(
            data=df,
            x='month',
            y='count',
            hue='media_type',
            ax=ax,
            palette=colors,
            alpha=0.8
        )

        # Customize the plot
        _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold', pad=20)  # pyright: ignore[reportUnknownMemberType]
        _ = ax.set_xlabel('Month', fontsize=14, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]
        _ = ax.set_ylabel('Play Count', fontsize=14, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]

        # Enhance legend
        _ = ax.legend(  # pyright: ignore[reportUnknownMemberType]
            title='Media Type',
            loc='best',
            frameon=True,
            fancybox=True,
            shadow=True,
            framealpha=0.9,
            fontsize=12
        )

        # Rotate x-axis labels for better readability
        ax.tick_params(axis='x', rotation=45, labelsize=12)  # pyright: ignore[reportUnknownMemberType]
        ax.tick_params(axis='y', labelsize=12)  # pyright: ignore[reportUnknownMemberType]

        # Add bar value annotations if enabled
        annotate_enabled = self.get_config_value('ANNOTATE_PLAY_COUNT_BY_MONTH', False)
        if annotate_enabled:
            # Get all bar patches and annotate them
            for patch in ax.patches:
                height = patch.get_height()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType,reportUnknownVariableType]
                if height and height > 0:  # Only annotate non-zero values
                    x_val = patch.get_x() + patch.get_width() / 2  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType,reportUnknownVariableType]
                    self.add_bar_value_annotation(
                        ax,
                        x=float(x_val),  # pyright: ignore[reportUnknownArgumentType]
                        y=float(height),  # pyright: ignore[reportUnknownArgumentType]
                        value=int(height),  # pyright: ignore[reportUnknownArgumentType]
                        ha='center',
                        va='bottom',
                        offset_y=2,
                        fontweight='bold'
                    )

        logger.info(f"Created separated monthly play count graph with {len(unique_media_types_list)} media types")

    def _generate_combined_visualization(self, ax: Axes, processed_records: ProcessedRecords) -> None:
        """
        Generate traditional combined visualization (backward compatibility).

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Use traditional aggregation method
        if processed_records:
            month_counts = aggregate_by_month(processed_records)
            logger.info(f"Aggregated data for {len(month_counts)} months")
        else:
            logger.warning("No valid records found, using empty data")
            month_counts = {}

        if month_counts:
            # Sort months chronologically
            sorted_months = sorted(month_counts.items())

            # Convert to pandas DataFrame for consistent handling
            df = pd.DataFrame(sorted_months, columns=['month', 'count'])

            # Create bar plot with modern styling
            _ = sns.barplot(
                data=df,
                x='month',
                y='count',
                ax=ax,
                color=self.get_tv_color(),  # Use TV color as default
                alpha=0.8
            )

            # Customize the plot
            _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold', pad=20)  # pyright: ignore[reportUnknownMemberType]
            _ = ax.set_xlabel('Month', fontsize=14, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]
            _ = ax.set_ylabel('Play Count', fontsize=14, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]

            # Rotate x-axis labels for better readability
            ax.tick_params(axis='x', rotation=45, labelsize=12)  # pyright: ignore[reportUnknownMemberType]
            ax.tick_params(axis='y', labelsize=12)  # pyright: ignore[reportUnknownMemberType]

            # Add bar value annotations if enabled
            annotate_enabled = self.get_config_value('ANNOTATE_PLAY_COUNT_BY_MONTH', False)
            if annotate_enabled:
                # Get all bar patches and annotate them
                for patch in ax.patches:
                    height = patch.get_height()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType,reportUnknownVariableType]
                    if height and height > 0:  # Only annotate non-zero values
                        x_val = patch.get_x() + patch.get_width() / 2  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType,reportUnknownVariableType]
                        self.add_bar_value_annotation(
                            ax,
                            x=float(x_val),  # pyright: ignore[reportUnknownArgumentType]
                            y=float(height),  # pyright: ignore[reportUnknownArgumentType]
                            value=int(height),  # pyright: ignore[reportUnknownArgumentType]
                            ha='center',
                            va='bottom',
                            offset_y=2,
                            fontweight='bold'
                        )

            logger.info(f"Created combined monthly play count graph with {len(sorted_months)} months")
        else:
            self._handle_empty_data_case(ax)

    def _handle_empty_data_case(self, ax: Axes) -> None:
        """
        Handle the case where no data is available.

        Args:
            ax: The matplotlib axes to display the message on
        """
        _ = ax.text(0.5, 0.5, "No play data available\nfor the selected time period",  # pyright: ignore[reportUnknownMemberType]
                   ha='center', va='center', transform=ax.transAxes, fontsize=16,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.7))
        _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]
        logger.warning("Generated empty monthly play count graph due to no data")
