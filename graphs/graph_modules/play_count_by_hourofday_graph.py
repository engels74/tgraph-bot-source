# graphs/graph_modules/play_count_by_hourofday_graph.py

"""
Improved hour of day graph generator with standardized error handling and resource management.
Handles generation of play count graphs by hour with proper validation, cleanup, and error handling.
"""

from .base_graph import BaseGraph
from .utils import get_color, validate_series_data
from config.modules.sanitizer import sanitize_user_id, InvalidUserIdError
from datetime import datetime
from matplotlib.ticker import MaxNLocator
from typing import Dict, Any, Optional, List, Union
import logging
import os

class HourOfDayError(Exception):
    """Base exception for hour of day graph-related errors."""
    pass

class DataFetchError(HourOfDayError):
    """Raised when there's an error fetching graph data."""
    pass

class DataValidationError(HourOfDayError):
    """Raised when data validation fails."""
    pass

class GraphGenerationError(HourOfDayError):
    """Raised when graph generation fails."""
    pass

class ResourceError(HourOfDayError):
    """Raised when there's an error managing graph resources."""
    pass

class PlayCountByHourOfDayGraph(BaseGraph):
    """Handles generation of play count graphs by hour."""
    
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        """
        Initialize the hour of day graph handler.
        
        Args:
            config: Configuration dictionary
            translations: Translation strings dictionary
            img_folder: Path to image output folder
            
        Raises:
            ValueError: If required configuration is missing
        """
        super().__init__(config, translations, img_folder)
        self.graph_type = "play_count_by_hourofday"
        self._verify_config()
        
    def _verify_config(self) -> None:
        """Verify required configuration exists."""
        required_keys = [
            'TIME_RANGE_DAYS',
            'ANNOTATE_PLAY_COUNT_BY_HOUROFDAY',
            'TV_COLOR',
            'MOVIE_COLOR',
            'GRAPH_BACKGROUND_COLOR'
        ]
        missing = [key for key in required_keys if key not in self.config]
        if missing:
            raise ValueError(f"Missing required configuration keys: {missing}")

    def _process_filename(self, user_id: Optional[str]) -> Optional[str]:
        """
        Process user ID for safe filename creation.
        
        Args:
            user_id: The user ID to process
            
        Returns:
            Optional[str]: A sanitized version of the user ID safe for filenames
            
        Raises:
            InvalidUserIdError: If user_id is invalid
        """
        if user_id is None:
            return None
            
        try:
            return sanitize_user_id(user_id)
        except InvalidUserIdError as e:
            logging.warning(f"Invalid user ID for filename: {e}")
            raise InvalidUserIdError(f"Invalid user ID format: {e}") from e

    def _validate_hours(self, data: List[int]) -> None:
        """
        Validate hour data points.
        
        Args:
            data: List of hour values
            
        Raises:
            DataValidationError: If validation fails
        """
        try:
            if len(data) != 24:
                raise DataValidationError(f"Expected 24 hours, got {len(data)}")
                
            for hour in data:
                if not isinstance(hour, (int, float)):
                    raise DataValidationError(f"Invalid hour value type: {type(hour)}")
                if hour < 0:
                    raise DataValidationError(f"Negative hour value: {hour}")
                    
        except Exception as e:
            raise DataValidationError(f"Hour validation failed: {str(e)}") from e

    async def fetch_data(self, data_fetcher, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch play count data by hour of day.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific data
            
        Returns:
            The fetched data
            
        Raises:
            DataFetchError: If data fetching fails
        """
        try:
            if self.data is not None:
                logging.debug("Using stored data for play count by hour of day")
                return self.data

            params = {"time_range": self.config["TIME_RANGE_DAYS"]}
            if user_id:
                params["user_id"] = sanitize_user_id(user_id)
            
            logging.debug("Fetching play count by hour of day data with params: %s", params)
            
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_hourofday", params)
            if not data or 'response' not in data or 'data' not in data['response']:
                error_msg = self.translations.get(
                    'error_fetch_play_count_hourofday_user' if user_id else 'error_fetch_play_count_hourofday',
                    'Failed to fetch play count by hour data{}: {}'
                ).format(f" for user {user_id}" if user_id else "", "No data returned")
                logging.error(error_msg)
                raise DataFetchError(error_msg)

            return data['response']['data']

        except InvalidUserIdError as e:
            raise DataFetchError(f"Invalid user ID: {str(e)}") from e
        except Exception as e:
            error_msg = self.translations.get(
                'error_fetch_play_count_hourofday',
                'Failed to fetch hour of day data: {error}'
            ).format(error=str(e))
            logging.error(error_msg)
            raise DataFetchError(error_msg) from e

    def process_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the raw data for plotting.
        
        Args:
            raw_data: Raw data from the API
            
        Returns:
            Processed data ready for plotting
            
        Raises:
            DataValidationError: If processing fails
        """
        try:
            if not isinstance(raw_data, dict) or 'series' not in raw_data:
                raise DataValidationError(self.translations["error_missing_series_play_count_by_hourofday"])

            series = raw_data['series']
            if not series:
                raise DataValidationError(self.translations["warning_empty_series_play_count_by_hourofday"])

            hours = list(range(24))
            
            # Validate series data
            validation_errors = validate_series_data(series, 24, "hour of day series")
            if validation_errors:
                raise DataValidationError("\n".join(validation_errors))

            processed_data = {
                "hours": hours,
                "series": []
            }

            for serie in series:
                # Validate each series' hour data
                self._validate_hours(serie["data"])
                
                processed_data["series"].append({
                    "name": serie["name"],
                    "data": serie["data"],
                    "color": get_color(serie["name"], self.config)
                })

            return processed_data

        except (KeyError, ValueError) as e:
            raise DataValidationError(f"Data validation failed: {str(e)}") from e
        except Exception as e:
            error_msg = f"Error processing hour of day data: {str(e)}"
            logging.error(error_msg)
            raise DataValidationError(error_msg) from e

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
                    processed_data["hours"],
                    serie["data"],
                    label=serie["name"],
                    marker="o",
                    color=serie["color"]
                )

                if self.config.get("ANNOTATE_PLAY_COUNT_BY_HOUROFDAY", False):
                    self._add_annotations(processed_data["hours"], serie["data"])

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

    def _add_annotations(self, hours: List[int], values: List[Union[int, float]]) -> None:
        """Add value annotations to the graph points."""
        for hour, value in zip(hours, values):
            if value > 0:
                self.annotate(hour, value, f"{int(value)}")

    async def generate(self, data_fetcher, user_id: Optional[str] = None) -> Optional[str]:
        """
        Generate the graph and return its file path.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific graphs
            
        Returns:
            The file path of the generated graph, or None if generation fails
            
        Raises:
            HourOfDayError: If graph generation fails
        """
        try:
            data = await self.fetch_data(data_fetcher, user_id)
            processed_data = self.process_data(data)
            self.plot(processed_data)

            # Create directories and save graph
            today = datetime.today().strftime("%Y-%m-%d")
            base_dir = os.path.join(self.img_folder, today)
            
            safe_user_id = self._process_filename(user_id) if user_id else None
            if safe_user_id:
                base_dir = os.path.join(base_dir, f"user_{safe_user_id}")
                
            file_name = f"play_count_by_hourofday{'_' + safe_user_id if safe_user_id else ''}.png"
            file_path = os.path.join(base_dir, file_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)
            
            logging.debug("Saved hour of day graph: %s", file_path)
            return file_path

        except (DataFetchError, DataValidationError, GraphGenerationError) as e:
            logging.error(str(e))
            return None
        except Exception as e:
            error_msg = f"Unexpected error generating hour of day graph: {str(e)}"
            logging.error(error_msg)
            raise HourOfDayError(error_msg) from e
        finally:
            self.cleanup_figure()
