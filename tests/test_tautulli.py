"""Tests for Tautulli API client.

This test suite validates the Tautulli API client including:
- Successful API responses using httpx mock
- API error handling (timeouts, 4xx, 5xx errors)
- Retry logic with exponential backoff
- get_history and get_user_history methods
- Response validation and field extraction

Requirements tested: 2.1, 2.2, 2.3, 2.4, 2.5
"""

# pyright: reportExplicitAny=false
# pyright: reportAny=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnusedCallResult=false

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from tgraph_bot.api.tautulli import (
    INITIAL_RETRY_DELAY,
    MAX_RETRIES,
    TautulliClient,
)
from tgraph_bot.utils.errors import TautulliAPIError


# Fixtures for test data
@pytest.fixture
def tautulli_client() -> TautulliClient:
    """Fixture providing a TautulliClient instance for testing."""
    return TautulliClient(
        api_key="test_api_key_1234567890",
        base_url="http://localhost:8181",
        timeout=5.0,
    )


@pytest.fixture
def sample_tautulli_response() -> dict[str, Any]:
    """Fixture providing a sample successful Tautulli API response."""
    return {
        "response": {
            "result": "success",
            "message": None,
            "data": {
                "recordsFiltered": 2,
                "recordsTotal": 2,
                "data": [
                    {
                        "date": 1704067200,
                        "media_type": "movie",
                        "stream_type": "direct play",
                        "platform": "Plex for Android",
                        "user": "JohnDoe",
                        "stream_video_resolution": "1080p",
                        "stream_video_full_resolution": "1920x1080",
                        "title": "Test Movie",
                        "year": 2024,
                    },
                    {
                        "date": 1704070800,
                        "media_type": "episode",
                        "stream_type": "transcode",
                        "platform": "Plex for iOS",
                        "user": "JaneDoe",
                        "stream_video_resolution": "720p",
                        "stream_video_full_resolution": "1280x720",
                        "title": "Test Show - S01E01",
                        "year": 2024,
                    },
                ],
            },
        }
    }


@pytest.fixture
def sample_empty_response() -> dict[str, Any]:
    """Fixture providing an empty but valid Tautulli API response."""
    return {
        "response": {
            "result": "success",
            "message": None,
            "data": {
                "recordsFiltered": 0,
                "recordsTotal": 0,
                "data": [],
            },
        }
    }


@pytest.fixture
def sample_error_response() -> dict[str, Any]:
    """Fixture providing a Tautulli API error response."""
    return {
        "response": {
            "result": "error",
            "message": "Invalid API key",
        }
    }


class TestTautulliClientCreation:
    """Tests for TautulliClient instantiation and immutability."""

    def test_create_client_with_required_params(self) -> None:
        """Test creating client with required parameters."""
        client = TautulliClient(
            api_key="test_key",
            base_url="http://localhost:8181",
        )

        assert client.api_key == "test_key"
        assert client.base_url == "http://localhost:8181"
        assert client.timeout == 30.0  # Default value

    def test_create_client_with_custom_timeout(self) -> None:
        """Test creating client with custom timeout."""
        client = TautulliClient(
            api_key="test_key",
            base_url="http://localhost:8181",
            timeout=10.0,
        )

        assert client.timeout == 10.0

    def test_client_is_frozen(self, tautulli_client: TautulliClient) -> None:
        """Test that TautulliClient is immutable (frozen=True)."""
        with pytest.raises((AttributeError, TypeError)):
            tautulli_client.api_key = "modified"  # pyright: ignore[reportAttributeAccessIssue]


