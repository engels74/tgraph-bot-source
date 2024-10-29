# graphs/graph_modules/play_count_by_month_graph.py

from .base_graph import BaseGraph
from typing import Dict, Any
import logging
import os
from datetime import datetime
from matplotlib.ticker import MaxNLocator

class PlayCountByMonthGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "play_count_by_month"

    async def fetch_data(self, data_fetcher, user_id: str = None) -> Dict[str, Any]:
        params = {"time_range": 12, "y_axis": "plays"}
        if user_id:
            params["user_id"] = user_id
        
        data = await data_fetcher.fetch_tautulli_data_async("get_plays_per_month", params)
        if not data or 'response' not in data or 'data' not in data['response']:
            logging.error(self.translations["error_fetch_play_count_month"])
            return None
        return data['response']['data']

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if 'categories' not in data or 'series' not in data:
            logging.error(self.translations["error_missing_data_play_count_by_month"])
            return None

        months = data['categories']
        series = data['series']

        if not months or not series:
            logging.warning(self.translations["warning_empty_data_play_count_by_month"])
            return None

        processed_data = {
            "months": [],
            "tv_data": [],
            "movie_data": []
        }

        for serie in series:
            if serie["name"] == "TV":
                tv_data = serie["data"]
            elif serie["name"] == "Movies":
                movie_data = serie["data"]

        # Filter out months with zero plays for both TV and movies
        for i, month in enumerate(months):
            if tv_data[i] > 0 or movie_data[i] > 0:
                processed_data["months"].append(month)
                processed_data["tv_data"].append(tv_data[i])
                processed_data["movie_data"].append(movie_data[i])

        if not processed_data["months"]:
            logging.warning(self.translations["warning_no_play_data_play_count_by_month"])
            return None

        return processed_data

    def plot(self, processed_data: Dict[str, Any]):
        self.setup_plot()

        bar_width = 0.75
        index = range(len(processed_data["months"]))

        # Plot movie data
        self.ax.bar(index, processed_data["movie_data"], bar_width,
                   label="Movies", color=self.get_color("Movies"))

        # Plot TV data, stacked on top of movie data
        self.ax.bar(index, processed_data["tv_data"], bar_width,
                   bottom=processed_data["movie_data"],
                   label="TV", color=self.get_color("TV"))

        if self.config["ANNOTATE_PLAY_COUNT_BY_MONTH"]:
            for i in range(len(index)):
                movie_value = processed_data["movie_data"][i]
                tv_value = processed_data["tv_data"][i]
                total = movie_value + tv_value

                # Annotate movie value if non-zero (in middle of movie section)
                if movie_value > 0:
                    self.annotate(i, movie_value/2, str(int(movie_value)))

                # Annotate TV value if non-zero (in middle of TV section)
                if tv_value > 0:
                    self.annotate(i, movie_value + tv_value/2, str(int(tv_value)))

                # Annotate total on top
                self.annotate(i, total, str(int(total)))

        # Use base class methods for consistent bold formatting
        self.add_title(self.translations["play_count_by_month_title"])
        self.add_labels(
            self.translations["play_count_by_month_xlabel"],
            self.translations["play_count_by_month_ylabel"]
        )

        self.ax.set_xticks(index)
        self.ax.set_xticklabels(processed_data["months"], rotation=45, ha="right")
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
        file_name = f"play_count_by_month{'_' + user_id if user_id else ''}.png"
        file_path = os.path.join(self.img_folder, today, file_name)
        self.save(file_path)

        return file_path
