"""Tests for data fetcher functionality."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from graphs.graph_modules.data_fetcher import DataFetcher


class TestDataFetcher:
    """Test cases for DataFetcher functionality."""

    @pytest.fixture
    def data_fetcher(self) -> DataFetcher:
        """Create a DataFetcher instance for testing."""
        return DataFetcher(
            base_url="http://localhost:8181",
            api_key="test_api_key",
            timeout=30.0,
            max_retries=3
        )

    @pytest.fixture
    def mock_successful_response(self) -> dict[str, Any]:
        """Mock successful API response."""
        return {
            "response": {
                "result": "success",
                "message": None,
                "data": {
                    "recordsFiltered": 100,
                    "recordsTotal": 100,
                    "data": [
                        {
                            "date": "2024-01-01",
                            "plays": 25,
                            "duration": 3600
                        }
                    ]
                }
            }
        }

    @pytest.fixture
    def mock_error_response(self) -> dict[str, Any]:
        """Mock error API response."""
        return {
            "response": {
                "result": "error",
                "message": "Invalid API key",
                "data": None
            }
        }

    def test_init(self, data_fetcher: DataFetcher) -> None:
        """Test DataFetcher initialization."""
        assert data_fetcher.base_url == "http://localhost:8181"
        assert data_fetcher.api_key == "test_api_key"
        assert data_fetcher.timeout == 30.0
        assert data_fetcher.max_retries == 3
        assert data_fetcher._client is None
        assert data_fetcher._cache == {}

    def test_init_strips_trailing_slash(self) -> None:
        """Test that trailing slash is stripped from base URL."""
        fetcher = DataFetcher(
            base_url="http://localhost:8181/",
            api_key="test_key"
        )
        assert fetcher.base_url == "http://localhost:8181"

    @pytest.mark.asyncio
    async def test_context_manager(self, data_fetcher: DataFetcher) -> None:
        """Test async context manager functionality."""
        async with data_fetcher as fetcher:
            assert fetcher._client is not None
            assert isinstance(fetcher._client, httpx.AsyncClient)
        
        # Client should be closed after exiting context
        assert fetcher._client is None

    @pytest.mark.asyncio
    async def test_make_request_not_initialized(self, data_fetcher: DataFetcher) -> None:
        """Test that _make_request raises error when not initialized."""
        with pytest.raises(RuntimeError, match="DataFetcher not initialized"):
            await data_fetcher._make_request("get_history")

    @pytest.mark.asyncio
    async def test_make_request_success(
        self, 
        data_fetcher: DataFetcher, 
        mock_successful_response: dict[str, Any]
    ) -> None:
        """Test successful API request."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock successful response
            mock_response = Mock()
            mock_response.json.return_value = mock_successful_response
            mock_response.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response
            
            async with data_fetcher:
                result = await data_fetcher._make_request("get_history", {"user_id": 1})
            
            # Verify request was made with correct parameters
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert call_args[0][0] == "http://localhost:8181/api/v2"
            assert call_args[1]["params"]["apikey"] == "test_api_key"
            assert call_args[1]["params"]["cmd"] == "get_history"
            assert call_args[1]["params"]["user_id"] == 1
            
            # Verify result
            expected_data = mock_successful_response["response"]["data"]
            assert result == expected_data

    @pytest.mark.asyncio
    async def test_make_request_api_error(
        self, 
        data_fetcher: DataFetcher, 
        mock_error_response: dict[str, Any]
    ) -> None:
        """Test API error response handling."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock error response
            mock_response = Mock()
            mock_response.json.return_value = mock_error_response
            mock_response.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response
            
            async with data_fetcher:
                with pytest.raises(ValueError, match="API error: Invalid API key"):
                    await data_fetcher._make_request("get_history")

    @pytest.mark.asyncio
    async def test_make_request_invalid_response_format(self, data_fetcher: DataFetcher) -> None:
        """Test handling of invalid response format."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock invalid response (not a dict)
            mock_response = Mock()
            mock_response.json.return_value = "invalid response"
            mock_response.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response
            
            async with data_fetcher:
                with pytest.raises(ValueError, match="Invalid API response format"):
                    await data_fetcher._make_request("get_history")

    @pytest.mark.asyncio
    async def test_make_request_timeout_retry(self, data_fetcher: DataFetcher) -> None:
        """Test timeout handling with retry logic."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock timeout on first two attempts, success on third
            mock_client.get.side_effect = [
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                Mock(json=lambda: {"response": {"result": "success", "data": {}}}, 
                     raise_for_status=lambda: None)
            ]
            
            with patch('asyncio.sleep') as mock_sleep:
                async with data_fetcher:
                    result = await data_fetcher._make_request("get_history")
                
                # Verify exponential backoff sleep calls
                assert mock_sleep.call_count == 2
                mock_sleep.assert_any_call(1)  # 2^0
                mock_sleep.assert_any_call(2)  # 2^1
                
                assert result == {}

    @pytest.mark.asyncio
    async def test_make_request_max_retries_exceeded(self, data_fetcher: DataFetcher) -> None:
        """Test that max retries are respected."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock timeout on all attempts
            mock_client.get.side_effect = httpx.TimeoutException("Timeout")
            
            with patch('asyncio.sleep'):
                async with data_fetcher:
                    with pytest.raises(httpx.TimeoutException):
                        await data_fetcher._make_request("get_history")
                
                # Should attempt max_retries + 1 times (4 total)
                assert mock_client.get.call_count == 4

    @pytest.mark.asyncio
    async def test_get_play_history_success(
        self, 
        data_fetcher: DataFetcher,
        mock_successful_response: dict[str, Any]
    ) -> None:
        """Test successful play history retrieval."""
        with patch.object(data_fetcher, '_make_request') as mock_make_request:
            mock_make_request.return_value = mock_successful_response["response"]["data"]
            
            async with data_fetcher:
                result = await data_fetcher.get_play_history(time_range=30, user_id=1)
            
            mock_make_request.assert_called_once_with(
                "get_history", 
                {"length": 1000, "start": 0, "user_id": 1}
            )
            assert result == mock_successful_response["response"]["data"]

    @pytest.mark.asyncio
    async def test_get_play_history_no_user_id(
        self, 
        data_fetcher: DataFetcher,
        mock_successful_response: dict[str, Any]
    ) -> None:
        """Test play history retrieval without user ID filter."""
        with patch.object(data_fetcher, '_make_request') as mock_make_request:
            mock_make_request.return_value = mock_successful_response["response"]["data"]
            
            async with data_fetcher:
                result = await data_fetcher.get_play_history(time_range=30)
            
            mock_make_request.assert_called_once_with(
                "get_history", 
                {"length": 1000, "start": 0}
            )
            assert result == mock_successful_response["response"]["data"]

    @pytest.mark.asyncio
    async def test_get_play_history_caching(
        self, 
        data_fetcher: DataFetcher,
        mock_successful_response: dict[str, Any]
    ) -> None:
        """Test that play history results are cached."""
        with patch.object(data_fetcher, '_make_request') as mock_make_request:
            mock_make_request.return_value = mock_successful_response["response"]["data"]
            
            async with data_fetcher:
                # First call should make request
                result1 = await data_fetcher.get_play_history(time_range=30, user_id=1)
                
                # Second call should use cache
                result2 = await data_fetcher.get_play_history(time_range=30, user_id=1)
            
            # Should only make one request due to caching
            assert mock_make_request.call_count == 1
            assert result1 == result2

    @pytest.mark.asyncio
    async def test_get_user_stats(
        self, 
        data_fetcher: DataFetcher,
        mock_successful_response: dict[str, Any]
    ) -> None:
        """Test user statistics retrieval."""
        with patch.object(data_fetcher, '_make_request') as mock_make_request:
            mock_make_request.return_value = mock_successful_response["response"]["data"]
            
            async with data_fetcher:
                result = await data_fetcher.get_user_stats(user_id=1)
            
            mock_make_request.assert_called_once_with("get_user", {"user_id": 1})
            assert result == mock_successful_response["response"]["data"]

    @pytest.mark.asyncio
    async def test_get_library_stats(
        self, 
        data_fetcher: DataFetcher,
        mock_successful_response: dict[str, Any]
    ) -> None:
        """Test library statistics retrieval."""
        with patch.object(data_fetcher, '_make_request') as mock_make_request:
            mock_make_request.return_value = mock_successful_response["response"]["data"]
            
            async with data_fetcher:
                result = await data_fetcher.get_library_stats()
            
            mock_make_request.assert_called_once_with("get_libraries")
            assert result == mock_successful_response["response"]["data"]

    def test_clear_cache(self, data_fetcher: DataFetcher) -> None:
        """Test cache clearing functionality."""
        # Add some data to cache
        data_fetcher._cache["test_key"] = {"test": "data"}
        assert len(data_fetcher._cache) == 1
        
        # Clear cache
        data_fetcher.clear_cache()
        assert len(data_fetcher._cache) == 0
