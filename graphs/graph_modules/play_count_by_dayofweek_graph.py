"""
Play count by day of week graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot play counts
by day of the week, resulting in a cleaner implementation and superior visual output.
Supports both combined and separated media type visualization.
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
    aggregate_by_day_of_week,
    aggregate_by_day_of_week_separated,
    get_media_type_display_info,
    ProcessedRecords,
)

if TYPE_CHECKING:
    from config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class PlayCountByDayOfWeekGraph(BaseGraph):
    """Graph showing play counts by day of the week."""

    def __init__(
        self,
        config: "TGraphBotConfig | dict[str, object] | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None
    ) -> None:
        """
        Initialize the play count by day of week graph.

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
        return "Play Count by Day of Week"

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """
        Generate the play count by day of week graph using the provided data.

        Args:
            data: Dictionary containing play history data from Tautulli API
                 Expected structure: {'data': [list of play records]}

        Returns:
            Path to the generated graph image file

        Raises:
            ValueError: If data is invalid or missing required fields
        """
        logger.info("Generating play count by day of week graph")

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
                raise ValueError(f"Invalid play history data for play count by day of week graph: {error_msg}")

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
                graph_type="play_count_by_dayofweek",
                user_id=None
            )

            logger.info(f"Play count by day of week graph saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.exception(f"Error generating play count by day of week graph: {e}")
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
        # Aggregate data by day of week with media type separation
        separated_data = aggregate_by_day_of_week_separated(processed_records)
        display_info = get_media_type_display_info()

        if not separated_data:
            self._handle_empty_data_case(ax)
            return

        # Define day order for consistent display
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        # Prepare data for plotting
        plot_data: list[dict[str, str | int]] = []
        for media_type, media_data in separated_data.items():
            if not media_data or all(count == 0 for count in media_data.values()):
                continue
                
            for day in day_order:
                count = media_data.get(day, 0)
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
                    'day': day,
                    'count': count,
                    'media_type': label,
                    'color': color
                })

        if not plot_data:
            self._handle_empty_data_case(ax)
            return

                # Create DataFrame for Seaborn
        df = pd.DataFrame(plot_data)

        # Create grouped bar plot - build color mapping from original data to avoid pandas type issues        
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
        
        _ = sns.barplot(
            data=df,
            x='day',
            y='count',
            hue='media_type',
            ax=ax,
            palette=colors,
            alpha=0.8
        )

        # Customize the plot
        _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold', pad=20)  # pyright: ignore[reportUnknownMemberType]
        _ = ax.set_xlabel('Day of Week', fontsize=14, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]
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

        # Add bar value annotations if enabled
        annotate_enabled = self.get_config_value('ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK', False)
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
                        offset_y=1,
                        fontweight='bold'
                    )

        logger.info(f"Created separated day of week graph with {len(unique_media_types_list)} media types")

    def _generate_combined_visualization(self, ax: Axes, processed_records: ProcessedRecords) -> None:
        """
        Generate traditional combined visualization (backward compatibility).

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Use traditional aggregation method
        if processed_records:
            day_counts = aggregate_by_day_of_week(processed_records)
            logger.info(f"Aggregated data for {len(day_counts)} days")
        else:
            logger.warning("No valid records found, using empty data")
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_counts = {day: 0 for day in day_names}

        # Define day order for consistent display
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Convert to pandas DataFrame
        days = [day for day in day_order if day in day_counts]
        counts = [day_counts[day] for day in days]

        if days and any(count > 0 for count in counts):
            df = pd.DataFrame({
                'day': days,
                'count': counts
            })

            # Create bar plot with modern styling
            _ = sns.barplot(
                data=df,
                x='day',
                y='count',
                ax=ax,
                color=self.get_tv_color(),  # Use TV color as default
                alpha=0.8
            )

            # Customize the plot
            _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold', pad=20)  # pyright: ignore[reportUnknownMemberType]
            _ = ax.set_xlabel('Day of Week', fontsize=14, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]
            _ = ax.set_ylabel('Play Count', fontsize=14, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]

            # Add bar value annotations if enabled
            annotate_enabled = self.get_config_value('ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK', False)
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
                            offset_y=1,
                            fontweight='bold'
                        )

            logger.info(f"Created combined day of week graph with {len(days)} days")
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
        logger.warning("Generated empty day of week graph due to no data")
