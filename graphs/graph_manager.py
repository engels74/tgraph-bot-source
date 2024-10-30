# graphs/graph_manager.py

import logging
import os
from datetime import datetime, timedelta  # Added timedelta
from typing import Dict, Any, List, Optional
from .graph_modules.graph_factory import GraphFactory
from .graph_modules.data_fetcher import DataFetcher
from .graph_modules.utils import ensure_folder_exists, cleanup_old_folders
import discord

class GraphManager:
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        self.config = config
        self.translations = translations
        self.img_folder = img_folder
        self.graph_factory = GraphFactory(config, translations, img_folder)
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
            if graph_type in graph_data:
                file_path = await graph_instance.generate(graph_data[graph_type])
                if file_path:
                    graph_files.append((graph_type, file_path))

        logging.info(self.translations["log_generated_graphs"])
        logging.info(self.translations["log_generated_graph_files"].format(count=len(graph_files)))

        self.cleanup_old_graph_folders()

        return [file_path for _, file_path in graph_files]

    def cleanup_old_graph_folders(self):
        """Clean up old graph folders based on the KEEP_DAYS configuration."""
        cleanup_old_folders(self.img_folder, self.config["KEEP_DAYS"], self.translations)

    async def delete_old_messages(self, channel: discord.TextChannel):
        """
        Delete old messages in the specified channel.

        :param channel: The Discord channel to delete messages from
        """
        try:
            async for message in channel.history(limit=100):
                if message.author == channel.guild.me:
                    await message.delete()
                    logging.info(self.translations["log_deleted_message"])
        except discord.errors.Forbidden:
            logging.error(self.translations["error_delete_messages_no_permission"])
        except Exception as e:
            logging.error(self.translations["error_delete_messages"].format(error=str(e)))

    def create_embed(self, graph_type: str, update_tracker: Optional[Any] = None) -> discord.Embed:
        """
        Create a Discord embed for a graph.

        :param graph_type: The type of graph being posted
        :param update_tracker: Optional UpdateTracker instance for timestamp handling
        :return: A Discord embed object
        """
        clean_type = graph_type.replace('ENABLE_', '').lower()

        default_time_range_days = 7  # Default value
        days = self.config.get("TIME_RANGE_DAYS", default_time_range_days)

        title = self.translations.get(f"{clean_type}_title", "").format(
            days=days
        )
        description = self.translations.get(f"{clean_type}_description", "").format(
            days=days
        )

        if update_tracker:
            next_update_str = update_tracker.get_next_update_discord()
            logging.info(f"Using update tracker timestamp for embed: {next_update_str}")
        else:
            default_days = 1  # Default value
            update_days = self.config.get("UPDATE_DAYS", default_days)
            next_update = datetime.now() + timedelta(days=update_days)
            next_update_str = f"<t:{int(next_update.timestamp())}:R>"
            logging.info(f"Using fallback timestamp for embed: {next_update_str}")

        description = f"{description}\n\n{self.translations['next_update'].format(next_update=next_update_str)}"

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue()
        )

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        footer_text = self.translations.get('embed_footer', 'Generated on {now}').format(now=now)
        embed.set_footer(text=footer_text)

        return embed

    async def post_graphs(self, channel: discord.TextChannel, graph_files: List[str], update_tracker: Optional[Any] = None):
        """
        Post graphs to the specified Discord channel with embeds.

        :param channel: The Discord channel to post graphs to
        :param graph_files: List of graph file paths to post
        :param update_tracker: Optional UpdateTracker instance for timestamp handling
        """
        try:
            enabled_graphs = {
                k: v for k, v in self.config.items()
                if k.startswith("ENABLE_") and v
            }

            graph_types = list(enabled_graphs.keys())
            graph_pairs = list(zip(graph_types, graph_files))

            for graph_type, file_path in graph_pairs:
                try:
                    embed = self.create_embed(graph_type, update_tracker)

                    with open(file_path, 'rb') as f:
                        file = discord.File(f, filename=os.path.basename(file_path))
                        embed.set_image(url=f"attachment://{os.path.basename(file_path)}")
                        await channel.send(embed=embed, file=file)

                    logging.info(self.translations["log_posted_message"].format(
                        filename=os.path.basename(file_path)
                    ))

                except discord.errors.Forbidden:
                    logging.error(self.translations["error_post_graphs_no_permission"])
                except Exception as e:
                    logging.error(self.translations["error_post_graphs"].format(error=str(e)))

        except Exception as e:
            logging.error(f"Error in post_graphs: {str(e)}")
