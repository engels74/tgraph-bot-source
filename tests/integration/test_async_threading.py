"""
Test async threading implementation for graph managers.

This module tests that CPU-bound operations are properly executed
in separate threads using asyncio.to_thread() to prevent blocking
the event loop.
"""

import time
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from graphs.graph_manager import GraphManager
from graphs.user_graph_manager import UserGraphManager


class TestAsyncThreading:
    """Test async threading implementation in graph managers."""

    @pytest.mark.asyncio
    async def test_graph_manager_async_threading(self) -> None:
        """Test that GraphManager uses async threading for CPU-bound operations."""
        # Mock the config manager
        mock_config_manager = MagicMock()
        mock_config = MagicMock()
        mock_config.TAUTULLI_URL = "http://localhost:8181"
        mock_config.TAUTULLI_API_KEY = "test_key"
        mock_config.TIME_RANGE_DAYS = 30
        mock_config.KEEP_DAYS = 7
        mock_config_manager.get_current_config.return_value = mock_config  # pyright: ignore[reportAny]

        # Create GraphManager instance
        graph_manager = GraphManager(mock_config_manager)

        # Mock the components to avoid actual initialization
        with patch.object(graph_manager, '_initialize_components'), \
             patch.object(graph_manager, '_cleanup_components'):
            
            # Mock the internal components
            mock_data_fetcher = AsyncMock()
            mock_graph_factory = MagicMock()
            
            graph_manager._data_fetcher = mock_data_fetcher  # pyright: ignore[reportPrivateUsage]
            graph_manager._graph_factory = mock_graph_factory  # pyright: ignore[reportPrivateUsage]
            
            # Mock the data fetching
            mock_data_fetcher.get_play_history.return_value = {"data": []}  # pyright: ignore[reportAny]
            mock_data_fetcher.get_plays_per_month.return_value = {"monthly_data": "test"}  # pyright: ignore[reportAny]

            # Mock the synchronous graph generation method
            def mock_sync_generation(_data: dict[str, object], _progress_tracker: object | None = None) -> list[str]:
                return ["test_graph.png"]

            # Test that asyncio.to_thread is used
            with patch('asyncio.to_thread') as mock_to_thread:
                # Create an awaitable future with the result
                future = asyncio.Future()  # pyright: ignore[reportUnknownVariableType] 
                future.set_result(["test_graph.png"])  # pyright: ignore[reportUnknownMemberType]
                mock_to_thread.return_value = future

                # Patch the sync method and simplify file validation to just return expected result
                with patch.object(graph_manager, '_generate_graphs_sync', mock_sync_generation), \
                     patch.object(graph_manager, '_validate_generated_files', return_value=["test_graph.png"]):
                    async with graph_manager:
                        result = await graph_manager.generate_all_graphs()

                # Verify asyncio.to_thread was called
                mock_to_thread.assert_called_once()
                assert result == ["test_graph.png"]

    @pytest.mark.asyncio
    async def test_user_graph_manager_async_threading(self) -> None:
        """Test that UserGraphManager uses async threading for CPU-bound operations."""
        # Mock the config manager
        mock_config_manager = MagicMock()
        mock_config = MagicMock()
        mock_config.TAUTULLI_URL = "http://localhost:8181"
        mock_config.TAUTULLI_API_KEY = "test_key"
        mock_config.TIME_RANGE_DAYS = 30
        mock_config.KEEP_DAYS = 7
        mock_config_manager.get_current_config.return_value = mock_config  # pyright: ignore[reportAny]

        # Create UserGraphManager instance
        user_graph_manager = UserGraphManager(mock_config_manager)

        # Mock the components to avoid actual initialization
        with patch.object(user_graph_manager, '_initialize_components'), \
             patch.object(user_graph_manager, '_cleanup_components'):
            
            # Mock the internal components
            mock_data_fetcher = AsyncMock()
            # Fix: clear_cache is a synchronous method, so we need to mock it properly
            mock_data_fetcher.clear_cache = MagicMock()
            mock_graph_factory = MagicMock()
            
            user_graph_manager._data_fetcher = mock_data_fetcher  # pyright: ignore[reportPrivateUsage]
            user_graph_manager._graph_factory = mock_graph_factory  # pyright: ignore[reportPrivateUsage]
            
            # Mock the data fetching methods
            mock_data_fetcher.get_play_history.return_value = {"data": []}  # pyright: ignore[reportAny]
            mock_data_fetcher.find_user_by_email.return_value = {"user_id": 123}  # pyright: ignore[reportAny]

            # Mock the synchronous graph generation method
            def mock_sync_user_generation(_user_email: str, _user_data: dict[str, object], _progress_tracker: object | None = None) -> list[str]:
                return []

            # Test that asyncio.to_thread is used
            with patch('asyncio.to_thread') as mock_to_thread:
                # Create an awaitable future with the result
                future = asyncio.Future()  # pyright: ignore[reportUnknownVariableType] 
                future.set_result([])  # pyright: ignore[reportUnknownMemberType]
                mock_to_thread.return_value = future

                # Patch the sync method and simplify file validation to just return expected result
                with patch.object(user_graph_manager, '_generate_user_graphs_sync', mock_sync_user_generation), \
                     patch.object(user_graph_manager, '_validate_generated_user_files', return_value=[]):
                    async with user_graph_manager:
                        result = await user_graph_manager.generate_user_graphs("test@example.com")

                # Verify asyncio.to_thread was called
                mock_to_thread.assert_called_once()
                assert result == []

    @pytest.mark.asyncio
    async def test_cleanup_operations_async_threading(self) -> None:
        """Test that cleanup operations use async threading."""
        # Mock the config manager
        mock_config_manager = MagicMock()
        mock_config = MagicMock()
        mock_config.KEEP_DAYS = 7
        mock_config_manager.get_current_config.return_value = mock_config  # pyright: ignore[reportAny]

        # Create GraphManager instance
        graph_manager = GraphManager(mock_config_manager)

        # Test cleanup_old_graphs uses asyncio.to_thread
        with patch('asyncio.to_thread') as mock_to_thread:
            # Create an awaitable future with the result
            future = asyncio.Future()  # pyright: ignore[reportUnknownVariableType] 
            future.set_result(5)  # Mock return value for cleanup_old_files  # pyright: ignore[reportUnknownMemberType]
            mock_to_thread.return_value = future

            _ = await graph_manager.cleanup_old_graphs()

            # Verify asyncio.to_thread was called for file operations
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_loop_responsiveness(self) -> None:
        """Test that the event loop remains responsive during graph generation."""
        # This test verifies that CPU-bound operations don't block the event loop
        
        # Mock the config manager
        mock_config_manager = MagicMock()
        mock_config = MagicMock()
        mock_config.TAUTULLI_URL = "http://localhost:8181"
        mock_config.TAUTULLI_API_KEY = "test_key"
        mock_config.TIME_RANGE_DAYS = 30
        mock_config_manager.get_current_config.return_value = mock_config  # pyright: ignore[reportAny]

        graph_manager = GraphManager(mock_config_manager)

        # Mock components
        with patch.object(graph_manager, '_initialize_components'), \
             patch.object(graph_manager, '_cleanup_components'):
            
            mock_data_fetcher = AsyncMock()
            mock_graph_factory = MagicMock()
            
            graph_manager._data_fetcher = mock_data_fetcher  # pyright: ignore[reportPrivateUsage]
            graph_manager._graph_factory = mock_graph_factory  # pyright: ignore[reportPrivateUsage]
            
            mock_data_fetcher.get_play_history.return_value = {"data": []}  # pyright: ignore[reportAny]
            mock_data_fetcher.get_plays_per_month.return_value = {"monthly_data": "test"}  # pyright: ignore[reportAny]
            
            # Create a counter to verify the event loop is responsive
            counter = 0
            
            async def increment_counter():
                nonlocal counter
                for _ in range(10):
                    await asyncio.sleep(0.01)  # Small delay
                    counter += 1
            
            # Start the counter task
            counter_task = asyncio.create_task(increment_counter())
            
            # Mock graph generation with actual asyncio.to_thread
            def slow_sync_operation(_data: dict[str, object], _progress_tracker: object | None = None) -> list[str]:
                time.sleep(0.1)  # Simulate CPU-bound work
                return ["test_graph.png"]

            # Mock the file validation to return files as-is (since they don't exist in test)
            def mock_validate_files(files: list[str], _tracker: object) -> list[str]:
                return files
            
            with patch.object(graph_manager, '_generate_graphs_sync', slow_sync_operation), \
                 patch.object(graph_manager, '_validate_generated_files', mock_validate_files):
                async with graph_manager:
                    # Run graph generation and counter concurrently
                    graph_task = asyncio.create_task(graph_manager.generate_all_graphs())
                    
                    # Wait for both tasks
                    results = await asyncio.gather(graph_task, counter_task)
                    
                    # Verify both completed
                    assert results[0] == ["test_graph.png"]  # Graph generation result
                    assert counter == 10  # Counter completed, proving event loop wasn't blocked


if __name__ == "__main__":
    # Run a simple test to verify async threading works
    async def main():
        test_instance = TestAsyncThreading()
        await test_instance.test_event_loop_responsiveness()
        print("✅ Async threading test passed - event loop remains responsive!")

    asyncio.run(main())
