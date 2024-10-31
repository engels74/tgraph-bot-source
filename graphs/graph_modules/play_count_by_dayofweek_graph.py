# graphs/graph_modules/play_count_by_dayofweek_graph.py

from .base_graph import BaseGraph
from .utils import get_color
from typing import Dict, Any, Optional, List
import logging
import os
import re
from datetime import datetime
from matplotlib.ticker import MaxNLocator

class PlayCountByDayOfWeekError(Exception):
    """Base exception for PlayCountByDayOfWeek graph-specific errors."""
    pass

class DataValidationError(PlayCountByDayOfWeekError):
    """Raised when data validation fails."""
    pass

class GraphGenerationError(PlayCountByDayOfWeekError):
    """Raised when graph generation fails."""
    pass

class PlayCountByDayOfWeekGraph(BaseGraph):
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        super().__init__(config, translations, img_folder)
        self.graph_type = "play_count_by_dayofweek"

    def _validate_series_data(self, series: List[Dict[str, Any]], days_count: int) -> List[str]:
        """
        Validate series data for completeness and consistency.
        
        Args:
            series: List of series data dictionaries
            days_count: Expected number of data points per series
            
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
                elif len(serie["data"]) != days_count:
                    errors.append(
                        f"Series {idx} ({serie.get('name', 'unnamed')}) data length mismatch: "
                        f"expected {days_count}, got {len(serie['data'])}"
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
        Fetch play count data by day of week.
        
        Args:
            data_fetcher: Data fetcher instance
            user_id: Optional user ID for user-specific data
            
        Returns:
            The fetched data or None if fetching fails
            
        Raises:
            PlayCountByDayOfWeekError: If data fetching fails
        """
        try:
            params = {"time_range": self.config["TIME_RANGE_DAYS"]}
            if user_id:
                params["user_id"] = user_id
            
            data = await data_fetcher.fetch_tautulli_data_async("get_plays_by_dayofweek", params)
            if not data or 'response' not in data or 'data' not in data['response']:
                raise PlayCountByDayOfWeekError(
                    self.translations["error_fetch_play_count_dayofweek"]
                )
            return data['response']['data']
            
        except PlayCountByDayOfWeekError:
            raise
        except Exception as e:
            error_msg = (
                self.translations.get(
                    'error_fetch_play_count_dayofweek_user',
                    'Failed to fetch play count by day of week data for user {user_id}: {error}'
                ) if user_id else
                self.translations["error_fetch_play_count_dayofweek"]
            )
            raise PlayCountByDayOfWeekError(error_msg.format(user_id=user_id, error=str(e)))

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
        if 'series' not in data:
            raise DataValidationError(
                self.translations["error_missing_series_play_count_by_dayofweek"]
            )

        series = data['series']
        if not series:
            raise DataValidationError(
                self.translations["warning_empty_series_play_count_by_dayofweek"]
            )

        days = list(range(7))
        day_labels = [self.translations[f"day_{i}"] for i in range(7)]

        # Validate series data
        validation_errors = self._validate_series_data(series, len(days))
        if validation_errors:
            raise DataValidationError(
                "Series data validation failed:\n" + "\n".join(validation_errors)
            )

        processed_data = {
            "days": days,
            "day_labels": day_labels,
            "series": []
        }

        try:
            for serie in series:
                processed_data["series"].append({
                    "name": serie["name"],
                    "data": serie["data"],
                    "color": get_color(serie["name"], self.config)
                })
        except KeyError as e:
            raise DataValidationError(f"Missing required key in series data: {e}")
        except ValueError as e:
            raise DataValidationError(f"Invalid value in series data: {e}")

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

            for serie in processed_data["series"]:
                self.ax.plot(processed_data["days"], serie["data"], 
                           label=serie["name"], marker="o", color=serie["color"])

                if self.config["ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK"]:
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
            self.ax.set_xticklabels(processed_data["day_labels"], ha="center")
            self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            self.add_legend()
            self.apply_tight_layout()
            
        except Exception as e:
            raise GraphGenerationError(f"Error plotting graph: {str(e)}")

    async def generate(self, data_fetcher, user_id: Optional[str] = None) -> Optional[str]:
        """
        Generate the graph and return its file path.
        
        Args:
            data_fetcher: The data fetcher instance to use
            user_id: Optional user ID for user-specific graphs
            
        Returns:
            The file path of the generated graph, or None if generation fails
        """
        try:
            data = await self.fetch_data(data_fetcher, user_id)
            processed_data = self.process_data(data)
            self.plot(processed_data)

            today = datetime.today().strftime("%Y-%m-%d")
            
            # Sanitize user_id if present
            safe_user_id = self._sanitize_filename(user_id) if user_id else None
            file_name = f"play_count_by_dayofweek{'_' + safe_user_id if safe_user_id else ''}.png"
            
            # Create the dated directory path
            dated_dir = os.path.join(self.img_folder, today)
            os.makedirs(dated_dir, exist_ok=True)
            
            file_path = os.path.join(dated_dir, file_name)
            self.save(file_path)

            return file_path
            
        except (PlayCountByDayOfWeekError, DataValidationError) as e:
            logging.error(str(e))
            return None
        except GraphGenerationError as e:
            logging.error(f"Failed to generate graph: {str(e)}")
            return None
        except Exception:  # Fixed: Removed unused 'as e'
            logging.exception("Unexpected error during graph generation")
            return None
