# graphs/graph_modules/play_count_by_month_graph.py

from .base_graph import BaseGraph
from .utils import validate_series_data
from config.modules.sanitizer import sanitize_user_id, InvalidUserIdError
from datetime import datetime
from matplotlib.ticker import MaxNLocator
from typing import Dict, Any, Optional, List
import logging
import os

class PlayCountByMonthError(Exception):
    """Base exception for PlayCountByMonth graph-specific errors."""
    pass

class DataValidationError(PlayCountByMonthError):
    """Raised when data validation fails."""
    pass

class GraphGenerationError(PlayCountByMonthError):
    """Raised when graph generation fails."""
    pass

class FileSystemError(PlayCountByMonthError):
    """Raised when there are file system related errors."""
    pass

class PlayCountByMonthGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "play_count_by_month"

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
        Fetch play count data by month.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific data
            
        Returns:
            The fetched data or None if fetching fails
            
        Raises:
            PlayCountByMonthError: If data fetching fails
        """
        try:
            if self.data is not None:
                logging.debug("Using stored data for play count by month")
                return self.data

            params = {"time_range": 12, "y_axis": "plays"}
            if user_id:
                try:
                    sanitized_user_id = sanitize_user_id(user_id)
                    params["user_id"] = sanitized_user_id
                except InvalidUserIdError as e:
                    logging.error(f"Invalid user ID format: {e}")
                    raise DataValidationError("Invalid user ID format") from e
            
            logging.debug("Fetching play count by month data with params: %s", params)
            
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_per_month", params)
            if not data or 'response' not in data or 'data' not in data['response']:
                error_msg = self.translations["error_fetch_play_count_month"]
                if user_id:
                    error_msg = self.translations.get(
                        'error_fetch_play_count_month_user',
                        'Failed to fetch play count by month data for user {user_id}: {error}'
                    ).format(user_id=user_id, error="No data returned")
                logging.error(error_msg)
                raise DataValidationError(error_msg)

            return data['response']['data']
            
        except DataValidationError:
            raise
        except Exception as e:
            error_msg = f"Error fetching play count by month data: {str(e)}"
            logging.error(error_msg)
            raise PlayCountByMonthError(error_msg) from e

    def validate_series_data(self, series: List[Dict[str, Any]], month_count: int) -> List[str]:
        """
        Validate series data for completeness and consistency.
        
        Args:
            series: List of series data dictionaries
            month_count: Expected number of data points per series
            
        Returns:
            List of validation error messages, empty if validation passes
        """
        return validate_series_data(series, month_count, "monthly series")

    def process_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process the raw data for plotting.
        
        Args:
            raw_data: Raw data from the API
            
        Returns:
            Processed data ready for plotting or None if validation fails
            
        Raises:
            DataValidationError: If processing fails with an unexpected error
        """
        try:
            if not isinstance(raw_data, dict) or 'categories' not in raw_data or 'series' not in raw_data:
                logging.error(self.translations["error_missing_data_play_count_by_month"])
                return None

            months = raw_data['categories']
            series = raw_data['series']

            if not months or not series:
                logging.error(self.translations["warning_empty_data_play_count_by_month"])
                return None

            # Validate series data
            validation_errors = self.validate_series_data(series, len(months))
            if validation_errors:
                for error in validation_errors:
                    logging.error("%s", error)
                return None

            processed_data = self._process_series_data(months, series)
            if not processed_data["months"]:
                logging.error(self.translations["warning_no_play_data_play_count_by_month"])
                return None

            return processed_data

        except Exception as e:
            error_msg = f"Error processing monthly play count data: {str(e)}"
            logging.error(error_msg)
            raise DataValidationError(error_msg) from e

    def _process_series_data(self, months: List[str], series: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        """
        Process series data and filter out months with zero plays.
        
        Args:
            months: List of month labels
            series: List of series data dictionaries
            
        Returns:
            Dictionary containing processed series data
        """
        tv_data = next((s["data"] for s in series if s["name"] == "TV"), [0] * len(months))
        movie_data = next((s["data"] for s in series if s["name"] == "Movies"), [0] * len(months))

        processed_data = {
            "months": [],
            "tv_data": [],
            "movie_data": []
        }

        # Filter out months with zero plays for both TV and movies
        for i, month in enumerate(months):
            if tv_data[i] > 0 or movie_data[i] > 0:
                processed_data["months"].append(month)
                processed_data["tv_data"].append(tv_data[i])
                processed_data["movie_data"].append(movie_data[i])

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

            bar_width = 0.75
            index = range(len(processed_data["months"]))

            # Plot movie data first
            self.ax.bar(index, processed_data["movie_data"], 
                       bar_width, label="Movies",
                       color=self.get_color("Movies"))

            # Plot TV data stacked on top
            self.ax.bar(index, processed_data["tv_data"], 
                       bar_width, bottom=processed_data["movie_data"],
                       label="TV", color=self.get_color("TV"))

            # Add annotations if enabled
            if self.config.get("ANNOTATE_PLAY_COUNT_BY_MONTH", False):
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
                    if total > 0:
                        self.annotate(i, total, str(int(total)))

            self.add_title(self.translations["play_count_by_month_title"])
            self.add_labels(
                self.translations["play_count_by_month_xlabel"],
                self.translations["play_count_by_month_ylabel"]
            )

            self.ax.set_xticks(index)
            self.ax.set_xticklabels(processed_data["months"], rotation=45, ha="right")
            self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            self.add_legend()
            self.apply_tight_layout()
            
        except Exception as e:
            logging.error(f"Error plotting monthly play count graph: {str(e)}")
            raise GraphGenerationError(f"Failed to plot graph: {str(e)}")

    async def generate(self, data_fetcher, user_id: Optional[str] = None) -> Optional[str]:
        """
        Generate the graph and return its file path.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific graphs
            
        Returns:
            The file path of the generated graph, or None if generation fails
            
        Raises:
            GraphGenerationError: If graph generation fails
            FileSystemError: If file system operations fail
        """
        try:
            logging.debug("Generate called with stored data: %s", "present" if self.data else "none")

            data = await self.fetch_data(data_fetcher, user_id)
            if data is None:
                raise DataValidationError("Failed to fetch monthly play count data")

            processed_data = self.process_data(data)
            if processed_data is None:
                raise DataValidationError("Failed to process monthly play count data")

            self.plot(processed_data)

            today = datetime.today().strftime("%Y-%m-%d")
            base_dir = os.path.join(self.img_folder, today)
            
            # Add sanitized user_id handling for directory and filename
            if user_id:
                try:
                    safe_user_id = self._process_filename(user_id)
                    if safe_user_id:
                        base_dir = os.path.join(base_dir, f"user_{safe_user_id}")
                        file_name = f"play_count_by_month_{safe_user_id}.png"
                    else:
                        file_name = "play_count_by_month.png"
                except InvalidUserIdError as e:
                    logging.error(f"Invalid user ID for file path: {e}")
                    raise FileSystemError("Invalid user ID for file path") from e
            else:
                file_name = "play_count_by_month.png"
                    
            file_path = os.path.join(base_dir, file_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)
            
            logging.debug("Saved monthly play count graph: %s", file_path)
            return file_path
            
        except (DataValidationError, PlayCountByMonthError, FileSystemError):
            raise
        except Exception as e:
            error_msg = f"Error generating monthly play count graph: {str(e)}"
            logging.error(error_msg)
            raise GraphGenerationError(error_msg) from e
