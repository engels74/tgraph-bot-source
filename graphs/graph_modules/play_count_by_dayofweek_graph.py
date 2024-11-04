# graphs/graph_modules/play_count_by_dayofweek_graph.py

from .base_graph import BaseGraph
from .utils import get_color, validate_series_data
from config.modules.sanitizer import sanitize_user_id, InvalidUserIdError
from datetime import datetime
from matplotlib.ticker import MaxNLocator
from typing import Dict, Any, Optional, List
import logging
import os

class PlayCountByDayOfWeekError(Exception):
    """Base exception for PlayCountByDayOfWeek graph-specific errors."""
    pass

class DataValidationError(PlayCountByDayOfWeekError):
    """Raised when data validation fails."""
    pass

class GraphGenerationError(PlayCountByDayOfWeekError):
    """Raised when graph generation fails."""
    pass

class FileSystemError(PlayCountByDayOfWeekError):
    """Raised when there are file system related errors."""
    pass

class PlayCountByDayOfWeekGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "play_count_by_dayofweek"

    def _validate_series_data(self, series: List[Dict[str, Any]], days_count: int) -> List[str]:
        return validate_series_data(series, days_count, "day of week series")

    def _process_filename(self, user_id: Optional[str]) -> Optional[str]:
        """
        Process user ID for safe filename creation.
        
        Args:
            user_id: The user ID to process
            
        Returns:
            A sanitized version of the user ID safe for filenames, or None if input is None
        """
        if user_id is None:
            return None
            
        try:
            return sanitize_user_id(user_id)
        except InvalidUserIdError as e:
            logging.warning(f"Invalid user ID for filename: {e}")
            return None

    async def fetch_data(self, data_fetcher, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch play count data by day of week.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific data
            
        Returns:
            The fetched data or None if fetching fails
        """
        try:
            # If we have stored data, use it instead of fetching
            if self.data is not None:
                logging.debug("Using stored data for play count by day of week")
                return self.data

            # Otherwise, fetch new data
            params = {"time_range": self.config["TIME_RANGE_DAYS"]}
            if user_id:
                params["user_id"] = user_id
            
            logging.debug("Fetching play count by day of week data with params: %s", params)
            
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_dayofweek", params)
            if not data or 'response' not in data or 'data' not in data['response']:
                error_msg = (
                    self.translations.get(
                        'error_fetch_play_count_dayofweek_user',
                        'Failed to fetch play count by day of week data for user {user_id}: {error}'
                    ) if user_id else
                    self.translations["error_fetch_play_count_dayofweek"]
                )
                if user_id:
                    logging.error(error_msg.format(user_id=user_id, error="No data returned"))
                else:
                    logging.error(error_msg)
                return None

            return data['response']['data']
            
        except Exception as e:
            error_msg = (
                self.translations.get(
                    'error_fetch_play_count_dayofweek_user',
                    'Failed to fetch play count by day of week data for user {user_id}: {error}'
                ) if user_id else
                self.translations["error_fetch_play_count_dayofweek"]
            )
            if user_id:
                logging.error(error_msg.format(user_id=user_id, error=str(e)))
            else:
                logging.error(f"{error_msg}: {str(e)}")
            return None

    def process_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process the fetched data for plotting.
        
        Args:
            data: Raw data from the API
            
        Returns:
            Processed data ready for plotting
            
        Raises:
            DataValidationError: If data validation fails
        """
        if 'series' not in data:
            raise DataValidationError(
                self.translations["error_missing_series_play_count_by_dayofweek"]
            )

        series = data['series']
        if not series:
            raise DataValidationError(
                self.translations["warning_empty_series_play_count_by_dayofweek"]
            )

        days = list(range(7))
        day_labels = [self.translations.get(f"day_{i}", f"Day {i}") for i in range(7)]

        # Validate series data
        validation_errors = self._validate_series_data(series, len(days))
        if validation_errors:
            raise DataValidationError(
                "Series data validation failed:\n" + "\n".join(validation_errors)
            )

        processed_data = {
            "days": days,
            "day_labels": day_labels,
            "series": []
        }

        try:
            for serie in series:
                processed_data["series"].append({
                    "name": serie["name"],
                    "data": serie["data"],
                    "color": get_color(serie["name"], self.config)
                })
        except KeyError as e:
            raise DataValidationError(f"Missing required key in series data: {e}")
        except ValueError as e:
            raise DataValidationError(f"Invalid value in series data: {e}")

        return processed_data

    def plot(self, processed_data: Dict[str, Any]) -> None:
        """
        Plot the processed data.
        
        Args:
            processed_data: Processed data ready for plotting
            
        Raises:
            GraphGenerationError: If plotting fails
        """
        try:
            self.setup_plot()

            for serie in processed_data["series"]:
                self.ax.plot(
                    processed_data["days"],
                    serie["data"],
                    label=serie["name"],
                    marker="o",
                    color=serie["color"]
                )

                if self.config.get("ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK", False):
                    for i, value in enumerate(serie["data"]):
                        if value > 0:
                            self.annotate(processed_data["days"][i], value, f"{value}")

            self.add_title(self.translations["play_count_by_dayofweek_title"].format(
                days=self.config["TIME_RANGE_DAYS"]
            ))
            self.add_labels(
                self.translations["play_count_by_dayofweek_xlabel"],
                self.translations["play_count_by_dayofweek_ylabel"]
            )

            self.ax.set_xticks(processed_data["days"])
            self.ax.set_xticklabels(processed_data["day_labels"], ha="center")
            self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            self.add_legend()
            self.apply_tight_layout()
            
        except Exception as e:
            raise GraphGenerationError(f"Error plotting graph: {str(e)}")

    async def generate(self, data_fetcher, user_id: Optional[str] = None) -> Optional[str]:
        """
        Generate the graph and return its file path.
        
        Args:
            data_fetcher: The data fetcher instance to use
            user_id: Optional user ID for user-specific graphs
            
        Returns:
            The file path of the generated graph, or None if generation fails
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

            # Save the graph
            today = datetime.today().strftime("%Y-%m-%d")
            base_dir = os.path.join(self.img_folder, today)
            if user_id:
                base_dir = os.path.join(base_dir, f"user_{user_id}")
                
            file_name = f"play_count_by_dayofweek{'_' + user_id if user_id else ''}.png"
            file_path = os.path.join(base_dir, file_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)
            
            logging.debug("Saved play count by day of week graph: %s", file_path)
            return file_path
            
        except Exception as e:
            logging.error(f"Error generating day of week graph: {str(e)}")
            return None
