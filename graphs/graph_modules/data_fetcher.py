"""
Data fetcher for TGraph Bot.

This module is responsible for fetching data from the Tautulli API.
It exclusively uses a modern, async-native HTTP client like httpx to perform
all API requests, ensuring that no I/O operations block the bot's event loop.
It includes robust error handling for API timeouts, connection issues, and
invalid responses, as well as caching results.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, cast
from types import TracebackType
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


class DataFetcher:
    """Handles fetching data from the Tautulli API with async HTTP requests."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3
    ) -> None:
        """
        Initialize the data fetcher.

        Args:
            base_url: Base URL for the Tautulli API
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url: str = base_url.rstrip('/')
        self.api_key: str = api_key
        self.timeout: float = timeout
        self.max_retries: int = max_retries
        self._client: httpx.AsyncClient | None = None
        self._cache: dict[str, dict[str, object]] = {}

    async def __aenter__(self) -> DataFetcher:
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        """Async context manager exit."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            
    async def _make_request(
        self,
        endpoint: str,
        params: dict[str, str | int | float | bool] | None = None
    ) -> dict[str, object]:
        """
        Make an authenticated request to the Tautulli API.
        
        Args:
            endpoint: API endpoint to call
            params: Additional parameters for the request
            
        Returns:
            JSON response data
            
        Raises:
            httpx.HTTPError: For HTTP-related errors
            ValueError: For invalid API responses
        """
        if self._client is None:
            raise RuntimeError("DataFetcher not initialized. Use as async context manager.")
            
        # Prepare request parameters
        request_params: dict[str, str | int | float | bool] = {
            "apikey": self.api_key,
            "cmd": endpoint,
            **(params or {})
        }

        url = urljoin(self.base_url, "/api/v2")

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Making API request to {endpoint} (attempt {attempt + 1})")

                response = await self._client.get(url, params=request_params)
                _ = response.raise_for_status()

                data: dict[str, object] = response.json()

                # Check for API-level errors
                if not isinstance(data, dict):
                    raise ValueError("Invalid API response format")

                response_data = data.get("response", {})
                if not isinstance(response_data, dict):
                    raise ValueError("API response is not a dictionary")

                if response_data.get("result") != "success":
                    error_msg = response_data.get("message", "Unknown API error")
                    raise ValueError(f"API error: {error_msg}")

                logger.debug(f"Successfully fetched data from {endpoint}")
                data_result = response_data.get("data", {})
                if not isinstance(data_result, dict):
                    raise ValueError("API response data is not a dictionary")
                return data_result
                
            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1} for {endpoint}")
                if attempt == self.max_retries:
                    raise
                delay = 2.0 ** attempt  # Exponential backoff
                await asyncio.sleep(delay)
                
            except httpx.HTTPError as e:
                logger.warning(f"HTTP error on attempt {attempt + 1} for {endpoint}: {e}")
                if attempt == self.max_retries:
                    raise
                delay = 2.0 ** attempt
                await asyncio.sleep(delay)
                
        # This should never be reached due to the raise statements above
        raise RuntimeError("Unexpected error in request retry loop")
        
    async def get_play_history(
        self,
        time_range: int = 30,
        user_id: int | None = None
    ) -> dict[str, object]:
        """
        Fetch play history data from Tautulli.
        
        Args:
            time_range: Number of days to fetch data for
            user_id: Specific user ID to filter by (None for all users)
            
        Returns:
            Play history data
        """
        cache_key = f"play_history_{time_range}_{user_id}"
        
        if cache_key in self._cache:
            logger.debug(f"Using cached data for {cache_key}")
            return self._cache[cache_key]
            
        params: dict[str, str | int | float | bool] = {
            "length": 1000,  # Maximum number of records
            "start": 0,
        }

        if user_id is not None:
            params["user_id"] = user_id
            
        data = await self._make_request("get_history", params)
        
        # Cache the result
        self._cache[cache_key] = data
        
        return data
        
    async def get_user_stats(self, user_id: int) -> dict[str, Any]:
        """
        Fetch statistics for a specific user.
        
        Args:
            user_id: The user ID to fetch stats for
            
        Returns:
            User statistics data
        """
        cache_key = f"user_stats_{user_id}"
        
        if cache_key in self._cache:
            logger.debug(f"Using cached data for {cache_key}")
            return self._cache[cache_key]
            
        data = await self._make_request("get_user", {"user_id": user_id})
        
        # Cache the result
        self._cache[cache_key] = data
        
        return data
        
    async def get_library_stats(self) -> dict[str, Any]:
        """
        Fetch library statistics.
        
        Returns:
            Library statistics data
        """
        cache_key = "library_stats"
        
        if cache_key in self._cache:
            logger.debug(f"Using cached data for {cache_key}")
            return self._cache[cache_key]
            
        data = await self._make_request("get_libraries")
        
        # Cache the result
        self._cache[cache_key] = data
        
        return data
        
    async def get_users(self) -> dict[str, Any]:
        """
        Fetch all users from Tautulli.

        Returns:
            Users data containing list of all users
        """
        cache_key = "users"

        if cache_key in self._cache:
            logger.debug(f"Using cached data for {cache_key}")
            return self._cache[cache_key]

        data = await self._make_request("get_users")

        # Cache the result
        self._cache[cache_key] = data

        return data

    async def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        """
        Find a user by their email address.

        Args:
            email: The user's email address

        Returns:
            User data if found, None otherwise
        """
        users_data = await self.get_users()

        # users_data should be a list of user dictionaries
        if isinstance(users_data, list):
            for user in users_data:
                if isinstance(user, dict):
                    user_email = user.get("email")
                    if user_email == email:
                        return user

        logger.warning(f"User not found with email: {email}")
        return None

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._cache.clear()
        logger.info("Data cache cleared")
