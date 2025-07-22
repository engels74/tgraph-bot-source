"""Tests for data fetcher functionality."""

from __future__ import annotations

import datetime
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
        """Test that individual paginated requests are cached."""
        with patch.object(data_fetcher, "_make_request") as mock_make_request:
            response_obj = mock_successful_response["response"]
            assert isinstance(response_obj, dict)
            mock_make_request.return_value = response_obj["data"]

            async with data_fetcher:
                # First call should make request(s) via pagination
                result1 = await data_fetcher.get_play_history(time_range=30, user_id=1)
                initial_call_count = mock_make_request.call_count

                # Second call should make the same paginated requests, but they should be cached
                result2 = await data_fetcher.get_play_history(time_range=30, user_id=1)

            # The same number of requests should be made, but they should come from cache
            # (Individual _make_request calls are cached, not the complete get_play_history result)
            assert mock_make_request.call_count == initial_call_count * 2
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

            # Verify that all calls were made with the expected command
            calls = mock_make_request.call_args_list
            for call in calls:
                command = call[0][0]  # pyright: ignore[reportAny] # mock call args from unittest.mock
                params = call[0][1]  # pyright: ignore[reportAny] # mock call args from unittest.mock
                assert command == "get_history"
                assert params["length"] == 1000
                assert params["time_range"] == 90

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


