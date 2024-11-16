# graphs/graph_modules/play_count_by_month_graph.py

"""
Play Count by Month graph generator with enhanced error handling and resource management.
Handles generation of monthly play count graphs with proper validation and cleanup.
"""

from .base_graph import BaseGraph
from .utils import validate_series_data
from config.modules.sanitizer import sanitize_user_id, InvalidUserIdError
from datetime import datetime
from matplotlib.ticker import MaxNLocator
from typing import Dict, Any, Optional, List
import logging
import os

class MonthlyGraphError(Exception):
    """Base exception for monthly graph-related errors."""
    pass

class DataFetchError(MonthlyGraphError):
    """Raised when there's an error fetching graph data."""
    pass

class DataValidationError(MonthlyGraphError):
    """Raised when data validation fails."""
    pass

class GraphGenerationError(MonthlyGraphError):
    """Raised when graph generation fails."""
    pass

class ResourceError(MonthlyGraphError):
    """Raised when there's an error managing graph resources."""
    pass

class PlayCountByMonthGraph(BaseGraph):
    """Handles generation of monthly play count graphs."""
    
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        """
        Initialize the monthly graph handler.
        
        Args:
            config: Configuration dictionary
            translations: Translation strings dictionary
            img_folder: Path to image output folder
            
        Raises:
            ValueError: If required configuration is missing
        """
        super().__init__(config, translations, img_folder)
        self.graph_type = "play_count_by_month"
        self._verify_config()
        
    def _verify_config(self) -> None:
        """Verify required configuration exists."""
        required_keys = [
            'ANNOTATE_PLAY_COUNT_BY_MONTH',
            'TV_COLOR',
            'MOVIE_COLOR',
            'GRAPH_BACKGROUND_COLOR',
            'ANNOTATION_COLOR',
            'ANNOTATION_OUTLINE_COLOR'
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

    def _validate_time_range(self, months: List[str]) -> None:
        """
        Validate the time range of the monthly data.
        
        Args:
            months: List of month strings
            
        Raises:
            DataValidationError: If validation fails
        """
        if not months:
            raise DataValidationError("Empty months list")
        
        try:
            parsed_dates = []
            for month in months:
                try:
                    # Try YYYY-MM format first
                    parsed = datetime.strptime(month, "%Y-%m")
                except ValueError:
                    try:
                        # Try MMM YYYY format (e.g. "Dec 2023")
                        parsed = datetime.strptime(month, "%b %Y")
                    except ValueError:
                        # Try MMMM YYYY format (e.g. "December 2023")
                        try:
                            parsed = datetime.strptime(month, "%B %Y")
                        except ValueError as e:
                            raise DataValidationError(f"Invalid month format: {month}") from e
                parsed_dates.append(parsed)
                
            # Check time range is reasonable
            first_month = min(parsed_dates)
            last_month = max(parsed_dates)
            month_diff = (last_month.year - first_month.year) * 12 + (last_month.month - first_month.month)
            
            if month_diff > 24:  # Maximum 2 years range
                raise DataValidationError("Time range exceeds maximum allowed (24 months)")
                
        except ValueError as e:
            raise DataValidationError(f"Invalid month format: {str(e)}") from e

    async def fetch_data(self, data_fetcher, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch monthly play count data.
        
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
                logging.debug("Using stored data for monthly play count")
                return self.data

            params = {"time_range": 12, "y_axis": "plays"}
            if user_id:
                params["user_id"] = sanitize_user_id(user_id)
            
            logging.debug("Fetching monthly play count data with params: %s", params)
            
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_per_month", params)
            if not data or 'response' not in data or 'data' not in data['response']:
                error_msg = self.translations.get(
                    'error_fetch_play_count_month_user' if user_id else 'error_fetch_play_count_month',
                    'Failed to fetch monthly play count data{}: {}'
                ).format(f" for user {user_id}" if user_id else "", "No data returned")
                logging.error(error_msg)
                raise DataFetchError(error_msg)

            # Additional data validation
            response_data = data['response']['data']
            if not isinstance(response_data, dict) or 'series' not in response_data:
                raise DataValidationError("Invalid API response format")

            return response_data

        except InvalidUserIdError as e:
            raise DataFetchError(f"Invalid user ID: {str(e)}") from e
        except Exception as e:
            error_msg = self.translations.get(
                'error_fetch_play_count_month',
                'Failed to fetch monthly play count data: {error}'
            ).format(error=str(e))
            logging.error(error_msg)
            raise DataFetchError(error_msg) from e

    def _process_series_data(self, series: List[Dict[str, Any]], months: List[str]) -> Dict[str, Any]:
        """
        Process series data and filter out months with zero plays.
        
        Args:
            series: List of series data dictionaries
            months: List of month labels
            
        Returns:
            Dictionary containing processed series data
            
        Raises:
            DataValidationError: If processing fails
        """
        try:
            tv_data = next((s["data"] for s in series if s["name"] == "TV"), [0] * len(months))
            movie_data = next((s["data"] for s in series if s["name"] == "Movies"), [0] * len(months))

            if len(tv_data) != len(months) or len(movie_data) != len(months):
                raise DataValidationError("Series data length mismatch with months")

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

            if not processed_data["months"]:
                raise DataValidationError("No non-zero data points found")

            return processed_data

        except Exception as e:
            raise DataValidationError(f"Failed to process series data: {str(e)}") from e

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
                raise DataValidationError(self.translations["error_missing_data_play_count_by_month"])

            months = raw_data['categories']
            series = raw_data['series']

            if not months or not series:
                raise DataValidationError(self.translations["warning_empty_data_play_count_by_month"])

            # Validate time range
            self._validate_time_range(months)

            # Validate series data
            validation_errors = validate_series_data(series, len(months), "monthly series")
            if validation_errors:
                raise DataValidationError("\n".join(validation_errors))

            processed_data = self._process_series_data(series, months)
            if not processed_data["months"]:
                raise DataValidationError(self.translations["warning_no_play_data_play_count_by_month"])

            return processed_data

        except DataValidationError:
            raise
        except Exception as e:
            error_msg = f"Error processing monthly play count data: {str(e)}"
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

            index = range(len(processed_data["months"]))
            bar_width = 0.75

            # Plot stacked bars
            self.ax.bar(
                index, 
                processed_data["movie_data"],
                bar_width,
                label="Movies",
                color=self.get_color("Movies")
            )

            self.ax.bar(
                index,
                processed_data["tv_data"],
                bar_width,
                bottom=processed_data["movie_data"],
                label="TV",
                color=self.get_color("TV")
            )

            if self.config.get("ANNOTATE_PLAY_COUNT_BY_MONTH", False):
                self._add_annotations(index, processed_data)

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
            error_msg = f"Error plotting monthly play count graph: {str(e)}"
            logging.error(error_msg)
            raise GraphGenerationError(error_msg) from e

    def _add_annotations(self, index: range, data: Dict[str, Any]) -> None:
        """Add value annotations to the graph bars."""
        for i in range(len(index)):
            movie_value = data["movie_data"][i]
            tv_value = data["tv_data"][i]
            total = movie_value + tv_value

            if movie_value > 0:
                self.annotate(i, movie_value/2, str(int(movie_value)))

            if tv_value > 0:
                self.annotate(i, movie_value + tv_value/2, str(int(tv_value)))

            if total > 0:
                self.annotate(i, total, str(int(total)))

    async def generate(self, data_fetcher, user_id: Optional[str] = None) -> Optional[str]:
        """
        Generate the graph and return its file path.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific graphs
            
        Returns:
            The file path of the generated graph, or None if generation fails
            
        Raises:
            MonthlyGraphError: If graph generation fails
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
                
            file_name = f"play_count_by_month{'_' + safe_user_id if safe_user_id else ''}.png"
            file_path = os.path.join(base_dir, file_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)
            
            logging.debug("Saved monthly play count graph: %s", file_path)
            return file_path

        except (DataFetchError, DataValidationError, GraphGenerationError) as e:
            logging.error(str(e))
            return None
        except Exception as e:
            error_msg = f"Unexpected error generating monthly play count graph: {str(e)}"
            logging.error(error_msg)
            raise MonthlyGraphError(error_msg) from e
        finally:
            self.cleanup_figure()
