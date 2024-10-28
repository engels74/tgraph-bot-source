# graphs/graph_modules/base_graph.py

from abc import ABC, abstractmethod
import matplotlib.pyplot as plt
from matplotlib import patheffects
from typing import Dict, Any
import logging

class BaseGraph(ABC):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        self.config = config
        self.translations = translations
        self.img_folder = img_folder
        self.plt = plt
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

    def setup_plot(self, figsize: tuple = (14, 8)):
        """
        Set up the plot with the given figure size.
        
        :param figsize: A tuple containing the width and height of the figure
        """
        self.figure, self.ax = plt.subplots(figsize=figsize)
        # Set font properties for all text elements
        plt.rcParams['font.weight'] = 'normal'
        plt.rcParams['axes.titleweight'] = 'bold'
        plt.rcParams['axes.labelweight'] = 'bold'

    def add_title(self, title: str):
        """
        Add a title to the graph.
        
        :param title: The title of the graph
        """
        self.ax.set_title(title, fontweight="bold", pad=20)

    def add_labels(self, xlabel: str, ylabel: str):
        """
        Add labels to the x and y axes.
        
        :param xlabel: The label for the x-axis
        :param ylabel: The label for the y-axis
        """
        self.ax.set_xlabel(xlabel, fontweight="bold", labelpad=10)
        self.ax.set_ylabel(ylabel, fontweight="bold", labelpad=10)

    def add_legend(self):
        """
        Add a legend to the graph.
        """
        self.ax.legend()

    def apply_tight_layout(self, pad: float = 3.0):
        """
        Apply tight layout to the plot.
        
        :param pad: The padding around the plot
        """
        self.plt.tight_layout(pad=pad)

    def save(self, filepath: str):
        """
        Save the graph to a file.
        
        :param filepath: The path where the graph should be saved
        """
        try:
            self.plt.savefig(filepath)
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
        The appearance is controlled by ANNOTATION_COLOR, ENABLE_ANNOTATION_OUTLINE,
        and ANNOTATION_OUTLINE_COLOR in the configuration.
        
        :param x: The x-coordinate of the annotation
        :param y: The y-coordinate of the annotation
        :param text: The text of the annotation
        """
        # Get annotation color (defaults to white)
        text_color = self.config["ANNOTATION_COLOR"].strip('"')

        # Create the annotation with default settings
        annotation_params = {
            "text": text,
            "xy": (x, y),
            "xytext": (0, 5),
            "textcoords": "offset points",
            "ha": "center",
            "va": "bottom",
            "fontsize": 8,
            "color": text_color,
            "weight": 'bold'  # Always use bold for better visibility
        }

        # Add outline effects if enabled
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
