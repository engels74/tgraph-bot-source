# graphs/graph_modules/play_count_by_dayofweek_graph.py

from .base_graph import BaseGraph
from .utils import get_color
from typing import Dict, Any
import logging
import os
from datetime import datetime
from matplotlib.ticker import MaxNLocator

class PlayCountByDayOfWeekGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "play_count_by_dayofweek"

    async def fetch_data(self, data_fetcher, user_id: str = None) -> Dict[str, Any]:
        params = {"time_range": self.config["TIME_RANGE_DAYS"]}
        if user_id:
            params["user_id"] = user_id
        
        data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_dayofweek", params)
        if not data or 'response' not in data or 'data' not in data['response']:
            logging.error(self.translations["error_fetch_play_count_dayofweek"])
            return None
        return data['response']['data']

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if 'series' not in data:
            logging.error(self.translations["error_missing_series_play_count_by_dayofweek"])
            return None

        series = data['series']
        if not series:
            logging.warning(self.translations["warning_empty_series_play_count_by_dayofweek"])
            return None

        days = list(range(7))
        day_labels = [self.translations[f"day_{i}"] for i in range(7)]

        processed_data = {
            "days": days,
            "day_labels": day_labels,
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

        for serie in processed_data["series"]:
            self.ax.plot(processed_data["days"], serie["data"], label=serie["name"], marker="o", color=serie["color"])

            if self.config["ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK"]:
                for i, value in enumerate(serie["data"]):
                    if value > 0:
                        self.annotate(processed_data["days"][i], value, f"{value}")

        # Use base class methods for consistent bold formatting
        self.add_title(self.translations["play_count_by_dayofweek_title"].format(days=self.config["TIME_RANGE_DAYS"]))
        self.add_labels(
            self.translations["play_count_by_dayofweek_xlabel"],
            self.translations["play_count_by_dayofweek_ylabel"]
        )

        self.ax.set_xticks(processed_data["days"])
        self.ax.set_xticklabels(processed_data["day_labels"], ha="center")
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
        file_name = f"play_count_by_dayofweek{'_' + user_id if user_id else ''}.png"
        file_path = os.path.join(self.img_folder, today, file_name)
        self.save(file_path)

        return file_path
