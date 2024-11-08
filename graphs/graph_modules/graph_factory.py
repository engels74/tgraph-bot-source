# graphs/graph_modules/graph_factory.py

"""
GraphFactory implementation with corrected type hints and improved error handling.
"""

from typing import Dict, Any, Tuple, Union, Optional
import asyncio
import logging
from .base_graph import BaseGraph
from .daily_play_count_graph import DailyPlayCountGraph
from .play_count_by_dayofweek_graph import PlayCountByDayOfWeekGraph
from .play_count_by_hourofday_graph import PlayCountByHourOfDayGraph
from .top_10_platforms_graph import Top10PlatformsGraph
from .top_10_users_graph import Top10UsersGraph
from .play_count_by_month_graph import PlayCountByMonthGraph

class GraphFactoryError(Exception):
    """Base exception for graph factory related errors."""
    pass

class DataFetchError(GraphFactoryError):
    """Raised when there is an error fetching graph data."""
    pass

class GraphGenerationError(GraphFactoryError):
    """Raised when there is an error generating a graph."""
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
            ValueError: If required configuration keys are missing
        """
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
        
        # Map graph types to their respective classes
        self.graph_classes: Dict[str, type[BaseGraph]] = {
            "daily_play_count": DailyPlayCountGraph,
            "play_count_by_dayofweek": PlayCountByDayOfWeekGraph,
            "play_count_by_hourofday": PlayCountByHourOfDayGraph,
            "top_10_platforms": Top10PlatformsGraph,
            "top_10_users": Top10UsersGraph,
            "play_count_by_month": PlayCountByMonthGraph
        }

    def create_graph(self, graph_type: str) -> BaseGraph:
        """
        Create and return a graph object of the specified type.
        
        Args:
            graph_type: The type of graph to create
            
        Returns:
            An instance of the requested graph type
            
        Raises:
            ValueError: If an invalid graph type is provided
        """
        graph_class = self.graph_classes.get(graph_type)
        if graph_class is None:
            raise ValueError(f"Invalid graph type: {graph_type}")
        
        return graph_class(self.config, self.translations, self.img_folder)

    def create_all_graphs(self) -> Dict[str, Union[
        DailyPlayCountGraph, PlayCountByDayOfWeekGraph, PlayCountByHourOfDayGraph,
        Top10PlatformsGraph, Top10UsersGraph, PlayCountByMonthGraph
    ]]:
        """
        Create and return instances of all enabled graph types.
        
        Returns:
            A dictionary mapping graph types to their respective graph instances
        """
        enabled_graphs = {}
        for graph_type, graph_class in self.graph_classes.items():
            config_key = f"ENABLE_{graph_type.upper()}"
            if self.config.get(config_key, False):
                enabled_graphs[graph_type] = graph_class(self.config, self.translations, self.img_folder)
                logging.debug(f"Created graph instance for {graph_type}")
            else:
                logging.debug(f"Skipping disabled graph type: {graph_type}")
        return enabled_graphs

    async def generate_graphs(self, data_fetcher, user_id: Optional[str] = None) -> Dict[str, str]:
        """
        Generate all enabled graphs concurrently and return their file paths.
        
        Args:
            data_fetcher: The DataFetcher instance to use for data retrieval
            user_id: Optional user ID for user-specific graphs
        
        Returns:
            A dictionary of graph type to generated graph file paths
        
        Raises:
            DataFetchError: If graph data cannot be fetched
            TimeoutError: If data fetching exceeds timeout
        """
        generated_graphs = {}
        
        try:
            async with asyncio.timeout(30):  # Add timeout for data fetching
                graph_data = await data_fetcher.fetch_all_graph_data(user_id)
                
            if not graph_data:
                raise DataFetchError(self.translations.get(
                    "error_fetch_graph_data",
                    "Failed to fetch graph data"
                ))
                
            # Generate graphs concurrently
            tasks = []
            for graph_type, graph_instance in self.create_all_graphs().items():
                if graph_data.get(graph_type):
                    tasks.append(self._generate_single_graph(
                        graph_type, graph_instance, data_fetcher, user_id
                    ))
                    
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logging.error(str(result))
                elif result:
                    graph_type, file_path = result
                    generated_graphs[graph_type] = file_path
                    
        except asyncio.TimeoutError:
            logging.error(self.translations.get(
                "error_timeout",
                "Timeout during graph generation"
            ))
        except DataFetchError as e:
            logging.error(str(e))
        except Exception as e:
            logging.error(self.translations.get(
                "error_graph_generation",
                "Error during graph generation: {error}"
            ).format(error=str(e)))
                
        return generated_graphs

    async def _generate_single_graph(
        self,
        graph_type: str,
        graph_instance: BaseGraph,
        data_fetcher,
        user_id: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Helper method to generate a single graph with proper error handling.
        
        Args:
            graph_type: The type of graph to generate
            graph_instance: The graph instance to use
            data_fetcher: The data fetcher instance
            user_id: Optional user ID for user-specific graphs
            
        Returns:
            A tuple of (graph_type, file_path) if successful, None if generation fails
            
        Raises:
            GraphGenerationError: If there is an error generating the graph
        """
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
            raise GraphGenerationError(self.translations.get(
                "error_generating_graph",
                "Error generating {graph_type} graph: {error}"
            ).format(graph_type=graph_type, error=str(e)))
