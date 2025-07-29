"""
Base graph class for TGraph Bot.

This module defines the abstract base class for all graph types.
It uses Matplotlib to handle the core figure and axes setup (e.g., size,
background color, titles), providing a canvas for the high-level Seaborn
library to draw onto.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING

# Ensure matplotlib uses non-GUI backend for thread safety
import matplotlib
import matplotlib.figure
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from ..utils.utils import (
    ProcessedRecords,
    apply_modern_seaborn_styling,
    censor_username,
    generate_graph_filename,
    get_current_graph_storage_path,
    process_play_history_data,
    validate_color,
    validate_graph_data,
)

if TYPE_CHECKING:
    from ....config.schema import TGraphBotConfig
    from ..config.config_accessor import ConfigAccessor
    from ..data.media_type_processor import MediaTypeProcessor

# Set matplotlib backend and configure logging
if matplotlib.get_backend() != "Agg":
    matplotlib.use("Agg")

# Suppress matplotlib categorical units warnings that occur with numeric data
# These warnings appear when seaborn/matplotlib auto-detects categorical units
# for numeric data, which is common in hour-of-day and similar time-based graphs
_matplotlib_category_logger = logging.getLogger("matplotlib.category")
_matplotlib_category_logger.setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class BaseGraph(ABC):
    """Abstract base class defining the common interface for all graph types."""

    def __init__(
        self,
        config: "TGraphBotConfig | dict[str, object] | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None,
    ) -> None:
        """
        Initialize the base graph.

        Args:
            config: Configuration object containing graph settings
            width: Figure width in inches
            height: Figure height in inches
            dpi: Dots per inch for the figure
            background_color: Background color for the graph (overrides config if provided)

        Raises:
            ValueError: If background_color is not a valid color format
        """
        self.config: "TGraphBotConfig | dict[str, object] | None" = config

        # Initialize ConfigAccessor for centralized configuration access
        if config is not None:
            # Import here to avoid circular imports
            from ..config.config_accessor import ConfigAccessor

            self._config_accessor: "ConfigAccessor | None" = ConfigAccessor(config)
        else:
            self._config_accessor = None

        # Lazy initialization for MediaTypeProcessor
        self._media_type_processor: "MediaTypeProcessor | None" = None

        # Use background color from config if not explicitly provided
        if background_color is None:
            if config is not None:
                bg_color = self.get_config_value("GRAPH_BACKGROUND_COLOR")
                background_color = str(bg_color) if bg_color is not None else "#ffffff"
            else:
                background_color = "#ffffff"

        # Validate color format using utility function
        if not validate_color(background_color):
            raise ValueError(f"Invalid background color format: {background_color}")

        self.width: int = width
        self.height: int = height
        self.dpi: int = dpi
        self.background_color: str = background_color
        self.figure: matplotlib.figure.Figure | None = None
        self.axes: Axes | None = None

    def get_config_value(self, key: str, default: object = None) -> object:
        """
        Get a configuration value using the centralized ConfigAccessor.

        Args:
            key: Configuration key to retrieve
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if self._config_accessor is None:
            return default

        if default is not None:
            return self._config_accessor.get_value(key, default)
        else:
            try:
                return self._config_accessor.get_value(key)
            except Exception:
                # If key doesn't exist and no default provided, return None for backward compatibility
                return None

    @property
    def media_type_processor(self) -> "MediaTypeProcessor":
        """
        Get the MediaTypeProcessor instance for this graph.

        This property provides lazy initialization of the MediaTypeProcessor
        to avoid circular import issues while providing centralized media
        type handling functionality.

        Returns:
            MediaTypeProcessor instance configured with this graph's config accessor
        """
        if self._media_type_processor is None:
            # Import here to avoid circular imports
            from ..data.media_type_processor import MediaTypeProcessor

            self._media_type_processor = MediaTypeProcessor(self._config_accessor)
        return self._media_type_processor

    def setup_figure(self) -> tuple[matplotlib.figure.Figure, Axes]:
        """
        Setup the matplotlib figure and axes.

        Returns:
            Tuple of (figure, axes)
        """
        # Create figure with specified dimensions
        self.figure, self.axes = plt.subplots(  # pyright: ignore[reportUnknownMemberType]
            figsize=(self.width, self.height),
            dpi=self.dpi,
            facecolor=self.background_color,
        )

        # Ensure axes is not None (it shouldn't be with our usage)
        if self.axes is None:  # pyright: ignore[reportUnnecessaryComparison]
            raise RuntimeError("Failed to create matplotlib axes")

        # Set axes background color
        self.axes.set_facecolor(self.background_color)

        return self.figure, self.axes

    def apply_seaborn_style(self) -> None:
        """
        Apply Seaborn styling based on configuration settings.

        This method sets up the Seaborn style context for the graph,
        including grid settings and overall aesthetic preferences.
        """
        import seaborn as sns

        # Apply modern styling
        apply_modern_seaborn_styling()

        # Set the default Seaborn style with enhanced appearance
        if self.get_grid_enabled():
            sns.set_style(
                "whitegrid",
                {
                    "axes.grid": True,
                    "axes.grid.axis": "y",
                    "grid.linewidth": 0.5,
                    "grid.alpha": 0.7,
                    "axes.edgecolor": "#333333",
                    "axes.linewidth": 1.2,
                },
            )
        else:
            sns.set_style("white")

        # Set color palette based on configuration
        if self.config is not None and self.get_media_type_separation_enabled():
            # Apply media type separation palette
            import seaborn as sns
            preferred_order = self.media_type_processor.get_preferred_order()
            custom_palette = [
                self.media_type_processor.get_color_for_type(media_type)
                for media_type in preferred_order
            ]
            sns.set_palette(custom_palette)  # pyright: ignore[reportUnknownMemberType]



    def get_user_configured_palette(self) -> str | None:
        """
        Get the user-configured palette for the current graph type.

        This method determines the specific palette configuration key for the current
        graph type and returns the palette value if configured.

        Returns:
            The palette name (e.g., 'viridis') if configured, None otherwise
        """
        if self.config is None:
            return None

        # Map graph class names to their corresponding palette configuration keys
        graph_type_to_palette_key = {
            "PlayCountByHourOfDayGraph": "PLAY_COUNT_BY_HOUROFDAY_PALETTE",
            "Top10UsersGraph": "TOP_10_USERS_PALETTE",
            "DailyPlayCountGraph": "DAILY_PLAY_COUNT_PALETTE",
            "PlayCountByDayOfWeekGraph": "PLAY_COUNT_BY_DAYOFWEEK_PALETTE",
            "Top10PlatformsGraph": "TOP_10_PLATFORMS_PALETTE",
            "PlayCountByMonthGraph": "PLAY_COUNT_BY_MONTH_PALETTE",
        }

        # Get the current graph's class name
        current_graph_class = self.__class__.__name__
        
        # Find the palette key for this specific graph type
        palette_key = graph_type_to_palette_key.get(current_graph_class)
        if palette_key is None:
            # No specific palette configuration for this graph type
            return None

        # Get the palette value for this specific graph
        palette_value = None
        if isinstance(self.config, dict):
            palette_value = self.config.get(palette_key)
        else:
            palette_value = getattr(self.config, palette_key, None)

        # Return the palette if it's configured with a non-empty string
        if (
            palette_value
            and isinstance(palette_value, str)
            and palette_value.strip()
        ):
            return palette_value.strip()
        
        return None


    def create_separated_legend(
        self, ax: "Axes", media_types_present: list[str]
    ) -> None:
        """
        Create a legend for separated media types.

        Args:
            ax: The matplotlib axes to add the legend to
            media_types_present: List of media types present in the data
        """
        import matplotlib.patches as mpatches

        # Create legend entries for present media types
        legend_handles: list[mpatches.Patch] = []
        legend_labels: list[str] = []

        for media_type in media_types_present:
            display_info = self.media_type_processor.get_display_info(media_type)
            patch = mpatches.Patch(
                color=display_info.color,
                label=display_info.display_name,
            )
            legend_handles.append(patch)
            legend_labels.append(display_info.display_name)

        if legend_handles:
            _ = ax.legend(  # pyright: ignore[reportUnknownMemberType]
                handles=legend_handles,
                labels=legend_labels,
                loc="best",
                frameon=True,
                fancybox=True,
                shadow=True,
                framealpha=0.9,
            )

    def get_grid_enabled(self) -> bool:
        """
        Get whether grid lines should be enabled for this graph.

        Returns:
            True if grid should be enabled, False otherwise
        """
        grid_enabled = self.get_config_value("ENABLE_GRAPH_GRID", False)
        return bool(grid_enabled)

    def get_media_type_separation_enabled(self) -> bool:
        """
        Get whether media type separation should be enabled for this graph.

        Returns:
            True if media type separation should be enabled, False otherwise
        """
        separation_enabled = self.get_config_value("ENABLE_MEDIA_TYPE_SEPARATION", True)
        return bool(separation_enabled)

    def get_stacked_bar_charts_enabled(self) -> bool:
        """
        Get whether stacked bar charts should be enabled when media type separation is active.

        Returns:
            True if stacked bar charts should be enabled, False otherwise
        """
        stacked_enabled = self.get_config_value("ENABLE_STACKED_BAR_CHARTS", False)
        return bool(stacked_enabled)

    def get_tv_color(self) -> str:
        """
        Get the color to use for TV shows in graphs.

        Returns:
            Hex color string for TV shows
        """
        return self.media_type_processor.get_color_for_type("tv")

    def get_movie_color(self) -> str:
        """
        Get the color to use for movies in graphs.

        Returns:
            Hex color string for movies
        """
        return self.media_type_processor.get_color_for_type("movie")

    def get_annotation_color(self) -> str:
        """
        Get the color to use for annotations in graphs.

        Returns:
            Hex color string for annotations
        """
        annotation_color = self.get_config_value("ANNOTATION_COLOR", "#ff0000")
        return str(annotation_color)

    def get_annotation_outline_color(self) -> str:
        """
        Get the outline color to use for annotations in graphs.

        Returns:
            Hex color string for annotation outlines
        """
        outline_color = self.get_config_value("ANNOTATION_OUTLINE_COLOR", "#000000")
        return str(outline_color)

    def is_annotation_outline_enabled(self) -> bool:
        """
        Get whether annotation outlines should be enabled.

        Returns:
            True if annotation outlines should be enabled, False otherwise
        """
        outline_enabled = self.get_config_value("ENABLE_ANNOTATION_OUTLINE", True)
        return bool(outline_enabled)

    def is_peak_annotations_enabled(self) -> bool:
        """
        Get whether peak annotations should be enabled.

        Returns:
            True if peak annotations should be enabled, False otherwise
        """
        peak_enabled = self.get_config_value("ENABLE_PEAK_ANNOTATIONS", True)
        return bool(peak_enabled)

    def get_peak_annotation_color(self) -> str:
        """
        Get the background color for peak annotation boxes.

        Returns:
            Hex color string for peak annotation background
        """
        peak_color = self.get_config_value("PEAK_ANNOTATION_COLOR", "#ffcc00")
        return str(peak_color)

    def get_peak_annotation_text_color(self) -> str:
        """
        Get the text color for peak annotations.

        Returns:
            Hex color string for peak annotation text
        """
        text_color = self.get_config_value("PEAK_ANNOTATION_TEXT_COLOR", "#000000")
        return str(text_color)

    def should_censor_usernames(self) -> bool:
        """
        Get whether usernames should be censored in this graph.

        Returns:
            True if usernames should be censored, False otherwise
        """
        censor_usernames = self.get_config_value("CENSOR_USERNAMES", True)
        return bool(censor_usernames)

    def get_annotation_font_size(self) -> int:
        """
        Get the font size to use for bar value annotations.

        Returns:
            Font size for annotations
        """
        font_size = self.get_config_value("ANNOTATION_FONT_SIZE", 10)
        if isinstance(font_size, (int, float)):
            return int(font_size)
        else:
            return 10  # Default fallback

    @abstractmethod
    def generate(self, data: Mapping[str, object]) -> str:
        """
        Generate the graph using the provided data.

        Args:
            data: Dictionary containing the data needed for the graph

        Returns:
            Path to the generated graph image file
        """
        pass

    @abstractmethod
    def get_title(self) -> str:
        """
        Get the title for this graph type.

        Returns:
            The graph title
        """
        pass

    def get_enhanced_title_with_timeframe(
        self, base_title: str, use_months: bool = False
    ) -> str:
        """
        Enhance a graph title with timeframe information from configuration.

        Args:
            base_title: The base title for the graph (e.g., "Daily Play Count")
            use_months: If True, use TIME_RANGE_MONTHS instead of TIME_RANGE_DAYS

        Returns:
            Enhanced title with timeframe information (e.g., "Daily Play Count (Last 30 days)")
        """
        if use_months:
            # Use TIME_RANGE_MONTHS for monthly graphs
            time_range = self.get_config_value("TIME_RANGE_MONTHS", 12)
            if isinstance(time_range, (int, float)):
                time_range_int = int(time_range)
                unit = "month" if time_range_int == 1 else "months"
                return f"{base_title} (Last {time_range_int} {unit})"
            else:
                return base_title
        else:
            # Use TIME_RANGE_DAYS for daily/weekly/hourly graphs
            time_range = self.get_config_value("TIME_RANGE_DAYS", 30)
            if isinstance(time_range, (int, float)):
                time_range_int = int(time_range)
                unit = "day" if time_range_int == 1 else "days"
                return f"{base_title} (Last {time_range_int} {unit})"
            else:
                return base_title

    def add_bar_value_annotation(
        self,
        ax: object,  # matplotlib.axes.Axes
        x: float,
        y: float,
        value: float | int,
        ha: str = "center",
        va: str = "bottom",
        offset_x: float = 0,
        offset_y: float = 0,
        fontsize: int | None = None,
        fontweight: str = "normal",
    ) -> None:
        """
        Add a value annotation to a bar or point with optional outline styling.

        Args:
            ax: The matplotlib axes to add annotation to
            x: X-coordinate for the annotation
            y: Y-coordinate for the annotation
            value: The value to display
            ha: Horizontal alignment ('left', 'center', 'right')
            va: Vertical alignment ('top', 'center', 'bottom')
            offset_x: Additional x offset from the position
            offset_y: Additional y offset from the position
            fontsize: Font size for the annotation (uses config default if None)
            fontweight: Font weight for the annotation
        """
        from matplotlib.axes import Axes

        if not isinstance(ax, Axes):
            return

        # Use config-based font size if not specified
        if fontsize is None:
            fontsize = self.get_annotation_font_size()

        # Format the value
        if isinstance(value, float):
            text = f"{value:.1f}" if value % 1 else f"{int(value)}"
        else:
            text = str(value)

        # Calculate actual position with offsets
        actual_x = x + offset_x
        actual_y = y + offset_y

        if self.is_annotation_outline_enabled():
            # Add text with white fill and black outline for better readability
            from matplotlib import patheffects

            _ = ax.text(  # pyright: ignore[reportUnknownMemberType]
                actual_x,
                actual_y,
                text,
                ha=ha,
                va=va,
                fontsize=fontsize,
                fontweight=fontweight,
                color="white",  # White text
                path_effects=[
                    patheffects.Stroke(
                        linewidth=3, foreground=self.get_annotation_outline_color()
                    ),
                    patheffects.Normal(),
                ],
            )
        else:
            # Add text without outline
            _ = ax.text(  # pyright: ignore[reportUnknownMemberType]
                actual_x,
                actual_y,
                text,
                ha=ha,
                va=va,
                fontsize=fontsize,
                fontweight=fontweight,
                color=self.get_annotation_color(),
            )

    def save_figure(
        self,
        output_path: str | None = None,
        graph_type: str | None = None,
        user_id: str | None = None,
    ) -> str:
        """
        Save the current figure to a file.

        Args:
            output_path: Path where to save the figure (optional, will be generated if not provided)
            graph_type: Type of graph for filename generation (required if output_path not provided)
            user_id: User ID for personal graphs (optional)

        Returns:
            The actual path where the figure was saved

        Raises:
            ValueError: If figure not initialized or invalid parameters
        """
        if self.figure is None:
            raise ValueError("Figure not initialized. Call setup_figure() first.")

        # Generate output path if not provided
        if output_path is None:
            if graph_type is None:
                raise ValueError("Either output_path or graph_type must be provided")

            # Use the new date-based directory structure
            graph_dir = get_current_graph_storage_path(user_email=user_id)
            filename = generate_graph_filename(graph_type, user_id=user_id)
            output_path = str(graph_dir / filename)
        else:
            # Ensure output directory exists for provided path
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Save with high quality settings
        self.figure.savefig(  # pyright: ignore[reportUnknownMemberType]
            output_path,
            dpi=self.dpi,
            bbox_inches="tight",
            facecolor=self.background_color,
            edgecolor="none",
            format="png",
        )

        logger.info(f"Saved graph to: {output_path}")
        return output_path

    def format_username(self, username: str, censor_enabled: bool = True) -> str:
        """
        Format a username for display, optionally censoring for privacy.

        Args:
            username: The username to format
            censor_enabled: Whether to censor the username for privacy

        Returns:
            Formatted username
        """
        return censor_username(username, censor_enabled)

    def cleanup(self) -> None:
        """
        Clean up matplotlib resources to prevent memory leaks.

        This method ensures proper cleanup of matplotlib figures and axes,
        preventing memory accumulation during repeated graph generation.
        """
        if self.figure is not None:
            try:
                # Close the specific figure to free memory
                plt.close(self.figure)  # pyright: ignore[reportUnknownMemberType]
                logger.debug(f"Closed matplotlib figure for {self.__class__.__name__}")
            except Exception as e:
                logger.warning(f"Error closing figure: {e}")
            finally:
                # Always reset references regardless of close success
                self.figure = None
                self.axes = None

        # Additional cleanup: clear any remaining matplotlib state
        try:
            # Force garbage collection of any remaining matplotlib objects
            # Use non-interactive cleanup methods that are thread-safe
            if hasattr(plt, "get_fignums") and plt.get_fignums():
                # Close all figures instead of clearing current figure
                plt.close("all")  # pyright: ignore[reportUnknownMemberType]
        except Exception as e:
            logger.debug(f"Minor cleanup warning: {e}")

    @classmethod
    def cleanup_all_figures(cls) -> None:
        """
        Clean up all matplotlib figures to prevent memory leaks.

        This is a utility method for bulk cleanup operations,
        useful when generating multiple graphs in sequence.
        """
        try:
            plt.close("all")  # pyright: ignore[reportUnknownMemberType]
            logger.debug("Closed all matplotlib figures")
        except Exception as e:
            logger.warning(f"Error during bulk figure cleanup: {e}")

    def __enter__(self) -> "BaseGraph":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit with cleanup."""
        self.cleanup()

    def extract_and_validate_play_history_data(
        self, data: Mapping[str, object]
    ) -> Mapping[str, object]:
        """
        Extract and validate play history data from the input data structure.

        This method implements the common pattern found across all Tautulli graph classes
        for extracting and validating play_history data from the API response.

        Args:
            data: Dictionary containing the full data structure from Tautulli API

        Returns:
            Validated play history data mapping

        Raises:
            ValueError: If data is invalid or missing required fields
        """
        from typing import cast

        # Extract play history data from the full data structure
        play_history_data_raw = data.get("play_history", {})
        if not isinstance(play_history_data_raw, dict):
            raise ValueError("Missing or invalid 'play_history' data in input")

        # Cast to the proper type for type checker
        play_history_data = cast(Mapping[str, object], play_history_data_raw)

        # Validate the play history data
        is_valid, error_msg = validate_graph_data(play_history_data, ["data"])
        if not is_valid:
            raise ValueError(f"Invalid play history data: {error_msg}")

        return play_history_data

    def process_play_history_safely(
        self, play_history_data: Mapping[str, object]
    ) -> ProcessedRecords:
        """
        Process play history data with error handling.

        This method implements the common pattern found across all Tautulli graph classes
        for processing play history data with graceful error handling.

        Args:
            play_history_data: Validated play history data mapping

        Returns:
            List of processed play history records, empty list if processing fails
        """
        try:
            processed_records = process_play_history_data(play_history_data)
            logger.info(f"Processed {len(processed_records)} play history records")
            return processed_records
        except Exception as e:
            logger.error(f"Error processing play history data: {e}")
            # Return empty list for graceful degradation
            return []

    def setup_figure_with_styling(self) -> tuple[matplotlib.figure.Figure, Axes]:
        """
        Setup figure and apply common styling patterns.

        This method combines the common sequence of setup_figure() and apply_seaborn_style()
        calls found across all graph classes.

        Returns:
            Tuple of (figure, axes) ready for plotting
        """
        # Setup figure and axes
        figure, axes = self.setup_figure()

        # Apply modern Seaborn styling
        self.apply_seaborn_style()

        return figure, axes

    def finalize_and_save_figure(
        self, graph_type: str, user_id: str | None = None
    ) -> str:
        """
        Finalize figure layout and save with cleanup.

        This method implements the common pattern found across all graph classes
        for finalizing the figure layout, saving, and cleanup.

        Args:
            graph_type: Type of graph for filename generation
            user_id: User ID for personal graphs (optional)

        Returns:
            Path to the saved graph file

        Raises:
            ValueError: If figure is not initialized
        """
        # Improve layout
        if self.figure is not None:
            self.figure.tight_layout()

        # Save the figure using base class utility method
        output_path = self.save_figure(graph_type=graph_type, user_id=user_id)

        logger.info(f"Graph saved to: {output_path}")
        return output_path

    def get_time_range_days_from_config(self) -> int:
        """
        Extract the TIME_RANGE_DAYS value from the graph's configuration.

        This method implements the common pattern found across all graph classes
        for extracting the time range configuration.

        Returns:
            Number of days for the time range from config, defaults to 30 if not found
        """
        time_range = self.get_config_value("TIME_RANGE_DAYS", 30)

        if isinstance(time_range, (int, float)):
            return int(time_range)
        else:
            logger.warning(
                f"Invalid TIME_RANGE_DAYS value: {time_range}, using default 30"
            )
            return 30

    def get_time_range_months_from_config(self) -> int:
        """
        Extract the TIME_RANGE_MONTHS value from the graph's configuration.

        This method implements the common pattern found across some graph classes
        for extracting the monthly time range configuration.

        Returns:
            Number of months for the time range from config, defaults to 12 if not found
        """
        time_range = self.get_config_value("TIME_RANGE_MONTHS", 12)

        if isinstance(time_range, (int, float)):
            return int(time_range)
        else:
            logger.warning(
                f"Invalid TIME_RANGE_MONTHS value: {time_range}, using default 12"
            )
            return 12

    def handle_empty_data_with_message(
        self, ax: Axes, message: str = "No data available for the selected time range."
    ) -> None:
        """
        Handle empty data case with standardized message display.

        This method implements the common pattern found across graph classes
        for handling empty data scenarios with user-friendly messages.

        Args:
            ax: The matplotlib axes to display the message on
            message: Message to display to the user
        """
        # Clear any existing content
        ax.clear()

        # Display the message
        _ = ax.text(  # pyright: ignore[reportUnknownMemberType]
            0.5,
            0.5,
            message,
            horizontalalignment="center",
            verticalalignment="center",
            transform=ax.transAxes,
            fontsize=14,
            fontweight="bold",
        )

        # Remove axes decorations
        ax.set_xticks([])  # pyright: ignore[reportAny] # matplotlib method returns Any
        ax.set_yticks([])  # pyright: ignore[reportAny] # matplotlib method returns Any
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)

        # Set a simple title
        _ = ax.set_title(self.get_title(), fontsize=16, fontweight="bold", pad=20)  # pyright: ignore[reportUnknownMemberType]
