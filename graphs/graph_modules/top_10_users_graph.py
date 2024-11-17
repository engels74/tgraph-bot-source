# graphs/graph_modules/top_10_users_graph.py

"""
Improved top 10 users graph generator with standardized error handling and resource management.
Handles generation of user statistics graphs with proper validation, cleanup, and error handling.
"""

from .base_graph import BaseGraph
from .utils import validate_series_data, censor_username
from config.modules.constants import ConfigKeyError
from datetime import datetime
from matplotlib.ticker import MaxNLocator
from typing import Dict, Any, Optional, List, Union
import logging
import os

class UsersGraphError(Exception):
    """Base exception for user graph-related errors."""
    pass

class DataFetchError(UsersGraphError):
    """Raised when there's an error fetching graph data."""
    pass

class DataValidationError(UsersGraphError):
    """Raised when data validation fails."""
    pass

class GraphGenerationError(UsersGraphError):
    """Raised when graph generation fails."""
    pass

class ResourceError(UsersGraphError):
    """Raised when there's an error managing graph resources."""
    pass

class Top10UsersGraph(BaseGraph):
    """Handles generation of top 10 users graphs."""
    
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        """
        Initialize the users graph handler.
        
        Args:
            config: Configuration dictionary
            translations: Translation strings dictionary
            img_folder: Path to image output folder
            
        Raises:
            ValueError: If required configuration is missing
        """
        super().__init__(config, translations, img_folder)
        self.graph_type = "top_10_users"
        self._verify_config()
        
    def _verify_config(self) -> None:
        """Verify required configuration exists."""
        required_keys = [
            'TIME_RANGE_DAYS',
            'ANNOTATE_TOP_10_USERS',
            'TV_COLOR',
            'MOVIE_COLOR',
            'GRAPH_BACKGROUND_COLOR',
            'CENSOR_USERNAMES'
        ]
        missing = [key for key in required_keys if key not in self.config]
        if missing:
            raise ValueError(f"Missing required configuration keys: {missing}")

    def _validate_user_data(self, users: List[str], series_data: List[List[int]]) -> None:
        """
        Validate user-specific data.
        
        Args:
            users: List of usernames
            series_data: List of data series
            
        Raises:
            DataValidationError: If validation fails
        """
        try:
            if not users:
                raise DataValidationError("No users provided")

            if len(users) > 10:
                raise DataValidationError("More than 10 users in data")

            for data_series in series_data:
                if len(data_series) != len(users):
                    raise DataValidationError(
                        f"Data series length ({len(data_series)}) "
                        f"doesn't match user count ({len(users)})"
                    )

            # Validate usernames
            for username in users:
                if not isinstance(username, str):
                    raise DataValidationError(f"Invalid username type: {type(username)}")
                if not username.strip():
                    raise DataValidationError("Empty username found")

        except Exception as e:
            raise DataValidationError(f"User data validation failed: {str(e)}") from e

    async def fetch_data(self, data_fetcher, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch top 10 users data.
        
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
                logging.debug("Using stored data for top 10 users")
                return self.data

            params = {"time_range": self.config["TIME_RANGE_DAYS"]}
            logging.debug("Fetching top 10 users data with params: %s", params)
            
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_top_10_users", params)
            if not data or 'response' not in data or 'data' not in data['response']:
                error_msg = self.translations.get(
                    'error_fetch_top_10_users',
                    'Failed to fetch top 10 users data: {error}'
                ).format(error="No data returned")
                logging.error(error_msg)
                raise DataFetchError(error_msg)

            return data['response']['data']
            
        except Exception as e:
            error_msg = self.translations.get(
                'error_fetch_top_10_users',
                'Failed to fetch top 10 users data: {error}'
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
                raise DataValidationError(self.translations["error_missing_data_top_10_users"])

            users = raw_data['categories']
            series = raw_data['series']

            if not series:
                raise DataValidationError(self.translations["warning_empty_series_top_10_users"])

            # Validate series data
            validation_errors = validate_series_data(series, len(users), "users series")
            if validation_errors:
                raise DataValidationError("\n".join(validation_errors))

            # Additional user-specific validation
            series_data = [serie["data"] for serie in series]
            self._validate_user_data(users, series_data)

            # Apply username censoring if enabled
            censored_users = [
                censor_username(user, self.config["CENSOR_USERNAMES"])
                for user in users
            ]

            processed_data = {
                "users": censored_users,
                "tv_data": next((s["data"] for s in series if s["name"] == "TV"), []),
                "movie_data": next((s["data"] for s in series if s["name"] == "Movies"), [])
            }

            return processed_data

        except (ValueError, ConfigKeyError) as e:
            raise DataValidationError(f"Data validation failed: {str(e)}") from e
        except Exception as e:
            error_msg = f"Error processing users data: {str(e)}"
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
            index = range(len(processed_data["users"]))

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

            if self.config.get("ANNOTATE_TOP_10_USERS", False):
                # Annotate individual values
                self._add_bar_annotations(index, processed_data["movie_data"])
                self._add_bar_annotations(index, processed_data["tv_data"], processed_data["movie_data"])
                
                # Annotate totals
                for i in range(len(index)):
                    total = processed_data["movie_data"][i] + processed_data["tv_data"][i]
                    self.annotate(i, total, str(int(total)))

            self.add_title(self.translations["top_10_users_title"].format(
                days=self.config["TIME_RANGE_DAYS"]
            ))
            self.add_labels(
                self.translations["top_10_users_xlabel"],
                self.translations["top_10_users_ylabel"]
            )

            self.ax.set_xticks(index)
            self.ax.set_xticklabels(processed_data["users"], rotation=45, ha="right")
            self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            self.add_legend()
            self.apply_tight_layout()

        except Exception as e:
            error_msg = f"Error plotting users graph: {str(e)}"
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
            UsersGraphError: If graph generation fails
        """
        try:
            data = await self.fetch_data(data_fetcher)  # Note: user_id not used for top 10 users
            processed_data = self.process_data(data)
            self.plot(processed_data)

            # Create directories and save graph
            today = datetime.today().strftime("%Y-%m-%d")
            base_dir = os.path.join(self.img_folder, today)
            file_path = os.path.join(base_dir, "top_10_users.png")
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)
            
            logging.debug("Saved users graph: %s", file_path)
            return file_path

        except (DataFetchError, DataValidationError, GraphGenerationError) as e:
            logging.error(str(e))
            return None
        except Exception as e:
            error_msg = f"Unexpected error generating users graph: {str(e)}"
            logging.error(error_msg)
            raise UsersGraphError(error_msg) from e
        finally:
            self.cleanup_figure()
