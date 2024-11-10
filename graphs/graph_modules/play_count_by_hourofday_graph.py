# graphs/graph_modules/play_count_by_hourofday_graph.py

from .base_graph import BaseGraph
from .utils import get_color, validate_series_data
from config.modules.sanitizer import sanitize_user_id, InvalidUserIdError
from datetime import datetime
from matplotlib.ticker import MaxNLocator
from typing import Dict, Any, Optional
import logging
import os

class PlayCountByHourOfDayError(Exception):
    """Base exception for PlayCountByHourOfDay graph-specific errors."""
    pass

class DataValidationError(PlayCountByHourOfDayError):
    """Raised when data validation fails."""
    pass

class GraphGenerationError(PlayCountByHourOfDayError):
    """Raised when graph generation fails."""
    pass

class PlayCountByHourOfDayGraph(BaseGraph):
    """Handles generation of play count by hour of day graphs."""
    
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        """
        Initialize the hour of day graph handler.
        
        Args:
            config: Configuration dictionary
            translations: Translation strings dictionary
            img_folder: Path to image output folder
        """
        super().__init__(config, translations, img_folder)
        self.graph_type = "play_count_by_hourofday"

    def _process_filename(self, user_id: Optional[str]) -> Optional[str]:
        """
        Process user ID for safe filename creation.
        
        Args:
            user_id: The user ID to process
            
        Returns:
            Optional[str]: A sanitized version of the user ID safe for filenames
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
        Fetch play count data by hour of day.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific data
            
        Returns:
            Optional[Dict[str, Any]]: The fetched data or None if fetching fails
        """
        try:
            if self.data is not None:
                logging.debug("Using stored data for play count by hour of day")
                return self.data

            params = {"time_range": self.config["TIME_RANGE_DAYS"]}
            if user_id:
                params["user_id"] = str(user_id)  # Ensure user_id is string
            
            logging.debug("Fetching play count by hour of day data with params: %s", params)
            
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_hourofday", params)
            if not data or 'response' not in data or 'data' not in data['response']:
                error_msg = self.translations.get(
                    'error_fetch_play_count_hourofday_user' if user_id else 'error_fetch_play_count_hourofday',
                    'Failed to fetch play count by hour of day data{}: {}'
                ).format(f" for user {user_id}" if user_id else "", "No data returned")
                logging.error(error_msg)
                raise DataValidationError(error_msg)

            return data['response']['data']
            
        except DataValidationError:
            raise
        except Exception as e:
            error_msg = self.translations.get(
                'error_fetch_play_count_hourofday_user' if user_id else 'error_fetch_play_count_hourofday',
                'Failed to fetch play count by hour of day data{}: {}'
            ).format(f" for user {user_id}" if user_id else "", str(e))
            logging.error(error_msg)
            raise PlayCountByHourOfDayError(error_msg) from e

    def process_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process the raw data into a format suitable for plotting."""
        try:
            if 'series' not in raw_data:
                error_msg = self.translations["error_missing_series_play_count_by_hourofday"]
                logging.error(error_msg)
                raise DataValidationError(error_msg)

            series = raw_data['series']
            if not series:
                error_msg = self.translations["warning_empty_series_play_count_by_hourofday"]
                logging.warning(error_msg)
                return None

            hours = list(range(24))

            # Validate series data
            errors = validate_series_data(series, 24, "hour of day series")
            if errors:
                error_msg = "\n".join(errors)
                logging.error(error_msg)
                raise DataValidationError(error_msg)

            processed_data = {
                "hours": hours,
                "series": []
            }

            # Process validated series data
            for serie in series:
                processed_data["series"].append({
                    "name": serie["name"],
                    "data": serie["data"],
                    "color": get_color(serie["name"], self.config)
                })

            if not processed_data["series"]:
                raise DataValidationError("No valid series data found after processing")

            return processed_data

        except (DataValidationError, KeyError):
            raise
        except Exception as e:
            error_msg = f"Error processing hour of day data: {str(e)}"
            logging.error(error_msg)
            raise PlayCountByHourOfDayError(error_msg) from e

    def plot(self, processed_data: Dict[str, Any]) -> None:
        """Plot the processed data."""
        try:
            self.setup_plot()

            for serie in processed_data["series"]:
                self.ax.plot(
                    processed_data["hours"],
                    serie["data"],
                    label=serie["name"],
                    marker="o",
                    color=serie["color"]
                )

                if self.config.get("ANNOTATE_PLAY_COUNT_BY_HOUROFDAY", False):
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
            self.ax.set_xticklabels([f"{h:02d}" for h in processed_data["hours"]])
            for tick in self.ax.get_xticklabels():
                tick.set_ha("center")
            self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            self.add_legend()
            self.apply_tight_layout()

        except Exception as e:
            error_msg = f"Error plotting hour of day graph: {str(e)}"
            logging.error(error_msg)
            raise GraphGenerationError(error_msg) from e

    async def generate(self, data_fetcher, user_id: Optional[str] = None) -> Optional[str]:
        """
        Generate the graph and save it to a file.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific graphs
            
        Returns:
            Optional[str]: The path to the generated graph file, or None if generation fails
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

            today = datetime.today().strftime("%Y-%m-%d")
            base_dir = os.path.join(self.img_folder, today)
            
            safe_user_id = self._process_filename(user_id)
            if safe_user_id:
                base_dir = os.path.join(base_dir, f"user_{safe_user_id}")
                
            file_name = f"play_count_by_hourofday{'_' + safe_user_id if safe_user_id else ''}.png"
            file_path = os.path.join(base_dir, file_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)
            
            logging.debug("Saved play count by hour of day graph: %s", file_path)
            return file_path
            
        except (DataValidationError, PlayCountByHourOfDayError):
            raise
        except Exception as e:
            error_msg = f"Error generating hour of day graph: {str(e)}"
            logging.error(error_msg)
            raise GraphGenerationError(error_msg) from e