class TestGetHistory:
    """Tests for get_history method.

    Requirements: 2.1, 2.2, 2.4, 2.5
    """

    @pytest.mark.asyncio
    async def test_get_history_success(
        self,
        tautulli_client: TautulliClient,
        sample_tautulli_response: dict[str, Any],
    ) -> None:
        """Test successful retrieval of history data."""
        # Mock the httpx client response
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = sample_tautulli_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await tautulli_client.get_history(days=7)

            # Verify we got the expected records
            assert len(result) == 2
            assert result[0]["media_type"] == "movie"
            assert result[0]["user"] == "JohnDoe"
            assert result[1]["media_type"] == "episode"
            assert result[1]["user"] == "JaneDoe"

            # Verify the API was called correctly
            mock_client.get.assert_called_once()
            call_url = mock_client.get.call_args[0][0]
            assert "cmd=get_history" in call_url
            assert "length=1000" in call_url

    @pytest.mark.asyncio
    async def test_get_history_with_custom_length(
        self,
        tautulli_client: TautulliClient,
        sample_tautulli_response: dict[str, Any],
    ) -> None:
        """Test get_history with custom length parameter."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = sample_tautulli_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await tautulli_client.get_history(days=30, length=500)

            assert len(result) == 2
            call_url = mock_client.get.call_args[0][0]
            assert "length=500" in call_url

    @pytest.mark.asyncio
    async def test_get_history_empty_response(
        self,
        tautulli_client: TautulliClient,
        sample_empty_response: dict[str, Any],
    ) -> None:
        """Test get_history with empty but valid response."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = sample_empty_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await tautulli_client.get_history(days=7)

            assert len(result) == 0

    @pytest.mark.parametrize(
        "invalid_days",
        [0, -1, 366, 1000],
    )
    @pytest.mark.asyncio
    async def test_get_history_invalid_days(
        self,
        tautulli_client: TautulliClient,
        invalid_days: int,
    ) -> None:
        """Test get_history rejects invalid days parameter."""
        with pytest.raises(ValueError, match="days must be between 1 and 365"):
            await tautulli_client.get_history(days=invalid_days)

    @pytest.mark.asyncio
    async def test_get_history_validates_required_fields(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test that records missing required fields are skipped."""
        # Response with one valid and one invalid record
        response_with_missing_fields = {
            "response": {
                "result": "success",
                "data": {
                    "data": [
                        {
                            "date": 1704067200,
                            "media_type": "movie",
                            "stream_type": "direct play",
                            "platform": "Plex",
                            "user": "User1",
                            "stream_video_resolution": "1080p",
                            "stream_video_full_resolution": "1920x1080",
                        },
                        {
                            # Missing required fields
                            "date": 1704070800,
                            "media_type": "movie",
                        },
                    ],
                },
            }
        }

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = response_with_missing_fields

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await tautulli_client.get_history(days=7)

            # Should only return the valid record
            assert len(result) == 1
            assert result[0]["user"] == "User1"


class TestGetUserHistory:
    """Tests for get_user_history method.

    Requirements: 2.1, 2.2, 2.4, 2.5
    """

    @pytest.mark.asyncio
    async def test_get_user_history_success(
        self,
        tautulli_client: TautulliClient,
        sample_tautulli_response: dict[str, Any],
    ) -> None:
        """Test successful retrieval of user-specific history."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = sample_tautulli_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await tautulli_client.get_user_history(
                username="JohnDoe",
                days=7,
            )

            assert len(result) == 2
            # Verify the API was called with user parameter
            call_url = mock_client.get.call_args[0][0]
            assert "user=JohnDoe" in call_url

    @pytest.mark.asyncio
    async def test_get_user_history_with_custom_length(
        self,
        tautulli_client: TautulliClient,
        sample_tautulli_response: dict[str, Any],
    ) -> None:
        """Test get_user_history with custom length parameter."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = sample_tautulli_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await tautulli_client.get_user_history(
                username="JohnDoe",
                days=30,
                length=200,
            )

            assert len(result) == 2
            call_url = mock_client.get.call_args[0][0]
            assert "length=200" in call_url

    @pytest.mark.parametrize(
        "invalid_days",
        [0, -1, 366, 1000],
    )
    @pytest.mark.asyncio
    async def test_get_user_history_invalid_days(
        self,
        tautulli_client: TautulliClient,
        invalid_days: int,
    ) -> None:
        """Test get_user_history rejects invalid days parameter."""
        with pytest.raises(ValueError, match="days must be between 1 and 365"):
            await tautulli_client.get_user_history(
                username="JohnDoe",
                days=invalid_days,
            )

    @pytest.mark.parametrize(
        "invalid_username",
        ["", "   "],
    )
    @pytest.mark.asyncio
    async def test_get_user_history_empty_username(
        self,
        tautulli_client: TautulliClient,
        invalid_username: str,
    ) -> None:
        """Test get_user_history rejects empty username."""
        with pytest.raises(ValueError, match="username cannot be empty"):
            await tautulli_client.get_user_history(
                username=invalid_username,
                days=7,
            )


class TestAPIErrorHandling:
    """Tests for API error handling.

    Requirements: 2.3
    """

    @pytest.mark.asyncio
    async def test_handle_404_error(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test handling of 404 Not Found error."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(TautulliAPIError) as exc_info:
                await tautulli_client.get_history(days=7)

            assert exc_info.value.status_code == 404
            assert "404" in str(exc_info.value)
            # Should not retry 4xx errors
            assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_handle_401_unauthorized(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test handling of 401 Unauthorized error."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(TautulliAPIError) as exc_info:
                await tautulli_client.get_history(days=7)

            assert exc_info.value.status_code == 401
            # Should not retry 4xx errors
            assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_handle_500_server_error_with_retry(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test retry logic for 500 server errors."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch("asyncio.sleep") as mock_sleep:
                with pytest.raises(TautulliAPIError) as exc_info:
                    await tautulli_client.get_history(days=7)

                assert exc_info.value.status_code == 500
                # Should retry MAX_RETRIES times
                assert mock_client.get.call_count == MAX_RETRIES
                # Should sleep between retries (exponential backoff)
                assert mock_sleep.call_count == MAX_RETRIES - 1

    @pytest.mark.asyncio
    async def test_handle_503_service_unavailable_with_retry(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test retry logic for 503 service unavailable errors."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch("asyncio.sleep"):
                with pytest.raises(TautulliAPIError) as exc_info:
                    await tautulli_client.get_history(days=7)

                assert exc_info.value.status_code == 503
                assert mock_client.get.call_count == MAX_RETRIES

    @pytest.mark.asyncio
    async def test_handle_timeout_with_retry(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test retry logic for timeout errors."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Request timeout")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch("asyncio.sleep") as mock_sleep:
                with pytest.raises(TautulliAPIError) as exc_info:
                    await tautulli_client.get_history(days=7)

                assert "timeout" in str(exc_info.value).lower()
                # Should retry MAX_RETRIES times
                assert mock_client.get.call_count == MAX_RETRIES
                assert mock_sleep.call_count == MAX_RETRIES - 1

    @pytest.mark.asyncio
    async def test_handle_network_error_with_retry(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test retry logic for network errors."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.NetworkError("Connection refused")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch("asyncio.sleep"):
                with pytest.raises(TautulliAPIError) as exc_info:
                    await tautulli_client.get_history(days=7)

                assert "HTTP error" in str(exc_info.value)
                assert mock_client.get.call_count == MAX_RETRIES

    @pytest.mark.asyncio
    async def test_handle_tautulli_api_error_response(
        self,
        tautulli_client: TautulliClient,
        sample_error_response: dict[str, Any],
    ) -> None:
        """Test handling of Tautulli-specific error response."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = sample_error_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(TautulliAPIError) as exc_info:
                await tautulli_client.get_history(days=7)

            assert "Invalid API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_invalid_json_response(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test handling of invalid JSON response."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(TautulliAPIError) as exc_info:
                await tautulli_client.get_history(days=7)

            assert "Failed to parse JSON" in str(exc_info.value)