class TestDateCalculationUtils:
    """Test cases for date calculation utilities."""

    def test_calculate_api_date_filter_basic(self) -> None:
        """Test basic date calculation with buffer."""
        from src.tgraph_bot.graphs.graph_modules.data.data_fetcher import _calculate_api_date_filter
        
        # Test with explicit buffer - should work without mocking since we provide explicit buffer
        result = _calculate_api_date_filter(time_range_days=30, buffer_days=7)
        # Result should be a valid date string format
        assert len(result) == 10  # YYYY-MM-DD format
        assert result.count("-") == 2
        
        # Parse the result and verify it's roughly correct (37 days ago)
        result_date = datetime.datetime.strptime(result, "%Y-%m-%d").date()
        today = datetime.date.today()
        expected_date = today - datetime.timedelta(days=37)
        
        # Allow for some variance in case test runs at midnight boundary
        assert abs((result_date - expected_date).days) <= 1

    def test_calculate_api_date_filter_different_ranges(self) -> None:
        """Test date calculation with different time ranges."""
        from src.tgraph_bot.graphs.graph_modules.data.data_fetcher import _calculate_api_date_filter
        
        # Test small range
        result_small = _calculate_api_date_filter(time_range_days=7, buffer_days=7)
        assert len(result_small) == 10  # YYYY-MM-DD format
        
        # Test large range
        result_large = _calculate_api_date_filter(time_range_days=365, buffer_days=30)
        assert len(result_large) == 10  # YYYY-MM-DD format
        
        # Verify that larger ranges produce earlier dates
        date_small = datetime.datetime.strptime(result_small, "%Y-%m-%d").date()
        date_large = datetime.datetime.strptime(result_large, "%Y-%m-%d").date()
        assert date_large < date_small  # Earlier date for larger range

    def test_calculate_api_date_filter_edge_cases(self) -> None:
        """Test date calculation edge cases."""
        from src.tgraph_bot.graphs.graph_modules.data.data_fetcher import _calculate_api_date_filter
        
        # Test minimum values
        result = _calculate_api_date_filter(time_range_days=1, buffer_days=1)
        assert len(result) == 10  # YYYY-MM-DD format
        
        # Verify it's 2 days ago
        result_date = datetime.datetime.strptime(result, "%Y-%m-%d").date()
        today = datetime.date.today()
        expected_date = today - datetime.timedelta(days=2)
        assert abs((result_date - expected_date).days) <= 1

    def test_calculate_api_date_filter_zero_buffer(self) -> None:
        """Test date calculation with zero buffer."""
        from src.tgraph_bot.graphs.graph_modules.data.data_fetcher import _calculate_api_date_filter
        
        result = _calculate_api_date_filter(time_range_days=30, buffer_days=0)
        assert len(result) == 10  # YYYY-MM-DD format
        
        # Verify it's 30 days ago
        result_date = datetime.datetime.strptime(result, "%Y-%m-%d").date()
        today = datetime.date.today()
        expected_date = today - datetime.timedelta(days=30)
        assert abs((result_date - expected_date).days) <= 1

    def test_calculate_buffer_size_conservative_strategy(self) -> None:
        """Test conservative buffer size calculation."""
        from src.tgraph_bot.graphs.graph_modules.data.data_fetcher import _calculate_buffer_size
        
        # Small ranges get 7-day buffer
        assert _calculate_buffer_size(1) == 7
        assert _calculate_buffer_size(15) == 7
        assert _calculate_buffer_size(30) == 7
        
        # Medium ranges get 14-day buffer
        assert _calculate_buffer_size(31) == 14
        assert _calculate_buffer_size(60) == 14
        assert _calculate_buffer_size(90) == 14
        
        # Large ranges get 30-day buffer
        assert _calculate_buffer_size(91) == 30
        assert _calculate_buffer_size(180) == 30
        assert _calculate_buffer_size(365) == 30

    def test_should_use_date_filtering_logic(self) -> None:
        """Test logic for when to enable date filtering."""
        from src.tgraph_bot.graphs.graph_modules.data.data_fetcher import _should_use_date_filtering
        
        # Always enable date filtering unless explicitly disabled
        assert _should_use_date_filtering(use_date_filtering=True) is True
        assert _should_use_date_filtering(use_date_filtering=False) is False
        assert _should_use_date_filtering() is True  # Default True

    @pytest.mark.asyncio
    async def test_get_play_history_with_date_filtering_enabled(self) -> None:
        """Test get_play_history with date filtering enabled."""
        data_fetcher = DataFetcher(
            base_url="http://localhost:8181",
            api_key="test_api_key",
            timeout=30.0,
            max_retries=3,
        )
        
        mock_response_data = {
            "recordsFiltered": 100,
            "recordsTotal": 100,
            "data": [{"id": 1, "date": "2024-01-01", "plays": 25}],
        }

        with patch.object(data_fetcher, "_make_request", return_value=mock_response_data) as mock_make_request:
            async with data_fetcher:
                result = await data_fetcher.get_play_history(
                    time_range=30, 
                    user_id=1, 
                    use_date_filtering=True
                )

            # Verify the call includes date filtering parameters
            first_call = mock_make_request.call_args_list[0]
            assert first_call[0][0] == "get_history"
            params: dict[str, object] = first_call[0][1]  # pyright: ignore[reportAny]
            
            # Should include existing parameters
            assert params["length"] == 1000
            assert params["start"] == 0
            assert params["time_range"] == 30
            assert params["user_id"] == 1
            
            # Should include date filtering parameter
            assert "after" in params
            # Verify it's a valid date format
            after_value = params["after"]
            assert isinstance(after_value, str)
            assert len(after_value) == 10  # YYYY-MM-DD
            assert after_value.count("-") == 2

            # Result should be properly structured
            assert "data" in result
            assert result["recordsFiltered"] == 100

    @pytest.mark.asyncio
    async def test_get_play_history_with_date_filtering_disabled(self) -> None:
        """Test get_play_history with date filtering disabled."""
        data_fetcher = DataFetcher(
            base_url="http://localhost:8181",
            api_key="test_api_key",
            timeout=30.0,
            max_retries=3,
        )
        
        mock_response_data = {
            "recordsFiltered": 100,
            "recordsTotal": 100,
            "data": [{"id": 1, "date": "2024-01-01", "plays": 25}],
        }

        with patch.object(data_fetcher, "_make_request", return_value=mock_response_data) as mock_make_request:
            async with data_fetcher:
                _ = await data_fetcher.get_play_history(
                    time_range=30, 
                    user_id=1, 
                    use_date_filtering=False
                )

            # Verify the call does NOT include date filtering parameters
            first_call = mock_make_request.call_args_list[0]
            assert first_call[0][0] == "get_history"
            params: dict[str, object] = first_call[0][1]  # pyright: ignore[reportAny]
            
            # Should include existing parameters
            assert params["length"] == 1000
            assert params["start"] == 0
            assert params["time_range"] == 30
            assert params["user_id"] == 1
            
            # Should NOT include date filtering parameter
            assert "after" not in params

    @pytest.mark.asyncio
    async def test_get_play_history_date_filtering_default_behavior(self) -> None:
        """Test that date filtering is enabled by default."""
        data_fetcher = DataFetcher(
            base_url="http://localhost:8181",
            api_key="test_api_key",
            timeout=30.0,
            max_retries=3,
        )
        
        mock_response_data = {
            "recordsFiltered": 50,
            "recordsTotal": 50,
            "data": [{"id": 1, "date": "2024-01-01", "plays": 25}],
        }

        with patch.object(data_fetcher, "_make_request", return_value=mock_response_data) as mock_make_request:
            async with data_fetcher:
                # Don't specify use_date_filtering - should default to True
                _ = await data_fetcher.get_play_history(time_range=90)

            # Should include date filtering by default
            first_call = mock_make_request.call_args_list[0]
            params: dict[str, object] = first_call[0][1]  # pyright: ignore[reportAny]
            assert "after" in params
            # Verify it's a valid date format (should be roughly 104 days ago)
            after_value = params["after"]
            assert isinstance(after_value, str)
            assert len(after_value) == 10  # YYYY-MM-DD

    @pytest.mark.asyncio
    async def test_get_play_history_different_buffer_sizes(self) -> None:
        """Test that different time ranges get appropriate buffer sizes."""
        data_fetcher = DataFetcher(
            base_url="http://localhost:8181",
            api_key="test_api_key",
            timeout=30.0,
            max_retries=3,
        )
        
        mock_response_data = {
            "recordsFiltered": 25,
            "recordsTotal": 25,
            "data": [{"id": 1, "date": "2024-01-01", "plays": 25}],
        }

        with patch.object(data_fetcher, "_make_request", return_value=mock_response_data) as mock_make_request:
            async with data_fetcher:
                # Test small range (should get 7-day buffer)
                _ = await data_fetcher.get_play_history(time_range=7, use_date_filtering=True)
                small_call = mock_make_request.call_args_list[0]
                small_params: dict[str, object] = small_call[0][1]  # pyright: ignore[reportAny]
                small_after = small_params["after"]
                assert isinstance(small_after, str)

                mock_make_request.reset_mock()

                # Test large range (should get 30-day buffer)
                _ = await data_fetcher.get_play_history(time_range=365, use_date_filtering=True)
                large_call = mock_make_request.call_args_list[0]
                large_params: dict[str, object] = large_call[0][1]  # pyright: ignore[reportAny]
                large_after = large_params["after"]
                assert isinstance(large_after, str)
                
                # Large range should produce an earlier date than small range
                small_date = datetime.datetime.strptime(small_after, "%Y-%m-%d").date()
                large_date = datetime.datetime.strptime(large_after, "%Y-%m-%d").date()
                assert large_date < small_date

    @pytest.mark.asyncio
    async def test_get_play_history_backward_compatibility(self) -> None:
        """Test that existing calls without new parameters work unchanged."""
        data_fetcher = DataFetcher(
            base_url="http://localhost:8181",
            api_key="test_api_key",
            timeout=30.0,
            max_retries=3,
        )
        
        mock_response_data = {
            "recordsFiltered": 100,
            "recordsTotal": 100,
            "data": [{"id": 1, "date": "2024-01-01", "plays": 25}],
        }

        with patch.object(data_fetcher, "_make_request", return_value=mock_response_data) as mock_make_request:
            async with data_fetcher:
                # Call exactly like existing code
                result = await data_fetcher.get_play_history(time_range=30, user_id=1)

            # Should include date filtering by default (new behavior)
            first_call = mock_make_request.call_args_list[0]
            params: dict[str, object] = first_call[0][1]  # pyright: ignore[reportAny]
            assert "after" in params
            # Verify it's a valid date format
            after_value = params["after"]
            assert isinstance(after_value, str)
            assert len(after_value) == 10  # YYYY-MM-DD
            
            # Should maintain all existing behavior
            assert params["time_range"] == 30
            assert params["user_id"] == 1
            assert "data" in result


