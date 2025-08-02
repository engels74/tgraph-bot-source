"""
Data fetcher for Tautulli API integration.

This module provides async HTTP client functionality for fetching data from
Tautulli's API with proper error handling, caching, and pagination support.
"""

from __future__ import annotations

import asyncio
import datetime
import hashlib
import logging
from typing import TYPE_CHECKING, TypedDict, cast, TypeAlias
from collections.abc import Mapping

import httpx

if TYPE_CHECKING:
    from types import TracebackType


# Type definitions for API structures
class TautulliAPIResponse(TypedDict, total=False):
    """Tautulli API response structure."""

    response: "TautulliResponse"


class TautulliResponse(TypedDict, total=False):
    """Tautulli response object structure."""

    result: str
    message: str
    data: dict[str, object] | list[dict[str, object]] | object


class PlayHistoryData(TypedDict):
    """Play history data structure."""

    data: list[Mapping[str, object]]
    recordsFiltered: int
    recordsTotal: int


# Type aliases for improved readability
APIParams: TypeAlias = dict[str, str | int | float | bool]
APIResponseDict: TypeAlias = dict[str, object]
APIResponseMapping: TypeAlias = Mapping[str, object]
APIResponseItem: TypeAlias = object  # Type for items in API response lists

logger = logging.getLogger(__name__)


def calculate_buffer_size(time_range_days: int) -> int:
    """
    Calculate conservative buffer size based on time range.

    Args:
        time_range_days: The configured time range in days

    Returns:
        Buffer size in days using conservative strategy
    """
    if time_range_days <= 30:
        return 7  # Small ranges get 7-day buffer
    elif time_range_days <= 90:
        return 14  # Medium ranges get 14-day buffer
    else:
        return 30  # Large ranges get 30-day buffer


def should_use_date_filtering(use_date_filtering: bool = True) -> bool:
    """
    Determine if date filtering should be used.

    Args:
        use_date_filtering: Whether to enable date filtering (defaults to True)

    Returns:
        True if date filtering should be used, False otherwise
    """
    return use_date_filtering


def calculate_api_date_filter(
    time_range_days: int, buffer_days: int | None = None
) -> str:
    """
    Calculate the 'after' date for Tautulli API filtering with safety buffer.

    Args:
        time_range_days: The desired time range in days
        buffer_days: Optional buffer size (calculated automatically if not provided)

    Returns:
        Date string in "YYYY-MM-DD" format for use in API 'after' parameter
    """
    if buffer_days is None:
        buffer_days = calculate_buffer_size(time_range_days)

    total_days = time_range_days + buffer_days
    after_date = datetime.date.today() - datetime.timedelta(days=total_days)
    return after_date.strftime("%Y-%m-%d")


