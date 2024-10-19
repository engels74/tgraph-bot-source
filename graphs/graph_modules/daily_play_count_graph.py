# graphs/graph_modules/daily_play_count_graph.py

from .base_graph import BaseGraph
from .utils import get_color
from typing import Dict, Any, Optional
import logging
import os
from datetime import datetime
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MaxNLocator

class DailyPlayCountError(Exception):
    """Base exception for DailyPlayCount graph-specific errors."""
    pass

class DailyPlayCountGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "daily_play_count"

    async def fetch_data(self, data_fetcher, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch daily play count data.
        
        Args:
            data_fetcher: The data fetcher instance
            user_id: Optional user ID for user-specific data
            
        Returns:
            The fetched data or None if fetching fails
        """
        try:
            # If we have stored data, use it instead of fetching
            if self.data is not None:
                logging.debug("Using stored data for daily play count")
                return self.data

            # Otherwise, fetch new data
            params = {"time_range": self.config["TIME_RANGE_DAYS"]}
            if user_id:
                params["user_id"] = user_id
            
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
                
            if 'categories' not in data or 'series' not in data:
                logging.error(f"Missing required keys in data. Keys present: {data.keys()}")
                return None
                
            return data
            
        except Exception as e:
            logging.error(f"Error fetching daily play count data: {str(e)}")
            return None

    def process_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process the raw data into a format suitable for plotting.
        
        Args:
            raw_data: The raw data from the API
            
        Returns:
            Processed data ready for plotting or None if processing fails
        """
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
        """Plot the processed data.
        
        Args:
            processed_data: The processed data ready for plotting
        """
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
            raise DailyPlayCountError(f"Failed to plot graph: {str(e)}")

    async def generate(self, data_fetcher, user_id: Optional[str] = None) -> Optional[str]:
        """Generate the graph and return its file path.
        
        Args:
            data_fetcher: The data fetcher instance
            user_id: Optional user ID for user-specific graphs
            
        Returns:
            The file path of the generated graph, or None if generation fails
        """
        try:
            logging.debug("Generate called with stored data: %s", "present" if self.data else "none")
            
            raw_data = await self.fetch_data(data_fetcher, user_id)
            if raw_data is None:
                return None

            processed_data = self.process_data(raw_data)
            if processed_data is None:
                return None

            self.plot(processed_data)

            # Save the graph
            today = datetime.today().strftime("%Y-%m-%d")
            file_name = f"daily_play_count{'_' + user_id if user_id else ''}.png"
            file_path = os.path.join(self.img_folder, today, file_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)

            return file_path
            
        except Exception as e:
            logging.error(f"Error generating daily play count graph: {str(e)}")
            return None
