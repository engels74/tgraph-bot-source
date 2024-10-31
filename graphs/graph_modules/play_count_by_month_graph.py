# graphs/graph_modules/play_count_by_month_graph.py

from .base_graph import BaseGraph
from typing import Dict, Any, Optional, List
import logging
import os
import re
from datetime import datetime
from matplotlib.ticker import MaxNLocator

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

    def _validate_series_data(self, series: List[Dict[str, Any]], months: List[str]) -> List[str]:
        """
        Validate series data for completeness and consistency.
        
        Args:
            series: List of series data dictionaries
            months: List of month labels
            
        Returns:
            List of validation error messages, empty if validation passes
        """
        errors = []
        for idx, serie in enumerate(series):
            if not isinstance(serie, dict):
                errors.append(f"Series {idx} is not a dictionary")
                continue
                
            # Check required keys
            for key in ("name", "data"):
                if key not in serie:
                    errors.append(f"Series {idx} missing required key: {key}")
                    
            # Validate data length if 'data' exists
            if "data" in serie:
                if not isinstance(serie["data"], (list, tuple)):
                    errors.append(f"Series {idx} data is not a list")
                elif len(serie["data"]) != len(months):
                    errors.append(
                        f"Series {idx} ({serie.get('name', 'unnamed')}) data length mismatch: "
                        f"expected {len(months)}, got {len(serie['data'])}"
                    )
                    
            # Validate data types if data exists
            if "data" in serie and isinstance(serie["data"], (list, tuple)):
                if not all(isinstance(x, (int, float)) for x in serie["data"]):
                    errors.append(f"Series {idx} contains non-numeric data")
                    
        return errors

    def _sanitize_filename(self, user_id: str) -> str:
        """
        Sanitize user ID for safe filename creation.
        
        Args:
            user_id: The user ID to sanitize
            
        Returns:
            A sanitized version of the user ID safe for filenames
        """
        # Remove any characters that aren't alphanumeric, underscore, or hyphen
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', str(user_id))
        # Ensure the filename isn't too long
        return sanitized[:50]

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
        params = {"time_range": 12, "y_axis": "plays"}
        if user_id:
            params["user_id"] = user_id
        
        try:
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_per_month", params)
            if not data or 'response' not in data or 'data' not in data['response']:
                raise PlayCountByMonthError(self.translations["error_fetch_play_count_month"])
            return data['response']['data']
        except Exception as e:
            error_msg = (
                self.translations.get(
                    'error_fetch_play_count_month_user',
                    'Failed to fetch play count by month data for user {user_id}: {error}'
                ) if user_id else
                self.translations["error_fetch_play_count_month"]
            )
            raise PlayCountByMonthError(error_msg.format(user_id=user_id, error=str(e)))

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the fetched data for plotting.
        
        Args:
            data: Raw data from the API
            
        Returns:
            Processed data ready for plotting
            
        Raises:
            DataValidationError: If data validation fails
        """
        if not isinstance(data, dict) or 'categories' not in data or 'series' not in data:
            raise DataValidationError(self.translations["error_missing_data_play_count_by_month"])

        months = data['categories']
        series = data['series']

        if not months or not series:
            raise DataValidationError(self.translations["warning_empty_data_play_count_by_month"])

        # Validate series data
        validation_errors = self._validate_series_data(series, months)
        if validation_errors:
            raise DataValidationError(
                "Series data validation failed:\n" + "\n".join(validation_errors)
            )

        # Initialize data arrays with zeros
        tv_data = [0] * len(months)
        movie_data = [0] * len(months)

        # Process series data
        for serie in series:
            if serie["name"] == "TV":
                tv_data = serie["data"]
            elif serie["name"] == "Movies":
                movie_data = serie["data"]

        # Combine and filter data
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
            raise DataValidationError(self.translations["warning_no_play_data_play_count_by_month"])

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

            # Plot movie data
            self.ax.bar(index, processed_data["movie_data"], bar_width,
                       label="Movies", color=self.get_color("Movies"))

            # Plot TV data, stacked on top of movie data
            self.ax.bar(index, processed_data["tv_data"], bar_width,
                       bottom=processed_data["movie_data"],
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
            raise GraphGenerationError(f"Error plotting graph: {str(e)}")

    async def generate(self, data_fetcher, user_id: Optional[str] = None) -> Optional[str]:
        """
        Generate the graph and save it to a file.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific graphs
            
        Returns:
            The path to the generated graph file, or None if generation fails
        """
        try:
            data = await self.fetch_data(data_fetcher, user_id)
            processed_data = self.process_data(data)
            self.plot(processed_data)

            # Create dated directory path
            today = datetime.today().strftime("%Y-%m-%d")
            dated_dir = os.path.join(self.img_folder, today)
            os.makedirs(dated_dir, exist_ok=True)

            # Create safe filename
            safe_user_id = self._sanitize_filename(user_id) if user_id else None
            file_name = f"play_count_by_month{'_' + safe_user_id if safe_user_id else ''}.png"
            file_path = os.path.join(dated_dir, file_name)

            # Save the graph
            self.save(file_path)
            return file_path

        except (PlayCountByMonthError, DataValidationError, GraphGenerationError) as e:
            logging.error(str(e))
            return None
        except Exception as e:
            logging.error(f"Unexpected error generating monthly play count graph: {str(e)}")
            return None
