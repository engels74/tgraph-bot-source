# graphs/graph_modules/top_10_platforms_graph.py

from .base_graph import BaseGraph
from .utils import get_color
from typing import Dict, Any
import logging
import os
from datetime import datetime
from matplotlib.ticker import MaxNLocator

class Top10PlatformsGraph(BaseGraph):
    """
    A graph representing the top 10 platforms by play count.

    This class generates a graph showing the top 10 platforms with the highest play counts.

    Attributes:
        config (Dict[str, Any]): Configuration parameters for the graph.
        translations (Dict[str, str]): Translation strings for labels.
        img_folder (str): Path to save generated images.
    """
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        """
        Initialize the Top10PlatformsGraph with configuration, translations, and image folder path.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
            translations (Dict[str, str]): Dictionary with translation mappings.
            img_folder (str): Path for storing generated images.
        """
        super().__init__(config, translations, img_folder)
        self.graph_type = "top_10_platforms"

        """
        Asynchronously fetch the data required for the top 10 platforms graph.

        Args:
            data_fetcher (Callable): Function to fetch the data.
            user_id (str, optional): User identifier to fetch personalized data. Defaults to None.

        Returns:
            Dict[str, Any]: A dictionary containing the fetched play count data for the top 10 platforms.
        """
    async def fetch_data(self, data_fetcher, user_id: str = None) -> Dict[str, Any]:
        params = {"time_range": self.config["TIME_RANGE_DAYS"]}
        if user_id:
            params["user_id"] = user_id
        
        data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_top_10_platforms", params)
        if not data or 'response' not in data or 'data' not in data['response']:
            logging.error(self.translations["error_fetch_top_10_platforms"])
            return None
        return data['response']['data']

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if 'categories' not in data or 'series' not in data:
            logging.error(self.translations["error_missing_data_top_10_platforms"])
            return None

        platforms = data['categories']
        series = data['series']

        if not series:
            logging.warning(self.translations["warning_empty_series_top_10_platforms"])
            return None

        processed_data = {
            "platforms": platforms,
            "series": []
        }

        for serie in series:
            processed_data["series"].append({
                "name": serie["name"],
                "data": serie["data"],
                "color": get_color(serie["name"], self.config)
            })

        return processed_data

    def plot(self, processed_data: Dict[str, Any]):
        self.setup_plot()

        bar_width = 0.35
        index = range(len(processed_data["platforms"]))

        for i, serie in enumerate(processed_data["series"]):
            bars = self.ax.bar([x + i * bar_width for x in index], serie["data"], 
                             bar_width, label=serie["name"], color=serie["color"])

            if self.config["ANNOTATE_TOP_10_PLATFORMS"]:
                for j, bar in enumerate(bars):
                    height = bar.get_height()
                    if height > 0:
                        # Use BaseGraph's annotate method instead of direct ax.text
                        x_pos = bar.get_x() + bar.get_width()/2
                        self.annotate(x_pos, height, f'{int(height)}')

        # Use base class methods for consistent bold formatting
        self.add_title(self.translations["top_10_platforms_title"].format(days=self.config["TIME_RANGE_DAYS"]))
        self.add_labels(
            self.translations["top_10_platforms_xlabel"],
            self.translations["top_10_platforms_ylabel"]
        )

        self.ax.set_xticks([x + bar_width/2 for x in index])
        self.ax.set_xticklabels(processed_data["platforms"], rotation=45, ha="right")
        self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        self.add_legend()
        self.apply_tight_layout()

    async def generate(self, data_fetcher, user_id: str = None) -> str:
        data = await self.fetch_data(data_fetcher, user_id)
        if data is None:
            return None

        processed_data = self.process_data(data)
        if processed_data is None:
            return None

        self.plot(processed_data)

        today = datetime.today().strftime("%Y-%m-%d")
        file_name = f"top_10_platforms{'_' + user_id if user_id else ''}.png"
        file_path = os.path.join(self.img_folder, today, file_name)
        self.save(file_path)

        return file_path
