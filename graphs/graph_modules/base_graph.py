# graphs/graph_modules/base_graph.py

from abc import ABC, abstractmethod
import matplotlib.pyplot as plt
from matplotlib import patheffects
from typing import Dict, Any, Tuple, Optional
import logging

class BaseGraph(ABC):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        self.config = config
        self.translations = translations
        self.img_folder = img_folder
        self.figure = None
        self.ax = None
        self._stored_data: Optional[Dict[str, Any]] = None  # Add storage for graph data

    @property
    def data(self) -> Optional[Dict[str, Any]]:
        """Get the stored graph data."""
        return self._stored_data

    @data.setter
    def data(self, value: Optional[Dict[str, Any]]):
        """Set the graph data.
        
        Args:
            value: The data to store for graph generation
        """
        self._stored_data = value

    @abstractmethod
    def fetch_data(self, data_fetcher, user_id: str = None) -> Dict[str, Any]:
        """
        Fetch the required data for the graph.
        
        Args:
            data_fetcher: The data fetcher object to use
            user_id: Optional user ID for user-specific graphs
            
        Returns:
            A dictionary containing the fetched data
        """
        pass

    @abstractmethod
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the fetched data into a format suitable for plotting.
        
        Args:
            data: The raw data fetched from the API
            
        Returns:
            A dictionary containing the processed data
        """
        pass

    @abstractmethod
    def plot(self, processed_data: Dict[str, Any]):
        """
        Plot the graph using the processed data.
        
        Args:
            processed_data: The processed data ready for plotting
        """
        pass

    def setup_plot(self, figsize: Tuple[int, int] = (14, 8)):
        """
        Set up the plot with the given figure size.
        
        Args:
            figsize: A tuple containing the width and height of the figure
        """
        # Create a new figure with specified size
        self.figure, self.ax = plt.subplots(figsize=figsize)
        
        # Set tick label properties
        self.ax.tick_params(
            axis='both',
            which='major',
            labelsize=10,
            width=1
        )

    def add_title(self, title: str):
        """
        Add a title to the graph.
        
        Args:
            title: The title of the graph
        """
        self.ax.set_title(
            title,
            fontdict={'weight': 'bold'},
            pad=20
        )

    def add_labels(self, xlabel: str, ylabel: str):
        """
        Add labels to the x and y axes.
        
        Args:
            xlabel: The label for the x-axis
            ylabel: The label for the y-axis
        """
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

    def add_legend(self, **kwargs):
        """
        Add a legend to the graph with consistent styling.
        
        Args:
            kwargs: Additional keyword arguments for legend customization
        """
        legend = self.ax.legend(**kwargs)
        # Apply consistent font weight to legend text
        for text in legend.get_texts():
            text.set_weight('normal')

    def apply_tight_layout(self, pad: float = 3.0):
        """
        Apply tight layout to the plot.
        
        Args:
            pad: The padding around the plot
        """
        self.figure.tight_layout(pad=pad)

    def save(self, filepath: str):
        """
        Save the graph to a file.
        
        Args:
            filepath: The path where the graph should be saved
        """
        if self.figure is None:
            logging.error("Figure is not initialized. Cannot save the graph.")
            return
        try:
            self.figure.savefig(filepath)
            logging.info(f"Graph saved successfully: {filepath}")
        except Exception as e:
            logging.error(f"Error saving graph to {filepath}: {str(e)}")
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
        # Handle case variations
        if series_name.upper() == "TV":
            color_key = "TV_COLOR"
        elif series_name.upper() == "MOVIES":
            color_key = "MOVIE_COLOR"
        else:
            raise ValueError(f"Color for series '{series_name}' not defined in configuration")

        color = self.config.get(color_key)
        if not color:
            raise ValueError(f"Color '{color_key}' not found in configuration")
            
        return color.strip('"\'')  # Remove any quotes from the color value

    def annotate(self, x, y, text):
        """
        Add an annotation to the graph with configurable color and outline.
        
        Args:
            x: The x-coordinate of the annotation
            y: The y-coordinate of the annotation
            text: The text of the annotation
        """
        text_color = self.config["ANNOTATION_COLOR"]
        
        annotation_params = {
            "text": text,
            "xy": (x, y),
            "xytext": (0, 5),
            "textcoords": "offset points",
            "ha": "center",
            "va": "bottom",
            "fontsize": 10,
            "color": text_color,
            "weight": 'bold'
        }

        if self.config["ENABLE_ANNOTATION_OUTLINE"]:
            outline_color = self.config["ANNOTATION_OUTLINE_COLOR"]
            annotation_params["path_effects"] = [
                patheffects.Stroke(linewidth=1, foreground=outline_color),
                patheffects.Normal()
            ]

        self.ax.annotate(**annotation_params)

    @abstractmethod
    async def generate(self, data_fetcher, user_id: str = None) -> Optional[str]:
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
