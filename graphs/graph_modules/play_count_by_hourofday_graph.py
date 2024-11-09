# graphs/graph_modules/play_count_by_hourofday_graph.py

from .base_graph import BaseGraph
from .utils import get_color
from datetime import datetime
from matplotlib.ticker import MaxNLocator
from typing import Dict, Any, Optional
import logging
import os

class PlayCountByHourOfDayGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "play_count_by_hourofday"

    async def fetch_data(self, data_fetcher, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch play count data by hour of day.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific data
            
        Returns:
            The fetched data or None if fetching fails
        """
        try:
            # If we have stored data, use it instead of fetching
            if self.data is not None:
                logging.debug("Using stored data for play count by hour of day")
                return self.data

            # Otherwise, fetch new data
            params = {"time_range": self.config["TIME_RANGE_DAYS"]}
            if user_id:
                params["user_id"] = user_id
            
            logging.debug("Fetching play count by hour of day data with params: %s", params)
            
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_hourofday", params)
            if not data or 'response' not in data or 'data' not in data['response']:
                error_msg = self.translations["error_fetch_play_count_hourofday"]
                if user_id:
                    error_msg = self.translations.get(
                        'error_fetch_play_count_hourofday_user',
                        'Failed to fetch play count by hour of day data for user {user_id}: {error}'
                    ).format(user_id=user_id, error="No data returned")
                logging.error(error_msg)
                return None

            return data['response']['data']
            
        except Exception as e:
            error_msg = self.translations.get(
                'error_fetch_play_count_hourofday_user' if user_id else 'error_fetch_play_count_hourofday',
                'Failed to fetch play count by hour of day data{}: {}'
            ).format(f" for user {user_id}" if user_id else "", str(e))
            logging.error(error_msg)
            return None

    def process_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process the raw data into a format suitable for plotting."""
        try:
            if not isinstance(raw_data, dict) or 'series' not in raw_data:
                logging.error(self.translations["error_missing_series_play_count_by_hourofday"])
                return None

            series = raw_data['series']
            if not series:
                logging.warning(self.translations["warning_empty_series_play_count_by_hourofday"])
                return None

            hours = list(range(24))

            processed_data = {
                "hours": hours,
                "series": []
            }

            # Validate and process each series
            for serie in series:
                if not isinstance(serie, dict) or 'name' not in serie or 'data' not in serie:
                    logging.error("Invalid series format: %s", serie)
                    continue

                if not isinstance(serie["data"], list) or len(serie["data"]) != 24:
                    logging.error("Invalid data length for series %s: expected 24, got %d",
                                serie["name"], len(serie["data"]) if isinstance(serie["data"], list) else 0)
                    continue

                if not all(isinstance(x, (int, float)) for x in serie["data"]):
                    logging.error("Invalid data type in series %s", serie["name"])
                    continue

                processed_data["series"].append({
                    "name": serie["name"],
                    "data": serie["data"],
                    "color": get_color(serie["name"], self.config)
                })

            if not processed_data["series"]:
                logging.error("No valid series data found after processing")
                return None

            return processed_data

        except Exception as e:
            logging.error(f"Error processing hour of day data: {str(e)}")
            return None

    def plot(self, processed_data: Dict[str, Any]) -> None:
        """Plot the processed data."""
        try:
            self.setup_plot()

            for serie in processed_data["series"]:
                self.ax.plot(processed_data["hours"], serie["data"], 
                            label=serie["name"], marker="o", color=serie["color"])

                if self.config["ANNOTATE_PLAY_COUNT_BY_HOUROFDAY"]:
                    for i, value in enumerate(serie["data"]):
                        if value > 0:
                            self.annotate(processed_data["hours"][i], value, f"{value}")

            self.add_title(self.translations["play_count_by_hourofday_title"].format(
                days=self.config["TIME_RANGE_DAYS"]
            ))
            self.add_labels(
                self.translations["play_count_by_hourofday_xlabel"],
                self.translations["play_count_by_hourofday_ylabel"]
            )

            self.ax.set_xticks(processed_data["hours"])
            # Format hours as 00-23 with proper alignment
            self.ax.set_xticklabels([f"{h:02d}" for h in processed_data["hours"]])
            for tick in self.ax.get_xticklabels():
                tick.set_ha("center")
            self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            self.add_legend()
            self.apply_tight_layout()

        except Exception as e:
            logging.error(f"Error plotting hour of day graph: {str(e)}")
            raise

    async def generate(self, data_fetcher, user_id: Optional[str] = None) -> Optional[str]:
        """
        Generate the graph and save it to a file.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific graphs
            
        Returns:
            The path to the generated graph file, or None if generation fails
        """
        try:
            logging.debug("Generate called with stored data: %s", "present" if self.data else "none")
            
            data = await self.fetch_data(data_fetcher, user_id)
            if data is None:
                return None

            processed_data = self.process_data(data)
            if processed_data is None:
                return None

            self.plot(processed_data)

            # Save the graph with proper file path handling
            today = datetime.today().strftime("%Y-%m-%d")
            file_name = f"play_count_by_hourofday{'_' + user_id if user_id else ''}.png"
            file_path = os.path.join(self.img_folder, today, file_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)
            
            logging.debug("Saved play count by hour of day graph: %s", file_path)
            return file_path
            
        except Exception as e:
            logging.error(f"Error generating hour of day graph: {str(e)}")
            return None
