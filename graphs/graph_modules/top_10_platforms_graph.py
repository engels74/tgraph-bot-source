# graphs/graph_modules/top_10_platforms_graph.py

"""
Improved top 10 platforms graph generator with standardized error handling and resource management.
Handles generation of platform statistics graphs with proper validation, cleanup, and error handling.
"""

from .base_graph import BaseGraph
from .utils import validate_series_data
from config.modules.constants import ConfigKeyError
from config.modules.sanitizer import sanitize_user_id, InvalidUserIdError
from datetime import datetime
from matplotlib.ticker import MaxNLocator
from typing import Dict, Any, Optional, List, Union
import logging
import os


class PlatformsGraphError(Exception):
    """Base exception for platform graph-related errors."""
    pass

class DataFetchError(PlatformsGraphError):
    """Raised when there's an error fetching graph data."""
    pass

class DataValidationError(PlatformsGraphError):
    """Raised when data validation fails."""
    pass

class GraphGenerationError(PlatformsGraphError):
    """Raised when graph generation fails."""
    pass

class ResourceError(PlatformsGraphError):
    """Raised when there's an error managing graph resources."""
    pass

class Top10PlatformsGraph(BaseGraph):
    """Handles generation of top 10 platforms graphs."""
    
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        """
        Initialize the platforms graph handler.
        
        Args:
            config: Configuration dictionary
            translations: Translation strings dictionary
            img_folder: Path to image output folder
            
        Raises:
            ValueError: If required configuration is missing
        """
        super().__init__(config, translations, img_folder)
        self.graph_type = "top_10_platforms"
        self._verify_config()

    def _verify_config(self) -> None:
        """Verify required configuration exists."""
        required_keys = [
            'TIME_RANGE_DAYS',
            'ANNOTATE_TOP_10_PLATFORMS',
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

    def _validate_platform_data(self, platforms: List[str], series_data: List[List[int]]) -> None:
        """
        Validate platform-specific data.
        
        Args:
            platforms: List of platform names
            series_data: List of data series
            
        Raises:
            DataValidationError: If validation fails
        """
        try:
            if not platforms:
                raise DataValidationError("No platforms provided")

            if len(platforms) > 10:
                raise DataValidationError("More than 10 platforms in data")

            for data_series in series_data:
                if len(data_series) != len(platforms):
                    raise DataValidationError(
                        f"Data series length ({len(data_series)}) "
                        f"doesn't match platform count ({len(platforms)})"
                    )

            # Validate platform names
            for platform in platforms:
                if not isinstance(platform, str):
                    raise DataValidationError(f"Invalid platform name type: {type(platform)}")
                if not platform.strip():
                    raise DataValidationError("Empty platform name found")

            # Validate numeric data
            for data_series in series_data:
                for value in data_series:
                    if not isinstance(value, (int, float)):
                        raise DataValidationError(
                            f"Invalid data type in series: {type(value)}. Expected numeric value."
                        )
                    if value < 0:
                        raise DataValidationError(f"Negative value found in series: {value}")

        except Exception as e:
            raise DataValidationError(f"Platform data validation failed: {str(e)}") from e

    async def fetch_data(self, data_fetcher, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch top 10 platforms data.
        
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
                logging.debug("Using stored data for top 10 platforms")
                return self.data

            params = {"time_range": self.config["TIME_RANGE_DAYS"]}
            if user_id:
                params["user_id"] = sanitize_user_id(user_id)
            
            logging.debug("Fetching top 10 platforms data with params: %s", params)
            
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_top_10_platforms", params)
            if not data or 'response' not in data or 'data' not in data['response']:
                error_msg = self.translations.get(
                    'error_fetch_top_10_platforms_user' if user_id else 'error_fetch_top_10_platforms',
                    'Failed to fetch platforms data{}: {}'
                ).format(f" for user {user_id}" if user_id else "", "No data returned")
                logging.error(error_msg)
                raise DataFetchError(error_msg)

            return data['response']['data']

        except InvalidUserIdError as e:
            raise DataFetchError(f"Invalid user ID: {str(e)}") from e
        except Exception as e:
            error_msg = self.translations.get(
                'error_fetch_top_10_platforms',
                'Failed to fetch platforms data: {error}'
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
                raise DataValidationError(self.translations["error_missing_data_top_10_platforms"])

            platforms = raw_data['categories']
            series = raw_data['series']

            if not series:
                raise DataValidationError(self.translations["warning_empty_series_top_10_platforms"])

            # Validate series data
            validation_errors = validate_series_data(series, len(platforms), "platforms series")
            if validation_errors:
                raise DataValidationError("\n".join(validation_errors))

            # Additional platform-specific validation
            series_data = [serie["data"] for serie in series]
            self._validate_platform_data(platforms, series_data)

            processed_data = {
                "platforms": platforms,
                "tv_data": next((s["data"] for s in series if s["name"] == "TV"), []),
                "movie_data": next((s["data"] for s in series if s["name"] == "Movies"), [])
            }

            return processed_data

        except (ConfigKeyError, ValueError) as e:
            raise DataValidationError(f"Data validation failed: {str(e)}") from e
        except Exception as e:
            error_msg = f"Error processing platforms data: {str(e)}"
            logging.error(error_msg)
            raise DataValidationError(error_msg) from e

    def _add_bar_annotations(self, index: List[int], data: List[Union[int, float]], bottom: Optional[List[float]] = None) -> None:
        """Add value annotations to bars."""
        for i, value in enumerate(data):
            if value > 0:
                y_pos = value/2
                if bottom is not None:
                    y_pos += bottom[i]
                self.annotate(i, y_pos, str(int(value)))

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
            index = range(len(processed_data["platforms"]))

            # Plot movie data
            self.ax.bar(
                index,
                processed_data["movie_data"],
                bar_width,
                label="Movies",
                color=self.get_color("Movies")
            )

            # Plot TV data stacked on top
            self.ax.bar(
                index,
                processed_data["tv_data"],
                bar_width,
                bottom=processed_data["movie_data"],
                label="TV",
                color=self.get_color("TV")
            )

            if self.config.get("ANNOTATE_TOP_10_PLATFORMS", False):
                # Annotate individual values
                self._add_bar_annotations(index, processed_data["movie_data"])
                self._add_bar_annotations(index, processed_data["tv_data"], processed_data["movie_data"])
                
                # Annotate totals
                for i in range(len(index)):
                    total = processed_data["movie_data"][i] + processed_data["tv_data"][i]
                    self.annotate(i, total, str(int(total)))

            self.add_title(self.translations["top_10_platforms_title"].format(
                days=self.config["TIME_RANGE_DAYS"]
            ))
            self.add_labels(
                self.translations["top_10_platforms_xlabel"],
                self.translations["top_10_platforms_ylabel"]
            )

            self.ax.set_xticks(index)
            self.ax.set_xticklabels(processed_data["platforms"], rotation=45, ha="right")
            self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            self.add_legend()
            self.apply_tight_layout()

        except Exception as e:
            error_msg = f"Error plotting platforms graph: {str(e)}"
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
            PlatformsGraphError: If graph generation fails
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
                
            file_name = f"top_10_platforms{'_' + safe_user_id if safe_user_id else ''}.png"
            file_path = os.path.join(base_dir, file_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)
            
            logging.debug("Saved platforms graph: %s", file_path)
            return file_path

        except (DataFetchError, DataValidationError, GraphGenerationError) as e:
            logging.error(str(e))
            return None
        except Exception as e:
            error_msg = f"Unexpected error generating platforms graph: {str(e)}"
            logging.error(error_msg)
            raise PlatformsGraphError(error_msg) from e
        finally:
            self.cleanup_figure()
