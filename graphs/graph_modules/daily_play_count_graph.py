# graphs/graph_modules/daily_play_count_graph.py

"""
Improved daily play count graph generator with standardized error handling and resource management.
Handles generation of daily play count graphs with proper validation, cleanup, and error handling.
"""

from .base_graph import BaseGraph
from .utils import get_color, validate_series_data
from config.modules.sanitizer import sanitize_user_id, InvalidUserIdError
from datetime import datetime
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MaxNLocator
from typing import Dict, Any, Optional, List, Union
import logging
import os

class DailyPlayCountError(Exception):
    """Base exception for daily play count graph-related errors."""
    pass

class DataFetchError(DailyPlayCountError):
    """Raised when there's an error fetching graph data."""
    pass

class DataValidationError(DailyPlayCountError):
    """Raised when data validation fails."""
    pass

class GraphGenerationError(DailyPlayCountError):
    """Raised when graph generation fails."""
    pass

class ResourceError(DailyPlayCountError):
    """Raised when there's an error managing graph resources."""
    pass

class DailyPlayCountGraph(BaseGraph):
    """Handles generation of daily play count graphs."""
    
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        """
        Initialize the daily play count graph handler.
        
        Args:
            config: Configuration dictionary
            translations: Translation strings dictionary
            img_folder: Path to image output folder
            
        Raises:
            ValueError: If required configuration is missing
        """
        super().__init__(config, translations, img_folder)
        self.graph_type = "daily_play_count"
        self._verify_config()
        
    def _verify_config(self) -> None:
        """Verify required configuration exists."""
        required_keys = [
            'TIME_RANGE_DAYS',
            'ANNOTATE_DAILY_PLAY_COUNT',
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

    def _validate_dates(self, dates: List[str]) -> List[datetime]:
        """
        Validate and convert date strings to datetime objects.
        
        Args:
            dates: List of date strings
            
        Returns:
            List of validated datetime objects
            
        Raises:
            DataValidationError: If date validation fails
        """
        try:
            datetime_dates = []
            for date in dates:
                try:
                    dt = datetime.strptime(date, "%Y-%m-%d")
                    datetime_dates.append(dt)
                except ValueError as e:
                    raise DataValidationError(f"Invalid date format: {date}") from e
            
            # Sort dates to ensure correct date range calculation
            datetime_dates.sort()
                    
            # Validate date range
            if datetime_dates:
                date_range = (datetime_dates[-1] - datetime_dates[0]).days
                if date_range > 365:  # Maximum 1 year range
                    raise DataValidationError("Date range exceeds maximum allowed (365 days)")
                    
            return datetime_dates
            
        except Exception as e:
            raise DataValidationError(f"Date validation failed: {str(e)}") from e

    async def fetch_data(self, data_fetcher, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch daily play count data.
        
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
                logging.debug("Using stored data for daily play count")
                return self.data

            params = {"time_range": self.config["TIME_RANGE_DAYS"]}
            if user_id:
                params["user_id"] = sanitize_user_id(user_id)
            
            logging.debug("Fetching daily play count data with params: %s", params)
            
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_date", params)
            if not data or 'response' not in data or 'data' not in data['response']:
                error_msg = self.translations.get(
                    'error_fetch_daily_play_count_user' if user_id else 'error_fetch_daily_play_count',
                    'Failed to fetch daily play count data{}: {}'
                ).format(f" for user {user_id}" if user_id else "", "No data returned")
                logging.error(error_msg)
                raise DataFetchError(error_msg)

            return data['response']['data']

        except InvalidUserIdError as e:
            raise DataFetchError(f"Invalid user ID: {str(e)}") from e
        except Exception as e:
            error_msg = self.translations.get(
                'error_fetch_daily_play_count',
                'Failed to fetch daily play count data: {error}'
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
            if not isinstance(raw_data, dict) or 'categories' not in raw_data or 'series' not in raw_data:
                raise DataValidationError(self.translations["error_missing_series_daily_play_count"])

            # Validate dates and convert to datetime objects
            datetime_dates = self._validate_dates(raw_data['categories'])
            series = raw_data['series']

            if not series:
                raise DataValidationError(self.translations["warning_empty_series_daily_play_count"])

            # Validate series data
            validation_errors = validate_series_data(series, len(datetime_dates), "daily series")
            if validation_errors:
                raise DataValidationError("\n".join(validation_errors))

            processed_data = {
                "dates": datetime_dates,
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
            error_msg = f"Error processing daily play count data: {str(e)}"
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
                    processed_data["dates"],
                    serie["data"],
                    label=serie["name"],
                    marker="o",
                    color=serie["color"]
                )

                if self.config.get("ANNOTATE_DAILY_PLAY_COUNT", False):
                    self._add_annotations(processed_data["dates"], serie["data"])

            self.add_title(self.translations["daily_play_count_title"].format(
                days=self.config["TIME_RANGE_DAYS"]
            ))
            self.add_labels(
                self.translations["daily_play_count_xlabel"],
                self.translations["daily_play_count_ylabel"]
            )

            self.ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
            self.ax.tick_params(axis='x', rotation=45)
            self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            self.add_legend()
            self.apply_tight_layout()

        except Exception as e:
            error_msg = f"Error plotting daily play count graph: {str(e)}"
            logging.error(error_msg)
            raise GraphGenerationError(error_msg) from e

    def _add_annotations(self, dates: List[datetime], values: List[Union[int, float]]) -> None:
        """Add value annotations to the graph points."""
        for date, value in zip(dates, values):
            if value > 0:
                self.annotate(date, value, f"{int(value)}")

    async def generate(self, data_fetcher, user_id: Optional[str] = None) -> Optional[str]:
        """
        Generate the graph and return its file path.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific graphs
            
        Returns:
            The file path of the generated graph, or None if generation fails
            
        Raises:
            DailyPlayCountError: If graph generation fails
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
                
            file_name = f"daily_play_count{'_' + safe_user_id if safe_user_id else ''}.png"
            file_path = os.path.join(base_dir, file_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)
            
            logging.debug("Saved daily play count graph: %s", file_path)
            return file_path

        except (DataFetchError, DataValidationError, GraphGenerationError) as e:
            logging.error(str(e))
            return None
        except Exception as e:
            error_msg = f"Unexpected error generating daily play count graph: {str(e)}"
            logging.error(error_msg)
            raise DailyPlayCountError(error_msg) from e
        finally:
            self.cleanup_figure()