class DataFetcher:
    """Async data fetcher for Tautulli API with caching and pagination."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize DataFetcher with connection parameters."""
        self.base_url: str = base_url.rstrip("/")
        self.api_key: str = api_key
        self.timeout: float = timeout
        self.max_retries: int = max_retries
        self._client: httpx.AsyncClient | None = None
        self._cache: dict[str, Mapping[str, object]] = {}

    async def __aenter__(self) -> DataFetcher:
        """Enter async context and initialize HTTP client."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context and cleanup HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _get_cache_key(self, command: str, params: APIParams | None = None) -> str:
        """Generate cache key for request."""
        key_data = f"{command}:{params or {}}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def _make_request(
        self, command: str, params: APIParams | None = None
    ) -> APIResponseMapping:
        """Make HTTP request to Tautulli API with retry logic."""
        if self._client is None:
            raise RuntimeError(
                "DataFetcher not initialized. Use as async context manager."
            )

        # Check cache first
        cache_key = self._get_cache_key(command, params)
        if cache_key in self._cache:
            return self._cache[cache_key]

        request_params = {
            "apikey": self.api_key,
            "cmd": command,
            **(params or {}),
        }

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.get(
                    f"{self.base_url}/api/v2",
                    params=request_params,
                )
                _ = response.raise_for_status()

                response_json = response.json()  # pyright: ignore[reportAny] # external API response
                if not isinstance(response_json, dict):
                    raise ValueError("Invalid API response format: expected dict")

                # Cast to our known structure after validation
                response_data = cast(dict[str, object], response_json)

                response_obj = response_data.get("response")
                if not isinstance(response_obj, dict):
                    raise ValueError(
                        "Invalid API response format: missing response object"
                    )

                # Cast to dict after validation
                response_dict = cast(dict[str, object], response_obj)
                if response_dict.get("result") == "error":
                    message_raw = response_dict.get("message", "Unknown API error")
                    message = (
                        message_raw
                        if isinstance(message_raw, str)
                        else "Unknown API error"
                    )
                    raise ValueError(f"API error: {message}")

                result_raw = response_dict.get("data", {})
                result: APIResponseMapping = (
                    cast(APIResponseMapping, result_raw)
                    if isinstance(result_raw, dict)
                    else cast(APIResponseMapping, {})
                )

                # Cache successful response
                self._cache[cache_key] = result
                return result

            except httpx.TimeoutException:
                if attempt < self.max_retries:
                    wait_time = 2.0**attempt
                    logger.warning(
                        "Request timeout (attempt %d/%d), retrying in %.1fs...",
                        attempt + 1,
                        self.max_retries + 1,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise

        # This should never be reached due to the exception handling above
        raise RuntimeError("Maximum retries exceeded")

    async def get_play_history(
        self,
        time_range: int,
        user_id: int | None = None,
        use_date_filtering: bool = True,
    ) -> PlayHistoryData:
        """
        Fetch play history with pagination support and optional date filtering.

        Args:
            time_range: Time range parameter for Tautulli API (legacy, kept for compatibility)
            user_id: Optional user ID to filter by
            use_date_filtering: Whether to use API-level date filtering with buffer (default: True)

        Returns:
            PlayHistoryData with fetched records and metadata
        """
        all_data: list[Mapping[str, object]] = []
        start = 0
        length = 1000
        total_records = 0

        params: APIParams = {
            "length": length,
            "start": start,
            "time_range": time_range,
        }
        if user_id is not None:
            params["user_id"] = user_id

        # Add date filtering with safety buffer if enabled
        if should_use_date_filtering(use_date_filtering):
            after_date = calculate_api_date_filter(time_range)
            params["after"] = after_date
            logger.debug(
                f"Using API date filtering: after={after_date} (time_range={time_range} days + buffer)"
            )

        while True:
            params["start"] = start
            response_data = await self._make_request("get_history", params)

            page_data_raw = response_data.get("data", [])
            if not isinstance(page_data_raw, list):
                break

            # Type-safe iteration over API response list
            page_items_count = 0
            for item_raw in page_data_raw:  # pyright: ignore[reportUnknownVariableType] # external API response
                page_items_count += 1
                item: APIResponseItem = item_raw  # pyright: ignore[reportUnknownVariableType] # external API response
                if isinstance(item, dict):
                    all_data.append(cast(Mapping[str, object], item))

            records_filtered_raw = response_data.get("recordsFiltered", 0)

            if isinstance(records_filtered_raw, int):
                total_records = records_filtered_raw

            # Stop if we got less than a full page or intelligent stopping for small time ranges
            if page_items_count < length or (time_range <= 7 and len(all_data) >= 500):
                break

            start += length

        return PlayHistoryData(
            data=all_data,
            recordsFiltered=total_records,
            recordsTotal=total_records,
        )

    async def get_plays_per_month(
        self, time_range_months: int = 12
    ) -> Mapping[str, object]:
        """Fetch monthly play statistics."""
        return await self._make_request(
            "get_plays_per_month", {"time_range": time_range_months}
        )

    async def get_user_stats(self, user_id: int) -> Mapping[str, object]:
        """Fetch user statistics."""
        return await self._make_request("get_user", {"user_id": user_id})

    async def get_library_stats(self) -> Mapping[str, object]:
        """Fetch library statistics."""
        return await self._make_request("get_libraries")

    async def find_user_by_email(self, email: str) -> Mapping[str, object] | None:
        """Find user by email address."""
        users_response = await self._make_request("get_users")
        users_data_raw = users_response.get("data", [])

        if isinstance(users_data_raw, list):
            # Type-safe iteration over API response list
            for user_raw in users_data_raw:  # pyright: ignore[reportUnknownVariableType] # external API response
                user: APIResponseItem = user_raw  # pyright: ignore[reportUnknownVariableType] # external API response
                if isinstance(user, dict):
                    user_dict = cast(dict[str, object], user)
                    if user_dict.get("email") == email:
                        return cast(Mapping[str, object], user_dict)

        return None

    async def get_media_metadata(self, rating_key: int) -> Mapping[str, object]:
        """
        Fetch media metadata including resolution information for a specific item.
        
        Args:
            rating_key: The Plex rating key for the media item
            
        Returns:
            Media metadata including resolution, codec, and other technical details
        """
        return await self._make_request("get_metadata", {"rating_key": rating_key})
    
    async def get_library_media_info(
        self, 
        section_id: int | None = None,
        order_column: str = "video_resolution",
        order_dir: str = "desc",
        length: int = 1000
    ) -> Mapping[str, object]:
        """
        Fetch library media information including resolution data.
        
        Args:
            section_id: Optional library section ID to filter by
            order_column: Column to order by (default: video_resolution)  
            order_dir: Order direction (asc/desc, default: desc)
            length: Number of items to fetch (default: 1000)
            
        Returns:
            Library media information with resolution and technical metadata
        """
        params: APIParams = {
            "order_column": order_column,
            "order_dir": order_dir,
            "length": length
        }
        if section_id is not None:
            params["section_id"] = section_id
            
        return await self._make_request("get_library_media_info", params)

    def clear_cache(self) -> None:
        """Clear the request cache."""
        self._cache.clear()
