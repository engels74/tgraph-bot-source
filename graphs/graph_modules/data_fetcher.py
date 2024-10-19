# graphs/graph_modules/data_fetcher.py

"""
Data fetching and caching functionality for TGraph Bot.
Handles both synchronous and asynchronous data retrieval from Tautulli API.
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta
from cachetools import TTLCache
import aiohttp
import asyncio
import requests

class DataFetcherError(Exception):
    """Base exception for data fetching errors."""
    pass

class ApiError(DataFetcherError):
    """Raised when there's an error in API communication."""
    pass

class DataProcessingError(DataFetcherError):
    """Raised when there's an error processing the fetched data."""
    pass

class DataFetcher:
    """Handles fetching and caching of data from Tautulli API."""
    
    def __init__(self, config: Dict[str, Any], cache_ttl: int = 300):
        """
        Initialize the DataFetcher.
        
        Args:
            config: Configuration dictionary containing API settings and parameters
            cache_ttl: Cache time-to-live in seconds (default: 300)
        """
        self.config = config
        self._cache_ttl = cache_ttl
        self._api_cache = TTLCache(maxsize=100, ttl=cache_ttl)

    def _create_cache_key(self, cmd: str, params: Dict[str, Any]) -> tuple:
        """
        Create a consistent cache key from command and parameters.
        
        Args:
            cmd: API command
            params: Command parameters
            
        Returns:
            A tuple suitable for use as a cache key
        """
        sorted_params = tuple(sorted(
            (k, str(v)) for k, v in params.items() 
            if v is not None
        ))
        return (cmd, sorted_params)

    def _get_cached_data(self, cache_key: tuple) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from cache.
        
        Args:
            cache_key: Cache key tuple
            
        Returns:
            Cached data if available, None otherwise
        """
        return self._api_cache.get(cache_key)

    def _set_cached_data(self, cache_key: tuple, data: Dict[str, Any]) -> None:
        """
        Store data in cache.
        
        Args:
            cache_key: Cache key tuple
            data: Data to cache
        """
        self._api_cache[cache_key] = data

    def _validate_data_structure(self, cmd: str, data: Any) -> bool:
        """
        Validate the data structure returned from Tautulli based on the command.
        
        Args:
            cmd: The API command
            data: The data to validate
            
        Returns:
            True if the data structure is valid, False otherwise
        """
        if cmd == "get_users":
            return True  # get_users has a different structure, handled separately
            
        if not isinstance(data, dict):
            return True  # Raw API responses are processed differently for some commands

        if cmd == "get_plays_by_date":
            return (
                'categories' in data
                and 'series' in data
                and isinstance(data['categories'], list)
                and isinstance(data['series'], list)
            )
        
        return True  # Default to true for unknown commands

    def fetch_tautulli_data(self, cmd: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Synchronously fetch data from Tautulli API with caching.
        
        Args:
            cmd: The Tautulli API command
            params: Additional parameters for the API call
            
        Returns:
            The processed API response data
            
        Raises:
            ApiError: If the API request fails
            DataProcessingError: If the response cannot be processed
        """
        try:
            if params is None:
                params = {}

            cache_key = self._create_cache_key(cmd, params)
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data

            if cmd != "get_users":  # Only add date params for non-user queries
                now = datetime.now().astimezone()
                start_date = now - timedelta(days=self.config["TIME_RANGE_DAYS"])
                params.update({
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": now.strftime("%Y-%m-%d"),
                })
            
            api_params = {
                "apikey": self.config["TAUTULLI_API_KEY"],
                "cmd": cmd,
                **params
            }

            api_params = {k: v for k, v in api_params.items() if v is not None}

            response = requests.get(self.config["TAUTULLI_URL"], params=api_params)
            response.raise_for_status()
            
            data = response.json()
            if not data or 'response' not in data:
                raise DataProcessingError("Invalid API response format")
                
            if cmd == "get_users":
                # For get_users, return the response directly
                return data
                
            if 'data' in data['response']:
                result_data = data['response']['data']
                if not self._validate_data_structure(cmd, result_data):
                    raise DataProcessingError(f"Invalid data structure for command {cmd}")
                    
                self._set_cached_data(cache_key, result_data)
                return result_data
            
            raise DataProcessingError("No data found in API response")
                
        except requests.RequestException as e:
            logging.error(f"Error fetching data from Tautulli API: {str(e)}")
            raise ApiError(f"API request failed: {str(e)}") from e
        except ValueError as e:
            logging.error(f"Error parsing API response: {str(e)}")
            raise DataProcessingError(f"Failed to parse API response: {str(e)}") from e

    async def fetch_tautulli_data_async(
        self, 
        cmd: str, 
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Asynchronously fetch data from Tautulli API with caching.
        
        Args:
            cmd: The Tautulli API command
            params: Additional parameters for the API call
            
        Returns:
            The processed API response data
            
        Raises:
            ApiError: If the API request fails
            DataProcessingError: If the response cannot be processed
        """
        if params is None:
            params = {}

        # Convert user_id to string if it exists in params
        if 'user_id' in params:
            params['user_id'] = str(params['user_id'])

        cache_key = self._create_cache_key(cmd, params)
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data

        try:
            if cmd != "get_users":  # Only add date params for non-user queries
                now = datetime.now().astimezone()
                start_date = now - timedelta(days=self.config["TIME_RANGE_DAYS"])
                params.update({
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": now.strftime("%Y-%m-%d"),
                })
            
            api_params = {
                "apikey": self.config["TAUTULLI_API_KEY"],
                "cmd": cmd,
                **params
            }

            # Ensure all params are strings for the API call
            api_params = {k: str(v) for k, v in api_params.items() if v is not None}

            async with aiohttp.ClientSession() as session:
                async with session.get(self.config["TAUTULLI_URL"], params=api_params) as response:
                    response.raise_for_status()
                    raw_data = await response.json()
                    
                    if not raw_data or 'response' not in raw_data:
                        raise DataProcessingError("Invalid API response format")

                    if cmd == "get_users":
                        return raw_data

                    if 'data' in raw_data['response']:
                        result_data = raw_data['response']['data']
                        if not self._validate_data_structure(cmd, result_data):
                            raise DataProcessingError(f"Invalid data structure for command {cmd}")
                            
                        self._set_cached_data(cache_key, result_data)
                        return result_data
                    
                    raise DataProcessingError("No data found in API response")
                    
        except aiohttp.ClientError as e:
            logging.error(f"Error fetching data from Tautulli API asynchronously: {str(e)}")
            raise ApiError(f"Async API request failed: {str(e)}") from e
        except ValueError as e:
            logging.error(f"Error parsing API response: {str(e)}")
            raise DataProcessingError(f"Failed to parse API response: {str(e)}") from e

    def get_user_id_from_email(self, email: str) -> Optional[str]:
        """
        Get the user ID from an email address.
        
        Args:
            email: The user's email address
                
        Returns:
            The user ID if found, None otherwise
        """
        if not email:
            return None

        try:
            response = self.fetch_tautulli_data("get_users")
            if not response or 'response' not in response or 'data' not in response['response']:
                logging.error("Invalid response structure from get_users API call")
                return None
                    
            users = response['response']['data']
            if not isinstance(users, list):
                logging.error("Users data is not a list")
                return None

            for user in users:
                if user.get('email') and user['email'].lower() == email.lower():
                    return user.get('user_id')
                        
            return None
                
        except (KeyError, TypeError) as e:
            logging.error(f"Error processing user data: {str(e)}")
            return None
        except DataFetcherError as e:
            logging.error(f"Error fetching user ID: {str(e)}")
            return None

    async def fetch_all_graph_data(self, user_id: str = None) -> Dict[str, Any]:
        """
        Asynchronously fetch all required data for graphs.
        
        Args:
            user_id: Optional user ID for user-specific graphs
            
        Returns:
            A dictionary containing all fetched data organized by graph type
        """
        tasks = []
        graph_types = []

        logging.debug("Starting fetch_all_graph_data with user_id: %s", user_id)

        def add_task(cmd: str, params: Dict[str, Any], graph_type: str) -> None:
            """Helper to add a task and its corresponding graph type."""
            if user_id:
                params["user_id"] = str(user_id)  # Ensure user_id is string
            logging.debug("Adding task for %s with params: %s", cmd, params)
            tasks.append(self.fetch_tautulli_data_async(cmd, params))
            graph_types.append(graph_type)

        # Base parameters with time range
        time_range_params = {"time_range": self.config["TIME_RANGE_DAYS"]}
        
        # Add tasks for enabled graphs
        if self.config.get("ENABLE_DAILY_PLAY_COUNT", False):
            add_task("get_plays_by_date", time_range_params.copy(), "daily_play_count")

        if self.config.get("ENABLE_PLAY_COUNT_BY_DAYOFWEEK", False):
            # Fix: Use correct endpoint for day of week data
            add_task("get_plays_by_dayofweek", time_range_params.copy(), "play_count_by_dayofweek")

        if self.config.get("ENABLE_PLAY_COUNT_BY_HOUROFDAY", False):
            # Fix: Use correct endpoint for hour of day data
            add_task("get_plays_by_hourofday", time_range_params.copy(), "play_count_by_hourofday")

        if self.config.get("ENABLE_TOP_10_PLATFORMS", False):
            add_task("get_plays_by_top_10_platforms", time_range_params.copy(), "top_10_platforms")

        if self.config.get("ENABLE_TOP_10_USERS", False) and not user_id:
            # Don't fetch top users data for user-specific graphs
            add_task("get_plays_by_top_10_users", time_range_params.copy(), "top_10_users")

        if self.config.get("ENABLE_PLAY_COUNT_BY_MONTH", False):
            # Fix: Use correct parameters for monthly data
            month_params = {"time_range": 12, "y_axis": "plays"}
            if user_id:
                month_params["user_id"] = str(user_id)
            add_task("get_plays_per_month", month_params, "play_count_by_month")

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            data = {}
            for result, graph_type in zip(results, graph_types):
                if isinstance(result, Exception):
                    logging.error(f"Error fetching data for {graph_type}: {str(result)}")
                    continue
                    
                if result is not None:
                    if 'response' in result and 'data' in result['response']:
                        data[graph_type] = result['response']['data']
                    else:
                        data[graph_type] = result
                    logging.debug("Successfully fetched data for %s", graph_type)
                else:
                    logging.warning(f"No data returned for {graph_type}")

            return data
                
        except Exception as e:
            logging.error(f"Error fetching graph data: {str(e)}")
            raise DataFetcherError(f"Failed to fetch graph data: {str(e)}")
