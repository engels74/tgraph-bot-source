# graphs/graph_modules/graph_factory.py

"""
GraphFactory implementation with enhanced error handling and type safety.
Provides centralized creation and management of graph instances with standardized
error handling and resource management.
"""

from .base_graph import BaseGraph
from .daily_play_count_graph import DailyPlayCountGraph
from .play_count_by_dayofweek_graph import PlayCountByDayOfWeekGraph
from .play_count_by_hourofday_graph import PlayCountByHourOfDayGraph
from .play_count_by_month_graph import PlayCountByMonthGraph
from .top_10_platforms_graph import Top10PlatformsGraph
from .top_10_users_graph import Top10UsersGraph
from typing import Dict, Any, Tuple, Optional, Type
import asyncio
import logging

class GraphFactoryError(Exception):
    """Base exception for graph factory related errors."""
    pass

class GraphCreationError(GraphFactoryError):
    """Raised when there is an error creating a graph instance."""
    pass

class GraphTypeError(GraphFactoryError):
    """Raised when an invalid graph type is specified."""
    pass

class DataProcessingError(GraphFactoryError):
    """Raised when there is an error processing graph data."""
    pass

class GraphGenerationError(GraphFactoryError):
    """Raised when there is an error generating graphs."""
    pass

class ResourceManagementError(GraphFactoryError):
    """Raised when there is an error managing graph resources."""
    pass