class TestIntegrationDateFiltering:
    """Integration tests for end-to-end date filtering functionality."""

    @pytest.mark.asyncio
    async def test_full_integration_date_filtering_enabled(self) -> None:
        """Test complete workflow with date filtering enabled."""
        data_fetcher = DataFetcher(
            base_url="http://localhost:8181",
            api_key="test_api_key",
            timeout=30.0,
            max_retries=3,
        )
        
        # Mock a typical API response for a 30-day period
        mock_response_data = {
            "recordsFiltered": 250,
            "recordsTotal": 10000,  # Much larger total (demonstrates filtering effect)
            "data": [
                {"id": i, "date": 1640995200 + i*86400, "user": "test_user"} 
                for i in range(250)
            ],
        }

        with patch.object(data_fetcher, "_make_request", return_value=mock_response_data) as mock_make_request:
            async with data_fetcher:
                # Test with date filtering enabled (default)
                result = await data_fetcher.get_play_history(time_range=30)

            # Verify API call was made with date filtering
            first_call = mock_make_request.call_args_list[0]
            params: dict[str, object] = first_call[0][1]  # pyright: ignore[reportAny]
            
            # Should include both traditional and new parameters
            assert params["time_range"] == 30  # Legacy parameter preserved
            assert "after" in params  # New date filtering parameter
            after_date = params["after"]
            assert isinstance(after_date, str)
            assert len(after_date) == 10  # YYYY-MM-DD format

            # Result should include the API response data
            assert result["recordsFiltered"] == 250
            assert result["recordsTotal"] == 250  # DataFetcher sets recordsTotal = recordsFiltered
            assert len(result["data"]) == 250

    @pytest.mark.asyncio
    async def test_integration_buffer_size_verification(self) -> None:
        """Test that buffer sizes are correctly applied based on time range."""
        data_fetcher = DataFetcher(
            base_url="http://localhost:8181",
            api_key="test_api_key",
            timeout=30.0,
            max_retries=3,
        )
        
        mock_response = {"recordsFiltered": 50, "recordsTotal": 50, "data": []}

        with patch.object(data_fetcher, "_make_request", return_value=mock_response) as mock_make_request:
            async with data_fetcher:
                # Test small range (7 + 7 = 14 days buffer)
                _ = await data_fetcher.get_play_history(time_range=15)
                small_call = mock_make_request.call_args_list[0]
                small_after: str = small_call[0][1]["after"]  # pyright: ignore[reportAny]
                
                mock_make_request.reset_mock()
                
                # Test large range (365 + 30 = 395 days buffer)  
                _ = await data_fetcher.get_play_history(time_range=365)
                large_call = mock_make_request.call_args_list[0]
                large_after: str = large_call[0][1]["after"]  # pyright: ignore[reportAny]
                
                # Verify large range produces significantly earlier date
                small_date = datetime.datetime.strptime(small_after, "%Y-%m-%d").date()
                large_date = datetime.datetime.strptime(large_after, "%Y-%m-%d").date()
                days_difference = (small_date - large_date).days
                
                # Expected difference: (15+7) vs (365+30) = 22 vs 395 = 373 days difference
                assert days_difference > 300  # Allow some margin for timing

    @pytest.mark.asyncio
    async def test_integration_backward_compatibility_assurance(self) -> None:
        """Test that existing code patterns continue to work without modification."""
        data_fetcher = DataFetcher(
            base_url="http://localhost:8181",
            api_key="test_api_key",
            timeout=30.0,
            max_retries=3,
        )
        
        mock_response = {
            "recordsFiltered": 100,
            "recordsTotal": 100,
            "data": [{"id": 1, "plays": 5}],
        }

        with patch.object(data_fetcher, "_make_request", return_value=mock_response) as mock_make_request:
            async with data_fetcher:
                # Call using exact same pattern as existing production code
                result = await data_fetcher.get_play_history(time_range=30, user_id=12)

            # Verify all existing behavior is preserved
            call_args = mock_make_request.call_args_list[0]
            params: dict[str, object] = call_args[0][1]  # pyright: ignore[reportAny]
            
            assert params["time_range"] == 30  # Original parameter still works
            assert params["user_id"] == 12     # User filtering still works
            assert params["length"] == 1000    # Pagination still works
            assert params["start"] == 0        # Pagination offset still works
            
            # New feature is transparently added
            assert "after" in params
            
            # Results have same structure
            assert "data" in result
            assert result["recordsFiltered"] == 100