class TestRetryLogic:
    """Tests for exponential backoff retry logic.

    Requirements: 2.3
    """

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test that retry delays follow exponential backoff pattern."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.text = "Server Error"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch("asyncio.sleep") as mock_sleep:
                with pytest.raises(TautulliAPIError):
                    await tautulli_client.get_history(days=7)

                # Check that sleep delays follow exponential backoff
                sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                assert len(sleep_calls) == MAX_RETRIES - 1

                # First delay should be INITIAL_RETRY_DELAY
                assert sleep_calls[0] == INITIAL_RETRY_DELAY

                # Each subsequent delay should be double the previous (or capped)
                for i in range(1, len(sleep_calls)):
                    expected_delay = min(
                        sleep_calls[i - 1] * 2,
                        10.0,  # MAX_RETRY_DELAY
                    )
                    assert sleep_calls[i] == expected_delay

    @pytest.mark.asyncio
    async def test_retry_success_on_second_attempt(
        self,
        tautulli_client: TautulliClient,
        sample_tautulli_response: dict[str, Any],
    ) -> None:
        """Test successful request after initial failure."""
        # First call fails, second succeeds
        mock_error_response = AsyncMock(spec=httpx.Response)
        mock_error_response.status_code = 500
        mock_error_response.text = "Server Error"

        mock_success_response = AsyncMock(spec=httpx.Response)
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = sample_tautulli_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [
                mock_error_response,
                mock_success_response,
            ]
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch("asyncio.sleep"):
                result = await tautulli_client.get_history(days=7)

                # Should succeed and return data
                assert len(result) == 2
                # Should have made 2 attempts
                assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_client_errors(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test that client errors (4xx) are not retried."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch("asyncio.sleep") as mock_sleep:
                with pytest.raises(TautulliAPIError):
                    await tautulli_client.get_history(days=7)

                # Should not retry
                assert mock_client.get.call_count == 1
                # Should not sleep
                assert mock_sleep.call_count == 0


class TestResponseValidation:
    """Tests for response validation logic.

    Requirements: 2.5
    """

    @pytest.mark.asyncio
    async def test_validate_response_not_dict(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test validation fails when response is not a dict."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = []  # List instead of dict

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(TautulliAPIError) as exc_info:
                await tautulli_client.get_history(days=7)

            assert "Invalid response structure" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_missing_response_key(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test validation fails when 'response' key is missing."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}  # No 'response' key

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(TautulliAPIError) as exc_info:
                await tautulli_client.get_history(days=7)

            assert "Invalid response structure" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_missing_data_key(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test validation fails when 'data' key is missing."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {"result": "success"}
        }  # No 'data' key

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(TautulliAPIError) as exc_info:
                await tautulli_client.get_history(days=7)

            assert "Invalid response structure" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_data_not_list(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test validation fails when data.data is not a list."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "result": "success",
                "data": {
                    "data": "not a list",  # Should be a list
                },
            }
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(TautulliAPIError) as exc_info:
                await tautulli_client.get_history(days=7)

            assert "not a list" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_skips_non_dict_records(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test that non-dict items in data array are skipped."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "result": "success",
                "data": {
                    "data": [
                        "not a dict",
                        {
                            "date": 1704067200,
                            "media_type": "movie",
                            "stream_type": "direct play",
                            "platform": "Plex",
                            "user": "User1",
                            "stream_video_resolution": "1080p",
                            "stream_video_full_resolution": "1920x1080",
                        },
                    ],
                },
            }
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await tautulli_client.get_history(days=7)

            # Should only return the valid dict record
            assert len(result) == 1


class TestURLBuilding:
    """Tests for URL building logic."""

    def test_build_url_removes_trailing_slash(
        self,
    ) -> None:
        """Test that trailing slashes are removed from base URL."""
        client = TautulliClient(
            api_key="test_key",
            base_url="http://localhost:8181/",
        )

        params = {"cmd": "get_history", "apikey": "test_key"}
        url = client.build_url(params)

        # Should not have double slashes
        assert "//" not in url.replace("http://", "")

    def test_build_url_includes_parameters(
        self,
        tautulli_client: TautulliClient,
    ) -> None:
        """Test that URL includes all query parameters."""
        params = {
            "cmd": "get_history",
            "apikey": "test_key",
            "length": 100,
        }
        url = tautulli_client.build_url(params)

        assert "cmd=get_history" in url
        assert "length=100" in url
        assert "/api/v2?" in url
