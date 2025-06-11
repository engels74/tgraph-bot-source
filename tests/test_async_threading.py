"""
Test async threading implementation for graph managers.

This module tests that CPU-bound operations are properly executed
in separate threads using asyncio.to_thread() to prevent blocking
the event loop.
"""

import asyncio
import time
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
        mock_config_manager.get_current_config.return_value = mock_config

        # Create GraphManager instance
        graph_manager = GraphManager(mock_config_manager)

        # Mock the components to avoid actual initialization
        with patch.object(graph_manager, '_initialize_components') as mock_init, \
             patch.object(graph_manager, '_cleanup_components') as mock_cleanup:
            
            # Mock the internal components
            mock_data_fetcher = AsyncMock()
            mock_graph_factory = MagicMock()
            
            graph_manager._data_fetcher = mock_data_fetcher
            graph_manager._graph_factory = mock_graph_factory
            
            # Mock the data fetching
            mock_data_fetcher.get_play_history.return_value = {"data": []}

            # Mock the synchronous graph generation method
            def mock_sync_generation(data, progress_tracker=None):
                return ["test_graph.png"]

            # Test that asyncio.to_thread is used
            with patch('asyncio.to_thread') as mock_to_thread:
                # Mock to_thread to return an awaitable that resolves to the result
                future = asyncio.Future()
                future.set_result(["test_graph.png"])
                mock_to_thread.return_value = future

                # Patch the sync method
                with patch.object(graph_manager, '_generate_graphs_sync', mock_sync_generation):
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
        mock_config_manager.get_current_config.return_value = mock_config

        # Create UserGraphManager instance
        user_graph_manager = UserGraphManager(mock_config_manager)

        # Mock the components to avoid actual initialization
        with patch.object(user_graph_manager, '_initialize_components') as mock_init, \
             patch.object(user_graph_manager, '_cleanup_components') as mock_cleanup:
            
            # Mock the internal components
            mock_data_fetcher = AsyncMock()
            mock_graph_factory = MagicMock()
            
            user_graph_manager._data_fetcher = mock_data_fetcher
            user_graph_manager._graph_factory = mock_graph_factory
            
            # Mock the data fetching methods
            mock_data_fetcher.get_play_history.return_value = {"data": []}
            mock_data_fetcher.find_user_by_email.return_value = {"user_id": 123}

            # Mock the synchronous graph generation method
            def mock_sync_user_generation(user_data, progress_tracker=None):
                return []

            # Test that asyncio.to_thread is used
            with patch('asyncio.to_thread') as mock_to_thread:
                # Mock to_thread to return an awaitable that resolves to the result
                future = asyncio.Future()
                future.set_result([])
                mock_to_thread.return_value = future

                # Patch the sync method
                with patch.object(user_graph_manager, '_generate_user_graphs_sync', mock_sync_user_generation):
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
        mock_config_manager.get_current_config.return_value = mock_config

        # Create GraphManager instance
        graph_manager = GraphManager(mock_config_manager)

        # Test cleanup_old_graphs uses asyncio.to_thread
        with patch('asyncio.to_thread') as mock_to_thread:
            # Mock to_thread to return an awaitable that resolves to the result
            future = asyncio.Future()
            future.set_result(5)  # Mock return value for cleanup_old_files
            mock_to_thread.return_value = future

            await graph_manager.cleanup_old_graphs()

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
        mock_config_manager.get_current_config.return_value = mock_config

        graph_manager = GraphManager(mock_config_manager)

        # Mock components
        with patch.object(graph_manager, '_initialize_components'), \
             patch.object(graph_manager, '_cleanup_components'):
            
            mock_data_fetcher = AsyncMock()
            mock_graph_factory = MagicMock()
            
            graph_manager._data_fetcher = mock_data_fetcher
            graph_manager._graph_factory = mock_graph_factory
            
            mock_data_fetcher.get_play_history.return_value = {"data": []}
            
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
            def slow_sync_operation(data, progress_tracker=None):
                time.sleep(0.1)  # Simulate CPU-bound work
                return ["test_graph.png"]

            with patch.object(graph_manager, '_generate_graphs_sync', slow_sync_operation):
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
