"""
Test module for performance regression testing.

This module provides comprehensive performance testing to ensure that
refactoring changes don't introduce performance regressions in graph
generation, memory usage, or other critical operations.

The tests validate:
- Graph generation performance benchmarks
- Memory usage patterns and leak detection
- Resource cleanup efficiency
- Configuration access performance
- Factory creation performance
- Concurrent operation performance
"""

from __future__ import annotations

import gc
import tempfile
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, override
from unittest.mock import MagicMock, patch

import psutil

from src.tgraph_bot.graphs.graph_modules.base_graph import BaseGraph
from src.tgraph_bot.graphs.graph_modules.config_accessor import ConfigAccessor
from src.tgraph_bot.graphs.graph_modules.graph_factory import GraphFactory
from tests.utils.graph_helpers import (
    create_test_config_comprehensive,
    create_test_config_minimal,
    matplotlib_cleanup,
    memory_monitoring,
    validate_no_memory_leaks,
)

if TYPE_CHECKING:
    from src.tgraph_bot.config.schema import TGraphBotConfig


class PerformanceTestGraph(BaseGraph):
    """Test graph optimized for performance testing."""
    
    def __init__(
        self,
        *,
        config: TGraphBotConfig | None = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str = "#ffffff",
        complexity_level: int = 1,
    ) -> None:
        """Initialize with configurable complexity for performance testing."""
        super().__init__(
            config=config,
            width=width,
            height=height,
            dpi=dpi,
            background_color=background_color,
        )
        self._complexity_level: int = complexity_level
    
    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """Generate a test graph with configurable complexity."""
        try:
            _ = self.setup_figure()
            
            if self.axes is not None:
                # Create plot with variable complexity
                for i in range(self._complexity_level):
                    x_data = list(range(100 * (i + 1)))
                    y_data = [j * (i + 1) for j in x_data]
                    _ = self.axes.plot(x_data, y_data, label=f"Series {i+1}")  # pyright: ignore[reportUnknownMemberType]
                
                _ = self.axes.set_title(self.get_title())  # pyright: ignore[reportUnknownMemberType]
                if self._complexity_level > 1:
                    _ = self.axes.legend()  # pyright: ignore[reportUnknownMemberType]
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                output_path = tmp.name
            
            return self.save_figure(output_path=output_path)
        finally:
            self.cleanup()
    
    @override
    def get_title(self) -> str:
        """Get the title for this performance test graph."""
        return f"Performance Test Graph (Complexity: {self._complexity_level})"


