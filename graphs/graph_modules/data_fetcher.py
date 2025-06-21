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
from typing import TypedDict
from types import TracebackType
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


# Type definitions for Tautulli API responses
class TautulliResponse(TypedDict):
    """Base structure for Tautulli API responses."""
    response: dict[str, object]


class PlayHistoryRecord(TypedDict, total=False):
    """Structure for individual play history records."""
    date: str
    tv_plays: int
    movie_plays: int
    music_plays: int
    total_plays: int
    duration: int
    user: str
    platform: str
    title: str
    media_type: str
    user_id: int
    friendly_name: str


class UserRecord(TypedDict, total=False):
    """Structure for user records."""
    user_id: int
    username: str
    friendly_name: str
    email: str
    thumb: str
    is_active: int


class PlatformRecord(TypedDict, total=False):
    """Structure for platform records."""
    platform: str
    total_plays: int
    total_duration: int


class LibraryRecord(TypedDict, total=False):
    """Structure for library records."""
    section_id: int
    section_name: str
    section_type: str
    count: int
    parent_count: int
    child_count: int


# Type aliases for common data structures
TautulliData = dict[str, object]
CacheData = dict[str, TautulliData]


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
        self._cache: CacheData = {}

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
    ) -> TautulliData:
        """
        Make an authenticated request to the Tautulli API.
        
        Args:
            endpoint: API endpoint to call
            params: Additional parameters for the request
            
        Returns:
            JSON response data as a dictionary
            
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

                data = response.json()  # pyright: ignore[reportAny]

                # Check for API-level errors
                if not isinstance(data, dict):
                    raise ValueError("Invalid API response format")

                response_data = data.get("response", {})  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                if not isinstance(response_data, dict):
                    raise ValueError("API response is not a dictionary")

                if response_data.get("result") != "success":  # pyright: ignore[reportUnknownMemberType]
                    error_msg = response_data.get("message", "Unknown API error")  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                    raise ValueError(f"API error: {error_msg}")

                logger.debug(f"Successfully fetched data from {endpoint}")
                data_result = response_data.get("data", {})  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                
                # For endpoints that return lists (like get_users), wrap in a dict with 'data' key
                # For endpoints that return dicts, return as-is
                if isinstance(data_result, list):
                    return {"data": data_result}
                elif isinstance(data_result, dict):
                    return data_result  # pyright: ignore[reportUnknownVariableType]
                else:
                    # Fallback for other data types
                    return {"data": data_result}
                
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
    ) -> TautulliData:
        """
        Fetch play history data from Tautulli.
        
        Args:
            time_range: Number of days to fetch data for
            user_id: Specific user ID to filter by (None for all users)
            
        Returns:
            Play history data as a dictionary
        """
        cache_key = f"play_history_{time_range}_{user_id}"
        
        if cache_key in self._cache:
            logger.debug(f"Using cached data for {cache_key}")
            cached_data = self._cache[cache_key]
            return cached_data
            
        params: dict[str, str | int | float | bool] = {
            "length": 1000,  # Maximum number of records
            "start": 0,
        }
        
        # Add time_range parameter to limit data to the specified number of days
        if time_range > 0:
            params["time_range"] = time_range

        if user_id is not None:
            params["user_id"] = user_id
            
        data = await self._make_request("get_history", params)
        
        # Cache the result
        self._cache[cache_key] = data
        
        return data
        
    async def get_user_stats(self, user_id: int) -> TautulliData:
        """
        Fetch statistics for a specific user.

        Args:
            user_id: The user ID to fetch stats for

        Returns:
            User statistics data as a dictionary
        """
        cache_key = f"user_stats_{user_id}"
        
        if cache_key in self._cache:
            logger.debug(f"Using cached data for {cache_key}")
            cached_data = self._cache[cache_key]
            return cached_data
            
        data = await self._make_request("get_user", {"user_id": user_id})
        
        # Cache the result
        self._cache[cache_key] = data
        
        return data
        
    async def get_library_stats(self) -> TautulliData:
        """
        Fetch library statistics.

        Returns:
            Library statistics data as a dictionary
        """
        cache_key = "library_stats"
        
        if cache_key in self._cache:
            logger.debug(f"Using cached data for {cache_key}")
            cached_data = self._cache[cache_key]
            return cached_data
            
        data = await self._make_request("get_libraries")
        
        # Cache the result
        self._cache[cache_key] = data
        
        return data
        
    async def get_users(self) -> TautulliData:
        """
        Fetch all users from Tautulli.

        Returns:
            Users data containing list of all users as a dictionary
        """
        cache_key = "users"

        if cache_key in self._cache:
            logger.debug(f"Using cached data for {cache_key}")
            cached_data = self._cache[cache_key]
            return cached_data

        data = await self._make_request("get_users")

        # Cache the result
        self._cache[cache_key] = data

        return data

    async def find_user_by_email(self, email: str) -> UserRecord | None:
        """
        Find a user by their email address.

        Args:
            email: The user's email address

        Returns:
            User data if found, None otherwise
        """
        users_data = await self.get_users()

        # The API returns a dict with a 'data' key containing the list of users
        users_list = users_data.get("data", [])
        if isinstance(users_list, list):
            for user in users_list:  # pyright: ignore[reportUnknownVariableType]
                if isinstance(user, dict):
                    user_email = user.get("email")  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                    if user_email == email:
                        # Construct a properly typed UserRecord from the API response
                        # Safely convert API response values to expected types
                        user_id_raw = user.get('user_id', 0)  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                        username_raw = user.get('username', '')  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                        friendly_name_raw = user.get('friendly_name', '')  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                        email_raw = user.get('email', '')  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                        thumb_raw = user.get('thumb', '')  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                        is_active_raw = user.get('is_active', 0)  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]

                        user_record: UserRecord = {
                            'user_id': int(user_id_raw) if isinstance(user_id_raw, (int, float, str)) else 0,
                            'username': str(username_raw) if username_raw is not None else '',  # pyright: ignore[reportUnknownArgumentType]
                            'friendly_name': str(friendly_name_raw) if friendly_name_raw is not None else '',  # pyright: ignore[reportUnknownArgumentType]
                            'email': str(email_raw) if email_raw is not None else '',  # pyright: ignore[reportUnknownArgumentType]
                            'thumb': str(thumb_raw) if thumb_raw is not None else '',  # pyright: ignore[reportUnknownArgumentType]
                            'is_active': int(is_active_raw) if isinstance(is_active_raw, (int, float, str)) else 0,
                        }
                        return user_record

        logger.warning(f"User not found with email: {email}")
        return None

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._cache.clear()
        logger.info("Data cache cleared")
