# graphs/user_graph_manager.py

import logging
import os
from datetime import datetime
from typing import Dict, Any, List
from .graph_modules.graph_factory import GraphFactory
from .graph_modules.data_fetcher import DataFetcher
from .graph_modules.utils import ensure_folder_exists

class UserGraphManager:
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        self.config = config
        self.translations = translations
        self.img_folder = img_folder
        self.graph_factory = GraphFactory(config, translations, img_folder)  # Pass img_folder here
        self.data_fetcher = DataFetcher(config)

    async def generate_user_graphs(self, user_id: str) -> List[str]:
        """
        Generate graphs for a specific user.
        
        :param user_id: The ID of the user to generate graphs for
        :return: A list of file paths for the generated graphs
        """
        today = datetime.today().strftime("%Y-%m-%d")
        user_folder = os.path.join(self.img_folder, today, f"user_{user_id}")
        ensure_folder_exists(user_folder)

        graph_files = []
        graph_data = await self.data_fetcher.fetch_all_graph_data(user_id)

        for graph_type, graph_instance in self.graph_factory.create_all_graphs().items():
            if graph_data.get(graph_type) and graph_type != "top_10_users":  # Exclude top 10 users graph for individual users
                file_path = await graph_instance.generate(self.data_fetcher, user_id)
                if file_path:
                    graph_files.append(file_path)

        logging.info(self.translations["log_generated_user_graphs"].format(user_id=user_id))
        logging.info(self.translations["log_generated_graph_files"].format(count=len(graph_files)))

        return graph_files

async def generate_user_graphs(user_id: str, config: Dict[str, Any], translations: Dict[str, str], img_folder: str) -> List[str]:
    """
    Generate graphs for a specific user using the UserGraphManager.
    
    :param user_id: The ID of the user to generate graphs for
    :param config: The configuration dictionary
    :param translations: The translations dictionary
    :param img_folder: The folder to save the graphs in
    :return: A list of file paths for the generated graphs
    """
    user_graph_manager = UserGraphManager(config, translations, img_folder)
    return await user_graph_manager.generate_user_graphs(user_id)
