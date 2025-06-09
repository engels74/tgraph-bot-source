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
from typing import Any, Optional

import matplotlib.pyplot as plt
import matplotlib.figure

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
        """
        self.width = width
        self.height = height
        self.dpi = dpi
        self.background_color = background_color
        self.figure: Optional[matplotlib.figure.Figure] = None
        self.axes: Optional[plt.Axes] = None
        
    def setup_figure(self) -> tuple[matplotlib.figure.Figure, plt.Axes]:
        """
        Setup the matplotlib figure and axes.
        
        Returns:
            Tuple of (figure, axes)
        """
        # Create figure with specified dimensions
        self.figure, self.axes = plt.subplots(
            figsize=(self.width, self.height),
            dpi=self.dpi,
            facecolor=self.background_color
        )
        
        # Set axes background color
        if self.axes is not None:
            self.axes.set_facecolor(self.background_color)
        
        return self.figure, self.axes
        
    @abstractmethod
    def generate(self, data: dict[str, Any]) -> str:
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
        
    def save_figure(self, output_path: str) -> str:
        """
        Save the current figure to a file.
        
        Args:
            output_path: Path where to save the figure
            
        Returns:
            The actual path where the figure was saved
        """
        if self.figure is None:
            raise ValueError("Figure not initialized. Call setup_figure() first.")
            
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save with high quality settings
        self.figure.savefig(
            output_path,
            dpi=self.dpi,
            bbox_inches='tight',
            facecolor=self.background_color,
            edgecolor='none',
            format='png'
        )
        
        logger.info(f"Saved graph to: {output_path}")
        return output_path
        
    def cleanup(self) -> None:
        """Clean up matplotlib resources."""
        if self.figure is not None:
            plt.close(self.figure)
            self.figure = None
            self.axes = None
            
    def __enter__(self) -> "BaseGraph":
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit with cleanup."""
        self.cleanup()
