# graphs/graph_modules/base_graph.py

from abc import ABC, abstractmethod
import matplotlib.pyplot as plt
from matplotlib import patheffects
from typing import Dict, Any, Tuple
import logging

class BaseGraph(ABC):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        self.config = config
        self.translations = translations
        self.img_folder = img_folder
        self.figure = None
        self.ax = None

    @abstractmethod
    def fetch_data(self, data_fetcher, user_id: str = None) -> Dict[str, Any]:
        """
        Fetch the required data for the graph.
        
        :param data_fetcher: The data fetcher object to use
        :param user_id: Optional user ID for user-specific graphs
        :return: A dictionary containing the fetched data
        """
        pass

    @abstractmethod
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the fetched data into a format suitable for plotting.
        
        :param data: The raw data fetched from the API
        :return: A dictionary containing the processed data
        """
        pass

    @abstractmethod
    def plot(self, processed_data: Dict[str, Any]):
        """
        Plot the graph using the processed data.
        
        :param processed_data: The processed data ready for plotting
        """
        pass

    def setup_plot(self, figsize: Tuple[int, int] = (14, 8)):
        """
        Set up the plot with the given figure size.
        
        :param figsize: A tuple containing the width and height of the figure
        """
        # Create a new figure with specified size
        self.figure, self.ax = plt.subplots(figsize=figsize)
        
        # Configure the axes with explicit font properties
        self.ax.set_title(
            self.ax.get_title(),
            fontdict={'weight': 'bold'},
            pad=20
        )
        
        # Set x and y label properties explicitly
        self.ax.xaxis.label.set_weight('bold')
        self.ax.yaxis.label.set_weight('bold')
        
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
        
        :param title: The title of the graph
        """
        self.ax.set_title(
            title,
            fontdict={'weight': 'bold'},
            pad=20
        )

    def add_labels(self, xlabel: str, ylabel: str):
        """
        Add labels to the x and y axes.
        
        :param xlabel: The label for the x-axis
        :param ylabel: The label for the y-axis
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
        
        :param kwargs: Additional keyword arguments for legend customization
        """
        legend = self.ax.legend(**kwargs)
        # Apply consistent font weight to legend text
        for text in legend.get_texts():
            text.set_weight('normal')

    def apply_tight_layout(self, pad: float = 3.0):
        """
        Apply tight layout to the plot.
        
        :param pad: The padding around the plot
        """
        self.figure.tight_layout(pad=pad)

    def save(self, filepath: str):
        """
        Save the graph to a file.
        
        :param filepath: The path where the graph should be saved
        """
        try:
            self.figure.savefig(filepath)
            logging.info(f"Graph saved successfully: {filepath}")
        except Exception as e:
            logging.error(f"Error saving graph to {filepath}: {str(e)}")
        finally:
            plt.close(self.figure)

    def get_color(self, series_name: str) -> str:
        """
        Get the color for TV shows or Movies.
        
        :param series_name: The media type ('TV' or 'Movies')
        :return: The color code for the series
        :raises ValueError: If series_name is not 'TV' or 'Movies'
        """
        if series_name == "TV":
            return self.config["TV_COLOR"].strip('"')
        elif series_name == "Movies":
            return self.config["MOVIE_COLOR"].strip('"')
        raise ValueError(f"Invalid series name: {series_name}. Must be 'TV' or 'Movies'")

    def annotate(self, x, y, text):
        """
        Add an annotation to the graph with configurable color and outline.
        
        :param x: The x-coordinate of the annotation
        :param y: The y-coordinate of the annotation
        :param text: The text of the annotation
        """
        text_color = self.config["ANNOTATION_COLOR"].strip('"')
        
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
            outline_color = self.config["ANNOTATION_OUTLINE_COLOR"].strip('"')
            annotation_params["path_effects"] = [
                patheffects.Stroke(linewidth=1, foreground=outline_color),
                patheffects.Normal()
            ]

        self.ax.annotate(**annotation_params)

    @abstractmethod
    def generate(self, data_fetcher, user_id: str = None) -> str:
        """
        Generate the graph and return the filepath.
        
        :param data_fetcher: The data fetcher object to use
        :param user_id: Optional user ID for user-specific graphs
        :return: The filepath of the generated graph
        """
        pass
