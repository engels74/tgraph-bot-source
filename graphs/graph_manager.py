# graphs/graph_manager.py

import logging
import os
from datetime import datetime
from typing import Dict, Any, List
from .graph_modules.graph_factory import GraphFactory
from .graph_modules.data_fetcher import DataFetcher
from .graph_modules.utils import ensure_folder_exists, cleanup_old_folders
import discord

class GraphManager:
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        self.config = config
        self.translations = translations
        self.img_folder = img_folder
        self.graph_factory = GraphFactory(config, translations)
        self.data_fetcher = DataFetcher(config)

    async def generate_and_save_graphs(self) -> List[str]:
        """
        Generate and save all enabled graphs.
        
        :return: A list of file paths for the generated graphs
        """
        today = datetime.today().strftime("%Y-%m-%d")
        dated_folder = os.path.join(self.img_folder, today)
        ensure_folder_exists(dated_folder)

        graph_files = []
        graph_data = await self.data_fetcher.fetch_all_graph_data()

        for graph_type, graph_instance in self.graph_factory.create_all_graphs().items():
            if graph_data.get(graph_type):
                file_path = await graph_instance.generate(self.data_fetcher)
                if file_path:
                    graph_files.append(file_path)

        logging.info(self.translations["log_generated_graphs"])
        logging.info(self.translations["log_generated_graph_files"].format(count=len(graph_files)))

        self.cleanup_old_graph_folders()

        return graph_files

    def cleanup_old_graph_folders(self):
        """
        Clean up old graph folders based on the KEEP_DAYS configuration.
        """
        cleanup_old_folders(self.img_folder, self.config["KEEP_DAYS"], self.translations)

    async def delete_old_messages(self, channel: discord.TextChannel):
        """
        Delete old messages in the specified channel.
        
        :param channel: The Discord channel to delete messages from
        """
        try:
            async for message in channel.history(limit=100):  # Adjust the limit as needed
                if message.author == channel.guild.me:
                    await message.delete()
                    logging.info(self.translations["log_deleted_message"])
        except discord.errors.Forbidden:
            logging.error(self.translations["error_delete_messages_no_permission"])
        except Exception as e:
            logging.error(self.translations["error_delete_messages"].format(error=str(e)))

    async def post_graphs(self, channel: discord.TextChannel, graph_files: List[str]):
        """
        Post graphs to the specified Discord channel.
        
        :param channel: The Discord channel to post graphs to
        :param graph_files: List of graph file paths to post
        """
        for file_path in graph_files:
            try:
                await channel.send(file=discord.File(file_path))
                logging.info(self.translations["log_posted_message"].format(filename=os.path.basename(file_path)))
            except discord.errors.Forbidden:
                logging.error(self.translations["error_post_graphs_no_permission"])
            except Exception as e:
                logging.error(self.translations["error_post_graphs"].format(error=str(e)))

async def generate_graphs(config: Dict[str, Any], translations: Dict[str, str], img_folder: str) -> List[str]:
    """
    Generate all graphs using the GraphManager.
    
    :param config: The configuration dictionary
    :param translations: The translations dictionary
    :param img_folder: The folder to save the graphs in
    :return: A list of file paths for the generated graphs
    """
    graph_manager = GraphManager(config, translations, img_folder)
    return await graph_manager.generate_and_save_graphs()
