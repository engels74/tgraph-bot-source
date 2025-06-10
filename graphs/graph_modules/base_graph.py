"""
Base graph class for TGraph Bot.

This module defines the abstract base class for all graph types.
It uses Matplotlib to handle the core figure and axes setup (e.g., size,
background color, titles), providing a canvas for the high-level Seaborn
library to draw onto.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from types import TracebackType

import matplotlib.pyplot as plt
import matplotlib.figure
from matplotlib.axes import Axes

from .utils import (
    ensure_graph_directory,
    generate_graph_filename,
    validate_color,
    censor_username,
)

logger = logging.getLogger(__name__)


class BaseGraph(ABC):
    """Abstract base class defining the common interface for all graph types."""
    
    def __init__(
        self,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str = "#ffffff"
    ) -> None:
        """
        Initialize the base graph.

        Args:
            width: Figure width in inches
            height: Figure height in inches
            dpi: Dots per inch for the figure
            background_color: Background color for the graph

        Raises:
            ValueError: If background_color is not a valid color format
        """
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

        # Set axes background color
        self.axes.set_facecolor(self.background_color)
        
        return self.figure, self.axes
        
    @abstractmethod
    def generate(self, data: dict[str, object]) -> str:
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
        """Clean up matplotlib resources."""
        if self.figure is not None:
            plt.close(self.figure)
            self.figure = None
            self.axes = None
            
    def __enter__(self) -> "BaseGraph":
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        """Context manager exit with cleanup."""
        self.cleanup()
