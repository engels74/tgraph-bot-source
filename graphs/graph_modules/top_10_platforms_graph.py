# graphs/graph_modules/top_10_platforms_graph.py

from .base_graph import BaseGraph
from typing import Dict, Any, Optional
import logging
import os
from datetime import datetime
from matplotlib.ticker import MaxNLocator

class Top10PlatformsError(Exception):
    """Base exception for Top10Platforms graph-specific errors."""
    pass

class DataValidationError(Top10PlatformsError):
    """Raised when data validation fails."""
    pass

class GraphGenerationError(Top10PlatformsError):
    """Raised when there is an error generating the graph."""
    pass

class Top10PlatformsGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "top_10_platforms"

    async def fetch_data(self, data_fetcher, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch top 10 platforms data.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific data
            
        Returns:
            The fetched data or None if fetching fails
        """
        try:
            # If we have stored data, use it instead of fetching
            if self.data is not None:
                logging.debug("Using stored data for top 10 platforms")
                return self.data

            # Otherwise, fetch new data
            params = {"time_range": self.config["TIME_RANGE_DAYS"]}
            if user_id:
                params["user_id"] = user_id
            
            logging.debug("Fetching top 10 platforms data with params: %s", params)
            
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_top_10_platforms", params)
            if not data or 'response' not in data or 'data' not in data['response']:
                error_msg = self.translations.get("error_fetch_top_10_platforms")
                if user_id:
                    error_msg = self.translations.get(
                        "error_fetch_top_10_platforms_user",
                        "Failed to fetch top 10 platforms data for user {user_id}: {error}"
                    ).format(user_id=user_id, error="No data returned")
                logging.error(error_msg)
                return None

            return data['response']['data']
            
        except Exception as e:
            logging.error(f"Error fetching top 10 platforms data: {str(e)}")
            return None

    def process_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process the raw data into a format suitable for plotting.
        
        Args:
            raw_data: Raw data from the API
        
        Returns:
            Processed data ready for plotting or None if processing fails
        """
        try:
            if 'categories' not in raw_data or 'series' not in raw_data:
                logging.error(self.translations["error_missing_data_top_10_platforms"])
                return None

            platforms = raw_data['categories']
            series = raw_data['series']

            if not series or not platforms:
                logging.warning(self.translations["warning_empty_series_top_10_platforms"])
                return None

            processed_data = {
                "platforms": platforms,
                "tv_data": [],
                "movie_data": []
            }

            logging.debug("Processing %d series for %d platforms", len(series), len(platforms))

            # Process each series (TV and Movies)
            for serie in series:
                if not isinstance(serie, dict) or 'name' not in serie or 'data' not in serie:
                    logging.error("Invalid series format: %s", serie)
                    continue

                if serie["name"] == "TV":
                    processed_data["tv_data"] = serie["data"]
                elif serie["name"] == "Movies":
                    processed_data["movie_data"] = serie["data"]

            # Validate data lengths
            if (len(processed_data["tv_data"]) != len(platforms) or 
                len(processed_data["movie_data"]) != len(platforms)):
                logging.error("[DEBUG] Data length mismatch: platforms=%d, tv=%d, movies=%d",
                            len(platforms), len(processed_data["tv_data"]), 
                            len(processed_data["movie_data"]))
                return None

            return processed_data

        except Exception as e:
            logging.error(f"Error processing top 10 platforms data: {str(e)}")
            return None

    def plot(self, processed_data: Dict[str, Any]) -> None:
        """Plot the processed data."""
        try:
            self.setup_plot()

            bar_width = 0.75
            index = range(len(processed_data["platforms"]))

            # Plot movie data
            self.ax.bar(index, processed_data["movie_data"], bar_width,
                                   label="Movies", color=self.get_color("Movies"))

            # Plot TV data, stacked on top of movie data
            self.ax.bar(index, processed_data["tv_data"], bar_width,
                                bottom=processed_data["movie_data"],
                                label="TV", color=self.get_color("TV"))

            if self.config["ANNOTATE_TOP_10_PLATFORMS"]:
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
            logging.error(f"Error plotting top 10 platforms graph: {str(e)}")
            raise GraphGenerationError(str(e))

    async def generate(self, data_fetcher, user_id: Optional[str] = None) -> Optional[str]:
        """Generate the graph and return its file path."""
        try:
            logging.debug("Generate called with stored data: %s", "present" if self.data else "none")

            data = await self.fetch_data(data_fetcher, user_id)
            if data is None:
                logging.error("Failed to fetch top 10 platforms data")
                return None

            processed_data = self.process_data(data)
            if processed_data is None:
                logging.error("Failed to process top 10 platforms data")
                return None

            self.plot(processed_data)

            today = datetime.today().strftime("%Y-%m-%d")
            file_name = f"top_10_platforms{'_' + user_id if user_id else ''}.png"
            file_path = os.path.join(self.img_folder, today, file_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)
            
            logging.debug("Saved top 10 platforms graph: %s", file_path)
            return file_path
            
        except Exception as e:
            logging.error(f"Error generating top 10 platforms graph: {str(e)}")
            return None
