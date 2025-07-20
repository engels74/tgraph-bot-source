"""Tests for data fetcher functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from src.tgraph_bot.graphs.graph_modules import DataFetcher


class TestDataFetcher:
    """Test cases for DataFetcher functionality."""

    @pytest.fixture
    def data_fetcher(self) -> DataFetcher:
        """Create a DataFetcher instance for testing."""
        return DataFetcher(
            base_url="http://localhost:8181",
            api_key="test_api_key",
            timeout=30.0,
            max_retries=3,
        )

    @pytest.fixture
    def mock_successful_response(self) -> dict[str, object]:
        """Mock successful API response."""
        return {
            "response": {
                "result": "success",
                "message": None,
                "data": {
                    "recordsFiltered": 100,
                    "recordsTotal": 100,
                    "data": [{"date": "2024-01-01", "plays": 25, "duration": 3600}],
                },
            }
        }

    @pytest.fixture
    def mock_error_response(self) -> dict[str, object]:
        """Mock error API response."""
        return {
            "response": {"result": "error", "message": "Invalid API key", "data": None}
        }

    def test_init(self, data_fetcher: DataFetcher) -> None:
        """Test DataFetcher initialization."""
        assert data_fetcher.base_url == "http://localhost:8181"
        assert data_fetcher.api_key == "test_api_key"
        assert data_fetcher.timeout == 30.0
        assert data_fetcher.max_retries == 3
        assert data_fetcher._client is None  # pyright: ignore[reportPrivateUsage]
        assert data_fetcher._cache == {}  # pyright: ignore[reportPrivateUsage]

    def test_init_strips_trailing_slash(self) -> None:
        """Test that trailing slash is stripped from base URL."""
        fetcher = DataFetcher(base_url="http://localhost:8181/", api_key="test_key")
        assert fetcher.base_url == "http://localhost:8181"

    @pytest.mark.asyncio
    async def test_context_manager(self, data_fetcher: DataFetcher) -> None:
        """Test async context manager functionality."""
        async with data_fetcher as fetcher:
            assert fetcher._client is not None  # pyright: ignore[reportPrivateUsage]
            assert isinstance(fetcher._client, httpx.AsyncClient)  # pyright: ignore[reportPrivateUsage]

        # Client should be closed after exiting context
        assert fetcher._client is None  # pyright: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_make_request_not_initialized(
        self, data_fetcher: DataFetcher
    ) -> None:
        """Test that _make_request raises error when not initialized."""
        with pytest.raises(RuntimeError, match="DataFetcher not initialized"):
            _ = await data_fetcher._make_request("get_history")  # pyright: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_make_request_success(
        self, data_fetcher: DataFetcher, mock_successful_response: dict[str, object]
    ) -> None:
        """Test successful API request."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock successful response
            mock_response = Mock()
            mock_response.json.return_value = mock_successful_response  # pyright: ignore[reportAny]
            mock_response.raise_for_status.return_value = None  # pyright: ignore[reportAny]
            mock_client.get.return_value = mock_response  # pyright: ignore[reportAny]

            async with data_fetcher:
                result = await data_fetcher._make_request("get_history", {"user_id": 1})  # pyright: ignore[reportPrivateUsage]

            # Verify request was made with correct parameters
            mock_client.get.assert_called_once()  # pyright: ignore[reportAny]
            call_args = mock_client.get.call_args  # pyright: ignore[reportAny]
            assert call_args is not None
            assert call_args[0][0] == "http://localhost:8181/api/v2"
            params: dict[str, object] = call_args[1]["params"]  # pyright: ignore[reportAny]
            assert params["apikey"] == "test_api_key"
            assert params["cmd"] == "get_history"
            assert params["user_id"] == 1

            # Verify result
            response_obj = mock_successful_response["response"]
            assert isinstance(response_obj, dict)
            expected_data: dict[str, object] = response_obj["data"]  # pyright: ignore[reportUnknownVariableType]
            assert result == expected_data

    @pytest.mark.asyncio
    async def test_make_request_api_error(
        self, data_fetcher: DataFetcher, mock_error_response: dict[str, object]
    ) -> None:
        """Test API error response handling."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock error response
            mock_response = Mock()
            mock_response.json.return_value = mock_error_response  # pyright: ignore[reportAny]
            mock_response.raise_for_status.return_value = None  # pyright: ignore[reportAny]
            mock_client.get.return_value = mock_response  # pyright: ignore[reportAny]

            async with data_fetcher:
                with pytest.raises(ValueError, match="API error: Invalid API key"):
                    _ = await data_fetcher._make_request("get_history")  # pyright: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_make_request_invalid_response_format(
        self, data_fetcher: DataFetcher
    ) -> None:
        """Test handling of invalid response format."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock invalid response (not a dict)
            mock_response = Mock()
            mock_response.json.return_value = "invalid response"  # pyright: ignore[reportAny]
            mock_response.raise_for_status.return_value = None  # pyright: ignore[reportAny]
            mock_client.get.return_value = mock_response  # pyright: ignore[reportAny]

            async with data_fetcher:
                with pytest.raises(ValueError, match="Invalid API response format"):
                    _ = await data_fetcher._make_request("get_history")  # pyright: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_make_request_timeout_retry(self, data_fetcher: DataFetcher) -> None:
        """Test timeout handling with retry logic."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock timeout on first two attempts, success on third
            mock_client.get.side_effect = [  # pyright: ignore[reportAny]
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                Mock(
                    json=lambda: {"response": {"result": "success", "data": {}}},  # pyright: ignore[reportUnknownLambdaType]
                    raise_for_status=lambda: None,
                ),
            ]

            with patch("asyncio.sleep") as mock_sleep:
                async with data_fetcher:
                    result = await data_fetcher._make_request("get_history")  # pyright: ignore[reportPrivateUsage]

                # Verify exponential backoff sleep calls
                assert mock_sleep.call_count == 2
                mock_sleep.assert_any_call(1)  # 2^0
                mock_sleep.assert_any_call(2)  # 2^1

                assert result == {}

    @pytest.mark.asyncio
    async def test_make_request_max_retries_exceeded(
        self, data_fetcher: DataFetcher
    ) -> None:
        """Test that max retries are respected."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock timeout on all attempts
            mock_client.get.side_effect = httpx.TimeoutException("Timeout")  # pyright: ignore[reportAny]

            with patch("asyncio.sleep"):
                async with data_fetcher:
                    with pytest.raises(httpx.TimeoutException):
                        _ = await data_fetcher._make_request("get_history")  # pyright: ignore[reportPrivateUsage]

                # Should attempt max_retries + 1 times (4 total)
                assert mock_client.get.call_count == 4  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_get_play_history_success(
        self, data_fetcher: DataFetcher, mock_successful_response: dict[str, object]
    ) -> None:
        """Test successful play history retrieval with pagination."""
        with patch.object(data_fetcher, "_make_request") as mock_make_request:
            response_obj = mock_successful_response["response"]
            assert isinstance(response_obj, dict)
            mock_make_request.return_value = response_obj["data"]

            async with data_fetcher:
                result = await data_fetcher.get_play_history(time_range=30, user_id=1)

            # With pagination, should make at least one call
            assert mock_make_request.call_count >= 1

            # Verify the first call has correct parameters
            first_call = mock_make_request.call_args_list[0]
            assert first_call[0][0] == "get_history"
            params: dict[str, object] = first_call[0][1]  # pyright: ignore[reportAny]
            assert params["length"] == 1000
            assert params["start"] == 0
            assert params["time_range"] == 30
            assert params["user_id"] == 1

            # Result should include the data and metadata
            assert "data" in result
            response_obj = mock_successful_response["response"]
            assert isinstance(response_obj, dict)
            expected_data = response_obj["data"]  # pyright: ignore[reportUnknownVariableType] # mock data structure
            assert isinstance(expected_data, dict)
            expected_data_inner = expected_data["data"]  # pyright: ignore[reportUnknownVariableType] # mock data structure
            assert result["data"] == expected_data_inner

    @pytest.mark.asyncio
    async def test_get_play_history_no_user_id(
        self, data_fetcher: DataFetcher, mock_successful_response: dict[str, object]
    ) -> None:
        """Test play history retrieval without user ID filter."""
        with patch.object(data_fetcher, "_make_request") as mock_make_request:
            response_obj = mock_successful_response["response"]
            assert isinstance(response_obj, dict)
            mock_make_request.return_value = response_obj["data"]

            async with data_fetcher:
                result = await data_fetcher.get_play_history(time_range=30)

            # With pagination, should make at least one call
            assert mock_make_request.call_count >= 1

            # Verify the first call has correct parameters (no user_id)
            first_call = mock_make_request.call_args_list[0]
            assert first_call[0][0] == "get_history"
            params: dict[str, object] = first_call[0][1]  # pyright: ignore[reportAny]
            assert params["length"] == 1000
            assert params["start"] == 0
            assert params["time_range"] == 30
            assert "user_id" not in params

            # Result should include the data
            assert "data" in result

    @pytest.mark.asyncio
    async def test_get_play_history_caching(
        self, data_fetcher: DataFetcher, mock_successful_response: dict[str, object]
    ) -> None:
        """Test that play history results are cached with pagination."""
        with patch.object(data_fetcher, "_make_request") as mock_make_request:
            response_obj = mock_successful_response["response"]
            assert isinstance(response_obj, dict)
            mock_make_request.return_value = response_obj["data"]

            async with data_fetcher:
                # First call should make request(s) via pagination
                result1 = await data_fetcher.get_play_history(time_range=30, user_id=1)
                initial_call_count = mock_make_request.call_count

                # Second call should use cache (no additional requests)
                result2 = await data_fetcher.get_play_history(time_range=30, user_id=1)

            # Should not make additional requests due to caching
            assert mock_make_request.call_count == initial_call_count
            assert result1 == result2

    @pytest.mark.asyncio
    async def test_get_play_history_pagination_multiple_pages(
        self, data_fetcher: DataFetcher
    ) -> None:
        """Test that pagination works correctly with multiple pages."""
        # Mock responses for multiple pages
        page1_response = {
            "recordsFiltered": 2500,
            "recordsTotal": 2500,
            "data": [
                {"id": i, "date": 1640995200 + i} for i in range(1000)
            ],  # 1000 records
        }

        page2_response = {
            "recordsFiltered": 2500,
            "recordsTotal": 2500,
            "data": [
                {"id": i, "date": 1640995200 + i} for i in range(1000, 2000)
            ],  # 1000 records
        }

        page3_response = {
            "recordsFiltered": 2500,
            "recordsTotal": 2500,
            "data": [
                {"id": i, "date": 1640995200 + i} for i in range(2000, 2500)
            ],  # 500 records (end)
        }

        mock_responses = [page1_response, page2_response, page3_response]

        with patch.object(
            data_fetcher, "_make_request", side_effect=mock_responses
        ) as mock_make_request:
            async with data_fetcher:
                result = await data_fetcher.get_play_history(
                    time_range=90
                )  # Long time range to avoid intelligent stopping

            # Should make 3 API calls (stops when page 3 returns < 1000 records)
            assert mock_make_request.call_count == 3

            # Verify pagination parameters for each call
            calls = mock_make_request.call_args_list

            # First call: start=0
            first_call_params: dict[str, object] = calls[0][0][1]  # pyright: ignore[reportAny]
            assert first_call_params["start"] == 0
            assert first_call_params["length"] == 1000

            # Second call: start=1000
            second_call_params: dict[str, object] = calls[1][0][1]  # pyright: ignore[reportAny]
            assert second_call_params["start"] == 1000
            assert second_call_params["length"] == 1000

            # Third call: start=2000
            third_call_params: dict[str, object] = calls[2][0][1]  # pyright: ignore[reportAny]
            assert third_call_params["start"] == 2000
            assert third_call_params["length"] == 1000

            # Result should contain all 2500 records
            result_data = result["data"]
            assert isinstance(result_data, list)
            assert len(result_data) == 2500
            assert result["recordsFiltered"] == 2500
            assert result["recordsTotal"] == 2500

    @pytest.mark.asyncio
    async def test_get_play_history_pagination_single_page(
        self, data_fetcher: DataFetcher
    ) -> None:
        """Test that pagination works correctly with single page (< 1000 records)."""
        single_page_response = {
            "recordsFiltered": 500,
            "recordsTotal": 500,
            "data": [{"id": i, "date": 1640995200 + i} for i in range(500)],
        }

        with patch.object(
            data_fetcher, "_make_request", return_value=single_page_response
        ) as mock_make_request:
            async with data_fetcher:
                result = await data_fetcher.get_play_history(time_range=30)

            # Should only make 1 API call (< 1000 records returned)
            assert mock_make_request.call_count == 1

            # Result should contain all 500 records
            result_data = result["data"]
            assert isinstance(result_data, list)
            assert len(result_data) == 500
            assert result["recordsFiltered"] == 500
            assert result["recordsTotal"] == 500

    @pytest.mark.asyncio
    async def test_get_play_history_pagination_intelligent_stopping(
        self, data_fetcher: DataFetcher
    ) -> None:
        """Test that intelligent stopping works for small time ranges."""
        # Mock response that would normally continue pagination
        large_page_response = {
            "recordsFiltered": 5000,
            "recordsTotal": 5000,
            "data": [{"id": i, "date": 1640995200 + i} for i in range(1000)],
        }

        with patch.object(
            data_fetcher, "_make_request", return_value=large_page_response
        ) as mock_make_request:
            async with data_fetcher:
                result = await data_fetcher.get_play_history(
                    time_range=7
                )  # Small time range

            # Should stop early due to intelligent stopping (small time range with sufficient data)
            # Exact count depends on intelligent stopping logic, but should be <= 2 calls
            assert mock_make_request.call_count <= 2

            # Result should contain data
            result_data = result["data"]
            assert isinstance(result_data, list)
            assert len(result_data) >= 500

    @pytest.mark.asyncio
    async def test_get_user_stats(
        self, data_fetcher: DataFetcher, mock_successful_response: dict[str, object]
    ) -> None:
        """Test user statistics retrieval."""
        with patch.object(data_fetcher, "_make_request") as mock_make_request:
            response_obj = mock_successful_response["response"]
            assert isinstance(response_obj, dict)
            mock_make_request.return_value = response_obj["data"]

            async with data_fetcher:
                result = await data_fetcher.get_user_stats(user_id=1)

            mock_make_request.assert_called_once_with("get_user", {"user_id": 1})
            response_obj = mock_successful_response["response"]
            assert isinstance(response_obj, dict)
            assert result == response_obj["data"]

    @pytest.mark.asyncio
    async def test_get_library_stats(
        self, data_fetcher: DataFetcher, mock_successful_response: dict[str, object]
    ) -> None:
        """Test library statistics retrieval."""
        with patch.object(data_fetcher, "_make_request") as mock_make_request:
            response_obj = mock_successful_response["response"]
            assert isinstance(response_obj, dict)
            mock_make_request.return_value = response_obj["data"]

            async with data_fetcher:
                result = await data_fetcher.get_library_stats()

            mock_make_request.assert_called_once_with("get_libraries")
            response_obj = mock_successful_response["response"]
            assert isinstance(response_obj, dict)
            assert result == response_obj["data"]

    def test_clear_cache(self, data_fetcher: DataFetcher) -> None:
        """Test cache clearing functionality."""
        # Add some data to cache
        data_fetcher._cache["test_key"] = {"test": "data"}  # pyright: ignore[reportPrivateUsage]
        assert len(data_fetcher._cache) == 1  # pyright: ignore[reportPrivateUsage]

        # Clear cache
        data_fetcher.clear_cache()
        assert len(data_fetcher._cache) == 0  # pyright: ignore[reportPrivateUsage]
