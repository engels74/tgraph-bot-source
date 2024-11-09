# graphs/graph_modules/play_count_by_month_graph.py

from .base_graph import BaseGraph
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

class PlayCountByMonthGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "play_count_by_month"

    async def fetch_data(self, data_fetcher, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch play count data by month.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific data
            
        Returns:
            The fetched data or None if fetching fails
        """
        try:
            # If we have stored data, use it instead of fetching
            if self.data is not None:
                logging.debug("Using stored data for play count by month")
                return self.data

            # Use 12 months for monthly data
            params = {"time_range": 12, "y_axis": "plays"}
            if user_id:
                params["user_id"] = user_id
            
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
                return None

            return data['response']['data']
            
        except Exception as e:
            logging.error(f"Error fetching play count by month data: {str(e)}")
            return None

    def validate_series_data(self, series: List[Dict[str, Any]], month_count: int) -> List[str]:
        """Validate series data for completeness and consistency."""
        errors = []
        for idx, serie in enumerate(series):
            if not isinstance(serie, dict):
                errors.append(f"Series {idx} is not a dictionary")
                continue
                
            if "name" not in serie or "data" not in serie:
                errors.append(f"Series {idx} missing required keys")
                continue
                
            data = serie["data"]
            if not isinstance(data, list):
                errors.append(f"Series {idx} ({serie['name']}) data is not a list")
                continue
                
            if len(data) != month_count:
                errors.append(
                    f"Series {idx} ({serie['name']}) data length mismatch: "
                    f"expected {month_count}, got {len(data)}"
                )
                
            if not all(isinstance(x, (int, float)) for x in data):
                errors.append(f"Series {idx} ({serie['name']}) contains non-numeric data")
                
        return errors

    def process_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process the raw data for plotting."""
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
            logging.error(f"Error processing monthly play count data: {str(e)}")
            return None

    def _process_series_data(self, months: List[str], series: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        """Process series data and filter out months with zero plays."""
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
        """Plot the processed data."""
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
        """Generate the graph and return its file path."""
        try:
            logging.debug("Generate called with stored data: %s", "present" if self.data else "none")

            data = await self.fetch_data(data_fetcher, user_id)
            if data is None:
                logging.error("Failed to fetch monthly play count data")
                return None

            processed_data = self.process_data(data)
            if processed_data is None:
                logging.error("Failed to process monthly play count data")
                return None

            self.plot(processed_data)

            # Save the graph
            today = datetime.today().strftime("%Y-%m-%d")
            file_name = f"play_count_by_month{'_' + user_id if user_id else ''}.png"
            file_path = os.path.join(self.img_folder, today, file_name)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.save(file_path)
            
            logging.debug("Saved monthly play count graph: %s", file_path)
            return file_path
            
        except Exception as e:
            logging.error(f"Error generating monthly play count graph: {str(e)}")
            return None
