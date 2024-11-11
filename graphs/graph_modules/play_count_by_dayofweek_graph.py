# graphs/graph_modules/play_count_by_dayofweek_graph.py

"""
Improved version of play_count_by_dayofweek_graph.py with standardized error handling
and resource management. Handles generation of play count graphs by day of week.
"""

from .base_graph import BaseGraph
from .utils import get_color, validate_series_data
from config.modules.sanitizer import sanitize_user_id, InvalidUserIdError
from datetime import datetime
from matplotlib.ticker import MaxNLocator
from typing import Dict, Any, Optional
import logging
import os

class DayOfWeekGraphError(Exception):
    """Base exception for day of week graph-related errors."""
    pass

class DataFetchError(DayOfWeekGraphError):
    """Raised when there's an error fetching graph data."""
    pass

class DataValidationError(DayOfWeekGraphError):
    """Raised when data validation fails."""
    pass

class GraphGenerationError(DayOfWeekGraphError):
    """Raised when graph generation fails."""
    pass

class ResourceError(DayOfWeekGraphError):
    """Raised when there's an error managing graph resources."""
    pass

class PlayCountByDayOfWeekGraph(BaseGraph):
    """Handles generation of play count graphs by day of week."""
    
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        """
        Initialize the day of week graph handler.
        
        Args:
            config: Configuration dictionary
            translations: Translation strings dictionary
            img_folder: Path to image output folder
            
        Raises:
            ValueError: If required configuration is missing
        """
        super().__init__(config, translations, img_folder)
        self.graph_type = "play_count_by_dayofweek"
        self._verify_config()
        
    def _verify_config(self) -> None:
        """Verify required configuration exists."""
        required_keys = [
            'TIME_RANGE_DAYS',
            'ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK',
            'TV_COLOR',
            'MOVIE_COLOR'
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

    async def fetch_data(self, data_fetcher, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch play count data by day of week.
        
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
                logging.debug("Using stored data for play count by day of week")
                return self.data

            params = {"time_range": self.config["TIME_RANGE_DAYS"]}
            if user_id:
                params["user_id"] = sanitize_user_id(user_id)
            
            logging.debug("Fetching play count by day of week data with params: %s", params)
            
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_dayofweek", params)
            if not data or 'response' not in data or 'data' not in data['response']:
                error_msg = self.translations.get(
                    'error_fetch_play_count_dayofweek_user' if user_id else 'error_fetch_play_count_dayofweek',
                    'Failed to fetch play count by day of week data{}: {}'
                ).format(f" for user {user_id}" if user_id else "", "No data returned")
                logging.error(error_msg)
                raise DataFetchError(error_msg)

            return data['response']['data']

        except InvalidUserIdError as e:
            raise DataFetchError(f"Invalid user ID: {str(e)}") from e
        except Exception as e:
            error_msg = self.translations.get(
                'error_fetch_play_count_dayofweek',
                'Failed to fetch day of week data: {error}'
            ).format(error=str(e))
            logging.error(error_msg)
            raise DataFetchError(error_msg) from e

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the raw data into a format suitable for plotting.
        
        Args:
            data: Raw data from the API
            
        Returns:
            Processed data ready for plotting
            
        Raises:
            DataValidationError: If data validation fails
        """
        try:
            if 'series' not in data:
                error_msg = self.translations["error_missing_series_play_count_by_dayofweek"]
                logging.error(error_msg)
                raise DataValidationError(error_msg)

            series = data['series']
            if not series:
                error_msg = self.translations["warning_empty_series_play_count_by_dayofweek"]
                logging.warning(error_msg)
                raise DataValidationError(error_msg)

            days = list(range(7))
            day_labels = [self.translations.get(f"day_{i}", f"Day {i}") for i in range(7)]

            validation_errors = validate_series_data(series, len(days), "day of week series")
            if validation_errors:
                error_msg = "\n".join(validation_errors)
                logging.error(error_msg)
                raise DataValidationError(error_msg)

            processed_data = {
                "days": days,
                "day_labels": day_labels,
                "series": []
            }

            for serie in series:
                try:
                    processed_data["series"].append({
                        "name": serie["name"],
                        "data": serie["data"],
                        "color": get_color(serie["name"], self.config)
                    })
                except KeyError as e:
                    raise DataValidationError(f"Missing required field in series data: {e}") from e
                except ValueError as e:
                    raise DataValidationError(f"Invalid value in series data: {e}") from e

            return processed_data

        except (KeyError, ValueError) as e:
            raise DataValidationError(f"Data validation failed: {str(e)}") from e
        except Exception as e:
            error_msg = f"Failed to process day of week data: {str(e)}"
            logging.error(error_msg)
            raise DataValidationError(error_msg) from e

    def plot(self, processed_data: Dict[str, Any]) -> None:
        """
        Plot the processed data.
        
        Args:
            processed_data: Processed data ready for plotting
            
        Raises:
            GraphGenerationError: If plotting fails
            ResourceError: If resource management fails
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
            self.ax.set_xticklabels(processed_data["day_labels"])
            self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            self.add_legend()
            self.apply_tight_layout()

        except Exception as e:
            error_msg = f"Error plotting graph: {str(e)}"
            logging.error(error_msg)
            raise GraphGenerationError(error_msg) from e

    async def generate(self, data_fetcher, user_id: Optional[str] = None) -> Optional[str]:
        """
        Generate the graph and return its file path.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific graphs
            
        Returns:
            The file path of the generated graph, or None if generation fails
            
        Raises:
            DayOfWeekGraphError: If graph generation fails
        """
        try:
            data = await self.fetch_data(data_fetcher, user_id)
            processed_data = self.process_data(data)
            self.plot(processed_data)

            # Save the graph with proper path handling
            today = datetime.today().strftime("%Y-%m-%d")
            base_dir = os.path.join(self.img_folder, today)
            
            safe_user_id = self._process_filename(user_id) if user_id else None
            if safe_user_id:
                base_dir = os.path.join(base_dir, f"user_{safe_user_id}")
                
            file_name = f"play_count_by_dayofweek{'_' + safe_user_id if safe_user_id else ''}.png"
            file_path = os.path.join(base_dir, file_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)
            
            logging.debug("Saved play count by day of week graph: %s", file_path)
            return file_path

        except (DataFetchError, DataValidationError, InvalidUserIdError) as e:
            logging.error(f"Failed to generate day of week graph: {str(e)}")
            return None
        except Exception as e:
            error_msg = f"Unexpected error generating day of week graph: {str(e)}"
            logging.error(error_msg)
            raise DayOfWeekGraphError(error_msg) from e
        finally:
            self.cleanup_figure()
