# graphs/graph_modules/daily_play_count_graph.py

from .base_graph import BaseGraph
from .utils import get_date_range, format_date, get_color
from typing import Dict, Any
import logging
import os
from datetime import datetime, timedelta
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MaxNLocator

class DailyPlayCountGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "daily_play_count"

    async def fetch_data(self, data_fetcher, user_id: str = None) -> Dict[str, Any]:
        params = {"time_range": self.config["TIME_RANGE_DAYS"]}
        if user_id:
            params["user_id"] = user_id
        
        data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_date", params)
        if not data or 'response' not in data or 'data' not in data['response']:
            logging.error(self.translations["error_fetch_daily_play_count"])
            return None
        return data['response']['data']

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if 'series' not in data:
            logging.error(self.translations["error_missing_series_daily_play_count"])
            return None

        series = data['series']
        if not series:
            logging.warning(self.translations["warning_empty_series_daily_play_count"])
            return None

        end_date = datetime.now().astimezone()
        end_date - timedelta(days=self.config["TIME_RANGE_DAYS"] - 1)
        dates = get_date_range(self.config["TIME_RANGE_DAYS"])
        date_strs = [format_date(date) for date in dates]

        processed_data = {
            "dates": dates,
            "date_strs": date_strs,
            "series": []
        }

        for serie in series:
            date_data_map = {date: 0 for date in date_strs}
            for date, value in zip(data['categories'], serie['data']):
                if date in date_data_map:
                    date_data_map[date] = value
            complete_data = [date_data_map[date] for date in date_strs]
            processed_data["series"].append({
                "name": serie["name"],
                "data": complete_data,
                "color": get_color(serie["name"], self.config)
            })

        return processed_data

    def plot(self, processed_data: Dict[str, Any]):
        self.setup_plot()

        for serie in processed_data["series"]:
            self.ax.plot(processed_data["dates"], serie["data"], label=serie["name"], marker="o", color=serie["color"])

            if self.config["ANNOTATE_DAILY_PLAY_COUNT"]:
                for i, value in enumerate(serie["data"]):
                    if value > 0:
                        self.annotate(processed_data["dates"][i], value, f"{value}")

        # Use base class methods for consistent bold formatting
        self.add_title(self.translations["daily_play_count_title"].format(days=self.config["TIME_RANGE_DAYS"]))
        self.add_labels(
            self.translations["daily_play_count_xlabel"],
            self.translations["daily_play_count_ylabel"]
        )

        self.ax.set_xticks(processed_data["dates"])
        self.ax.set_xticklabels(processed_data["date_strs"], rotation=45, ha="right")
        self.ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
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
        file_name = f"daily_play_count{'_' + user_id if user_id else ''}.png"
        file_path = os.path.join(self.img_folder, today, file_name)
        self.save(file_path)

        return file_path
