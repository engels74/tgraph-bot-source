# graphs/graph_modules/graph_factory.py

from typing import Dict, Any, Type
from .base_graph import BaseGraph
from .daily_play_count_graph import DailyPlayCountGraph
from .play_count_by_dayofweek_graph import PlayCountByDayOfWeekGraph
from .play_count_by_hourofday_graph import PlayCountByHourOfDayGraph
from .top_10_platforms_graph import Top10PlatformsGraph
from .top_10_users_graph import Top10UsersGraph
from .play_count_by_month_graph import PlayCountByMonthGraph

class GraphFactory:
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        self.config = config
        self.translations = translations
        self.img_folder = img_folder  # Add this line
        self.graph_classes: Dict[str, Type[BaseGraph]] = {
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
        
        :param graph_type: The type of graph to create
        :return: An instance of the requested graph type
        :raises ValueError: If an invalid graph type is provided
        """
        graph_class = self.graph_classes.get(graph_type)
        if graph_class is None:
            raise ValueError(f"Invalid graph type: {graph_type}")
        
        return graph_class(self.config, self.translations, self.img_folder)

    def create_all_graphs(self) -> Dict[str, BaseGraph]:
        """
        Create and return instances of all enabled graph types.
        
        :return: A dictionary of graph type to graph object instances
        """
        enabled_graphs = {}
        for graph_type, graph_class in self.graph_classes.items():
            config_key = f"ENABLE_{graph_type.upper()}"
            if self.config.get(config_key, False):
                enabled_graphs[graph_type] = graph_class(self.config, self.translations, self.img_folder)
        
        return enabled_graphs

    async def generate_graphs(self, data_fetcher, user_id: str = None) -> Dict[str, str]:
        """
        Generate all enabled graphs and return their file paths.
        
        :param data_fetcher: The DataFetcher instance to use for data retrieval
        :param user_id: Optional user ID for user-specific graphs
        :return: A dictionary of graph type to generated graph file paths
        """
        graph_data = await data_fetcher.fetch_all_graph_data(user_id)
        generated_graphs = {}

        for graph_type, graph_instance in self.create_all_graphs().items():
            if graph_data.get(graph_type):
                file_path = await graph_instance.generate(data_fetcher, user_id)
                if file_path:
                    generated_graphs[graph_type] = file_path

        return generated_graphs