class GraphFactory:
    """Factory class for creating and managing graph instances."""

    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        """
        Initialize the GraphFactory.
        
        Args:
            config: Configuration dictionary containing graph settings
            translations: Dictionary of translation strings
            img_folder: Path to the image output folder
        
        Raises:
            GraphCreationError: If initialization fails due to missing configuration
            ValueError: If required configuration keys are missing
        """
        try:
            # Validate required configuration keys
            required_keys = {f"ENABLE_{graph_type.upper()}" for graph_type in [
                "daily_play_count", "play_count_by_dayofweek", "play_count_by_hourofday",
                "top_10_platforms", "top_10_users", "play_count_by_month"
            ]}
            missing_keys = required_keys - set(config.keys())
            if missing_keys:
                raise ValueError(f"Missing required configuration keys: {missing_keys}")

            self.config = config
            self.translations = translations
            self.img_folder = img_folder
            
            # Map graph types to their respective classes with proper type hints
            self.graph_classes: Dict[str, Type[BaseGraph]] = {
                "daily_play_count": DailyPlayCountGraph,
                "play_count_by_dayofweek": PlayCountByDayOfWeekGraph,
                "play_count_by_hourofday": PlayCountByHourOfDayGraph,
                "top_10_platforms": Top10PlatformsGraph,
                "top_10_users": Top10UsersGraph,
                "play_count_by_month": PlayCountByMonthGraph
            }
        except ValueError as e:
            error_msg = self.translations.get(
                'error_graph_factory_init',
                'Failed to initialize graph factory: {error}'
            ).format(error=str(e))
            logging.error(error_msg)
            raise GraphCreationError(error_msg) from e
        except Exception as e:
            error_msg = self.translations.get(
                'error_unexpected_init',
                'Unexpected error initializing graph factory: {error}'
            ).format(error=str(e))
            logging.error(error_msg)
            raise GraphCreationError(error_msg) from e

    def create_graph(self, graph_type: str) -> BaseGraph:
        """
        Create and return a graph object of the specified type.
        
        Args:
            graph_type: The type of graph to create
            
        Returns:
            An instance of the requested graph type
            
        Raises:
            GraphTypeError: If an invalid graph type is provided
            GraphCreationError: If graph instance creation fails
        """
        try:
            graph_class = self.graph_classes.get(graph_type)
            if graph_class is None:
                error_msg = self.translations.get(
                    'error_invalid_graph_type',
                    'Invalid graph type: {type}'
                ).format(type=graph_type)
                raise GraphTypeError(error_msg)
            
            return graph_class(self.config, self.translations, self.img_folder)
            
        except GraphTypeError:
            raise
        except Exception as e:
            error_msg = self.translations.get(
                'error_graph_creation',
                'Failed to create graph of type {type}: {error}'
            ).format(type=graph_type, error=str(e))
            logging.error(error_msg)
            raise GraphCreationError(error_msg) from e

    def create_all_graphs(self) -> Dict[str, BaseGraph]:
        """
        Create and return instances of all enabled graph types.
        
        Returns:
            A dictionary mapping graph types to their respective graph instances
            
        Raises:
            GraphCreationError: If creation of any graph instance fails
        """
        try:
            enabled_graphs = {}
            for graph_type, graph_class in self.graph_classes.items():
                config_key = f"ENABLE_{graph_type.upper()}"
                if self.config.get(config_key, False):
                    try:
                        enabled_graphs[graph_type] = graph_class(
                            self.config, self.translations, self.img_folder
                        )
                        logging.debug(f"Created graph instance for {graph_type}")
                    except Exception as e:
                        error_msg = self.translations.get(
                            'error_graph_instance_creation',
                            'Failed to create instance of {type}: {error}'
                        ).format(type=graph_type, error=str(e))
                        logging.error(error_msg)
                        raise GraphCreationError(error_msg) from e
                else:
                    logging.debug(f"Skipping disabled graph type: {graph_type}")
                    
            return enabled_graphs
            
        except Exception as e:
            error_msg = self.translations.get(
                'error_creating_graphs',
                'Failed to create graph instances: {error}'
            ).format(error=str(e))
            logging.error(error_msg)
            raise GraphCreationError(error_msg) from e

    async def _generate_single_graph(
        self,
        graph_type: str,
        graph_instance: BaseGraph,
        data_fetcher: Any,
        user_id: Optional[str],
        sem: asyncio.Semaphore
    ) -> Optional[Tuple[str, str]]:
        """
        Helper method to generate a single graph with proper error handling and resource management.
        
        Args:
            graph_type: The type of graph to generate
            graph_instance: The graph instance to use
            data_fetcher: The data fetcher instance
            user_id: Optional user ID for user-specific graphs
            sem: Semaphore for controlling concurrent operations
            
        Returns:
            A tuple of (graph_type, file_path) if successful, None if generation fails
            
        Raises:
            GraphGenerationError: If there is an error generating the graph
        """
        async with sem:  # Control concurrent graph generations
            try:
                file_path = await graph_instance.generate(data_fetcher, user_id)
                if file_path:
                    logging.info(self.translations.get(
                        "log_graph_generated",
                        "Generated {graph_type} graph"
                    ).format(graph_type=graph_type))
                    return graph_type, file_path
                return None
                
            except Exception as e:
                error_msg = self.translations.get(
                    "error_generating_graph",
                    "Error generating {graph_type} graph: {error}"
                ).format(graph_type=graph_type, error=str(e))
                raise GraphGenerationError(error_msg) from e
            finally:
                # Ensure proper resource cleanup
                if hasattr(graph_instance, 'cleanup_figure'):
                    graph_instance.cleanup_figure()

    async def generate_graphs(
        self, 
        data_fetcher: Any, 
        user_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate all enabled graphs concurrently and return their file paths.
        
        Args:
            data_fetcher: The DataFetcher instance to use for data retrieval
            user_id: Optional user ID for user-specific graphs
        
        Returns:
            A dictionary of graph type to generated graph file paths
        
        Raises:
            DataProcessingError: If graph data cannot be fetched
            GraphGenerationError: If graph generation fails
            ResourceManagementError: If resource management fails
        """
        generated_graphs = {}
        
        try:
            # Add timeout for data fetching
            async with asyncio.timeout(30):
                graph_data = await data_fetcher.fetch_all_graph_data(user_id)
                
            if not graph_data:
                error_msg = self.translations.get(
                    "error_fetch_graph_data",
                    "Failed to fetch graph data"
                )
                raise DataProcessingError(error_msg)
                
            # Generate graphs concurrently with semaphore to limit concurrent operations
            sem = asyncio.Semaphore(3)  # Limit to 3 concurrent graph generations
            tasks = []
            
            for graph_type, graph_instance in self.create_all_graphs().items():
                if graph_type in graph_data:
                    graph_instance.data = graph_data[graph_type]
                    tasks.append(
                        self._generate_single_graph(
                            graph_type, graph_instance, data_fetcher, user_id, sem
                        )
                    )
                    
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        logging.error(f"Graph generation error: {str(result)}")
                    elif result:
                        graph_type, file_path = result
                        generated_graphs[graph_type] = file_path
                        
            except Exception as e:
                error_msg = self.translations.get(
                    'error_concurrent_generation',
                    'Error during concurrent graph generation: {error}'
                ).format(error=str(e))
                raise GraphGenerationError(error_msg) from e
                    
        except asyncio.TimeoutError as e:
            error_msg = self.translations.get(
                "error_timeout",
                "Timeout during graph generation"
            )
            logging.error(error_msg)
            raise GraphGenerationError(error_msg) from e
        except DataProcessingError:
            raise
        except Exception as e:
            error_msg = self.translations.get(
                "error_graph_generation",
                "Error during graph generation: {error}"
            ).format(error=str(e))
            logging.error(error_msg)
            raise GraphGenerationError(error_msg) from e
                
        return generated_graphs
