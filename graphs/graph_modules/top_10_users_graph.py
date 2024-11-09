# graphs/graph_modules/top_10_users_graph.py

from .base_graph import BaseGraph
from .utils import censor_username
from typing import Dict, Any, Optional
import logging
import os
from datetime import datetime
from matplotlib.ticker import MaxNLocator

class Top10UsersError(Exception):
    """Base exception for Top10Users graph-specific errors."""
    pass

class DataValidationError(Top10UsersError):
    """Raised when data validation fails."""
    pass

class GraphGenerationError(Top10UsersError):
    """Raised when graph generation fails."""
    pass

class Top10UsersGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "top_10_users"

    async def fetch_data(self, data_fetcher, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch top 10 users data.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific data
            
        Returns:
            The fetched data
            
        Raises:
            Top10UsersError: If data fetching fails
        """
        try:
            # If we have stored data, use it instead of fetching
            if self.data is not None:
                logging.debug("Using stored data for top 10 users")
                return self.data

            # Otherwise, fetch new data
            params = {"time_range": self.config["TIME_RANGE_DAYS"]}
            logging.debug("Fetching top 10 users data with params: %s", params)
            
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_top_10_users", params)
            if not data or 'response' not in data or 'data' not in data['response']:
                error_msg = self.translations["error_fetch_top_10_users"]
                logging.error(error_msg)
                raise Top10UsersError(error_msg)

            return data['response']['data']
            
        except (KeyError, TypeError) as e:
            error_msg = f"Error in data structure: {str(e)}"
            logging.error(error_msg)
            raise Top10UsersError(error_msg) from e
        except ValueError as e:
            error_msg = f"Invalid value in data: {str(e)}"
            logging.error(error_msg)
            raise Top10UsersError(error_msg) from e

    def process_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the raw data into a format suitable for plotting.
        
        Args:
            raw_data: Raw data from the API
            
        Returns:
            Processed data ready for plotting
            
        Raises:
            DataValidationError: If data validation fails
        """
        if 'categories' not in raw_data or 'series' not in raw_data:
            error_msg = self.translations["error_missing_data_top_10_users"]
            logging.error(error_msg)
            raise DataValidationError("Missing 'categories' or 'series' in raw_data")

        users = raw_data['categories']
        series = raw_data['series']

        if not series:
            error_msg = self.translations["warning_empty_series_top_10_users"]
            logging.error(error_msg)
            raise DataValidationError("Series data is empty")

        logging.debug("Processing data for %d users", len(users))

        try:
            # Apply username censoring if enabled
            censored_users = [
                censor_username(user, self.config["CENSOR_USERNAMES"])
                for user in users
            ]

            processed_data = {
                "users": censored_users,
                "tv_data": [],
                "movie_data": []
            }

            # Process each series (TV and Movies)
            for serie in series:
                if not isinstance(serie, dict) or 'name' not in serie or 'data' not in serie:
                    raise DataValidationError(f"Invalid series format: {serie}")

                if not isinstance(serie["data"], list):
                    raise DataValidationError(f"Invalid data type for series {serie['name']}")

                if serie["name"] == "TV":
                    processed_data["tv_data"] = serie["data"]
                elif serie["name"] == "Movies":
                    processed_data["movie_data"] = serie["data"]

            # Validate data lengths
            if (len(processed_data["tv_data"]) != len(users) or 
                len(processed_data["movie_data"]) != len(users)):
                raise DataValidationError(
                    f"Data length mismatch: users={len(users)}, "
                    f"tv={len(processed_data['tv_data'])}, "
                    f"movies={len(processed_data['movie_data'])}"
                )

            # Sort data by total plays
            combined_data = list(zip(
                censored_users,
                processed_data["tv_data"],
                processed_data["movie_data"]
            ))
            combined_data.sort(key=lambda x: x[1] + x[2], reverse=True)

            # Unzip the sorted data
            processed_data["users"] = [item[0] for item in combined_data]
            processed_data["tv_data"] = [item[1] for item in combined_data]
            processed_data["movie_data"] = [item[2] for item in combined_data]

            return processed_data

        except (KeyError, TypeError, ValueError) as e:
            error_msg = f"Error processing data: {str(e)}"
            logging.error(error_msg)
            raise DataValidationError(error_msg) from e

    def plot(self, processed_data: Dict[str, Any]) -> None:
        """
        Plot the processed data.
        
        Args:
            processed_data: The processed data to plot
            
        Raises:
            GraphGenerationError: If plotting fails
        """
        try:
            self.setup_plot()

            bar_width = 0.75
            index = range(len(processed_data["users"]))

            # Plot movie data
            self.ax.bar(index, processed_data["movie_data"], bar_width,
                       label="Movies", color=self.get_color("Movies"))

            # Plot TV data, stacked on top of movie data
            self.ax.bar(index, processed_data["tv_data"], bar_width,
                       bottom=processed_data["movie_data"],
                       label="TV", color=self.get_color("TV"))

            if self.config["ANNOTATE_TOP_10_USERS"]:
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
            error_msg = f"Error plotting graph: {str(e)}"
            logging.error(error_msg)
            raise GraphGenerationError(error_msg) from e

    async def generate(self, data_fetcher, user_id: Optional[str] = None) -> Optional[str]:
        """Generate the graph and return its file path."""
        try:
            logging.debug("Generate called with stored data: %s", "present" if self.data else "none")

            try:
                data = await self.fetch_data(data_fetcher, user_id)
                processed_data = self.process_data(data)
                self.plot(processed_data)
            except (Top10UsersError, DataValidationError, GraphGenerationError) as e:
                logging.error(str(e))
                return None

            today = datetime.today().strftime("%Y-%m-%d")
            file_name = "top_10_users.png"
            file_path = os.path.join(self.img_folder, today, file_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)
            
            logging.debug("Saved top 10 users graph: %s", file_path)
            return file_path
            
        except OSError as e:
            logging.error(f"File system error: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error in generate: {str(e)}")
            return None
