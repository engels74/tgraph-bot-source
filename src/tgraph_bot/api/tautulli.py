"""Tautulli API client for retrieving Plex streaming data.

This module provides an async HTTP client for communicating with Tautulli's API,
including retry logic, error handling, and response validation.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
"""

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, NotRequired, ReadOnly, TypedDict, cast

import httpx

from tgraph_bot.utils.errors import TautulliAPIError

logger = logging.getLogger(__name__)

# Constants for retry logic
MAX_RETRIES: Final[int] = 3
INITIAL_RETRY_DELAY: Final[float] = 1.0
MAX_RETRY_DELAY: Final[float] = 10.0

# Type aliases using PEP 695 syntax
type StreamRecordList = list[dict[str, object]]
type QueryParams = Mapping[str, object]


# TypedDict models for Tautulli API responses
class TautulliStreamRecord(TypedDict):
    """Structure of a stream record returned from Tautulli API.

    Fields:
        date: Unix timestamp of stream start
        media_type: Type of media (movie, episode, track, live, collection, playlist)
        stream_type: Legacy stream type field (direct play, transcode, copy)
        transcode_decision: More accurate stream classification (direct play, direct stream, transcode)
        platform: Client platform name (e.g., "Plex for Android")
        player: Specific player name (e.g., "Plex Web (Chrome)")
        user: Username of the viewer
        stream_video_resolution: Resolution label (e.g., "1080p", "720p")
        stream_video_full_resolution: Full resolution string (e.g., "1920x1080")
        duration: Total media duration in seconds
        play_duration: Actual watch time in seconds
        percent_complete: Percentage of media watched (0-100)
        location: Network location ("wan" or "lan")
    """

    # Core identification fields
    date: ReadOnly[int]
    media_type: ReadOnly[str]
    user: ReadOnly[str]

    # Stream type fields (transcode_decision is more accurate than stream_type)
    stream_type: ReadOnly[str]
    transcode_decision: ReadOnly[str]

    # Platform and player information
    platform: ReadOnly[str]
    player: ReadOnly[str]

    # Video resolution information
    stream_video_resolution: ReadOnly[str]
    stream_video_full_resolution: ReadOnly[str]

    # Duration and completion tracking (optional fields)
    duration: NotRequired[int]
    play_duration: NotRequired[int]
    percent_complete: NotRequired[int]

    # Network location (optional)
    location: NotRequired[str]


class TautulliDataSection(TypedDict):
    """Structure of the data section in Tautulli API response."""

    recordsFiltered: NotRequired[int]
    recordsTotal: NotRequired[int]
    data: list[dict[str, object]]


class TautulliResponseSection(TypedDict):
    """Structure of the response section in Tautulli API response."""

    result: NotRequired[str]
    message: NotRequired[str | None]
    data: TautulliDataSection


class TautulliAPIResponse(TypedDict):
    """Top-level structure of Tautulli API response."""

    response: TautulliResponseSection


