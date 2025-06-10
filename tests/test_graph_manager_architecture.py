"""
Tests for GraphManager architecture design and implementation.

This module tests the core architectural components of the GraphManager
to ensure proper dependency injection, async context management, and
integration with existing components.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from graphs.graph_manager import GraphManager
from config.manager import ConfigManager
from config.schema import TGraphBotConfig


class TestGraphManagerArchitecture:
    """Test cases for GraphManager architecture."""

    def test_init_with_config_manager(self) -> None:
        """Test GraphManager initialization with ConfigManager."""
        config_manager = ConfigManager()
        
        # Create a mock config
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )
        config_manager.set_current_config(mock_config)
        
        graph_manager = GraphManager(config_manager)
        
        assert graph_manager.config_manager is config_manager
        assert graph_manager._data_fetcher is None
        assert graph_manager._graph_factory is None

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Test GraphManager async context manager functionality."""
        config_manager = ConfigManager()
        
        # Create a mock config
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )
        config_manager.set_current_config(mock_config)
        
        with patch('graphs.graph_manager.DataFetcher') as mock_data_fetcher_class:
            with patch('graphs.graph_manager.GraphFactory') as mock_graph_factory_class:
                # Setup mocks
                mock_data_fetcher = AsyncMock()
                mock_data_fetcher.__aenter__ = AsyncMock(return_value=mock_data_fetcher)
                mock_data_fetcher.__aexit__ = AsyncMock(return_value=None)
                mock_data_fetcher_class.return_value = mock_data_fetcher
                
                mock_graph_factory = MagicMock()
                mock_graph_factory_class.return_value = mock_graph_factory
                
                # Test context manager
                async with GraphManager(config_manager) as graph_manager:
                    # Verify components are initialized
                    assert graph_manager._data_fetcher is not None
                    assert graph_manager._graph_factory is not None
                    
                    # Verify DataFetcher was created with correct parameters
                    mock_data_fetcher_class.assert_called_once_with(
                        base_url="http://localhost:8181/api/v2",
                        api_key="test_key",
                        timeout=30.0,
                        max_retries=3
                    )
                    
                    # Verify GraphFactory was created with config
                    mock_graph_factory_class.assert_called_once_with(mock_config)
                
                # Verify cleanup was called
                mock_data_fetcher.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_all_graphs_architecture(self) -> None:
        """Test the generate_all_graphs method architecture."""
        config_manager = ConfigManager()
        
        # Create a mock config
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
            TIME_RANGE_DAYS=30,
        )
        config_manager.set_current_config(mock_config)
        
        with patch('graphs.graph_manager.DataFetcher') as mock_data_fetcher_class:
            with patch('graphs.graph_manager.GraphFactory') as mock_graph_factory_class:
                with patch('asyncio.to_thread') as mock_to_thread:
                    # Setup mocks
                    mock_data_fetcher = AsyncMock()
                    mock_data_fetcher.__aenter__ = AsyncMock(return_value=mock_data_fetcher)
                    mock_data_fetcher.__aexit__ = AsyncMock(return_value=None)
                    mock_data_fetcher.get_play_history = AsyncMock(return_value={"test": "data"})
                    mock_data_fetcher_class.return_value = mock_data_fetcher
                    
                    mock_graph_factory = MagicMock()
                    mock_graph_factory.generate_all_graphs = MagicMock(return_value=["graph1.png", "graph2.png"])
                    mock_graph_factory_class.return_value = mock_graph_factory
                    
                    mock_to_thread.return_value = ["graph1.png", "graph2.png"]
                    
                    # Test generate_all_graphs
                    async with GraphManager(config_manager) as graph_manager:
                        result = await graph_manager.generate_all_graphs()
                        
                        # Verify data fetching was called
                        mock_data_fetcher.get_play_history.assert_called_once_with(time_range=30)
                        
                        # Verify asyncio.to_thread was used for graph generation
                        mock_to_thread.assert_called_once()
                        
                        # Verify result
                        assert result == ["graph1.png", "graph2.png"]

    @pytest.mark.asyncio
    async def test_error_handling_architecture(self) -> None:
        """Test error handling in the GraphManager architecture."""
        config_manager = ConfigManager()
        
        # Create a mock config
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )
        config_manager.set_current_config(mock_config)
        
        graph_manager = GraphManager(config_manager)
        
        # Test error when components not initialized
        with pytest.raises(RuntimeError, match="GraphManager components not initialized"):
            await graph_manager.generate_all_graphs()

    def test_architecture_interfaces(self) -> None:
        """Test that GraphManager has the expected interface methods."""
        config_manager = ConfigManager()
        mock_config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_token",
            CHANNEL_ID=123456789,
        )
        config_manager.set_current_config(mock_config)
        
        graph_manager = GraphManager(config_manager)
        
        # Verify expected methods exist
        assert hasattr(graph_manager, 'generate_all_graphs')
        assert hasattr(graph_manager, 'post_graphs_to_discord')
        assert hasattr(graph_manager, 'cleanup_old_graphs')
        assert hasattr(graph_manager, 'update_graphs_full_cycle')
        
        # Verify async context manager methods
        assert hasattr(graph_manager, '__aenter__')
        assert hasattr(graph_manager, '__aexit__')
        
        # Verify methods are coroutines
        import inspect
        assert inspect.iscoroutinefunction(graph_manager.generate_all_graphs)
        assert inspect.iscoroutinefunction(graph_manager.post_graphs_to_discord)
        assert inspect.iscoroutinefunction(graph_manager.cleanup_old_graphs)
        assert inspect.iscoroutinefunction(graph_manager.update_graphs_full_cycle)
