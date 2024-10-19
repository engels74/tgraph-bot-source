# graphs/graph_manager.py

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING
from .graph_modules.graph_factory import GraphFactory
from .graph_modules.utils import ensure_folder_exists, cleanup_old_folders
import discord
import aiofiles
import io
import asyncio

if TYPE_CHECKING:
    from .update_tracker import UpdateTracker
    from .graph_modules.data_fetcher import DataFetcher

class GraphManager:
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        self.config = config
        self.translations = translations
        self.img_folder = img_folder
        self.graph_factory = GraphFactory(config, translations, img_folder)

    async def generate_and_save_graphs(self, data_fetcher: 'DataFetcher') -> List[Tuple[str, str]]:
        """Generate and save all enabled graphs."""
        today = datetime.today().strftime("%Y-%m-%d")
        dated_folder = os.path.join(self.img_folder, today)
        ensure_folder_exists(dated_folder)

        graph_files = []
        
        try:
            logging.debug("Starting generate_and_save_graphs")
            # Fetch all graph data using the provided data_fetcher
            graph_data = await data_fetcher.fetch_all_graph_data()
            logging.debug("Fetched graph_data keys: %s", list(graph_data.keys() if graph_data else []))

            for graph_type, graph_instance in self.graph_factory.create_all_graphs().items():
                logging.debug("Processing graph type: %s", graph_type)
                if graph_type in graph_data:
                    try:
                        # Pass None for user_id and let the graph instance handle the data internally
                        logging.debug("Calling generate() for %s", graph_type)
                        graph_instance.data = graph_data[graph_type]  # Store the data in the instance
                        file_path = await graph_instance.generate(data_fetcher)  # Don't pass graph data as user_id
                        if file_path:
                            graph_files.append((graph_type, file_path))
                            logging.debug("Generated %s: %s", graph_type, file_path)
                    except Exception as e:
                        logging.error("Error generating %s: %s", graph_type, str(e))
                        logging.error(self.translations["error_generating_graph"].format(
                            graph_type=graph_type
                        ))
                        continue

            logging.debug("Final graph_files count: %d", len(graph_files))
            return graph_files
                
        except Exception as e:
            logging.error("Error in generate_and_save_graphs: %s", str(e), exc_info=True)
            return []

    def cleanup_old_graph_folders(self):
        """Clean up old graph folders based on the KEEP_DAYS configuration."""
        try:
            cleanup_old_folders(self.img_folder, self.config["KEEP_DAYS"], self.translations)
        except OSError as e:
            logging.error(self.translations.get(
                "error_cleanup_folders",
                "Error cleaning up folders: {error}"
            ).format(error=str(e)))

    async def delete_old_messages(self, channel: discord.TextChannel, limit: int = 100):
        """
        Delete old messages in the specified channel.
        
        Args:
            channel: The Discord channel to delete messages from
            limit: Maximum number of messages to check (default: 100)
        """
        try:
            async for message in channel.history(limit=limit):
                if message.author == channel.guild.me:
                    await message.delete()
                    await asyncio.sleep(1)  # Rate limiting: Wait 1s between deletions
                    logging.info(self.translations["log_deleted_message"])
        except discord.errors.Forbidden:
            logging.error(self.translations["error_delete_messages_no_permission"])
        except Exception as e:
            logging.error(self.translations["error_delete_messages"].format(error=str(e)))

    def create_embed(self, graph_type: str, update_tracker: Optional['UpdateTracker'] = None) -> discord.Embed:
        """
        Create a Discord embed for a graph.
        
        Args:
            graph_type: The type of graph being posted
            update_tracker: Optional UpdateTracker instance for timestamp handling
        
        Returns:
            A Discord embed object
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
            logging.debug(f"Using update tracker timestamp for embed: {next_update_str}")
        else:
            default_days = 1  # Default value
            update_days = self.config.get("UPDATE_DAYS", default_days)
            next_update = datetime.now() + timedelta(days=update_days)
            next_update_str = f"<t:{int(next_update.timestamp())}:R>"
            logging.debug(f"Using fallback timestamp for embed: {next_update_str}")

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

    async def post_graphs(self, channel: discord.TextChannel, graph_files: List[Tuple[str, str]], update_tracker: Optional['UpdateTracker'] = None):
        """
        Post graphs to the specified Discord channel with embeds.
        
        Args:
            channel: The Discord channel to post graphs to
            graph_files: List of tuples containing (graph_type, file_path) for the graphs
            update_tracker: Optional UpdateTracker instance for timestamp handling
        """
        try:
            enabled_graphs = {
                k: v for k, v in self.config.items()
                if k.startswith("ENABLE_") and v
            }

            graph_types = list(enabled_graphs.keys())
            graph_pairs = list(zip(graph_types, [f[1] for f in graph_files]))

            for graph_type, file_path in graph_pairs:
                try:
                    embed = self.create_embed(graph_type, update_tracker)

                    async with aiofiles.open(file_path, 'rb') as f:
                        content = await f.read()
                        file = discord.File(io.BytesIO(content), filename=os.path.basename(file_path))
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