@dataclass(slots=True, frozen=True)
class TautulliClient:
    """Async client for Tautulli API interactions.

    This client handles all communication with the Tautulli API, including:
    - Authentication with API key
    - Request retry logic with exponential backoff
    - Error handling for timeouts, 4xx, and 5xx errors
    - Response validation

    The client is immutable (frozen) and uses slots for memory efficiency.

    Attributes:
        api_key: Tautulli API key for authentication
        base_url: Base URL of the Tautulli instance (including http(s)://)
        timeout: Request timeout in seconds

    Requirements:
        - 2.1: Establish connection to Tautulli API endpoint
        - 2.2: Retrieve records for configured time range (1-365 days)
        - 2.3: Log error details for failed requests
        - 2.4: Extract required fields from streaming data
        - 2.5: Validate API responses before processing
    """

    api_key: str
    base_url: str
    timeout: float = 30.0

    def build_url(self, params: QueryParams) -> str:
        """Build the full API URL with query parameters.

        Args:
            params: Query parameters to include in the URL

        Returns:
            Full URL with encoded query parameters
        """
        # Remove trailing slash from base_url if present
        base = self.base_url.rstrip("/")

        # Build query string
        query_parts: list[str] = []
        for key, value in params.items():
            query_parts.append(f"{key}={value}")

        query_string = "&".join(query_parts)
        return f"{base}/api/v2?{query_string}"

    def _build_url_for_logging(self, params: QueryParams) -> str:
        """Build API URL with masked API key for logging purposes.

        Args:
            params: Query parameters to include in the URL

        Returns:
            Full URL with API key masked as ****
        """
        # Remove trailing slash from base_url if present
        base = self.base_url.rstrip("/")

        # Build query string with masked API key
        query_parts: list[str] = []
        for key, value in params.items():
            if key == "apikey":
                query_parts.append(f"{key}=****")
            else:
                query_parts.append(f"{key}={value}")

        query_string = "&".join(query_parts)
        return f"{base}/api/v2?{query_string}"

    async def get_history(
        self,
        *,
        days: int,
        length: int = 1000,
    ) -> StreamRecordList:
        """Retrieve play history for the specified number of days.

        Fetches streaming history from Tautulli for all users within
        the specified time range. Results are limited to the specified length.

        Args:
            days: Number of days of history to retrieve (1-365)
            length: Maximum number of records to retrieve (default: 1000)

        Returns:
            List of stream record dictionaries containing:
            - date: Unix timestamp of stream start
            - media_type: Type of media (movie, episode, track, live, etc.)
            - stream_type: Legacy stream type (direct play, transcode, copy)
            - transcode_decision: Accurate stream type (direct play, direct stream, transcode)
            - platform: Client platform name (e.g., "Plex for Android")
            - player: Specific player name (e.g., "Plex Web (Chrome)")
            - user: Username
            - stream_video_resolution: Resolution label (e.g., "1080p", "720p")
            - stream_video_full_resolution: Full resolution (e.g., "1920x1080")
            - duration: Total media duration in seconds (optional)
            - play_duration: Actual watch time in seconds (optional)
            - percent_complete: Percentage watched 0-100 (optional)
            - location: Network location "wan" or "lan" (optional)

        Raises:
            TautulliAPIError: If API request fails or response is invalid
            ValueError: If days is not in range 1-365

        Requirements:
            - 2.1: Connect to Tautulli API
            - 2.2: Retrieve records for time range
            - 2.4: Extract required fields
            - 2.5: Validate API responses
        """
        if not 1 <= days <= 365:
            raise ValueError(f"days must be between 1 and 365, got {days}")

        params = {
            "cmd": "get_history",
            "apikey": self.api_key,
            "length": length,
            "order_column": "date",
            "order_dir": "desc",
        }

        try:
            response_data = await self._make_request(params)
            return self._extract_history_records(response_data)
        except TautulliAPIError:
            # Re-raise TautulliAPIError as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            logger.error(
                f"Unexpected error retrieving history: {e}",
                extra={"days": days, "length": length},
            )
            raise TautulliAPIError(
                f"Failed to retrieve history: {e}",
                url=self._build_url_for_logging(params),
            ) from e

    async def get_user_history(
        self,
        *,
        username: str,
        days: int,
        length: int = 1000,
    ) -> StreamRecordList:
        """Retrieve play history for a specific user.

        Fetches streaming history from Tautulli for a single user within
        the specified time range.

        Args:
            username: Username to retrieve history for
            days: Number of days of history to retrieve (1-365)
            length: Maximum number of records to retrieve (default: 1000)

        Returns:
            List of stream record dictionaries (same structure as get_history)

        Raises:
            TautulliAPIError: If API request fails or response is invalid
            ValueError: If days is not in range 1-365 or username is empty

        Requirements:
            - 2.1: Connect to Tautulli API
            - 2.2: Retrieve records for time range
            - 2.4: Extract required fields
            - 2.5: Validate API responses
        """
        if not 1 <= days <= 365:
            raise ValueError(f"days must be between 1 and 365, got {days}")
        if not username or not username.strip():
            raise ValueError("username cannot be empty")

        params = {
            "cmd": "get_history",
            "apikey": self.api_key,
            "user": username,
            "length": length,
            "order_column": "date",
            "order_dir": "desc",
        }

        try:
            response_data = await self._make_request(params)
            return self._extract_history_records(response_data)
        except TautulliAPIError:
            # Re-raise TautulliAPIError as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            logger.error(
                f"Unexpected error retrieving user history: {e}",
                extra={"username": username, "days": days, "length": length},
            )
            raise TautulliAPIError(
                f"Failed to retrieve user history: {e}",
                url=self._build_url_for_logging(params),
            ) from e

    async def _make_request(
        self,
        params: QueryParams,
    ) -> TautulliAPIResponse:
        """Make an HTTP request to the Tautulli API with retry logic.

        Implements exponential backoff retry logic for transient failures
        (5xx errors, timeouts, network errors). Does not retry client errors (4xx).

        Args:
            params: Query parameters for the API request

        Returns:
            Parsed JSON response data

        Raises:
            TautulliAPIError: If all retry attempts fail or non-retriable error occurs

        Requirements:
            - 2.1: Establish API connection
            - 2.3: Log error details
            - 2.5: Validate responses
        """
        url = self.build_url(params)
        url_for_logging = self._build_url_for_logging(params)
        retry_delay = INITIAL_RETRY_DELAY

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.debug(
                        f"Tautulli API request (attempt {attempt + 1}/{MAX_RETRIES})",
                        extra={"url": url_for_logging, "cmd": params.get("cmd")},
                    )

                    response = await client.get(url)

                    # Check for HTTP errors
                    if response.status_code >= 400:
                        error_msg = (
                            f"Tautulli API returned {response.status_code}: "
                            f"{response.text}"
                        )
                        logger.error(
                            error_msg,
                            extra={
                                "status_code": response.status_code,
                                "url": url_for_logging,
                                "attempt": attempt + 1,
                            },
                        )

                        # Don't retry client errors (4xx)
                        if 400 <= response.status_code < 500:
                            raise TautulliAPIError(
                                error_msg,
                                status_code=response.status_code,
                                url=url_for_logging,
                            )

                        # Retry server errors (5xx) if we have attempts left
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(retry_delay)
                            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
                            continue

                        # Max retries reached
                        raise TautulliAPIError(
                            f"Max retries reached: {error_msg}",
                            status_code=response.status_code,
                            url=url_for_logging,
                        )

                    # Parse JSON response
                    try:
                        raw_data: object = response.json()  # pyright: ignore[reportAny]  # httpx returns Any
                    except Exception as e:
                        raise TautulliAPIError(
                            f"Failed to parse JSON response: {e}",
                            status_code=response.status_code,
                            url=url_for_logging,
                        ) from e

                    # Validate response structure with type narrowing
                    if not isinstance(raw_data, dict):
                        raise TautulliAPIError(
                            f"Invalid response structure: expected dict, got {type(raw_data).__name__}",
                            status_code=response.status_code,
                            url=url_for_logging,
                        )

                    # Check for required 'response' key
                    if "response" not in raw_data:
                        raise TautulliAPIError(
                            "Invalid response structure: missing 'response' key",
                            status_code=response.status_code,
                            url=url_for_logging,
                        )

                    # Validate response section is a dict
                    response_section_raw: object = raw_data["response"]  # pyright: ignore[reportUnknownVariableType]  # validated below
                    if not isinstance(response_section_raw, dict):
                        raise TautulliAPIError(
                            "Invalid response structure: 'response' is not a dict",
                            status_code=response.status_code,
                            url=url_for_logging,
                        )

                    # Check for Tautulli-specific error in response
                    result_raw: object = response_section_raw.get("result")  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]  # dict.get incomplete stubs
                    if result_raw == "error":
                        message_raw: object = response_section_raw.get("message")  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]  # dict.get incomplete stubs
                        error_msg = (
                            message_raw
                            if isinstance(message_raw, str)
                            else "Unknown error"
                        )
                        raise TautulliAPIError(
                            f"Tautulli API error: {error_msg}",
                            status_code=response.status_code,
                            url=url_for_logging,
                        )

                    logger.debug(
                        "Tautulli API request successful",
                        extra={"url": url_for_logging, "status_code": response.status_code},
                    )

                    # Cast to TautulliAPIResponse after validation
                    # We've validated the structure, so this cast is safe
                    return cast(TautulliAPIResponse, cast(object, raw_data))

            except httpx.TimeoutException as e:
                error_msg = f"Request timeout after {self.timeout}s"
                logger.warning(
                    error_msg,
                    extra={"url": url_for_logging, "attempt": attempt + 1, "timeout": self.timeout},
                )

                # Retry timeouts if we have attempts left
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
                    continue

                # Max retries reached
                raise TautulliAPIError(
                    f"Max retries reached: {error_msg}",
                    url=url_for_logging,
                ) from e

            except httpx.HTTPError as e:
                error_msg = f"HTTP error: {e}"
                logger.warning(
                    error_msg,
                    extra={"url": url_for_logging, "attempt": attempt + 1},
                )

                # Retry network errors if we have attempts left
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
                    continue

                # Max retries reached
                raise TautulliAPIError(
                    f"Max retries reached: {error_msg}",
                    url=url_for_logging,
                ) from e

            except TautulliAPIError:
                # Re-raise TautulliAPIError as-is (no retry)
                raise

        # Should never reach here, but just in case
        raise TautulliAPIError("Unexpected error: max retries reached", url=url_for_logging)

    def _extract_history_records(
        self,
        response_data: TautulliAPIResponse,
    ) -> StreamRecordList:
        """Extract and validate history records from API response.

        Args:
            response_data: Parsed JSON response from Tautulli API

        Returns:
            List of validated stream record dictionaries

        Raises:
            TautulliAPIError: If response structure is invalid or data is missing

        Requirements:
            - 2.4: Extract required fields from streaming data
            - 2.5: Validate API responses before processing
        """
        try:
            # Navigate to the data array with validation
            response_section = response_data["response"]

            # Check for required 'data' key
            if "data" not in response_section:
                raise TautulliAPIError("Invalid response structure: missing 'data' key")

            data_section_raw: object = response_section["data"]
            if not isinstance(data_section_raw, dict):  # pyright: ignore[reportUnnecessaryIsInstance]  # runtime validation
                raise TautulliAPIError(  # pyright: ignore[reportUnreachable]  # runtime validation needed
                    "Invalid response structure: 'data' is not a dict"
                )

            # Cast after validation
            data_section: TautulliDataSection = cast(
                TautulliDataSection, cast(object, data_section_raw)
            )

            raw_records = data_section["data"]
            if not isinstance(raw_records, list):  # pyright: ignore[reportUnnecessaryIsInstance]  # runtime validation
                raise TautulliAPIError(
                    "Invalid response structure: 'data.data' is not a list"
                )

            # Validate required fields in each record
            validated_records: list[dict[str, object]] = []
            required_fields = {
                "date",
                "media_type",
                "stream_type",
                "transcode_decision",
                "platform",
                "player",
                "user",
                "stream_video_resolution",
                "stream_video_full_resolution",
            }

            for i, raw_record in enumerate(raw_records):
                # Check for required fields
                # Note: raw_record is dict[str, object] from TypedDict
                if not isinstance(raw_record, dict):  # pyright: ignore[reportUnnecessaryIsInstance]  # runtime check
                    logger.warning(
                        f"Skipping invalid record at index {i}: not a dict",
                        extra={"record_type": type(raw_record).__name__},
                    )
                    continue

                missing_fields = required_fields - raw_record.keys()
                if missing_fields:
                    logger.warning(
                        f"Skipping record at index {i}: missing fields {missing_fields}",
                        extra={"record_keys": list(raw_record.keys())},
                    )
                    continue

                validated_records.append(raw_record)

            logger.info(
                f"Extracted {len(validated_records)} valid records from Tautulli API",
                extra={
                    "total_records": len(raw_records),
                    "valid_records": len(validated_records),
                },
            )

            return validated_records

        except KeyError as e:
            raise TautulliAPIError(
                f"Missing expected field in API response: {e}"
            ) from e
        except Exception as e:
            raise TautulliAPIError(f"Failed to extract history records: {e}") from e
