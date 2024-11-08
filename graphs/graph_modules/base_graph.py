# graphs/graph_modules/base_graph.py
"""
Improved base graph class with better error handling, type hints, and documentation.
"""

from abc import ABC, abstractmethod
import matplotlib.pyplot as plt
from matplotlib import patheffects
import matplotlib.figure
import matplotlib.axes
from typing import Dict, Any, Tuple, Optional, Union
import logging

class BaseGraphError(Exception):
    """Base exception class for graph-related errors."""
    pass

class PlottingError(BaseGraphError):
    """Raised when there's an error during plot operations."""
    pass

class BaseGraph(ABC):
    """Abstract base class for all graph types."""

    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        """
        Initialize the base graph.

        Args:
            config: Configuration dictionary
            translations: Translation strings dictionary
            img_folder: Path to image output folder

        Raises:
            ValueError: If required configuration or translation keys are missing
        """
        self._validate_init_params(config, translations, img_folder)
        self.config = config
        self.translations = translations
        self.img_folder = img_folder
        self.figure: Optional[matplotlib.figure.Figure] = None
        self.ax: Optional[matplotlib.axes.Axes] = None
        self._stored_data: Optional[Dict[str, Any]] = None

    def _validate_init_params(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str) -> None:
        """
        Validate initialization parameters.

        Args:
            config: Configuration dictionary
            translations: Translation strings dictionary
            img_folder: Path to image output folder

        Raises:
            ValueError: If any required parameters are invalid
        """
        if not isinstance(config, dict):
            raise ValueError("Config must be a dictionary")
        if not isinstance(translations, dict):
            raise ValueError("Translations must be a dictionary")
        if not isinstance(img_folder, str) or not img_folder.strip():
            raise ValueError("Image folder path must be a non-empty string")

        # Check for required configuration keys
        required_config_keys = {"TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR", "ANNOTATION_OUTLINE_COLOR"}
        missing_keys = required_config_keys - set(config.keys())
        if missing_keys:
            raise ValueError(f"Missing required configuration keys: {missing_keys}")

    @property
    def data(self) -> Optional[Dict[str, Any]]:
        """Get the stored graph data."""
        return self._stored_data

    @data.setter
    def data(self, value: Optional[Dict[str, Any]]) -> None:
        """
        Set the graph data.

        Args:
            value: The data to store for graph generation
        """
        self._stored_data = value

    @abstractmethod
    async def fetch_data(self, data_fetcher: Any, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch the required data for the graph.

        Args:
            data_fetcher: The data fetcher object to use
            user_id: Optional user ID for user-specific graphs

        Returns:
            A dictionary containing the fetched data, or None if fetching fails
        """
        pass

    @abstractmethod
    def process_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process the fetched data into a format suitable for plotting.

        Args:
            data: The raw data fetched from the API

        Returns:
            A dictionary containing the processed data, or None if processing fails
        """
        pass

    @abstractmethod
    def plot(self, processed_data: Dict[str, Any]) -> None:
        """
        Plot the graph using the processed data.

        Args:
            processed_data: The processed data ready for plotting

        Raises:
            PlottingError: If there's an error during plotting
        """
        pass

    def setup_plot(self, figsize: Tuple[int, int] = (14, 8)) -> None:
        """
        Set up the plot with the given figure size.

        Args:
            figsize: A tuple containing the width and height of the figure

        Raises:
            PlottingError: If plot setup fails
        """
        try:
            plt.style.use('default')  # Ensure consistent style
            self.figure, self.ax = plt.subplots(figsize=figsize)

            if not self.ax:
                raise PlottingError("Failed to create plot axes")

            # Set tick label properties
            self.ax.tick_params(
                axis='both',
                which='major',
                labelsize=10,
                width=1
            )

            # Set background color and grid
            self.ax.set_facecolor('white')
            self.ax.grid(True, linestyle='--', alpha=0.7)

        except Exception as e:
            raise PlottingError(f"Error setting up plot: {str(e)}") from e

    def add_title(self, title: str) -> None:
        """
        Add a title to the graph.

        Args:
            title: The title of the graph

        Raises:
            PlottingError: If adding title fails
        """
        if not self.ax:
            raise PlottingError("Plot axes not initialized")

        try:
            self.ax.set_title(
                title,
                fontdict={'weight': 'bold', 'size': 12},
                pad=20
            )
        except Exception as e:
            raise PlottingError(f"Error adding title: {str(e)}") from e

    def add_labels(self, xlabel: str, ylabel: str) -> None:
        """
        Add labels to the x and y axes.

        Args:
            xlabel: The label for the x-axis
            ylabel: The label for the y-axis

        Raises:
            PlottingError: If adding labels fails
        """
        if not self.ax:
            raise PlottingError("Plot axes not initialized")

        try:
            self.ax.set_xlabel(
                xlabel,
                fontdict={'weight': 'bold'},
                labelpad=10
            )
            self.ax.set_ylabel(
                ylabel,
                fontdict={'weight': 'bold'},
                labelpad=10
            )
        except Exception as e:
            raise PlottingError(f"Error adding axis labels: {str(e)}") from e

    def add_legend(self, **kwargs) -> None:
        """
        Add a legend to the graph with consistent styling.

        Args:
            **kwargs: Additional keyword arguments for legend customization

        Raises:
            PlottingError: If adding legend fails
        """
        if not self.ax:
            raise PlottingError("Plot axes not initialized")

        try:
            legend = self.ax.legend(**kwargs)
            if legend:
                for text in legend.get_texts():
                    text.set_weight('normal')
            else:
                logging.warning("Legend not added; legend object is None")
        except Exception as e:
            raise PlottingError(f"Error adding legend: {str(e)}") from e

    def apply_tight_layout(self, pad: float = 3.0) -> None:
        """
        Apply tight layout to the plot.

        Args:
            pad: The padding around the plot

        Raises:
            PlottingError: If applying tight layout fails
        """
        if not self.figure:
            raise PlottingError("Figure not initialized")

        try:
            self.figure.tight_layout(pad=pad)
        except Exception as e:
            raise PlottingError(f"Error applying tight layout: {str(e)}") from e

    def save(self, filepath: str) -> None:
        """
        Save the graph to a file.

        Args:
            filepath: The path where the graph should be saved

        Raises:
            PlottingError: If saving fails
        """
        if not self.figure:
            raise PlottingError("Figure not initialized")

        try:
            self.figure.savefig(filepath, dpi=300, bbox_inches='tight')
            logging.info(f"Graph saved successfully: {filepath}")
        except Exception as e:
            raise PlottingError(f"Error saving graph to {filepath}: {str(e)}") from e
        finally:
            plt.close(self.figure)

    def get_color(self, series_name: str) -> str:
        """
        Get the color for a given series.

        Args:
            series_name: The media type (e.g., 'TV' or 'Movies')

        Returns:
            The color code for the series

        Raises:
            ValueError: If color is not defined in configuration
        """
        series_name = series_name.upper()
        color_map = {
            "TV": "TV_COLOR",
            "MOVIES": "MOVIE_COLOR"
        }

        if series_name not in color_map:
            raise ValueError(f"Color for series '{series_name}' not defined")

        color_key = color_map[series_name]
        color = self.config.get(color_key)

        if not color:
            raise ValueError(f"Color '{color_key}' not found in configuration")

        return color.strip('"\'')

    def annotate(self, x: Union[int, float], y: Union[int, float], text: str) -> None:
        """
        Add an annotation to the graph with configurable color and outline.

        Args:
            x: The x-coordinate of the annotation
            y: The y-coordinate of the annotation
            text: The text of the annotation

        Raises:
            PlottingError: If annotation fails
        """
        if not self.ax:
            raise PlottingError("Plot axes not initialized")

        try:
            annotation_params = {
                "text": text,
                "xy": (x, y),
                "xytext": (0, 5),
                "textcoords": "offset points",
                "ha": "center",
                "va": "bottom",
                "fontsize": 10,
                "color": self.config["ANNOTATION_COLOR"],
                "weight": 'bold'
            }

            if self.config.get("ENABLE_ANNOTATION_OUTLINE", True):
                annotation_params["path_effects"] = [
                    patheffects.Stroke(
                        linewidth=1,
                        foreground=self.config["ANNOTATION_OUTLINE_COLOR"]
                    ),
                    patheffects.Normal()
                ]

            self.ax.annotate(**annotation_params)
        except Exception as e:
            raise PlottingError(f"Error adding annotation: {str(e)}") from e

    @abstractmethod
    async def generate(self, data_fetcher: Any, user_id: Optional[str] = None) -> Optional[str]:
        """
        Generate the graph and return the filepath.
        If self.data is set, use that instead of fetching new data.

        Args:
            data_fetcher: The data fetcher object to use
            user_id: Optional user ID for user-specific graphs

        Returns:
            The filepath of the generated graph, or None if generation fails
        """
        pass
