"""
Data fetcher for TGraph Bot.

This module is responsible for fetching data from the Tautulli API.
It exclusively uses a modern, async-native HTTP client like httpx to perform
all API requests, ensuring that no I/O operations block the bot's event loop.
It includes robust error handling for API timeouts, connection issues, and
invalid responses, as well as caching results.
"""

import asyncio
import logging
from typing import Any, Optional
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
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: dict[str, Any] = {}
        
    async def __aenter__(self) -> "DataFetcher":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self
        
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            
    async def _make_request(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
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
        request_params = {
            "apikey": self.api_key,
            "cmd": endpoint,
            **(params or {})
        }
        
        url = urljoin(self.base_url, "/api/v2")
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Making API request to {endpoint} (attempt {attempt + 1})")
                
                response = await self._client.get(url, params=request_params)
                response.raise_for_status()
                
                data = response.json()
                
                # Check for API-level errors
                if not isinstance(data, dict):
                    raise ValueError("Invalid API response format")
                    
                if data.get("response", {}).get("result") != "success":
                    error_msg = data.get("response", {}).get("message", "Unknown API error")
                    raise ValueError(f"API error: {error_msg}")
                    
                logger.debug(f"Successfully fetched data from {endpoint}")
                return data.get("response", {}).get("data", {})
                
            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1} for {endpoint}")
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except httpx.HTTPError as e:
                logger.warning(f"HTTP error on attempt {attempt + 1} for {endpoint}: {e}")
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)
                
        # This should never be reached due to the raise statements above
        raise RuntimeError("Unexpected error in request retry loop")
        
    async def get_play_history(
        self,
        time_range: int = 30,
        user_id: Optional[int] = None
    ) -> dict[str, Any]:
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
            
        params = {
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
        
    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._cache.clear()
        logger.info("Data cache cleared")
