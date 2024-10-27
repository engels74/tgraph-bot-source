# graphs/graph_modules/base_graph.py

from abc import ABC, abstractmethod
import matplotlib.pyplot as plt
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
        Get the color for a given series name.
        
        :param series_name: The name of the series
        :return: The color code for the series
        """
        if series_name == "TV":
            return self.config["TV_COLOR"].strip('"')
        elif series_name == "Movies":
            return self.config["MOVIE_COLOR"].strip('"')
        else:
            return "#1f77b4"  # Default color

    def annotate(self, x, y, text, color: str = None):
        """
        Add an annotation to the graph.
        
        :param x: The x-coordinate of the annotation
        :param y: The y-coordinate of the annotation
        :param text: The text of the annotation
        :param color: The color of the annotation text
        """
        if color is None:
            color = self.config["ANNOTATION_COLOR"].strip('"')
        self.ax.annotate(text, (x, y), xytext=(0, 5), textcoords="offset points",
                         ha="center", va="bottom", fontsize=8, color=color)

    @abstractmethod
    def generate(self, data_fetcher, user_id: str = None) -> str:
        """
        Generate the graph and return the filepath.
        
        :param data_fetcher: The data fetcher object to use
        :param user_id: Optional user ID for user-specific graphs
        :return: The filepath of the generated graph
        """
        pass