class TestPerformanceRegression:
    """Test cases for performance regression detection."""
    
    def test_basic_graph_generation_performance(self) -> None:
        """Test basic graph generation performance benchmarks."""
        with matplotlib_cleanup():
            graph = PerformanceTestGraph()
            test_data: dict[str, object] = {"test_key": "test_value"}
            
            # Measure generation time
            start_time = time.time()
            output_path = graph.generate(test_data)
            generation_time = time.time() - start_time
            
            # Basic graph generation should complete in under 2 seconds
            assert generation_time < 2.0, f"Graph generation took {generation_time:.2f}s, expected < 2.0s"
            
            # Verify output was created
            assert Path(output_path).exists()
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)
    
    def test_complex_graph_generation_performance(self) -> None:
        """Test performance with more complex graphs."""
        with matplotlib_cleanup():
            complex_graph = PerformanceTestGraph(complexity_level=5)
            test_data: dict[str, object] = {"test_key": "test_value"}
            
            # Measure generation time for complex graph
            start_time = time.time()
            output_path = complex_graph.generate(test_data)
            generation_time = time.time() - start_time
            
            # Complex graph should still complete in reasonable time (under 5 seconds)
            assert generation_time < 5.0, f"Complex graph generation took {generation_time:.2f}s, expected < 5.0s"
            
            # Verify output was created
            assert Path(output_path).exists()
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)
    
    def test_figure_setup_performance(self) -> None:
        """Test figure setup and cleanup performance."""
        with matplotlib_cleanup():
            graph = PerformanceTestGraph()
            
            # Measure setup time
            start_time = time.time()
            _ = graph.setup_figure()
            setup_time = time.time() - start_time
            
            # Setup should be very fast (under 0.5 seconds)
            assert setup_time < 0.5, f"Figure setup took {setup_time:.2f}s, expected < 0.5s"
            
            # Measure cleanup time
            start_time = time.time()
            graph.cleanup()
            cleanup_time = time.time() - start_time
            
            # Cleanup should be even faster (under 0.1 seconds)
            assert cleanup_time < 0.1, f"Figure cleanup took {cleanup_time:.2f}s, expected < 0.1s"
    
    def test_memory_usage_during_generation(self) -> None:
        """Test memory usage patterns during graph generation."""
        def generate_graph() -> None:
            with matplotlib_cleanup():
                graph = PerformanceTestGraph()
                test_data: dict[str, object] = {"test_key": "test_value"}
                output_path = graph.generate(test_data)
                Path(output_path).unlink(missing_ok=True)
        
        with memory_monitoring() as memory_info:
            generate_graph()
        
        # Memory usage should be reasonable (under 50MB for basic graph)
        memory_used = memory_info['memory_used_mb']
        assert memory_used < 50.0, f"Graph generation used {memory_used:.2f}MB, expected < 50MB"
    
    def test_memory_leak_detection(self) -> None:
        """Test for memory leaks in repeated graph generation."""
        def generate_multiple_graphs() -> None:
            with matplotlib_cleanup():
                graph = PerformanceTestGraph()
                test_data: dict[str, object] = {"test_key": "test_value"}
                output_path = graph.generate(test_data)
                Path(output_path).unlink(missing_ok=True)
        
        # Test that repeated operations don't cause significant memory leaks
        validate_no_memory_leaks(
            generate_multiple_graphs,
            max_memory_increase_mb=20.0,  # Allow up to 20MB increase over 5 iterations
            iterations=5,
        )
    
    def test_configuration_access_performance(self) -> None:
        """Test performance of configuration access operations."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)
        
        # Measure configuration access time
        start_time = time.time()
        
        # Perform multiple configuration accesses
        for _ in range(1000):
            _ = accessor.get_value("TV_COLOR")
            _ = accessor.get_value("MOVIE_COLOR")
            _ = accessor.get_value("ENABLE_DAILY_PLAY_COUNT")
        
        access_time = time.time() - start_time
        
        # 1000 configuration accesses should be very fast (under 0.1 seconds)
        assert access_time < 0.1, f"1000 config accesses took {access_time:.2f}s, expected < 0.1s"
    
    def test_graph_factory_creation_performance(self) -> None:
        """Test performance of GraphFactory creation and operations."""
        config = create_test_config_comprehensive()
        
        # Measure factory creation time
        start_time = time.time()
        factory = GraphFactory(config)
        creation_time = time.time() - start_time
        
        # Factory creation should be fast (under 0.1 seconds)
        assert creation_time < 0.1, f"Factory creation took {creation_time:.2f}s, expected < 0.1s"
        
        # Measure enabled graph types retrieval
        start_time = time.time()
        enabled_types = factory.get_enabled_graph_types()
        retrieval_time = time.time() - start_time
        
        # Graph types retrieval should be very fast (under 0.01 seconds)
        assert retrieval_time < 0.01, f"Graph types retrieval took {retrieval_time:.2f}s, expected < 0.01s"
        assert len(enabled_types) > 0
    
    def test_concurrent_graph_generation_performance(self) -> None:
        """Test performance of concurrent graph generation."""
        results: list[float] = []
        errors: list[Exception] = []
        
        def generate_graph_thread() -> None:
            try:
                with matplotlib_cleanup():
                    graph = PerformanceTestGraph()
                    test_data: dict[str, object] = {"test_key": "test_value"}
                    
                    start_time = time.time()
                    output_path = graph.generate(test_data)
                    generation_time = time.time() - start_time
                    
                    results.append(generation_time)
                    Path(output_path).unlink(missing_ok=True)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        num_threads = 3  # Use fewer threads to avoid overwhelming the system
        
        for _ in range(num_threads):
            thread = threading.Thread(target=generate_graph_thread)
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Check that no errors occurred
        assert len(errors) == 0, f"Errors in concurrent generation: {errors}"
        
        # Check that all threads completed successfully
        assert len(results) == num_threads, f"Expected {num_threads} results, got {len(results)}"
        
        # Concurrent generation should not take much longer than sequential
        # Allow up to 3x the time of a single generation for overhead
        assert total_time < 6.0, f"Concurrent generation took {total_time:.2f}s, expected < 6.0s"
        
        # Individual generation times should still be reasonable
        max_individual_time = max(results)
        assert max_individual_time < 3.0, f"Slowest thread took {max_individual_time:.2f}s, expected < 3.0s"
    
    def test_repeated_setup_cleanup_performance(self) -> None:
        """Test performance of repeated setup and cleanup operations."""
        graph = PerformanceTestGraph()
        
        setup_times: list[float] = []
        cleanup_times: list[float] = []
        
        # Perform multiple setup/cleanup cycles
        for _ in range(10):
            # Measure setup time
            start_time = time.time()
            _ = graph.setup_figure()
            setup_time = time.time() - start_time
            setup_times.append(setup_time)
            
            # Measure cleanup time
            start_time = time.time()
            graph.cleanup()
            cleanup_time = time.time() - start_time
            cleanup_times.append(cleanup_time)
        
        # Calculate averages
        avg_setup_time = sum(setup_times) / len(setup_times)
        avg_cleanup_time = sum(cleanup_times) / len(cleanup_times)
        
        # Average times should be reasonable
        assert avg_setup_time < 0.1, f"Average setup time {avg_setup_time:.3f}s, expected < 0.1s"
        assert avg_cleanup_time < 0.05, f"Average cleanup time {avg_cleanup_time:.3f}s, expected < 0.05s"
        
        # Check for performance consistency (no outliers)
        max_setup_time = max(setup_times)
        max_cleanup_time = max(cleanup_times)
        
        assert max_setup_time < 0.2, f"Slowest setup {max_setup_time:.3f}s, expected < 0.2s"
        assert max_cleanup_time < 0.1, f"Slowest cleanup {max_cleanup_time:.3f}s, expected < 0.1s"
    
    def test_large_data_processing_performance(self) -> None:
        """Test performance with larger datasets."""
        # Create larger test dataset
        large_data = {
            "data": [
                {
                    "date": f"2024-01-{i:02d}",
                    "user": f"user_{i % 10}",
                    "title": f"Content {i}",
                    "media_type": "movie" if i % 2 == 0 else "episode",
                    "platform": f"Platform {i % 3}",
                }
                for i in range(1, 1001)  # 1000 data points
            ]
        }
        
        with matplotlib_cleanup():
            graph = PerformanceTestGraph(complexity_level=2)
            
            # Measure generation time with large dataset
            start_time = time.time()
            output_path = graph.generate(large_data)
            generation_time = time.time() - start_time
            
            # Large dataset processing should still be reasonable (under 3 seconds)
            assert generation_time < 3.0, f"Large data processing took {generation_time:.2f}s, expected < 3.0s"
            
            # Verify output was created
            assert Path(output_path).exists()
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)
    
    def test_configuration_validation_performance(self) -> None:
        """Test performance of configuration validation operations."""
        # Test multiple configuration validations
        configs = [
            create_test_config_minimal(),
            create_test_config_comprehensive(),
        ]
        
        start_time = time.time()
        
        for config in configs * 100:  # Test 200 validations
            graph = PerformanceTestGraph(config=config)
            _ = graph.get_tv_color()
            _ = graph.get_movie_color()
            _ = graph.background_color
        
        validation_time = time.time() - start_time
        
        # 200 configuration validations should be fast (under 0.5 seconds)
        assert validation_time < 0.5, f"200 config validations took {validation_time:.2f}s, expected < 0.5s"
    
    def test_media_type_processor_performance(self) -> None:
        """Test performance of media type processor operations."""
        config = create_test_config_comprehensive()
        graph = PerformanceTestGraph(config=config)
        
        # Access media type processor
        start_time = time.time()
        processor = graph.media_type_processor
        access_time = time.time() - start_time
        
        # Processor access should be instant (under 0.01 seconds)
        assert access_time < 0.01, f"Processor access took {access_time:.3f}s, expected < 0.01s"
        
        # Test processor operations
        start_time = time.time()
        
        for _ in range(1000):
            _ = processor.get_color_for_type("tv")
            _ = processor.get_color_for_type("movie")
            _ = processor.get_display_info("tv")
        
        operation_time = time.time() - start_time
        
        # 1000 processor operations should be very fast (under 0.1 seconds)
        assert operation_time < 0.1, f"1000 processor ops took {operation_time:.2f}s, expected < 0.1s"
    
    def test_memory_efficiency_multiple_graphs(self) -> None:
        """Test memory efficiency when creating multiple graphs."""
        def create_multiple_graphs() -> None:
            graphs: list[PerformanceTestGraph] = []
            try:
                # Create multiple graphs
                for _ in range(5):
                    graph = PerformanceTestGraph(complexity_level=1)
                    graphs.append(graph)
                
                # Use each graph
                test_data: dict[str, object] = {"test_key": "test_value"}
                for graph in graphs:
                    with matplotlib_cleanup():
                        output_path = graph.generate(test_data)
                        Path(output_path).unlink(missing_ok=True)
            finally:
                # Clean up all graphs
                for graph in graphs:
                    if hasattr(graph, 'cleanup'):
                        graph.cleanup()
        
        with memory_monitoring() as memory_info:
            create_multiple_graphs()
        
        # Multiple graphs should not use excessive memory (under 100MB)
        memory_used = memory_info['memory_used_mb']
        assert memory_used < 100.0, f"Multiple graphs used {memory_used:.2f}MB, expected < 100MB"
    
    def test_garbage_collection_efficiency(self) -> None:
        """Test that objects are properly garbage collected."""
        def create_and_destroy_graph() -> None:
            with matplotlib_cleanup():
                graph = PerformanceTestGraph()
                _ = graph.setup_figure()
                test_data: dict[str, object] = {"test_key": "test_value"}
                output_path = graph.generate(test_data)
                Path(output_path).unlink(missing_ok=True)
                # Graph goes out of scope here
        
        # Get initial object count
        initial_objects = len(gc.get_objects())
        
        # Create and destroy graphs multiple times
        for _ in range(5):
            create_and_destroy_graph()
        
        # Force garbage collection
        _ = gc.collect()
        
        # Check final object count
        final_objects = len(gc.get_objects())
        objects_increase = final_objects - initial_objects
        
        # Object count should not increase significantly (allow some variation)
        assert objects_increase < 1000, f"Object count increased by {objects_increase}, expected < 1000"
    
    @patch('matplotlib.pyplot.savefig')
    def test_file_io_performance(self, mock_savefig: MagicMock) -> None:
        """Test file I/O performance patterns."""
        # Mock savefig to avoid actual file I/O
        mock_savefig.return_value = None
        
        with matplotlib_cleanup():
            graph = PerformanceTestGraph()
            test_data: dict[str, object] = {"test_key": "test_value"}
            
            # Measure time without file I/O
            start_time = time.time()
            _ = graph.generate(test_data)
            generation_time = time.time() - start_time
            
            # Without file I/O, generation should be very fast (under 1 second)
            assert generation_time < 1.0, f"Generation without I/O took {generation_time:.2f}s, expected < 1.0s"
            
            # Verify savefig was called
            mock_savefig.assert_called_once()
    
    def test_resource_cleanup_thoroughness(self) -> None:
        """Test that all resources are thoroughly cleaned up."""
        graph = PerformanceTestGraph()
        
        # Set up figure
        _ = graph.setup_figure()
        
        # Verify resources exist
        assert graph.figure is not None
        assert graph.axes is not None
        
        # Store references to check cleanup
        figure_ref = graph.figure
        axes_ref = graph.axes
        
        # Clean up
        graph.cleanup()
        
        # Verify thorough cleanup
        assert graph.figure is None
        assert graph.axes is None
        
        # Force garbage collection to ensure references are cleaned
        _ = gc.collect()
        
        # Original objects should be cleaned up by matplotlib
        # We can't directly test this without matplotlib internals,
        # but we can ensure our references are cleared
        assert figure_ref is not None  # Reference still exists but should be cleaned by matplotlib
        assert axes_ref is not None    # Reference still exists but should be cleaned by matplotlib