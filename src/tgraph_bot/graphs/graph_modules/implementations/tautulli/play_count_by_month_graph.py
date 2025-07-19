"""
Play count by month graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot play counts
by month, supporting both combined and separated media type visualization.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, cast, override

import numpy as np
from numpy.typing import NDArray
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.container import BarContainer
from matplotlib.patches import Rectangle

from ...utils.annotation_helper import AnnotationHelper
from ...core.base_graph import BaseGraph
from ...data.data_processor import data_processor
from ...data.empty_data_handler import EmptyDataHandler
from ...utils.utils import (
    ProcessedRecords,
    aggregate_by_month,
    aggregate_by_month_separated,
    get_media_type_display_info,
)
from ...visualization.visualization_mixin import VisualizationMixin

if TYPE_CHECKING:
    from pandas import DataFrame

    from .....config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class PlayCountByMonthGraph(BaseGraph, VisualizationMixin):
    """Graph showing play counts by month."""

    def __init__(
        self,
        config: "TGraphBotConfig | dict[str, object] | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None,
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
            "Play Count by Month", use_months=True
        )

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """
        Generate the play count by month graph using the provided data.

        Args:
            data: Dictionary containing monthly plays data from Tautulli API
                 Expected structure: {'monthly_plays': {'categories': [...], 'series': [...]}}

        Returns:
            Path to the generated graph image file

        Raises:
            ValueError: If data is invalid or missing required fields
        """
        logger.info("Generating play count by month graph")

        try:
            # Step 1: Extract monthly plays data using DataProcessor
            response_data = data_processor.extract_monthly_plays_data(data)

            # Step 2: Setup figure with styling using combined utility
            _, ax = self.setup_figure_with_styling()

            # Step 3: Configure grid styling (explicit for bar charts)
            self.configure_seaborn_style_with_grid()

            # Step 4: Check if media type separation is enabled
            use_separation = self.get_media_type_separation_enabled()

            if use_separation:
                # Check if stacked bars are enabled
                use_stacked = self.get_stacked_bar_charts_enabled()
                if use_stacked:
                    # Generate stacked visualization using monthly API data
                    self._generate_stacked_visualization_from_api(ax, response_data)
                else:
                    # Generate separated visualization using monthly API data (grouped bars)
                    self._generate_separated_visualization_from_api(ax, response_data)
            else:
                # Generate traditional combined visualization using monthly API data
                self._generate_combined_visualization_from_api(ax, response_data)

            # Step 5: Finalize and save using combined utility
            output_path = self.finalize_and_save_figure(
                graph_type="play_count_by_month", user_id=None
            )
            return output_path

        except Exception as e:
            logger.exception(f"Error generating play count by month graph: {e}")
            raise
        finally:
            self.cleanup()

    def _generate_separated_visualization_from_api(
        self, ax: Axes, response_data: Mapping[str, object]
    ) -> None:
        """
        Generate separated visualization using data from Tautulli's get_plays_per_month API.

        Args:
            ax: The matplotlib axes to plot on
            response_data: The data section from the API response
        """
        # Extract categories (months) and series (media types with data)
        categories = response_data.get("categories", [])
        series = response_data.get("series", [])

        if not isinstance(categories, list) or not isinstance(series, list):
            self._handle_empty_data_case()
            return

        if not categories or not series:
            self._handle_empty_data_case()
            return

        # Prepare data for plotting
        plot_data: list[dict[str, str | int]] = []
        display_info = get_media_type_display_info()

        # series comes from external Tautulli API - runtime type checking required
        for series_item in series:  # pyright: ignore[reportUnknownVariableType] # external API data
            # Runtime type validation for external API data
            if not isinstance(series_item, dict):
                continue

            series_name = str(series_item.get("name", ""))  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType] # external API data
            series_data_raw = series_item.get("data", [])  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType] # external API data

            if not isinstance(series_data_raw, list) or len(series_data_raw) != len(  # pyright: ignore[reportUnknownArgumentType] # external API data
                categories  # pyright: ignore[reportUnknownArgumentType] # external API data
            ):
                continue

            # Map series name to media type
            media_type = "tv" if series_name.lower() in ["tv", "tv series"] else "movie"

            # Get display info
            if media_type in display_info:
                label = display_info[media_type]["display_name"]
                color = display_info[media_type]["color"]

                # Override with config colors if available
                if media_type == "tv":
                    color = self.get_tv_color()
                elif media_type == "movie":
                    color = self.get_movie_color()
            else:
                label = series_name
                color = "#666666"

            # Add data points for each month
            # External API data requires runtime validation
            for month, count in zip(categories, series_data_raw):  # pyright: ignore[reportUnknownArgumentType,reportUnknownVariableType] # external API data
                month_str = str(month)  # pyright: ignore[reportUnknownArgumentType] # external API data
                if (
                    isinstance(count, (int, float)) and count > 0
                ):  # Only include non-zero values
                    plot_data.append(
                        {
                            "month": month_str,
                            "count": int(count),  # external API data conversion
                            "media_type": label,
                            "color": color,
                        }
                    )

        if not plot_data:
            self._handle_empty_data_case()
            return

        # Create DataFrame for Seaborn
        df: DataFrame = pd.DataFrame(plot_data)

        # Build color mapping and unique media types
        color_mapping: dict[str, str] = {}
        unique_media_types_set: set[str] = set()

        for item in plot_data:
            media_type_key = str(item["media_type"])
            color_key = str(item["color"])
            unique_media_types_set.add(media_type_key)
            if media_type_key not in color_mapping:
                color_mapping[media_type_key] = color_key

        # Create ordered list for consistent plotting - use consistent order instead of alphabetical
        # to ensure TV Series always gets blue and Movies get orange
        preferred_order = ["TV Series", "Movies", "Music", "Other"]
        unique_media_types_list: list[str] = []

        # Add media types in preferred order if they exist
        for media_type in preferred_order:
            if media_type in unique_media_types_set:
                unique_media_types_list.append(media_type)

        # Add any remaining media types not in preferred order (shouldn't happen normally)
        for media_type in sorted(unique_media_types_set):
            if media_type not in unique_media_types_list:
                unique_media_types_list.append(media_type)

        colors: list[str] = [color_mapping[mt] for mt in unique_media_types_list]

        # Create grouped bar plot with proper spacing
        _ = sns.barplot(  # pyright: ignore[reportUnknownMemberType] # seaborn method overloads
            data=df,
            x="month",
            y="count",
            hue="media_type",
            ax=ax,
            palette=colors,
            alpha=0.8,
            edgecolor="white",
            linewidth=0.7,
        )

        # Customize the plot - matplotlib methods lack complete type stubs
        _ = ax.set_title(self.get_title(), fontsize=18, fontweight="bold", pad=20)  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete
        _ = ax.set_xlabel("Month", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete
        _ = ax.set_ylabel("Play Count", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete

        # Enhance legend
        _ = ax.legend(  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete
            title="Media Type",
            loc="best",
            frameon=True,
            fancybox=True,
            shadow=True,
            framealpha=0.9,
            fontsize=12,
        )

        # Rotate x-axis labels for better readability
        ax.tick_params(axis="x", rotation=45, labelsize=12)  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete
        ax.tick_params(axis="y", labelsize=12)  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete

        # Add bar value annotations if enabled
        self.annotation_helper.annotate_bar_patches(
            ax,
            "ANNOTATE_PLAY_COUNT_BY_MONTH",
            offset_y=2,
            fontweight="bold",
        )

        logger.info(
            f"Created separated monthly play count graph with {len(unique_media_types_list)} media types and {len(categories)} months"  # pyright: ignore[reportUnknownArgumentType] # external API data
        )

    def _generate_stacked_visualization_from_api(
        self, ax: Axes, response_data: Mapping[str, object]
    ) -> None:
        """
        Generate stacked bar visualization using data from Tautulli's get_plays_per_month API.

        Args:
            ax: The matplotlib axes to plot on
            response_data: The data section from the API response
        """
        # Extract categories (months) and series (media types with data)
        categories_raw = response_data.get("categories", [])
        series_raw = response_data.get("series", [])

        if not isinstance(categories_raw, list) or not isinstance(series_raw, list):
            self._handle_empty_data_case()
            return

        if not categories_raw or not series_raw:
            self._handle_empty_data_case()
            return

        # Type-safe assignments after validation
        categories: list[str] = [str(cat) for cat in categories_raw]  # pyright: ignore[reportUnknownArgumentType,reportUnknownVariableType] # external API data
        series: list[object] = series_raw  # pyright: ignore[reportUnknownVariableType] # external API data

        # Prepare data for stacked bars
        media_type_data: dict[str, list[int]] = {}
        media_type_colors: dict[str, str] = {}
        display_info = get_media_type_display_info()

        # Process series data from API
        for series_item in series:
            if not isinstance(series_item, dict):
                continue

            series_name = str(series_item.get("name", ""))  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType] # external API data
            series_data_raw = series_item.get("data", [])  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType] # external API data

            if not isinstance(series_data_raw, list) or len(series_data_raw) != len(  # pyright: ignore[reportUnknownArgumentType] # external API data
                categories
            ):
                continue

            # Map series name to media type
            media_type = "tv" if series_name.lower() in ["tv", "tv series"] else "movie"

            # Convert data to integers
            values_list: list[int] = []
            for count in series_data_raw:  # pyright: ignore[reportUnknownVariableType] # external API data
                if isinstance(count, (int, float)):
                    values_list.append(int(count))
                else:
                    values_list.append(0)

            media_type_data[media_type] = values_list

            # Get colors for media types
            if media_type == "tv":
                media_type_colors[media_type] = self.get_tv_color()
            elif media_type == "movie":
                media_type_colors[media_type] = self.get_movie_color()
            elif media_type in display_info:
                media_type_colors[media_type] = display_info[media_type]["color"]
            else:
                media_type_colors[media_type] = "#666666"

        if not media_type_data:
            self._handle_empty_data_case()
            return

        # Create data arrays for stacking
        x = np.arange(len(categories))  # the label locations
        width = 0.8  # width of the bars

        # Use preferred order for consistent coloring
        # Movies at bottom, TV series on top for stacked bars
        preferred_order = ["movie", "tv", "music", "other"]
        ordered_media_types: list[str] = []

        # Add media types in preferred order if they exist
        for media_type in preferred_order:
            if media_type in media_type_data:
                ordered_media_types.append(media_type)

        # Add any remaining media types
        for media_type in media_type_data:
            if media_type not in ordered_media_types:
                ordered_media_types.append(media_type)

        # Create stacked bars
        bottom = np.zeros(len(categories))
        bar_containers: list[tuple[BarContainer, str, NDArray[np.int64]]] = []

        for media_type in ordered_media_types:
            values = np.array(media_type_data[media_type])
            color = media_type_colors[media_type]

            # Get display name for legend
            if media_type in display_info:
                label = display_info[media_type]["display_name"]
            else:
                label = media_type.title()

            bars = ax.bar(  # pyright: ignore[reportUnknownMemberType] # matplotlib complex type signature
                x,
                values,
                width,
                label=label,
                bottom=bottom,
                color=color,
                alpha=0.8,
                edgecolor="white",
                linewidth=1.5,
            )
            bar_containers.append((bars, media_type, values))
            bottom += values

        # Set labels and title
        _ = ax.set_xlabel("Month", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType]
        _ = ax.set_ylabel("Play Count", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType]
        _ = ax.set_title(self.get_title(), fontsize=18, fontweight="bold", pad=20)  # pyright: ignore[reportUnknownMemberType]
        _ = ax.set_xticks(x)  # pyright: ignore[reportAny] # matplotlib method returns Any
        _ = ax.set_xticklabels(categories, rotation=45, ha="right")  # pyright: ignore[reportAny] # matplotlib method returns Any

        # Adjust tick parameters
        ax.tick_params(axis="x", labelsize=12)  # pyright: ignore[reportUnknownMemberType]
        ax.tick_params(axis="y", labelsize=12)  # pyright: ignore[reportUnknownMemberType]

        # Add legend
        _ = ax.legend(  # pyright: ignore[reportUnknownMemberType]
            loc="best",
            frameon=True,
            fancybox=True,
            shadow=True,
            framealpha=0.9,
            fontsize=12,
        )

        # Add annotations if enabled
        self.annotation_helper.annotate_stacked_bar_segments(
            ax,
            "ANNOTATE_PLAY_COUNT_BY_MONTH",
            bar_containers,
            categories,
            include_totals=True,
            segment_fontsize=9,
            total_fontsize=11,
        )

        logger.info(
            f"Created stacked monthly play count graph with {len(ordered_media_types)} media types and {len(categories)} months"
        )

    def _generate_combined_visualization_from_api(
        self, ax: Axes, response_data: Mapping[str, object]
    ) -> None:
        """
        Generate combined visualization using data from Tautulli's get_plays_per_month API.

        Args:
            ax: The matplotlib axes to plot on
            response_data: The data section from the API response
        """
        # Extract categories (months) and series (media types with data)
        categories = response_data.get("categories", [])
        series = response_data.get("series", [])

        if not isinstance(categories, list) or not isinstance(series, list):
            self._handle_empty_data_case()
            return

        if not categories or not series:
            self._handle_empty_data_case()
            return

        # Combine all series data into totals for each month
        month_totals: dict[str, int] = {}

        # series comes from external Tautulli API - runtime type checking required
        for series_item in series:  # pyright: ignore[reportUnknownVariableType] # external API data
            # Runtime type validation for external API data
            if not isinstance(series_item, dict):
                continue

            series_data_raw = series_item.get("data", [])  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType] # external API data

            if not isinstance(series_data_raw, list) or len(series_data_raw) != len(  # pyright: ignore[reportUnknownArgumentType] # external API data
                categories  # pyright: ignore[reportUnknownArgumentType] # external API data
            ):
                continue

            # Add data for each month
            # External API data requires runtime validation
            for month, count in zip(categories, series_data_raw):  # pyright: ignore[reportUnknownArgumentType,reportUnknownVariableType] # external API data
                month_str = str(month)  # pyright: ignore[reportUnknownArgumentType] # external API data
                if month_str not in month_totals:
                    month_totals[month_str] = 0

                if isinstance(count, (int, float)):
                    month_totals[month_str] += int(
                        count
                    )  # external API data conversion

        if not month_totals or all(count == 0 for count in month_totals.values()):
            self._handle_empty_data_case()
            return

        # Convert to DataFrame for plotting
        df: DataFrame = pd.DataFrame(
            [
                {"month": month, "count": count}
                for month, count in month_totals.items()
                if count > 0  # Only include months with data
            ]
        )

        # Create bar plot with modern styling
        _ = sns.barplot(  # pyright: ignore[reportUnknownMemberType] # seaborn method overloads
            data=df,
            x="month",
            y="count",
            ax=ax,
            color=self.get_tv_color(),  # Use TV color as default
            alpha=0.8,
            edgecolor="white",
            linewidth=0.7,
        )

        # Customize the plot - matplotlib methods lack complete type stubs
        _ = ax.set_title(self.get_title(), fontsize=18, fontweight="bold", pad=20)  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete
        _ = ax.set_xlabel("Month", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete
        _ = ax.set_ylabel("Play Count", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete

        # Rotate x-axis labels for better readability
        ax.tick_params(axis="x", rotation=45, labelsize=12)  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete
        ax.tick_params(axis="y", labelsize=12)  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete

        # Add bar value annotations if enabled
        annotate_enabled = self.get_config_value("ANNOTATE_PLAY_COUNT_BY_MONTH", False)
        if annotate_enabled:
            # Get all bar patches and annotate them
            for patch in ax.patches:  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType] # matplotlib patches collection
                if (
                    hasattr(patch, "get_height")
                    and hasattr(patch, "get_x")
                    and hasattr(patch, "get_width")
                ):  # pyright: ignore[reportUnknownArgumentType] # matplotlib patch attributes
                    rect_patch = cast(Rectangle, patch)
                    height = rect_patch.get_height()
                    if height and height > 0:  # Only annotate non-zero values
                        x_val = rect_patch.get_x() + rect_patch.get_width() / 2
                        self.add_bar_value_annotation(
                            ax,
                            x=float(x_val),
                            y=float(height),
                            value=int(height),
                            ha="center",
                            va="bottom",
                            offset_y=2,
                            fontweight="bold",
                        )

        logger.info(
            f"Created combined monthly play count graph with {len(month_totals)} months"
        )

    # Keep the old methods for backward compatibility
    def _generate_separated_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate separated visualization showing Movies and TV Series separately using processed play history records.

        NOTE: This method is kept for backward compatibility. The new implementation uses
        _generate_separated_visualization_from_api() which works with Tautulli's get_plays_per_month API data.

        Args:
            ax: The matplotlib axes to plot on
            processed_records: List of processed play history records
        """
        # Aggregate data by month with media type separation
        separated_data = aggregate_by_month_separated(processed_records)
        display_info = get_media_type_display_info()

        if not separated_data:
            self._handle_empty_data_case()
            return

        # Prepare data for plotting
        plot_data: list[dict[str, str | int]] = []
        for media_type, media_data in separated_data.items():
            if not media_data or all(count == 0 for count in media_data.values()):
                continue

            for month, count in media_data.items():
                if media_type in display_info:
                    label = display_info[media_type]["display_name"]
                    color = display_info[media_type]["color"]

                    # Override with config colors if available
                    if media_type == "tv":
                        color = self.get_tv_color()
                    elif media_type == "movie":
                        color = self.get_movie_color()
                else:
                    label = media_type.title()
                    color = "#666666"

                plot_data.append(
                    {
                        "month": month,
                        "count": count,
                        "media_type": label,
                        "color": color,
                    }
                )

        if not plot_data:
            self._handle_empty_data_case()
            return

        # Create DataFrame for Seaborn
        df: DataFrame = pd.DataFrame(plot_data)

        # Build color mapping and unique media types from the original plot_data
        color_mapping: dict[str, str] = {}
        unique_media_types_set: set[str] = set()

        for item in plot_data:
            media_type_key = str(item["media_type"])
            color_key = str(item["color"])
            unique_media_types_set.add(media_type_key)
            if media_type_key not in color_mapping:
                color_mapping[media_type_key] = color_key

        # Create ordered list for consistent plotting - use consistent order instead of alphabetical
        # to ensure TV Series always gets blue and Movies get orange
        preferred_order = ["TV Series", "Movies", "Music", "Other"]
        unique_media_types_list: list[str] = []

        # Add media types in preferred order if they exist
        for media_type in preferred_order:
            if media_type in unique_media_types_set:
                unique_media_types_list.append(media_type)

        # Add any remaining media types not in preferred order (shouldn't happen normally)
        for media_type in sorted(unique_media_types_set):
            if media_type not in unique_media_types_list:
                unique_media_types_list.append(media_type)

        colors: list[str] = [color_mapping[mt] for mt in unique_media_types_list]

        # Sort months chronologically for proper x-axis ordering
        df["month_sort"] = pd.to_datetime(df["month"], format="%Y-%m")  # pyright: ignore[reportUnknownMemberType] # pandas method overloads
        df = df.sort_values("month_sort")  # pyright: ignore[reportUnknownMemberType] # pandas method overloads

        # Create grouped bar plot
        _ = sns.barplot(  # pyright: ignore[reportUnknownMemberType] # seaborn method overloads
            data=df,
            x="month",
            y="count",
            hue="media_type",
            ax=ax,
            palette=colors,
            alpha=0.8,
        )

        # Customize the plot
        _ = ax.set_title(self.get_title(), fontsize=18, fontweight="bold", pad=20)  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete
        _ = ax.set_xlabel("Month", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete
        _ = ax.set_ylabel("Play Count", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete

        # Enhance legend
        _ = ax.legend(  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete
            title="Media Type",
            loc="best",
            frameon=True,
            fancybox=True,
            shadow=True,
            framealpha=0.9,
            fontsize=12,
        )

        # Rotate x-axis labels for better readability
        ax.tick_params(axis="x", rotation=45, labelsize=12)  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete
        ax.tick_params(axis="y", labelsize=12)  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete

        # Add bar value annotations if enabled
        annotate_enabled = self.get_config_value("ANNOTATE_PLAY_COUNT_BY_MONTH", False)
        if annotate_enabled:
            # Get all bar patches and annotate them
            for patch in ax.patches:  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType] # matplotlib patches collection
                if (
                    hasattr(patch, "get_height")
                    and hasattr(patch, "get_x")
                    and hasattr(patch, "get_width")
                ):  # pyright: ignore[reportUnknownArgumentType] # matplotlib patch attributes
                    rect_patch = cast(Rectangle, patch)
                    height = rect_patch.get_height()
                    if height and height > 0:  # Only annotate non-zero values
                        x_val = rect_patch.get_x() + rect_patch.get_width() / 2
                        self.add_bar_value_annotation(
                            ax,
                            x=float(x_val),
                            y=float(height),
                            value=int(height),
                            ha="center",
                            va="bottom",
                            offset_y=2,
                            fontweight="bold",
                        )

        logger.info(
            f"Created separated monthly play count graph with {len(unique_media_types_list)} media types"
        )

    def _generate_combined_visualization(
        self, ax: Axes, processed_records: ProcessedRecords
    ) -> None:
        """
        Generate traditional combined visualization using processed play history records.

        NOTE: This method is kept for backward compatibility. The new implementation uses
        _generate_combined_visualization_from_api() which works with Tautulli's get_plays_per_month API data.

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
            df: DataFrame = pd.DataFrame(sorted_months, columns=["month", "count"])

            # Create bar plot with modern styling
            _ = sns.barplot(  # pyright: ignore[reportUnknownMemberType] # seaborn method overloads
                data=df,
                x="month",
                y="count",
                ax=ax,
                color=self.get_tv_color(),  # Use TV color as default
                alpha=0.8,
            )

            # Customize the plot - matplotlib methods lack complete type stubs
            _ = ax.set_title(self.get_title(), fontsize=18, fontweight="bold", pad=20)  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete
            _ = ax.set_xlabel("Month", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete
            _ = ax.set_ylabel("Play Count", fontsize=14, fontweight="bold")  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete

            # Rotate x-axis labels for better readability
            ax.tick_params(axis="x", rotation=45, labelsize=12)  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete
            ax.tick_params(axis="y", labelsize=12)  # pyright: ignore[reportUnknownMemberType] # matplotlib stubs incomplete

            # Add bar value annotations if enabled
            annotate_enabled = self.get_config_value(
                "ANNOTATE_PLAY_COUNT_BY_MONTH", False
            )
            if annotate_enabled:
                # Get all bar patches and annotate them
                for patch in ax.patches:  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType] # matplotlib patches collection
                    height = patch.get_height()  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType] # matplotlib patch attributes
                    if height and height > 0:  # Only annotate non-zero values
                        x_val = patch.get_x() + patch.get_width() / 2  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType] # matplotlib patch attributes
                        self.add_bar_value_annotation(
                            ax,
                            x=float(x_val),  # pyright: ignore[reportUnknownArgumentType] # matplotlib patch result
                            y=float(height),  # pyright: ignore[reportUnknownArgumentType] # matplotlib patch result
                            value=int(height),  # pyright: ignore[reportUnknownArgumentType] # matplotlib patch result
                            ha="center",
                            va="bottom",
                            offset_y=2,
                            fontweight="bold",
                        )

            logger.info(
                f"Created combined monthly play count graph with {len(sorted_months)} months"
            )
        else:
            self._handle_empty_data_case()

    def _handle_empty_data_case(self) -> None:
        """
        Handle the case where no data is available.

        Uses the EmptyDataHandler utility to display a standardized empty data message.
        """
        empty_data_handler = EmptyDataHandler()
        empty_data_handler.display_empty_data_message(
            self.axes,
            message="No play data available\nfor the selected time period",
            log_message="Generated empty monthly play count graph due to no data",
        )
