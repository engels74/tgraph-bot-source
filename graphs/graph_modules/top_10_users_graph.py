# graphs/graph_modules/top_10_users_graph.py

from .base_graph import BaseGraph
from .utils import censor_username
from typing import Dict, Any
import logging
import os
from datetime import datetime
from matplotlib.ticker import MaxNLocator

class Top10UsersGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "top_10_users"

    async def fetch_data(self, data_fetcher, user_id: str = None) -> Dict[str, Any]:
        params = {"time_range": self.config["TIME_RANGE_DAYS"]}
        # Note: We don't use user_id for this graph as it's always about all users
        
        data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_top_10_users", params)
        if not data or 'response' not in data or 'data' not in data['response']:
            logging.error(self.translations["error_fetch_top_10_users"])
            return None
        return data['response']['data']

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if 'categories' not in data or 'series' not in data:
            logging.error(self.translations["error_missing_data_top_10_users"])
            return None

        users = data['categories']
        series = data['series']

        if not series:
            logging.warning(self.translations["warning_empty_series_top_10_users"])
            return None

        censored_users = [censor_username(user, self.config["CENSOR_USERNAMES"]) for user in users]

        processed_data = {
            "users": censored_users,
            "tv_data": [],
            "movie_data": []
        }

        for serie in series:
            if serie["name"] == "TV":
                processed_data["tv_data"] = serie["data"]
            elif serie["name"] == "Movies":
                processed_data["movie_data"] = serie["data"]

        # Combine data and sort by total plays
        combined_data = list(zip(censored_users, processed_data["tv_data"], processed_data["movie_data"]))
        combined_data.sort(key=lambda x: x[1] + x[2], reverse=True)

        processed_data["users"] = [item[0] for item in combined_data]
        processed_data["tv_data"] = [item[1] for item in combined_data]
        processed_data["movie_data"] = [item[2] for item in combined_data]

        return processed_data

    def plot(self, processed_data: Dict[str, Any]):
        self.setup_plot()

        bar_width = 0.75
        index = range(len(processed_data["users"]))

        # Plot movie data
        self.ax.bar(index, processed_data["movie_data"], bar_width,
                               label="Movies", color=self.get_color("Movies"))

        # Plot TV data, stacked on top of movie data
        self.ax.bar(index, processed_data["tv_data"], bar_width,
                            bottom=processed_data["movie_data"],
                            label="TV", color=self.get_color("TV"))

        if self.config["ANNOTATE_TOP_10_USERS"]:
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

        self.ax.set_xlabel(self.translations["top_10_users_xlabel"])
        self.ax.set_ylabel(self.translations["top_10_users_ylabel"])
        self.ax.set_title(self.translations["top_10_users_title"].format(days=self.config["TIME_RANGE_DAYS"]))

        self.ax.set_xticks(index)
        self.ax.set_xticklabels(processed_data["users"], rotation=45, ha="right")
        self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        self.add_legend()
        self.apply_tight_layout()

    async def generate(self, data_fetcher, user_id: str = None) -> str:
        data = await self.fetch_data(data_fetcher)
        if data is None:
            return None

        processed_data = self.process_data(data)
        if processed_data is None:
            return None

        self.plot(processed_data)

        today = datetime.today().strftime("%Y-%m-%d")
        file_name = "top_10_users.png"
        file_path = os.path.join(self.img_folder, today, file_name)
        self.save(file_path)

        return file_path
