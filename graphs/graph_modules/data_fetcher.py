# graphs/graph_modules/data_fetcher.py

import requests
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta
from cachetools import TTLCache, cached
import asyncio
import aiohttp

class DataFetcher:
    def __init__(self, config: Dict[str, Any], cache_ttl: int = 300):
        self.config = config
        self.cache = TTLCache(maxsize=100, ttl=cache_ttl)  # Cache with 5 minutes TTL

    @cached(cache=TTLCache(maxsize=100, ttl=300))
    def fetch_tautulli_data(self, cmd: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch data from Tautulli API with caching.
        
        :param cmd: The Tautulli API command
        :param params: Additional parameters for the API call
        :return: The API response data or None if there's an error
        """
        if params is None:
            params = {}

        now = datetime.now().astimezone()
        start_date = now - timedelta(days=self.config["TIME_RANGE_DAYS"])
        
        params.update({
            "apikey": self.config["TAUTULLI_API_KEY"],
            "cmd": cmd,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": now.strftime("%Y-%m-%d"),
        })

        # Remove None values from params
        params = {k: v for k, v in params.items() if v is not None}

        try:
            response = requests.get(self.config["TAUTULLI_URL"], params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error fetching data from Tautulli API: {str(e)}")
            return None

    async def fetch_tautulli_data_async(self, cmd: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Asynchronously fetch data from Tautulli API with caching.
        
        :param cmd: The Tautulli API command
        :param params: Additional parameters for the API call
        :return: The API response data or None if there's an error
        """
        if params is None:
            params = {}

        cache_key = (cmd, frozenset(params.items()))
        if cache_key in self.cache:
            return self.cache[cache_key]

        now = datetime.now().astimezone()
        start_date = now - timedelta(days=self.config["TIME_RANGE_DAYS"])
        
        params.update({
            "apikey": self.config["TAUTULLI_API_KEY"],
            "cmd": cmd,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": now.strftime("%Y-%m-%d"),
        })

        # Remove None values from params
        params = {k: v for k, v in params.items() if v is not None}

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(self.config["TAUTULLI_URL"], params=params) as response
            ):
                response.raise_for_status()
                data = await response.json()
                self.cache[cache_key] = data
                return data
        except aiohttp.ClientError as e:
            logging.error(f"Error fetching data from Tautulli API asynchronously: {str(e)}")
            return None

    def get_user_id_from_email(self, email: str) -> Optional[str]:
        """
        Get the user ID from an email address.
        
        :param email: The user's email address
        :return: The user ID if found, None otherwise
        """
        if not email:
            return None

        try:
            response = self.fetch_tautulli_data("get_users")
            if response and 'response' in response and 'data' in response['response']:
                users = response['response']['data']
                for user in users:
                    if user.get('email') and user['email'].lower() == email.lower():
                        return user['user_id']
            return None
        except Exception as e:
            logging.error(f"Error fetching user ID from email: {str(e)}")
            return None

    async def fetch_all_graph_data(self, user_id: str = None) -> Dict[str, Any]:
        """
        Asynchronously fetch all required data for graphs.
        
        :param user_id: Optional user ID for user-specific graphs
        :return: A dictionary containing all fetched data
        """
        tasks = []
        if self.config["ENABLE_DAILY_PLAY_COUNT"]:
            tasks.append(self.fetch_tautulli_data_async("get_plays_by_date", 
                                                        {"time_range": self.config["TIME_RANGE_DAYS"], "user_id": user_id}))
        if self.config["ENABLE_PLAY_COUNT_BY_DAYOFWEEK"]:
            tasks.append(self.fetch_tautulli_data_async("get_plays_by_dayofweek", 
                                                        {"time_range": self.config["TIME_RANGE_DAYS"], "user_id": user_id}))
        if self.config["ENABLE_PLAY_COUNT_BY_HOUROFDAY"]:
            tasks.append(self.fetch_tautulli_data_async("get_plays_by_hourofday", 
                                                        {"time_range": self.config["TIME_RANGE_DAYS"], "user_id": user_id}))
        if self.config["ENABLE_TOP_10_PLATFORMS"]:
            tasks.append(self.fetch_tautulli_data_async("get_plays_by_top_10_platforms", 
                                                        {"time_range": self.config["TIME_RANGE_DAYS"], "user_id": user_id}))
        if self.config["ENABLE_TOP_10_USERS"] and not user_id:
            tasks.append(self.fetch_tautulli_data_async("get_plays_by_top_10_users", 
                                                        {"time_range": self.config["TIME_RANGE_DAYS"]}))
        if self.config["ENABLE_PLAY_COUNT_BY_MONTH"]:
            tasks.append(self.fetch_tautulli_data_async("get_plays_per_month", 
                                                        {"time_range": 12, "y_axis": "plays", "user_id": user_id}))

        results = await asyncio.gather(*tasks)
        
        data = {}
        for result, graph_type in zip(results, [k for k, v in self.config.items() if k.startswith("ENABLE_") and v]):
            if result is not None and 'response' in result and 'data' in result['response']:
                data[graph_type.lower().replace("enable_", "")] = result['response']['data']
            else:
                logging.warning(f"Failed to fetch data for {graph_type}")

        return data
