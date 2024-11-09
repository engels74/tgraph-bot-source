# graphs/graph_modules/daily_play_count_graph.py

"""
Improved version of daily_play_count_graph.py with security fixes and enhancements.
"""

from .base_graph import BaseGraph
from .utils import get_color
from datetime import datetime
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MaxNLocator
from typing import Dict, Any, Optional
import logging
import os
import re

class DailyPlayCountError(Exception):
    """Base exception for DailyPlayCount graph-specific errors."""
    pass

class FileSystemError(DailyPlayCountError):
    """Raised when there are file system related errors."""
    pass

class DailyPlayCountGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "daily_play_count"

    def _sanitize_user_id(self, user_id: Optional[str]) -> str:
        """
        Sanitize user ID for safe file name creation.
        
        Args:
            user_id: Raw user ID string
            
        Returns:
            Sanitized user ID safe for file name use
        """
        if not user_id:
            return ""
            
        # Remove any characters that aren't alphanumeric, underscore, or hyphen
        sanitized = re.sub(r'[^\w\-]', '', str(user_id))
        
        # Limit length to prevent extremely long filenames
        sanitized = sanitized[:50]
        
        # Ensure we don't start with a period (hidden files)
        if sanitized.startswith('.'):
            sanitized = f"_dot_{sanitized[1:]}"
            
        return sanitized

    async def fetch_data(self, data_fetcher, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch daily play count data."""
        try:
            # If we have stored data, use it instead of fetching
            if self.data is not None:
                logging.debug("Using stored data for daily play count")
                return self.data

            # Otherwise, fetch new data
            params = {"time_range": self.config["TIME_RANGE_DAYS"]}
            if user_id:
                params["user_id"] = str(user_id)  # Ensure user_id is string
            
            logging.debug("Fetching daily play count data with params: %s", params)
            
            # Fetch data from data_fetcher
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_date", params)
            
            # Validate the data structure
            if not data:
                logging.error(self.translations["error_fetch_daily_play_count"])
                return None
                
            if not isinstance(data, dict):
                logging.error(f"Invalid data type received: {type(data)}")
                return None
                
            if 'response' not in data or 'data' not in data['response']:
                logging.error(f"Missing required keys in data. Keys present: {data.keys()}")
                return None
                
            return data['response']['data']
            
        except Exception as e:
            error_msg = self.translations.get(
                'error_fetch_daily_play_count_user' if user_id else 'error_fetch_daily_play_count',
                'Failed to fetch daily play count data{}: {}'
            ).format(f" for user {user_id}" if user_id else "", str(e))
            logging.error(error_msg)
            return None

    def process_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process the raw data into a format suitable for plotting."""
        try:
            if not isinstance(raw_data, dict) or 'categories' not in raw_data or 'series' not in raw_data:
                logging.error(self.translations["error_missing_series_daily_play_count"])
                return None

            categories = raw_data['categories']
            series = raw_data['series']

            if not series:
                logging.warning(self.translations["warning_empty_series_daily_play_count"])
                return None

            # Convert string dates to datetime objects
            try:
                datetime_dates = [datetime.strptime(date, "%Y-%m-%d") for date in categories]
            except ValueError as e:
                logging.error(f"Error parsing dates: {str(e)}")
                return None

            processed_data = {
                "dates": datetime_dates,
                "series": []
            }

            # Process each series (TV and Movies)
            for serie in series:
                if not isinstance(serie, dict) or 'name' not in serie or 'data' not in serie:
                    logging.error(f"Invalid series data format: {serie}")
                    continue
                
                # Validate data points
                if not all(isinstance(x, (int, float)) for x in serie["data"]):
                    logging.error(f"Invalid data points in series {serie['name']}")
                    continue

                processed_data["series"].append({
                    "name": serie["name"],
                    "data": serie["data"],
                    "color": get_color(serie["name"], self.config)
                })

            if not processed_data["series"]:
                logging.error("No valid series data found")
                return None

            return processed_data
            
        except Exception as e:
            logging.error(f"Error processing daily play count data: {str(e)}")
            return None

    def plot(self, processed_data: Dict[str, Any]) -> None:
        """Plot the processed data."""
        try:
            self.setup_plot()

            for serie in processed_data["series"]:
                self.ax.plot(
                    processed_data["dates"], 
                    serie["data"],
                    label=serie["name"],
                    marker="o",
                    color=serie["color"]
                )

                if self.config["ANNOTATE_DAILY_PLAY_COUNT"]:
                    for i, value in enumerate(serie["data"]):
                        if value > 0:
                            self.annotate(processed_data["dates"][i], value, f"{value}")

            self.add_title(self.translations["daily_play_count_title"].format(
                days=self.config["TIME_RANGE_DAYS"]
            ))
            self.add_labels(
                self.translations["daily_play_count_xlabel"],
                self.translations["daily_play_count_ylabel"]
            )

            self.ax.set_xticks(processed_data["dates"])
            self.ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
            self.ax.tick_params(axis='x', rotation=45)
            self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            self.add_legend()
            self.apply_tight_layout()
            
        except Exception as e:
            logging.error(f"Error plotting daily play count graph: {str(e)}")
            raise

    async def generate(self, data_fetcher, user_id: Optional[str] = None) -> Optional[str]:
        """Generate the graph and return its file path."""
        try:
            logging.debug("Generate called with stored data: %s", "present" if self.data else "none")
            
            raw_data = await self.fetch_data(data_fetcher, user_id)
            if raw_data is None:
                return None

            processed_data = self.process_data(raw_data)
            if processed_data is None:
                return None

            self.plot(processed_data)

            # Save the graph with sanitized user_id
            today = datetime.today().strftime("%Y-%m-%d")
            sanitized_user_id = self._sanitize_user_id(user_id)
            file_name = f"daily_play_count{'_' + sanitized_user_id if sanitized_user_id else ''}.png"
            
            # Ensure the path is within the intended directory
            dated_dir = os.path.join(self.img_folder, today)
            file_path = os.path.join(dated_dir, file_name)
            
            # Verify the final path is within the intended directory
            if not os.path.abspath(file_path).startswith(os.path.abspath(self.img_folder)):
                raise FileSystemError("Invalid file path generated")
            
            os.makedirs(dated_dir, exist_ok=True)
            self.save(file_path)

            logging.debug("Saved daily play count graph: %s", file_path)
            return file_path
            
        except FileSystemError:
            logging.error("Security violation: Attempted file path traversal")
            return None
        except Exception as e:
            logging.error(f"Error generating daily play count graph: {str(e)}")
            return None
