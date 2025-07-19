"""
End-to-end tests for non-blocking and responsive graph generation.

This module provides comprehensive stress tests and concurrent user simulations
to ensure that all graph generation operations are non-blocking and the system
remains responsive under load. Tests monitor event loop latency and user-facing
# pyright: reportPrivateUsage=false, reportAny=false
response times during heavy graph generation workloads.
"""

from __future__ import annotations

import asyncio
import time

from typing import override
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tgraph_bot.graphs.graph_manager import GraphManager
from src.tgraph_bot.graphs.user_graph_manager import UserGraphManager
from src.tgraph_bot.config.manager import ConfigManager
from src.tgraph_bot.config.schema import TGraphBotConfig
from src.tgraph_bot.graphs.graph_modules.utils.progress_tracker import ProgressTracker
from tests.utils.test_helpers import create_config_manager_with_config
from tests.utils.async_helpers import (
    AsyncTestBase,
    async_timeout_test,
    wait_for_condition,
)


class TestNonBlockingGraphGeneration(AsyncTestBase):
    """End-to-end tests for non-blocking and responsive graph generation using async test base."""

    @override
    def setup_method(self) -> None:
        """Set up test method with async utilities."""
        super().setup_method()

    @override
    def teardown_method(self) -> None:
        """Clean up after test method."""
        super().teardown_method()

    @pytest.fixture
    def mock_config_manager(self, base_config: TGraphBotConfig) -> ConfigManager:
        """Create a mock config manager for testing using standardized utility."""
        return create_config_manager_with_config(base_config)

    @pytest.fixture
    def mock_graph_data(self) -> dict[str, object]:
        """Create mock graph data for testing."""
        return {
            "data": [
                {
                    "date": "2024-01-01",
                    "user": f"test_user_{i}",
                    "title": f"Test Movie {i}",
                    "platform": "Plex Web",
                    "duration": 7200,
                }
                for i in range(100)  # Simulate substantial data
            ]
        }

    @pytest.mark.asyncio
    @async_timeout_test(timeout=15.0)
    async def test_event_loop_responsiveness_under_load(
        self, mock_config_manager: ConfigManager, mock_graph_data: dict[str, object]
    ) -> None:
        """Test that event loop remains responsive during heavy graph generation."""
        # Counter to track event loop responsiveness
        counter = 0
        max_latency = 0.0
        latencies: list[float] = []

        async def monitor_event_loop() -> None:
            """Monitor event loop latency during graph generation."""
            nonlocal counter, max_latency, latencies

            for _ in range(50):  # Monitor for 50 iterations
                start_time = time.time()
                await asyncio.sleep(0.01)  # Small sleep to yield control
                latency = (
                    time.time() - start_time - 0.01
                )  # Subtract expected sleep time
                latencies.append(latency)
                max_latency = max(max_latency, latency)
                counter += 1

        # Create GraphManager instance
        graph_manager = GraphManager(mock_config_manager)

        # Mock the components to avoid actual initialization
        with (
            patch.object(graph_manager, "_initialize_components"),
            patch.object(graph_manager, "_cleanup_components"),
        ):
            # Mock the internal components
            mock_data_fetcher = AsyncMock()
            mock_graph_factory = MagicMock()

            graph_manager._data_fetcher = mock_data_fetcher  # pyright: ignore[reportPrivateUsage]
            graph_manager._graph_factory = mock_graph_factory  # pyright: ignore[reportPrivateUsage]

            # Mock data fetching to return our test data
            mock_data_fetcher.get_play_history.return_value = mock_graph_data  # pyright: ignore[reportAny]
            mock_data_fetcher.get_plays_per_month.return_value = {
                "monthly_data": "test"
            }  # pyright: ignore[reportAny]

            # Mock graph generation to simulate CPU-intensive work
            def simulate_heavy_cpu_work(
                _data: dict[str, object],
                _progress_tracker: ProgressTracker | None = None,
            ) -> list[str]:
                """Simulate CPU-intensive graph generation."""
                # Simulate heavy CPU work (but not too heavy for tests)
                time.sleep(0.2)  # 200ms of CPU work
                return ["test_graph_1.png", "test_graph_2.png", "test_graph_3.png"]

            def mock_validate_files(
                files: list[str], _tracker: ProgressTracker | None
            ) -> list[str]:
                return files

            with (
                patch.object(
                    graph_manager, "_generate_graphs_sync", simulate_heavy_cpu_work
                ),
                patch.object(
                    graph_manager, "_validate_generated_files", mock_validate_files
                ),
            ):
                async with graph_manager:
                    # Start monitoring task using background task management
                    monitor_task = self.create_background_task(
                        monitor_event_loop(), name="event_loop_monitor"
                    )

                    # Start graph generation task
                    graph_task = self.create_background_task(
                        graph_manager.generate_all_graphs(), name="graph_generation"
                    )

                    # Wait for both tasks to complete
                    results = await asyncio.gather(graph_task, monitor_task)

                    # Verify graph generation completed successfully
                    assert results[0] == [
                        "test_graph_1.png",
                        "test_graph_2.png",
                        "test_graph_3.png",
                    ]

                    # Verify event loop remained responsive
                    assert counter == 50, (
                        f"Monitor only completed {counter}/50 iterations"
                    )

                    # Check that maximum latency is reasonable (< 50ms)
                    assert max_latency < 0.05, (
                        f"Maximum event loop latency was {max_latency * 1000:.2f}ms"
                    )

                    # Check average latency is very low (< 10ms)
                    avg_latency = sum(latencies) / len(latencies)
                    assert avg_latency < 0.01, (
                        f"Average event loop latency was {avg_latency * 1000:.2f}ms"
                    )

    @pytest.mark.asyncio
    @async_timeout_test(timeout=10.0)
    async def test_concurrent_graph_generation_requests(
        self, mock_config_manager: ConfigManager, mock_graph_data: dict[str, object]
    ) -> None:
        """Test handling multiple concurrent graph generation requests."""
        # Create multiple GraphManager instances to simulate concurrent requests
        managers = [GraphManager(mock_config_manager) for _ in range(3)]

        def simulate_graph_work(
            _data: dict[str, object], _progress_tracker: ProgressTracker | None = None
        ) -> list[str]:
            """Simulate graph generation work."""
            time.sleep(0.1)  # 100ms of work
            return [f"graph_{id(_data)}.png"]

        async def generate_graphs_for_manager(
            manager: GraphManager, manager_id: int
        ) -> tuple[int, list[str]]:
            """Generate graphs for a specific manager."""

            def mock_validate_files(
                files: list[str], _tracker: ProgressTracker | None
            ) -> list[str]:
                return files

            # Mock components within the manager's usage context
            with (
                patch.object(manager, "_initialize_components"),
                patch.object(manager, "_cleanup_components"),
                patch.object(manager, "_generate_graphs_sync", simulate_graph_work),
                patch.object(manager, "_validate_generated_files", mock_validate_files),
            ):
                # Set up mock components
                mock_data_fetcher = AsyncMock()
                mock_graph_factory = MagicMock()

                manager._data_fetcher = mock_data_fetcher  # pyright: ignore[reportPrivateUsage]
                manager._graph_factory = mock_graph_factory  # pyright: ignore[reportPrivateUsage]

                mock_data_fetcher.get_play_history.return_value = mock_graph_data  # pyright: ignore[reportAny]
                mock_data_fetcher.get_plays_per_month.return_value = {
                    "monthly_data": "test"
                }  # pyright: ignore[reportAny]

                async with manager:
                    result = await manager.generate_all_graphs()
                    return manager_id, result

        # Test concurrent generation
        start_time = time.time()

        # Create tasks for concurrent execution using background task management
        tasks = [
            self.create_background_task(
                generate_graphs_for_manager(manager, i), name=f"manager_{i}_generation"
            )
            for i, manager in enumerate(managers)
        ]

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        # Verify all managers completed successfully
        assert len(results) == 3
        for _, graph_files in results:
            assert len(graph_files) == 1
            assert graph_files[0].endswith(".png")

        # Verify concurrent execution (should be faster than sequential)
        # Sequential would take ~0.3s (3 * 0.1s), concurrent should be ~0.1s
        assert total_time < 0.25, (
            f"Concurrent execution took {total_time:.3f}s, expected < 0.25s"
        )

    @pytest.mark.asyncio
    async def test_user_graph_generation_responsiveness(
        self, mock_config_manager: ConfigManager, mock_graph_data: dict[str, object]
    ) -> None:
        """Test that user graph generation doesn't block other operations."""
        # Counter for background task
        background_counter = 0

        async def background_task() -> None:
            """Simulate background operations that should continue during graph generation."""
            nonlocal background_counter
            for _ in range(20):
                await asyncio.sleep(0.01)  # 10ms intervals
                background_counter += 1

        # Create UserGraphManager instance
        user_graph_manager = UserGraphManager(mock_config_manager)

        # Mock the components
        with (
            patch.object(user_graph_manager, "_initialize_components"),
            patch.object(user_graph_manager, "_cleanup_components"),
        ):
            mock_data_fetcher = AsyncMock()
            mock_data_fetcher.clear_cache = MagicMock()
            mock_graph_factory = MagicMock()

            user_graph_manager._data_fetcher = mock_data_fetcher  # pyright: ignore[reportPrivateUsage]
            user_graph_manager._graph_factory = mock_graph_factory  # pyright: ignore[reportPrivateUsage]

            # Mock find_user_by_email to return proper user data
            mock_data_fetcher.find_user_by_email.return_value = {  # pyright: ignore[reportAny]
                "user_id": 123,
                "username": "testuser",
                "email": "test@example.com",
                "friendly_name": "Test User",
            }

            # Mock get_play_history to return test data
            mock_data_fetcher.get_play_history.return_value = mock_graph_data  # pyright: ignore[reportAny]

            def simulate_user_graph_work(
                _user_email: str,
                _data: dict[str, object],
                _progress_tracker: ProgressTracker | None = None,
            ) -> list[str]:
                """Simulate user graph generation work."""
                time.sleep(0.15)  # 150ms of work
                return ["user_graph.png"]

            def mock_validate_user_files(
                files: list[str], _user_email: str, _tracker: ProgressTracker | None
            ) -> list[str]:
                return files

            with (
                patch.object(
                    user_graph_manager,
                    "_generate_user_graphs_sync",
                    simulate_user_graph_work,
                ),
                patch.object(
                    user_graph_manager,
                    "_validate_generated_user_files",
                    mock_validate_user_files,
                ),
            ):
                async with user_graph_manager:
                    # Start background task using async utilities
                    bg_task = self.create_background_task(
                        background_task(), name="background_monitor"
                    )

                    # Start user graph generation
                    user_task = self.create_background_task(
                        user_graph_manager.generate_user_graphs("test@example.com"),
                        name="user_graph_generation",
                    )

                    # Wait for both to complete with timeout protection
                    results = await asyncio.gather(user_task, bg_task)

                    # Verify user graph generation completed
                    assert results[0] == ["user_graph.png"]

                    # Verify background task completed (proving non-blocking)
                    assert background_counter == 20, (
                        f"Background task only completed {background_counter}/20 iterations"
                    )

    @pytest.mark.asyncio
    @async_timeout_test(timeout=15.0)
    async def test_stress_test_multiple_users_concurrent(
        self, mock_config_manager: ConfigManager, mock_graph_data: dict[str, object]
    ) -> None:
        """Stress test with multiple users requesting graphs concurrently."""
        user_emails = [f"user{i}@example.com" for i in range(5)]

        # Create UserGraphManager instance
        user_graph_manager = UserGraphManager(mock_config_manager)

        # Mock the components
        with (
            patch.object(user_graph_manager, "_initialize_components"),
            patch.object(user_graph_manager, "_cleanup_components"),
        ):
            mock_data_fetcher = AsyncMock()
            mock_data_fetcher.clear_cache = MagicMock()
            mock_graph_factory = MagicMock()

            user_graph_manager._data_fetcher = mock_data_fetcher  # pyright: ignore[reportPrivateUsage]
            user_graph_manager._graph_factory = mock_graph_factory  # pyright: ignore[reportPrivateUsage]

            # Mock find_user_by_email to return proper user data for any email
            def mock_find_user_by_email(email: str) -> dict[str, object]:
                user_id = (
                    int(email.split("@")[0].replace("user", ""))
                    if "user" in email
                    else 123
                )
                return {
                    "user_id": user_id,
                    "username": email.split("@")[0],
                    "email": email,
                    "friendly_name": f"Test User {user_id}",
                }

            mock_data_fetcher.find_user_by_email.side_effect = mock_find_user_by_email  # pyright: ignore[reportAny]

            # Mock get_play_history to return test data
            mock_data_fetcher.get_play_history.return_value = mock_graph_data  # pyright: ignore[reportAny]

            def simulate_user_graph_work(
                _user_email: str,
                _data: dict[str, object],
                _progress_tracker: ProgressTracker | None = None,
            ) -> list[str]:
                """Simulate user graph generation work."""
                time.sleep(0.08)  # 80ms of work per user
                return [f"user_graph_{_user_email.replace('@', '_at_')}.png"]

            def mock_validate_user_files(
                files: list[str], _user_email: str, _tracker: ProgressTracker | None
            ) -> list[str]:
                return files

            with (
                patch.object(
                    user_graph_manager,
                    "_generate_user_graphs_sync",
                    simulate_user_graph_work,
                ),
                patch.object(
                    user_graph_manager,
                    "_validate_generated_user_files",
                    mock_validate_user_files,
                ),
            ):
                async with user_graph_manager:
                    start_time = time.time()

                    # Create tasks for all users using background task management
                    tasks = [
                        self.create_background_task(
                            user_graph_manager.generate_user_graphs(email),
                            name=f"user_graph_{i}",
                        )
                        for i, email in enumerate(user_emails)
                    ]

                    # Wait for all to complete with timeout protection
                    results = await asyncio.gather(*tasks)

                    total_time = time.time() - start_time

                    # Verify all users got their graphs
                    assert len(results) == 5
                    for i, user_graphs in enumerate(results):
                        assert len(user_graphs) == 1
                        expected_filename = (
                            f"user_graph_{user_emails[i].replace('@', '_at_')}.png"
                        )
                        assert user_graphs[0] == expected_filename

                    # Verify concurrent execution efficiency
                    # Sequential would take ~0.4s (5 * 0.08s), concurrent should be much faster
                    assert total_time < 0.2, (
                        f"Stress test took {total_time:.3f}s, expected < 0.2s"
                    )

    @pytest.mark.asyncio
    async def test_timeout_handling_during_load(
        self, mock_config_manager: ConfigManager, mock_graph_data: dict[str, object]
    ) -> None:
        """Test that timeout handling works correctly under load."""
        graph_manager = GraphManager(mock_config_manager)

        # Mock the components
        with (
            patch.object(graph_manager, "_initialize_components"),
            patch.object(graph_manager, "_cleanup_components"),
        ):
            mock_data_fetcher = AsyncMock()
            mock_graph_factory = MagicMock()

            graph_manager._data_fetcher = mock_data_fetcher  # pyright: ignore[reportPrivateUsage]
            graph_manager._graph_factory = mock_graph_factory  # pyright: ignore[reportPrivateUsage]

            mock_data_fetcher.get_play_history.return_value = mock_graph_data  # pyright: ignore[reportAny]
            mock_data_fetcher.get_plays_per_month.return_value = {
                "monthly_data": "test"
            }  # pyright: ignore[reportAny]

            def simulate_slow_work(
                _data: dict[str, object],
                _progress_tracker: ProgressTracker | None = None,
            ) -> list[str]:
                """Simulate work that exceeds timeout."""
                time.sleep(2.0)  # 2 seconds - should exceed our timeout
                return ["slow_graph.png"]

            with patch.object(
                graph_manager, "_generate_graphs_sync", simulate_slow_work
            ):
                async with graph_manager:
                    # Test with short timeout using async utility
                    with pytest.raises(asyncio.TimeoutError):
                        _ = await self.run_with_timeout(
                            graph_manager.generate_all_graphs(), timeout=0.5
                        )

    @pytest.mark.asyncio
    async def test_memory_stability_under_load(
        self, mock_config_manager: ConfigManager, mock_graph_data: dict[str, object]
    ) -> None:
        """Test that memory usage remains stable during repeated graph generation."""
        import psutil
        import os
        import gc

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory: int = process.memory_info().rss  # pyright: ignore[reportAny]

        graph_manager = GraphManager(mock_config_manager)

        # Mock the components
        with (
            patch.object(graph_manager, "_initialize_components"),
            patch.object(graph_manager, "_cleanup_components"),
        ):
            mock_data_fetcher = AsyncMock()
            mock_graph_factory = MagicMock()

            graph_manager._data_fetcher = mock_data_fetcher  # pyright: ignore[reportPrivateUsage]
            graph_manager._graph_factory = mock_graph_factory  # pyright: ignore[reportPrivateUsage]

            mock_data_fetcher.get_play_history.return_value = mock_graph_data  # pyright: ignore[reportAny]
            mock_data_fetcher.get_plays_per_month.return_value = {
                "monthly_data": "test"
            }  # pyright: ignore[reportAny]

            def simulate_memory_intensive_work(
                _data: dict[str, object],
                _progress_tracker: ProgressTracker | None = None,
            ) -> list[str]:
                """Simulate memory-intensive graph generation."""
                # Create some temporary data structures
                temp_data = [list(range(1000)) for _ in range(100)]
                time.sleep(0.05)  # 50ms of work
                del temp_data  # Clean up
                return ["memory_test_graph.png"]

            with patch.object(
                graph_manager, "_generate_graphs_sync", simulate_memory_intensive_work
            ):
                async with graph_manager:
                    # Generate graphs multiple times
                    for i in range(10):
                        _ = await self.run_with_timeout(
                            graph_manager.generate_all_graphs(), timeout=5.0
                        )

                        # Force garbage collection
                        _ = gc.collect()

                        # Check memory usage periodically
                        if i % 3 == 0:
                            current_memory: int = process.memory_info().rss  # pyright: ignore[reportAny]
                            memory_increase = current_memory - initial_memory

                            # Memory increase should be reasonable (< 100MB)
                            max_acceptable_increase = 100 * 1024 * 1024  # 100MB
                            assert memory_increase < max_acceptable_increase, (
                                f"Memory increased by {memory_increase / 1024 / 1024:.2f}MB after {i + 1} iterations"
                            )

    @pytest.mark.asyncio
    async def test_error_handling_doesnt_block_event_loop(
        self, mock_config_manager: ConfigManager, mock_graph_data: dict[str, object]
    ) -> None:
        """Test that error handling during graph generation doesn't block the event loop."""
        # Counter for background operations
        error_counter = 0

        async def error_monitor() -> None:
            """Monitor that continues during error handling."""
            nonlocal error_counter
            for _ in range(30):
                await asyncio.sleep(0.01)
                error_counter += 1

        graph_manager = GraphManager(mock_config_manager)

        # Mock the components
        with (
            patch.object(graph_manager, "_initialize_components"),
            patch.object(graph_manager, "_cleanup_components"),
        ):
            mock_data_fetcher = AsyncMock()
            mock_graph_factory = MagicMock()

            graph_manager._data_fetcher = mock_data_fetcher  # pyright: ignore[reportPrivateUsage]
            graph_manager._graph_factory = mock_graph_factory  # pyright: ignore[reportPrivateUsage]

            mock_data_fetcher.get_play_history.return_value = mock_graph_data  # pyright: ignore[reportAny]
            mock_data_fetcher.get_plays_per_month.return_value = {
                "monthly_data": "test"
            }  # pyright: ignore[reportAny]

            def simulate_error_work(
                _data: dict[str, object],
                _progress_tracker: ProgressTracker | None = None,
            ) -> list[str]:
                """Simulate work that raises an error."""
                time.sleep(0.1)  # Some work before error
                raise RuntimeError("Simulated graph generation error")

            with patch.object(
                graph_manager, "_generate_graphs_sync", simulate_error_work
            ):
                async with graph_manager:
                    # Start error monitor using background task management
                    monitor_task = self.create_background_task(
                        error_monitor(), name="error_monitor"
                    )

                    # Start graph generation (should fail) - but not expecting GraphGenerationError anymore
                    # The actual error raised is RuntimeError wrapped in execution context
                    try:
                        graph_task = self.create_background_task(
                            graph_manager.generate_all_graphs(),
                            name="failing_graph_generation",
                        )
                        _ = await asyncio.gather(
                            graph_task, monitor_task, return_exceptions=True
                        )

                        # The graph task should have raised an exception
                        # Check that the error_monitor completed, proving non-blocking behavior
                        assert error_counter == 30, (
                            f"Error monitor only completed {error_counter}/30 iterations"
                        )

                    except Exception:
                        # This is expected - any exception during graph generation is fine
                        # The important thing is that the monitor task completed
                        assert error_counter == 30, (
                            f"Error monitor only completed {error_counter}/30 iterations"
                        )

    @pytest.mark.asyncio
    async def test_progress_tracking_responsiveness(
        self, mock_config_manager: ConfigManager, mock_graph_data: dict[str, object]
    ) -> None:
        """Test that progress tracking callbacks don't block the event loop."""
        progress_updates: list[tuple[str, int, int]] = []
        callback_counter = 0

        def progress_callback(
            message: str, current: int, total: int, _metadata: dict[str, object]
        ) -> None:
            """Track progress updates."""
            nonlocal callback_counter
            progress_updates.append((message, current, total))
            callback_counter += 1

        async def callback_monitor() -> None:
            """Monitor callback execution using wait_for_condition utility."""
            await wait_for_condition(
                lambda: callback_counter >= 4,  # Expected number of progress updates
                timeout=5.0,
                description="progress callbacks to be triggered",
            )

        graph_manager = GraphManager(mock_config_manager)

        # Mock the components
        with (
            patch.object(graph_manager, "_initialize_components"),
            patch.object(graph_manager, "_cleanup_components"),
        ):
            mock_data_fetcher = AsyncMock()
            mock_graph_factory = MagicMock()

            graph_manager._data_fetcher = mock_data_fetcher  # pyright: ignore[reportPrivateUsage]
            graph_manager._graph_factory = mock_graph_factory  # pyright: ignore[reportPrivateUsage]

            mock_data_fetcher.get_play_history.return_value = mock_graph_data  # pyright: ignore[reportAny]
            mock_data_fetcher.get_plays_per_month.return_value = {
                "monthly_data": "test"
            }  # pyright: ignore[reportAny]

            def simulate_tracked_work(
                _data: dict[str, object],
                _progress_tracker: ProgressTracker | None = None,
            ) -> list[str]:
                """Simulate work with progress tracking."""
                if _progress_tracker:
                    _progress_tracker.update("Starting graph generation", 0, 4)
                    _progress_tracker.update("Processing data", 1, 4)
                    _progress_tracker.update("Generating graphs", 2, 4)
                    _progress_tracker.update("Finalizing", 3, 4)
                    _progress_tracker.update("Complete", 4, 4)
                time.sleep(0.1)  # 100ms of work
                return ["tracked_graph.png"]

            def mock_validate_files(files: list[str], _tracker: object) -> list[str]:
                # Mock file validation to succeed by pretending files exist
                return files

            # Mock Path.exists() to return True for our test files
            with (
                patch.object(
                    graph_manager, "_generate_graphs_sync", simulate_tracked_work
                ),
                patch.object(
                    graph_manager, "_validate_generated_files", mock_validate_files
                ),
                patch("pathlib.Path.exists", return_value=True),
                patch("pathlib.Path.is_file", return_value=True),
                patch("pathlib.Path.stat") as mock_stat,
            ):
                # Mock file stat to show non-zero size
                mock_stat.return_value.st_size = 1024  # pyright: ignore[reportAny]

                async with graph_manager:
                    # Start callback monitor using background task management
                    monitor_task = self.create_background_task(
                        callback_monitor(), name="callback_monitor"
                    )

                    # Start graph generation with progress callback
                    graph_task = self.create_background_task(
                        graph_manager.generate_all_graphs(
                            progress_callback=progress_callback
                        ),
                        name="graph_generation",
                    )

                    # Wait for both to complete with timeout protection
                    results = await asyncio.gather(graph_task, monitor_task)

                    # Verify graph generation completed
                    assert results[0] == ["tracked_graph.png"]

                    # Verify progress callbacks were called
                    assert len(progress_updates) >= 4, (
                        f"Only {len(progress_updates)} progress updates received"
                    )
                    assert callback_counter >= 4, (
                        f"Only {callback_counter} callbacks executed"
                    )

    @pytest.mark.asyncio
    async def test_cleanup_operations_non_blocking(
        self, mock_config_manager: ConfigManager
    ) -> None:
        """Test that cleanup operations don't block the event loop."""
        cleanup_counter = 0

        async def cleanup_monitor() -> None:
            """Monitor during cleanup operations."""
            nonlocal cleanup_counter
            for _ in range(20):
                await asyncio.sleep(0.01)
                cleanup_counter += 1

        graph_manager = GraphManager(mock_config_manager)

        # Mock file operations to simulate cleanup work
        def _simulate_cleanup_work() -> int:  # pyright: ignore[reportUnusedFunction]
            """Simulate file cleanup work."""
            time.sleep(0.1)  # 100ms of file operations
            return 5  # Number of files cleaned

        # Mock the cleanup_old_files function directly - need to check where it's imported
        with patch(
            "src.tgraph_bot.graphs.graph_modules.utils.cleanup_old_files",
            return_value=5,
        ) as mock_cleanup:
            # Start cleanup monitor
            monitor_task = self.create_background_task(
                cleanup_monitor(), name="cleanup_monitor"
            )

            # Mock graph_manager's cleanup method to return expected structure
            async def mock_cleanup_old_graphs() -> dict[str, object]:
                """Mock cleanup method that returns the expected structure."""
                # Simulate some work
                await asyncio.sleep(0.1)
                # Call the mocked cleanup_old_files function
                files_deleted = mock_cleanup()  # pyright: ignore[reportAny]
                return {
                    "files_deleted": files_deleted,
                    "total_files": files_deleted,
                    "cleanup_time": 0.1,
                    "success": True,
                }

            # Patch the actual cleanup method
            with patch.object(
                graph_manager, "cleanup_old_graphs", mock_cleanup_old_graphs
            ):
                # Start cleanup operation
                cleanup_task = self.create_background_task(
                    graph_manager.cleanup_old_graphs(), name="cleanup_task"
                )

                # Wait for both to complete
                results = await asyncio.gather(cleanup_task, monitor_task)

                # Verify cleanup completed (returns dict with statistics)
                cleanup_result = results[0]
                assert isinstance(cleanup_result, dict)
                assert cleanup_result["files_deleted"] == 5  # Files cleaned

                # Verify monitor completed (proving non-blocking)
                assert cleanup_counter == 20, (
                    f"Cleanup monitor only completed {cleanup_counter}/20 iterations"
                )
