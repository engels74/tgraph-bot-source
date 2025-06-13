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

import matplotlib.pyplot as plt
import matplotlib.figure
from matplotlib.axes import Axes

from .utils import (
    ensure_graph_directory,
    generate_graph_filename,
    validate_color,
    censor_username,
)

if TYPE_CHECKING:
    from config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class BaseGraph(ABC):
    """Abstract base class defining the common interface for all graph types."""

    def __init__(
        self,
        config: "TGraphBotConfig | None" = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str | None = None
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
        self.config: "TGraphBotConfig | None" = config

        # Use background color from config if not explicitly provided
        if background_color is None and config is not None:
            # Handle both TGraphBotConfig objects and dict configs for backward compatibility
            if hasattr(config, 'GRAPH_BACKGROUND_COLOR'):
                background_color = str(config.GRAPH_BACKGROUND_COLOR)
            elif isinstance(config, dict) and 'GRAPH_BACKGROUND_COLOR' in config:
                bg_color = config.get('GRAPH_BACKGROUND_COLOR')  # pyright: ignore[reportUnknownMemberType]
                background_color = str(bg_color) if bg_color is not None else "#ffffff"  # pyright: ignore[reportUnknownArgumentType]
            else:
                background_color = "#ffffff"
        elif background_color is None:
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
            facecolor=self.background_color
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

        # Set the default Seaborn style
        sns.set_style("whitegrid" if self.get_grid_enabled() else "white")

        # Set color palette if available
        if self.config is not None and hasattr(self.config, 'TV_COLOR'):
            # Create a custom palette using TV and Movie colors
            custom_palette = [self.config.TV_COLOR, self.config.MOVIE_COLOR]
            sns.set_palette(custom_palette)

    def get_grid_enabled(self) -> bool:
        """
        Get whether grid lines should be enabled for this graph.

        Returns:
            True if grid should be enabled, False otherwise
        """
        if self.config is not None:
            # Handle both TGraphBotConfig objects and dict configs for backward compatibility
            if hasattr(self.config, 'ENABLE_GRAPH_GRID'):
                return bool(self.config.ENABLE_GRAPH_GRID)
            elif isinstance(self.config, dict) and 'ENABLE_GRAPH_GRID' in self.config:
                return bool(self.config.get('ENABLE_GRAPH_GRID', False))  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
        return False

    def get_tv_color(self) -> str:
        """
        Get the color to use for TV shows in graphs.

        Returns:
            Hex color string for TV shows
        """
        if self.config is not None:
            return self.config.TV_COLOR
        return "#1f77b4"  # Default blue

    def get_movie_color(self) -> str:
        """
        Get the color to use for movies in graphs.

        Returns:
            Hex color string for movies
        """
        if self.config is not None:
            return self.config.MOVIE_COLOR
        return "#ff7f0e"  # Default orange

    def get_annotation_color(self) -> str:
        """
        Get the color to use for annotations in graphs.

        Returns:
            Hex color string for annotations
        """
        if self.config is not None:
            return self.config.ANNOTATION_COLOR
        return "#ff0000"  # Default red

    def get_annotation_outline_color(self) -> str:
        """
        Get the outline color to use for annotations in graphs.

        Returns:
            Hex color string for annotation outlines
        """
        if self.config is not None:
            return self.config.ANNOTATION_OUTLINE_COLOR
        return "#000000"  # Default black

    def is_annotation_outline_enabled(self) -> bool:
        """
        Get whether annotation outlines should be enabled.

        Returns:
            True if annotation outlines should be enabled, False otherwise
        """
        if self.config is not None:
            return self.config.ENABLE_ANNOTATION_OUTLINE
        return True  # Default enabled

    def should_censor_usernames(self) -> bool:
        """
        Get whether usernames should be censored in this graph.

        Returns:
            True if usernames should be censored, False otherwise
        """
        if self.config is not None:
            return self.config.CENSOR_USERNAMES
        return True  # Default to censoring for privacy

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
        
    def save_figure(self, output_path: str | None = None, graph_type: str | None = None, user_id: str | None = None) -> str:
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

            # Use utility function to ensure graph directory exists
            graph_dir = ensure_graph_directory()
            filename = generate_graph_filename(graph_type, user_id=user_id)
            output_path = str(graph_dir / filename)
        else:
            # Ensure output directory exists for provided path
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Save with high quality settings
        self.figure.savefig(  # pyright: ignore[reportUnknownMemberType]
            output_path,
            dpi=self.dpi,
            bbox_inches='tight',
            facecolor=self.background_color,
            edgecolor='none',
            format='png'
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
                plt.close(self.figure)
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
            plt.clf()  # Clear current figure
            plt.cla()  # Clear current axes
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
            plt.close('all')
            logger.debug("Closed all matplotlib figures")
        except Exception as e:
            logger.warning(f"Error during bulk figure cleanup: {e}")
            
    def __enter__(self) -> "BaseGraph":
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        """Context manager exit with cleanup."""
        self.cleanup()
