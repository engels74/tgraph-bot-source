"""
Tests for memory management and resource cleanup in TGraph Bot graphs.

This module tests that matplotlib figures are properly cleaned up
and that repeated graph generation doesn't cause memory leaks.
"""

import gc
import tempfile
from pathlib import Path
from typing import override
from collections.abc import Mapping
from unittest.mock import MagicMock, patch
import psutil
import os

import pytest
import matplotlib.pyplot as plt

from graphs.graph_modules.base_graph import BaseGraph
from graphs.graph_modules.graph_factory import GraphFactory
from config.schema import TGraphBotConfig


def create_test_config() -> TGraphBotConfig:
    """Create a minimal test configuration."""
    return TGraphBotConfig(
        TAUTULLI_API_KEY="test_key",
        TAUTULLI_URL="http://test.local",
        DISCORD_TOKEN="test_token",
        CHANNEL_ID=123456789,
        ENABLE_DAILY_PLAY_COUNT=True,
        ENABLE_TOP_10_USERS=False,
        ENABLE_TOP_10_PLATFORMS=False,
        ENABLE_PLAY_COUNT_BY_DAYOFWEEK=False,
        ENABLE_PLAY_COUNT_BY_HOUROFDAY=False,
        ENABLE_PLAY_COUNT_BY_MONTH=False,
    )


class MemoryTestGraph(BaseGraph):
    """Simple test graph for memory testing."""

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """Generate a simple test graph."""
        try:
            _ = self.setup_figure()
            if self.axes is not None:
                _ = self.axes.plot([1, 2, 3], [1, 4, 2])  # pyright: ignore[reportUnknownMemberType]
                _ = self.axes.set_title(self.get_title())  # pyright: ignore[reportUnknownMemberType]

            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                output_path = tmp.name

            return self.save_figure(output_path=output_path)
        finally:
            # Always cleanup matplotlib resources
            self.cleanup()

    @override
    def get_title(self) -> str:
        """Get the title for this test graph."""
        return "Memory Test Graph"


