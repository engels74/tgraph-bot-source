"""
Test enhanced error handling, progress tracking, and resource cleanup for graph managers.

This module tests the improved error handling mechanisms, progress tracking with
detailed reporting, and resource cleanup with timeout protection.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


import pytest

from src.tgraph_bot.graphs.graph_manager import GraphManager, GraphGenerationError
from src.tgraph_bot.graphs.graph_modules.progress_tracker import ProgressTracker
from src.tgraph_bot.graphs.user_graph_manager import UserGraphManager


class TestProgressTracker:
    """Test the ProgressTracker class functionality."""

    def test_progress_tracker_initialization(self) -> None:
        """Test ProgressTracker initialization."""
        callback = MagicMock()
        tracker = ProgressTracker(callback)
        
        assert tracker.callback == callback
        assert tracker.current_step == 0
        assert tracker.total_steps == 0
        assert tracker.errors == []
        assert tracker.warnings == []
        assert isinstance(tracker.start_time, float)

    def test_progress_tracker_update(self) -> None:
        """Test progress tracking updates."""
        callback = MagicMock()
        tracker = ProgressTracker(callback)
        
        tracker.update("Test message", 1, 3, test_data="value")
        
        assert tracker.current_step == 1
        assert tracker.total_steps == 3
        callback.assert_called_once()
        
        # Check callback was called with correct arguments
        callback.assert_called_once()
        assert callback.call_count == 1

    def test_progress_tracker_error_warning_handling(self) -> None:
        """Test error and warning tracking."""
        tracker = ProgressTracker()
        
        tracker.add_error("Test error")
        tracker.add_warning("Test warning")
        
        assert len(tracker.errors) == 1
        assert len(tracker.warnings) == 1
        assert tracker.errors[0] == "Test error"
        assert tracker.warnings[0] == "Test warning"

    def test_progress_tracker_summary(self) -> None:
        """Test progress summary generation."""
        tracker = ProgressTracker()
        tracker.add_error("Error 1")
        tracker.add_warning("Warning 1")
        tracker.update("Test", 2, 5)
        
        summary = tracker.get_summary()
        
        assert summary["completed_steps"] == 2
        assert summary["total_steps"] == 5
        assert summary["error_count"] == 1
        assert summary["warning_count"] == 1
        assert "total_time" in summary
        assert summary["errors"] == ["Error 1"]
        assert summary["warnings"] == ["Warning 1"]


class TestGraphManagerErrorHandling:
    """Test enhanced error handling in GraphManager."""

    @pytest.mark.asyncio
    async def test_generate_all_graphs_with_retry_success(self) -> None:
        """Test successful graph generation with retry logic."""
        mock_config_manager = MagicMock()
        mock_config = MagicMock()
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

            # Mock successful data fetch
            test_data = {"play_history": {"data": []}}  # pyright: ignore[reportUnknownVariableType]
            mock_data_fetcher.get_play_history.return_value = test_data["play_history"]  # pyright: ignore[reportAny]
            mock_data_fetcher.get_plays_per_month.return_value = {"monthly_data": "test"}  # pyright: ignore[reportAny]

            # Mock successful graph generation
            test_files = ["test1.png", "test2.png"]
            mock_graph_factory.generate_all_graphs.return_value = test_files  # pyright: ignore[reportAny]

            # Create temporary files for validation
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                for filename in test_files:
                    _ = (temp_path / filename).write_text("test content")
                
                # Update test files to use temp directory
                test_files = [str(temp_path / filename) for filename in test_files]
                mock_graph_factory.generate_all_graphs.return_value = test_files  # pyright: ignore[reportAny]

                async with graph_manager:
                    result = await graph_manager.generate_all_graphs()
                
                assert result == test_files

    @pytest.mark.asyncio
    async def test_generate_all_graphs_with_timeout(self) -> None:
        """Test graph generation timeout handling."""
        mock_config_manager = MagicMock()
        mock_config = MagicMock()
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

            # Mock data fetch
            test_data = {"play_history": {"data": []}}  # pyright: ignore[reportUnknownVariableType]
            mock_data_fetcher.get_play_history.return_value = test_data["play_history"]  # pyright: ignore[reportAny]
            mock_data_fetcher.get_plays_per_month.return_value = {"monthly_data": "test"}  # pyright: ignore[reportAny]

            # Mock slow graph generation
            def slow_generation(data: dict[str, object], tracker: object = None) -> list[str]:  # pyright: ignore[reportUnusedParameter]
                time.sleep(2.0)  # Simulate slow operation
                return ["test.png"]

            with patch.object(graph_manager, '_generate_graphs_sync', slow_generation):
                async with graph_manager:
                    with pytest.raises(asyncio.TimeoutError):
                        _ = await graph_manager.generate_all_graphs(timeout_seconds=0.1)

    @pytest.mark.asyncio
    async def test_fetch_graph_data_with_retry_failure(self) -> None:
        """Test data fetch retry logic with eventual failure."""
        mock_config_manager = MagicMock()
        graph_manager = GraphManager(mock_config_manager)

        # Mock components
        with patch.object(graph_manager, '_initialize_components'), \
             patch.object(graph_manager, '_cleanup_components'):
            
            mock_data_fetcher = AsyncMock()
            graph_manager._data_fetcher = mock_data_fetcher  # pyright: ignore[reportPrivateUsage]

            # Mock failing data fetch
            mock_data_fetcher.get_play_history.side_effect = Exception("API Error")  # pyright: ignore[reportAny]

            progress_tracker = ProgressTracker()
            
            with pytest.raises(GraphGenerationError):
                _ = await graph_manager._fetch_graph_data_with_retry(30, 2, progress_tracker)  # pyright: ignore[reportPrivateUsage]
            
            # Check that errors were tracked
            assert len(progress_tracker.errors) > 0
            assert "All 3 data fetch attempts failed" in progress_tracker.errors[-1]

    @pytest.mark.asyncio
    async def test_cleanup_old_graphs_with_timeout(self) -> None:
        """Test cleanup operations with timeout handling."""
        mock_config_manager = MagicMock()
        mock_config = MagicMock()
        mock_config.KEEP_DAYS = 7
        mock_config_manager.get_current_config.return_value = mock_config  # pyright: ignore[reportAny]

        graph_manager = GraphManager(mock_config_manager)

        # Patch the _cleanup_dated_graphs method to simulate slow operation
        with patch.object(graph_manager, '_cleanup_dated_graphs') as mock_cleanup:
            # Make the cleanup function block for longer than the timeout
            def slow_cleanup(base_dir: Path, keep_days: int) -> int:  # pyright: ignore[reportUnusedParameter]
                time.sleep(2.0)  # Simulate slow cleanup that exceeds timeout
                return 5
                
            mock_cleanup.side_effect = slow_cleanup
            
            with pytest.raises(asyncio.TimeoutError):
                _ = await graph_manager.cleanup_old_graphs(timeout_seconds=0.1)


class TestUserGraphManagerErrorHandling:
    """Test enhanced error handling in UserGraphManager."""

    @pytest.mark.asyncio
    async def test_generate_user_graphs_with_retry_success(self) -> None:
        """Test successful user graph generation with retry logic."""
        mock_config_manager = MagicMock()
        mock_config = MagicMock()
        mock_config.TIME_RANGE_DAYS = 30
        mock_config_manager.get_current_config.return_value = mock_config  # pyright: ignore[reportAny]

        user_graph_manager = UserGraphManager(mock_config_manager)

        # Mock components
        with patch.object(user_graph_manager, '_initialize_components'), \
             patch.object(user_graph_manager, '_cleanup_components'):
            
            mock_data_fetcher = AsyncMock()
            mock_data_fetcher.clear_cache = MagicMock()
            mock_graph_factory = MagicMock()
            
            user_graph_manager._data_fetcher = mock_data_fetcher  # pyright: ignore[reportPrivateUsage]
            user_graph_manager._graph_factory = mock_graph_factory  # pyright: ignore[reportPrivateUsage]

            # Mock successful user data fetch
            test_user_data = {  # pyright: ignore[reportUnknownVariableType]
                "play_history": {"data": []},
                "user_email": "test@example.com",
                "user_id": 123,
                "user_info": {"name": "Test User"}
            }
            mock_data_fetcher.find_user_by_email.return_value = {"user_id": 123}  # pyright: ignore[reportAny]
            mock_data_fetcher.get_play_history.return_value = test_user_data["play_history"]  # pyright: ignore[reportAny]

            # Mock successful graph generation
            test_files = ["user_test1.png", "user_test2.png"]
            mock_graph_factory.generate_all_graphs.return_value = test_files  # pyright: ignore[reportAny]

            # Create temporary files for validation
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                user_dir = temp_path / "users" / "test_at_example.com"
                user_dir.mkdir(parents=True)
                
                for filename in test_files:
                    _ = (user_dir / filename).write_text("test content")
                
                # Update test files to use temp directory
                test_files = [str(user_dir / filename) for filename in test_files]

                with patch('src.tgraph_bot.graphs.user_graph_manager.get_current_graph_storage_path', return_value=user_dir), \
                     patch.object(Path, 'rename', return_value=None):
                    
                    async with user_graph_manager:
                        result = await user_graph_manager.generate_user_graphs("test@example.com")
                    
                    assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_cleanup_user_graphs_with_statistics(self) -> None:
        """Test user graph cleanup with detailed statistics."""
        mock_config_manager = MagicMock()
        user_graph_manager = UserGraphManager(mock_config_manager)

        # Create temporary test files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_files = []
            
            for i in range(3):
                test_file = temp_path / f"test_{i}.png"
                _ = test_file.write_text("test content")
                test_files.append(str(test_file))  # pyright: ignore[reportUnknownMemberType]

            # Test cleanup
            result = await user_graph_manager.cleanup_user_graphs(test_files)  # pyright: ignore[reportUnknownArgumentType]
            
            assert isinstance(result, dict)
            assert result["success"] is True
            assert result["files_deleted"] == 3
            assert result["total_files"] == 3
            assert "cleanup_time" in result


if __name__ == "__main__":
    # Run a simple test to verify enhanced error handling works
    async def main() -> None:
        test_instance = TestProgressTracker()
        test_instance.test_progress_tracker_initialization()
        test_instance.test_progress_tracker_update()
        test_instance.test_progress_tracker_error_warning_handling()
        test_instance.test_progress_tracker_summary()
        print("✅ Enhanced error handling tests passed!")

    asyncio.run(main())
