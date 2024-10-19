# graphs/graph_modules/play_count_by_hourofday_graph.py

from .base_graph import BaseGraph
from .utils import get_color
from typing import Dict, Any
import logging
import os
from datetime import datetime
from matplotlib.ticker import MaxNLocator

class PlayCountByHourOfDayGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "play_count_by_hourofday"

    async def fetch_data(self, data_fetcher, user_id: str = None) -> Dict[str, Any]:
        params = {"time_range": self.config["TIME_RANGE_DAYS"]}
        if user_id:
            params["user_id"] = user_id
        
        data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_hourofday", params)
        if not data or 'response' not in data or 'data' not in data['response']:
            logging.error(self.translations["error_fetch_play_count_hourofday"])
            return None
        return data['response']['data']

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if 'series' not in data:
            logging.error(self.translations["error_missing_series_play_count_by_hourofday"])
            return None

        series = data['series']
        if not series:
            logging.warning(self.translations["warning_empty_series_play_count_by_hourofday"])
            return None

        hours = list(range(24))

        processed_data = {
            "hours": hours,
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
            self.ax.plot(processed_data["hours"], serie["data"], label=serie["name"], marker="o", color=serie["color"])

            if self.config["ANNOTATE_PLAY_COUNT_BY_HOUROFDAY"]:
                for i, value in enumerate(serie["data"]):
                    if value > 0:
                        self.annotate(processed_data["hours"][i], value, f"{value}")

        self.ax.set_xlabel(self.translations["play_count_by_hourofday_xlabel"])
        self.ax.set_ylabel(self.translations["play_count_by_hourofday_ylabel"])
        self.ax.set_title(self.translations["play_count_by_hourofday_title"].format(days=self.config["TIME_RANGE_DAYS"]))

        self.ax.set_xticks(processed_data["hours"])
        self.ax.set_xticklabels(processed_data["hours"], ha="center")
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
        file_name = f"play_count_by_hourofday{'_' + user_id if user_id else ''}.png"
        file_path = os.path.join(self.img_folder, today, file_name)
        self.save(file_path)

        return file_path
