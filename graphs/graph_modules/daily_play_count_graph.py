"""
Daily play count graph for TGraph Bot.

This module inherits from BaseGraph and uses the Seaborn library
to implement the logic to plot daily play counts. This approach
simplifies the plotting code and produces a more aesthetically pleasing result.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, override

import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes

from .base_graph import BaseGraph
from .utils import (
    validate_graph_data,
    process_play_history_data,
    aggregate_by_date,
    aggregate_by_date_separated,
    handle_empty_data,
    get_media_type_display_info,
    ProcessedRecords,
)

if TYPE_CHECKING:
    from config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class DailyPlayCountGraph(BaseGraph):
    """Graph showing daily play counts over time."""

    def __init__(
        self,
        config: "TGraphBotConfig | dict[str, object] | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None
    ) -> None:
        """
        Initialize the daily play count graph.

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
        return "Daily Play Count"

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """
        Generate the daily play count graph using the provided data.

        Args:
            data: Dictionary containing play history data from Tautulli API
                 Expected structure: {'data': [list of play records]}

        Returns:
            Path to the generated graph image file

        Raises:
            ValueError: If data is invalid or missing required fields
        """
        logger.info("Generating daily play count graph")

        try:
            # Step 1: Validate input data
            is_valid, error_msg = validate_graph_data(data, ['data'])
            if not is_valid:
                raise ValueError(f"Invalid data for daily play count graph: {error_msg}")

            # Step 2: Process raw play history data
            try:
                processed_records = process_play_history_data(data)
                logger.info(f"Processed {len(processed_records)} play history records")
            except Exception as e:
                logger.error(f"Error processing play history data: {e}")
                # Use empty data structure for graceful degradation
                processed_records = []

            # Step 3: Setup figure and axes
            _, ax = self.setup_figure()

            # Step 4: Apply modern Seaborn styling
            self.apply_seaborn_style()

            # Step 5: Check if media type separation is enabled
            use_separation = self.get_media_type_separation_enabled()

            if use_separation and processed_records:
                # Generate separated visualization
                self._generate_separated_visualization(ax, processed_records)
            else:
                # Generate traditional combined visualization
                self._generate_combined_visualization(ax, processed_records)

            # Step 6: Improve layout and save
            if self.figure is not None:
                self.figure.tight_layout()

            # Save the figure using base class utility method
            output_path = self.save_figure(
                graph_type="daily_play_count",
                user_id=None
            )

            logger.info(f"Daily play count graph saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.exception(f"Error generating daily play count graph: {e}")
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
        # Aggregate data by date with media type separation
        separated_data = aggregate_by_date_separated(processed_records)
        display_info = get_media_type_display_info()

        if not separated_data:
            self._handle_empty_data_case(ax)
            return

        # Prepare data for plotting
        all_dates = set()
        for media_type_data in separated_data.values():
            all_dates.update(media_type_data.keys())

        if not all_dates:
            self._handle_empty_data_case(ax)
            return

        # Sort dates for proper timeline
        sorted_dates = sorted(all_dates)
        date_objects = [pd.to_datetime(date) for date in sorted_dates]  # pyright: ignore[reportUnknownMemberType]

        # Plot each media type separately
        media_types_plotted = []
        for media_type, media_data in separated_data.items():
            if not media_data:
                continue

            # Prepare data for this media type
            counts = [media_data.get(date, 0) for date in sorted_dates]
            
            # Skip if no data for this media type
            if all(count == 0 for count in counts):
                continue

            # Get display information
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
                color = '#666666'  # Default gray for unknown types

            # Create the plot
            _ = ax.plot(  # pyright: ignore[reportUnknownMemberType]
                date_objects,
                counts,
                marker='o',
                linewidth=3,
                markersize=8,
                label=label,
                color=color,
                markerfacecolor=color,
                markeredgecolor='white',
                markeredgewidth=1.5,
                alpha=0.8
            )
            
            media_types_plotted.append(media_type)

        if not media_types_plotted:
            self._handle_empty_data_case(ax)
            return

        # Customize the plot
        _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold', pad=20)  # pyright: ignore[reportUnknownMemberType]
        _ = ax.set_xlabel('Date', fontsize=14, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]
        _ = ax.set_ylabel('Play Count', fontsize=14, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]

        # Format dates on x-axis
        import matplotlib.dates as mdates
        _ = ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))  # pyright: ignore[reportUnknownMemberType]
        _ = ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(sorted_dates) // 10)))  # pyright: ignore[reportUnknownMemberType]
        _ = ax.tick_params(axis='x', rotation=45)  # pyright: ignore[reportUnknownMemberType]

        # Add legend
        _ = ax.legend(  # pyright: ignore[reportUnknownMemberType]
            loc='best',
            frameon=True,
            fancybox=True,
            shadow=True,
            framealpha=0.9,
            fontsize=12
        )

        # Add annotations if enabled
        annotate_enabled = self.get_config_value('ANNOTATE_DAILY_PLAY_COUNT', False)
        if annotate_enabled:
            self._add_peak_annotations(ax, separated_data, date_objects, sorted_dates)

        logger.info(f"Created separated daily play count graph with {len(media_types_plotted)} media types")

    def _generate_combined_visualization(self, ax: Axes, processed_records: ProcessedRecords) -> None:
        """
        Generate traditional combined visualization (backward compatibility).

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Use traditional aggregation method
        if processed_records:
            daily_counts = aggregate_by_date(processed_records)
            logger.info(f"Aggregated data for {len(daily_counts)} days")
        else:
            logger.warning("No valid records found, using empty data")
            daily_counts = handle_empty_data('daily')
            if not isinstance(daily_counts, dict):
                daily_counts = {}

        if daily_counts:
            # Convert to pandas DataFrame for easier plotting
            dates = list(daily_counts.keys())
            counts = list(daily_counts.values())

            # Create DataFrame
            df = pd.DataFrame({
                'date': pd.to_datetime([str(d) for d in dates]),  # pyright: ignore[reportUnknownMemberType]
                'play_count': counts
            })
            df = df.sort_values('date')  # pyright: ignore[reportUnknownMemberType]

            # Create line plot with modern styling
            _ = sns.lineplot(
                data=df,
                x='date',
                y='play_count',
                ax=ax,
                marker='o',
                linewidth=3,
                markersize=8,
                color=self.get_tv_color(),  # Use TV color as default
                markerfacecolor=self.get_tv_color(),
                markeredgecolor='white',
                markeredgewidth=1.5
            )

            # Customize the plot
            _ = ax.set_title(self.get_title(), fontsize=18, fontweight='bold', pad=20)  # pyright: ignore[reportUnknownMemberType]
            _ = ax.set_xlabel('Date', fontsize=14, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]
            _ = ax.set_ylabel('Play Count', fontsize=14, fontweight='bold')  # pyright: ignore[reportUnknownMemberType]

            # Rotate x-axis labels for better readability
            _ = ax.tick_params(axis='x', rotation=45)  # pyright: ignore[reportUnknownMemberType]

            # Add annotations if enabled
            annotate_enabled = self.get_config_value('ANNOTATE_DAILY_PLAY_COUNT', False)
            if annotate_enabled:
                # Convert counts to integers for proper comparison
                int_counts = [int(c) for c in counts]
                max_count = max(int_counts)
                max_date_idx = int_counts.index(max_count)
                max_date = dates[max_date_idx]

                # Convert date to timestamp for annotation
                max_date_ts = pd.to_datetime(max_date)  # pyright: ignore[reportUnknownMemberType]
                if hasattr(max_date_ts, 'timestamp'):
                    x_coord = float(max_date_ts.timestamp())
                else:
                    x_coord = float(max_date_idx)

                _ = ax.annotate(  # pyright: ignore[reportUnknownMemberType]
                    f'Peak: {max_count}',
                    xy=(x_coord, float(max_count)),
                    xytext=(10, 10),
                    textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor=self.get_annotation_color(), alpha=0.7),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
                )

            logger.info(f"Created combined daily play count graph with {len(dates)} data points")

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
        logger.warning("Generated empty daily play count graph due to no data")

    def _add_peak_annotations(
        self, 
        ax: Axes, 
        separated_data: dict[str, dict[str, int]], 
        date_objects: list[object], 
        sorted_dates: list[str]
    ) -> None:
        """
        Add peak annotations for separated data.

        Args:
            ax: The matplotlib axes to add annotations to
            separated_data: Dictionary of separated media type data
            date_objects: List of datetime objects for dates
            sorted_dates: List of sorted date strings
        """
        display_info = get_media_type_display_info()
        
        for media_type, media_data in separated_data.items():
            if not media_data:
                continue
                
            counts = [media_data.get(date, 0) for date in sorted_dates]
            if all(count == 0 for count in counts):
                continue
                
            max_count = max(counts)
            if max_count > 0:
                max_idx = counts.index(max_count)
                max_date_obj = date_objects[max_idx]
                
                # Get label for this media type
                label = display_info.get(media_type, {}).get('display_name', media_type.title())
                
                _ = ax.annotate(  # pyright: ignore[reportUnknownMemberType]
                    f'{label} Peak: {max_count}',
                    xy=(float(max_idx), max_count),  # Use index as x-coordinate instead of date object
                    xytext=(10, 10),
                    textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor=self.get_annotation_color(), alpha=0.7),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
                    fontsize=10
                )
