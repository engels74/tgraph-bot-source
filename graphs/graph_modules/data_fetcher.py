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
        Fetch play history data from Tautulli with automatic pagination.

        This method automatically fetches additional records beyond the initial 1000
        if the TIME_RANGE_DAYS configuration suggests more data might be available.
        It continues fetching until all records within the time range are retrieved
        or reasonable limits are reached.

        Args:
            time_range: Number of days to fetch data for
            user_id: Specific user ID to filter by (None for all users)

        Returns:
            Play history data as a dictionary with all paginated records combined
        """
        cache_key = f"play_history_{time_range}_{user_id}"

        if cache_key in self._cache:
            logger.debug(f"Using cached data for {cache_key}")
            cached_data = self._cache[cache_key]
            return cached_data

        # Fetch data with automatic pagination
        data = await self._fetch_paginated_history(time_range, user_id)

        # Cache the combined result
        self._cache[cache_key] = data

        return data

    async def _fetch_paginated_history(
        self,
        time_range: int,
        user_id: int | None = None
    ) -> TautulliData:
        """
        Fetch play history data with automatic pagination.

        This method implements intelligent pagination that continues fetching
        records until all data within the time range is retrieved or reasonable
        limits are reached to prevent excessive API calls.

        Args:
            time_range: Number of days to fetch data for
            user_id: Specific user ID to filter by (None for all users)

        Returns:
            Combined play history data from all pages
        """
        all_records: list[dict[str, object]] = []
        start_offset = 0
        page_size = 1000
        max_records = 5000  # Safety limit to prevent excessive memory usage
        max_api_calls = 5   # Limit API calls to prevent rate limiting
        api_call_count = 0
        first_page_metadata: dict[str, object] = {}

        logger.info(f"Starting paginated fetch for time_range={time_range} days, user_id={user_id}")

        while api_call_count < max_api_calls and len(all_records) < max_records:
            # Prepare parameters for this page
            params: dict[str, str | int | float | bool] = {
                "length": page_size,
                "start": start_offset,
            }

            # Add time_range parameter to limit data to the specified number of days
            if time_range > 0:
                params["time_range"] = time_range

            if user_id is not None:
                params["user_id"] = user_id

            try:
                # Fetch this page of data
                page_data = await self._make_request("get_history", params)
                api_call_count += 1

                # Store metadata from the first page for the final response
                if api_call_count == 1:
                    first_page_metadata = {k: v for k, v in page_data.items() if k != 'data'}

                # Extract records from this page
                page_records_raw = page_data.get("data", [])
                if not isinstance(page_records_raw, list):
                    logger.warning(f"Page {api_call_count}: Expected list of records, got {type(page_records_raw)}")
                    break

                # Validate that all items in the list are dictionaries
                page_records: list[dict[str, object]] = []
                for item in page_records_raw:  # pyright: ignore[reportUnknownVariableType]
                    if isinstance(item, dict):
                        page_records.append(item)  # pyright: ignore[reportUnknownArgumentType]
                    else:
                        logger.warning(f"Skipping non-dict record: {type(item)}")  # pyright: ignore[reportUnknownArgumentType]

                records_count = len(page_records)
                logger.info(f"Page {api_call_count}: Fetched {records_count} records (offset {start_offset})")

                # If no records returned, we've reached the end
                if records_count == 0:
                    logger.info("No more records available, pagination complete")
                    break

                # Add records to our collection
                all_records.extend(page_records)

                # If we got fewer records than requested, we've reached the end
                if records_count < page_size:
                    logger.info(f"Received {records_count} < {page_size} records, reached end of data")
                    break

                # Check if we should continue based on time range intelligence
                if self._should_stop_pagination(all_records, time_range, api_call_count):
                    logger.info("Stopping pagination based on intelligent analysis")
                    break

                # Prepare for next page
                start_offset += page_size

            except Exception as e:
                logger.error(f"Error fetching page {api_call_count + 1}: {e}")
                # If we have some data, return what we have; otherwise re-raise
                if all_records:
                    logger.warning("Returning partial data due to pagination error")
                    break
                else:
                    raise

        total_records = len(all_records)

        # Log comprehensive pagination summary
        if api_call_count == 1:
            logger.info(f"Single page sufficient: fetched {total_records} records")
        else:
            logger.info(f"Pagination complete: fetched {total_records} total records in {api_call_count} API calls")

        # Log performance metrics for monitoring
        if total_records > 2000:
            logger.info(f"Large dataset retrieved: {total_records} records for {time_range} day time range")
        elif total_records < 100 and time_range > 7:
            logger.info(f"Small dataset: only {total_records} records for {time_range} day time range")

        # Return data in the same format as the original method
        # Include metadata from the first page if available
        result_data: TautulliData = {"data": all_records}

        # If we have metadata from the first page, include it
        if first_page_metadata:
            result_data.update(first_page_metadata)
            # Update the record counts to reflect the total fetched
            result_data['recordsFiltered'] = total_records
            result_data['recordsTotal'] = total_records

        return result_data

    def _should_stop_pagination(
        self,
        all_records: list[dict[str, object]],
        time_range: int,
        api_call_count: int
    ) -> bool:
        """
        Determine if pagination should stop based on intelligent analysis.

        This method analyzes the fetched records to determine if we likely
        have all the data we need for the specified time range, helping to
        avoid unnecessary API calls.

        Args:
            all_records: All records fetched so far
            time_range: Number of days we're fetching data for
            api_call_count: Number of API calls made so far

        Returns:
            True if pagination should stop, False to continue
        """
        if not all_records:
            return False

        # For small time ranges, we likely don't need many records
        if time_range <= 7 and len(all_records) >= 500:
            logger.debug(f"Small time range ({time_range} days) with {len(all_records)} records, likely sufficient")
            return True

        # For medium time ranges, moderate number of records should be sufficient
        if time_range <= 30 and len(all_records) >= 2000:
            logger.debug(f"Medium time range ({time_range} days) with {len(all_records)} records, likely sufficient")
            return True

        # If we've made several API calls, consider stopping to avoid excessive requests
        if api_call_count >= 3 and len(all_records) >= 1500:
            logger.debug(f"Made {api_call_count} API calls with {len(all_records)} records, stopping to avoid excessive requests")
            return True

        # Continue pagination
        return False

    async def get_plays_per_month(
        self,
        time_range_months: int = 12,
        user_id: int | None = None
    ) -> TautulliData:
        """
        Fetch play count data by month from Tautulli using the native get_plays_per_month endpoint.
        
        Args:
            time_range_months: Number of months to fetch data for
            user_id: Specific user ID to filter by (None for all users)
            
        Returns:
            Monthly play count data as a dictionary
        """
        cache_key = f"plays_per_month_{time_range_months}_{user_id}"
        
        if cache_key in self._cache:
            logger.debug(f"Using cached data for {cache_key}")
            cached_data = self._cache[cache_key]
            return cached_data
            
        params: dict[str, str | int | float | bool] = {
            "time_range": time_range_months,
            "y_axis": "plays",  # We want play counts, not duration
            "grouping": 0  # No grouping
        }

        if user_id is not None:
            params["user_id"] = user_id
            
        data = await self._make_request("get_plays_per_month", params)
        
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