class TestMemoryManagement:
    """Test cases for memory management and resource cleanup."""
    
    def test_single_graph_cleanup(self) -> None:
        """Test that a single graph properly cleans up its resources."""
        graph = MemoryTestGraph()

        # Generate graph
        with tempfile.TemporaryDirectory():
            output_path = graph.generate({"test": "data"})

            # Verify file was created
            assert Path(output_path).exists()

            # Verify cleanup occurred (figure should be None after generate)
            assert graph.figure is None
            assert graph.axes is None

            # Clean up test file
            Path(output_path).unlink(missing_ok=True)
    
    def test_context_manager_cleanup(self) -> None:
        """Test that context manager properly cleans up resources."""
        with MemoryTestGraph() as graph:
            _ = graph.setup_figure()
            assert graph.figure is not None
            assert graph.axes is not None
        
        # After context exit, resources should be cleaned up
        assert graph.figure is None
        assert graph.axes is None
    
    def test_multiple_graphs_sequential_cleanup(self) -> None:
        """Test that multiple graphs generated sequentially clean up properly."""
        initial_figures = len(plt.get_fignums())
        
        for i in range(5):
            graph = MemoryTestGraph()
            with tempfile.TemporaryDirectory():
                output_path = graph.generate({"test": f"data_{i}"})

                # Verify file was created
                assert Path(output_path).exists()

                # Clean up test file
                Path(output_path).unlink(missing_ok=True)
        
        # Verify no figures remain open
        final_figures = len(plt.get_fignums())
        assert final_figures == initial_figures
    
    def test_exception_during_generation_still_cleans_up(self) -> None:
        """Test that cleanup occurs even when graph generation fails."""
        
        class FailingGraph(BaseGraph):
            @override
            def generate(self, data: Mapping[str, object]) -> str:
                try:
                    _ = self.setup_figure()
                    # Simulate an error during generation
                    raise ValueError("Simulated error")
                finally:
                    # Ensure cleanup happens even on error
                    self.cleanup()

            @override
            def get_title(self) -> str:
                return "Failing Graph"
        
        graph = FailingGraph()
        
        with pytest.raises(ValueError, match="Simulated error"):
            _ = graph.generate({"test": "data"})
        
        # Even after exception, cleanup should have occurred
        assert graph.figure is None
        assert graph.axes is None
    
    def test_cleanup_all_figures_method(self) -> None:
        """Test the cleanup_all_figures class method."""
        # Create some figures manually
        _ = plt.figure()  # pyright: ignore[reportUnknownMemberType]
        _ = plt.figure()  # pyright: ignore[reportUnknownMemberType]
        _ = plt.figure()  # pyright: ignore[reportUnknownMemberType]
        
        initial_count = len(plt.get_fignums())
        assert initial_count >= 3
        
        # Call cleanup_all_figures
        BaseGraph.cleanup_all_figures()
        
        # All figures should be closed
        final_count = len(plt.get_fignums())
        assert final_count == 0
    
    @patch('matplotlib.pyplot.close')
    def test_cleanup_handles_close_errors_gracefully(self, mock_close: MagicMock) -> None:
        """Test that cleanup handles matplotlib close errors gracefully."""
        # Make plt.close raise an exception
        mock_close.side_effect = RuntimeError("Mock close error")
        
        graph = MemoryTestGraph()
        _ = graph.setup_figure()
        
        # Cleanup should not raise an exception even if close fails
        graph.cleanup()
        
        # References should still be cleared
        assert graph.figure is None
        assert graph.axes is None
    
    def test_graph_factory_bulk_generation_cleanup(self) -> None:
        """Test that GraphFactory properly cleans up when generating multiple graphs."""
        # Create a minimal config for testing
        config = create_test_config()
        
        factory = GraphFactory(config)
        
        # Mock data for graph generation
        mock_data: dict[str, object] = {
            "data": [
                {"date": "2024-01-01", "user": "test_user", "title": "Test Movie"}
            ]
        }
        
        initial_figures = len(plt.get_fignums())
        
        # Generate all graphs
        with patch.object(factory, 'create_enabled_graphs') as mock_create:
            # Return a list with our test graph
            mock_create.return_value = [MemoryTestGraph()]
            
            generated_paths = factory.generate_all_graphs(mock_data)
            
            # Verify graphs were generated
            assert len(generated_paths) == 1
            
            # Clean up generated files
            for path in generated_paths:
                Path(path).unlink(missing_ok=True)
        
        # Verify no figures remain open (should be 0 or equal to initial)
        final_figures = len(plt.get_fignums())
        assert final_figures <= initial_figures
    
    def test_memory_usage_stability(self) -> None:
        """Test that repeated graph generation doesn't continuously increase memory."""
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Generate multiple graphs
        for i in range(10):
            graph = MemoryTestGraph()
            with tempfile.TemporaryDirectory():
                output_path = graph.generate({"test": f"data_{i}"})
                Path(output_path).unlink(missing_ok=True)
            
            # Force garbage collection
            _ = gc.collect()
        
        # Get final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (less than 50MB)
        # This is a reasonable threshold for matplotlib overhead
        max_acceptable_increase = 50 * 1024 * 1024  # 50MB in bytes
        assert memory_increase < max_acceptable_increase, \
            f"Memory increased by {memory_increase / 1024 / 1024:.2f}MB, which exceeds the 50MB threshold"
    
    def test_cleanup_all_graph_resources_method(self) -> None:
        """Test the GraphFactory cleanup_all_graph_resources method."""
        config = create_test_config()
        factory = GraphFactory(config)
        
        # Create some figures
        _ = plt.figure()  # pyright: ignore[reportUnknownMemberType]
        _ = plt.figure()  # pyright: ignore[reportUnknownMemberType]
        
        initial_count = len(plt.get_fignums())
        assert initial_count >= 2
        
        # Call cleanup method
        factory.cleanup_all_graph_resources()
        
        # All figures should be closed
        final_count = len(plt.get_fignums())
        assert final_count == 0
