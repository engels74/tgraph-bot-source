# graphs/graph_modules/data_fetcher.py

from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta
from cachetools import TTLCache, cached
import aiohttp
import asyncio

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
            config: Configuration dictionary
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
        # Sort parameters for consistent cache keys
        sorted_params = tuple(sorted(
            (k, v) for k, v in params.items() 
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

    @cached(cache=TTLCache(maxsize=100, ttl=300))
    def fetch_tautulli_data(self, cmd: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Synchronously fetch data from Tautulli API with caching.
        
        Args:
            cmd: The Tautulli API command
            params: Additional parameters for the API call
            
        Returns:
            The API response data or None if there's an error
            
        Raises:
            ApiError: If the API request fails
        """
        try:
            import requests  # Import here to avoid global import
            
            if params is None:
                params = {}

            now = datetime.now().astimezone()
            start_date = now - timedelta(days=self.config["TIME_RANGE_DAYS"])
            
            api_params = {
                "apikey": self.config["TAUTULLI_API_KEY"],
                "cmd": cmd,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": now.strftime("%Y-%m-%d"),
                **params
            }

            # Remove None values from params
            api_params = {k: v for k, v in api_params.items() if v is not None}

            response = requests.get(self.config["TAUTULLI_URL"], params=api_params)
            response.raise_for_status()
            return response.json()
            
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
    ) -> Optional[Dict[str, Any]]:
        """
        Asynchronously fetch data from Tautulli API with caching.
        
        Args:
            cmd: The Tautulli API command
            params: Additional parameters for the API call
            
        Returns:
            The API response data or None if there's an error
        """
        if params is None:
            params = {}

        # Create cache key and check cache
        cache_key = self._create_cache_key(cmd, params)
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data

        try:
            now = datetime.now().astimezone()
            start_date = now - timedelta(days=self.config["TIME_RANGE_DAYS"])
            
            api_params = {
                "apikey": self.config["TAUTULLI_API_KEY"],
                "cmd": cmd,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": now.strftime("%Y-%m-%d"),
                **params
            }

            # Remove None values from params
            api_params = {k: v for k, v in api_params.items() if v is not None}

            async with aiohttp.ClientSession() as session:
                async with session.get(self.config["TAUTULLI_URL"], params=api_params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    self._set_cached_data(cache_key, data)
                    return data
                    
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
            if not response:
                return None
                
            if 'response' not in response or 'data' not in response['response']:
                raise DataProcessingError("Invalid API response format")
                
            users = response['response']['data']
            for user in users:
                if user.get('email') and user['email'].lower() == email.lower():
                    return user['user_id']
                    
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
            A dictionary containing all fetched data
        """
        # Initialize lists to track tasks and corresponding graph types
        tasks = []
        graph_types = []

        def add_task(cmd: str, params: Dict[str, Any], graph_type: str) -> None:
            """Helper to add a task and its corresponding graph type."""
            tasks.append(self.fetch_tautulli_data_async(cmd, params))
            graph_types.append(graph_type)

        # Add tasks and their corresponding graph types in a consistent order
        time_range_params = {"time_range": self.config["TIME_RANGE_DAYS"]}
        if user_id:
            time_range_params["user_id"] = user_id

        if self.config["ENABLE_DAILY_PLAY_COUNT"]:
            add_task("get_plays_by_date", time_range_params, "daily_play_count")

        if self.config["ENABLE_PLAY_COUNT_BY_DAYOFWEEK"]:
            add_task("get_plays_by_dayofweek", time_range_params, "play_count_by_dayofweek")

        if self.config["ENABLE_PLAY_COUNT_BY_HOUROFDAY"]:
            add_task("get_plays_by_hourofday", time_range_params, "play_count_by_hourofday")

        if self.config["ENABLE_TOP_10_PLATFORMS"]:
            add_task("get_plays_by_top_10_platforms", time_range_params, "top_10_platforms")

        if self.config["ENABLE_TOP_10_USERS"] and not user_id:
            add_task("get_plays_by_top_10_users", time_range_params, "top_10_users")

        if self.config["ENABLE_PLAY_COUNT_BY_MONTH"]:
            month_params = {"time_range": 12, "y_axis": "plays"}
            if user_id:
                month_params["user_id"] = user_id
            add_task("get_plays_per_month", month_params, "play_count_by_month")

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        data = {}
        for result, graph_type in zip(results, graph_types):
            if isinstance(result, Exception):
                logging.error(f"Error fetching data for {graph_type}: {str(result)}")
                continue
                
            if result and 'response' in result and 'data' in result['response']:
                data[graph_type] = result['response']['data']
            else:
                logging.warning(f"Failed to fetch data for {graph_type}")

        return data
