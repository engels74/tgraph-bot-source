# graphs/graph_modules/top_10_platforms_graph.py

from .base_graph import BaseGraph
from .utils import get_color
from typing import Dict, Any
import logging
import os
from datetime import datetime
from matplotlib.ticker import MaxNLocator

class TautulliDataError(Exception):
    """Raised when there is an error fetching or processing Tautulli data."""
    pass

class Top10PlatformsGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "top_10_platforms"

    async def fetch_data(self, data_fetcher, user_id: str = None) -> Dict[str, Any]:
        params = {"time_range": self.config["TIME_RANGE_DAYS"]}
        if user_id:
            params["user_id"] = user_id
        
        data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_top_10_platforms", params)
        if not data or 'response' not in data or 'data' not in data['response']:
            error_msg = self.translations["error_fetch_top_10_platforms"]
            logging.error(error_msg)
            raise TautulliDataError(error_msg)
        return data['response']['data']

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if 'categories' not in data or 'series' not in data:
            error_msg = self.translations["error_missing_data_top_10_platforms"]
            logging.error(error_msg)
            raise TautulliDataError(error_msg)

        platforms = data['categories']
        series = data['series']

        if not series:
            error_msg = self.translations["warning_empty_series_top_10_platforms"]
            logging.warning(error_msg)
            raise TautulliDataError(error_msg)

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
        try:
            data = await self.fetch_data(data_fetcher, user_id)
            processed_data = self.process_data(data)
            self.plot(processed_data)

            today = datetime.today().strftime("%Y-%m-%d")
            file_name = f"top_10_platforms{'_' + user_id if user_id else ''}.png"
            file_path = os.path.join(self.img_folder, today, file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)

            return file_path
            
        except TautulliDataError as e:
            logging.error(f"Error generating top 10 platforms graph: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error generating top 10 platforms graph: {str(e)}")
            return None
