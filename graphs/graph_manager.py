# graphs/graph_manager.py

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING
from .graph_modules.graph_factory import GraphFactory, GraphFactoryError
from .graph_modules.data_fetcher import DataFetcher, DataFetcherError
from .graph_modules.utils import ensure_folder_exists
import discord
import aiofiles
import io
import asyncio

if TYPE_CHECKING:
    from .update_tracker import UpdateTracker

class GraphManagerError(Exception):
    """Base exception for GraphManager-related errors."""
    pass

class GraphGenerationError(GraphManagerError):
    """Raised when there's an error generating graphs."""
    pass

class DiscordError(GraphManagerError):
    """Raised when there's an error interacting with Discord."""
    pass

class GraphManager:
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        self.config = config
        self.translations = translations
        self.img_folder = img_folder
        self.graph_factory = GraphFactory(config, translations, img_folder)

    async def generate_and_save_graphs(self, data_fetcher: 'DataFetcher') -> List[Tuple[str, str]]:
        """Generate and save all enabled graphs.
        
        Args:
            data_fetcher: DataFetcher instance to use for data retrieval
            
        Returns:
            List of tuples containing (graph_type, file_path)
            
        Raises:
            GraphGenerationError: If graph generation fails
        """
        today = datetime.today().strftime("%Y-%m-%d")
        dated_folder = os.path.join(self.img_folder, today)
        ensure_folder_exists(dated_folder)

        graph_files = []
        
        try:
            logging.debug("Starting generate_and_save_graphs")
            graph_data = await data_fetcher.fetch_all_graph_data()
            if not graph_data:
                raise DataFetcherError("Failed to fetch graph data")
                
            logging.debug("Fetched graph_data keys: %s", list(graph_data.keys()))

            for graph_type, graph_instance in self.graph_factory.create_all_graphs().items():
                try:
                    if graph_type not in graph_data:
                        logging.warning(f"No data available for {graph_type}")
                        continue
                        
                    logging.debug("Generating %s", graph_type)
                    graph_instance.data = graph_data[graph_type]
                    file_path = await graph_instance.generate(data_fetcher)
                    
                    if file_path:
                        graph_files.append((graph_type, file_path))
                        logging.debug("Generated %s: %s", graph_type, file_path)
                except (GraphFactoryError, IOError) as e:
                    logging.error("Error generating %s: %s", graph_type, str(e))
                    raise GraphGenerationError(f"Failed to generate {graph_type}: {str(e)}")

            if not graph_files:
                raise GraphGenerationError("No graphs were generated successfully")

            logging.debug("Final graph_files count: %d", len(graph_files))
            return graph_files
                
        except DataFetcherError as e:
            logging.error("Failed to fetch graph data: %s", str(e))
            raise GraphGenerationError("Failed to fetch data for graphs") from e
        except Exception as e:
            logging.error("Unexpected error in generate_and_save_graphs: %s", str(e))
            raise GraphGenerationError("Unexpected error during graph generation") from e

    async def delete_old_messages(self, channel: discord.TextChannel, limit: int = 100):
        """Delete old messages in the specified channel.
        
        Args:
            channel: The Discord channel to delete messages from
            limit: Maximum number of messages to check
            
        Raises:
            DiscordError: If message deletion fails
        """
        try:
            async for message in channel.history(limit=limit):
                if message.author == channel.guild.me:
                    try:
                        await message.delete()
                        await asyncio.sleep(1)  # Rate limiting
                        logging.info(self.translations["log_deleted_message"])
                    except discord.Forbidden:
                        raise DiscordError("Missing permissions to delete messages")
                    except discord.HTTPException as e:
                        raise DiscordError(f"Failed to delete message: {str(e)}")
        except discord.Forbidden as e:
            logging.error("Missing permissions to access channel history")
            raise DiscordError("Missing permissions to access channel history") from e
        except discord.HTTPException as e:
            logging.error("Failed to fetch channel history: %s", str(e))
            raise DiscordError("Failed to fetch channel history") from e

    def create_embed(self, graph_type: str, update_tracker: Optional['UpdateTracker'] = None) -> discord.Embed:
        """Create a Discord embed for a graph.
        
        Args:
            graph_type: Type of graph
            update_tracker: Optional UpdateTracker for timestamps
            
        Returns:
            Discord Embed object
        """
        clean_type = graph_type.replace('ENABLE_', '').lower()
        days = self.config.get("TIME_RANGE_DAYS", 7)

        title = self.translations.get(f"{clean_type}_title", "").format(days=days)
        description = self.translations.get(f"{clean_type}_description", "").format(days=days)

        if update_tracker:
            next_update_str = update_tracker.get_next_update_discord()
            logging.debug("Using update tracker timestamp: %s", next_update_str)
        else:
            update_days = self.config.get("UPDATE_DAYS", 1)
            next_update = datetime.now() + timedelta(days=update_days)
            next_update_str = f"<t:{int(next_update.timestamp())}:R>"
            logging.debug("Using fallback timestamp: %s", next_update_str)

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

    async def post_graphs(self, 
                         channel: discord.TextChannel, 
                         graph_files: List[Tuple[str, str]], 
                         update_tracker: Optional['UpdateTracker'] = None):
        """Post graphs to Discord channel with embeds.
        
        Args:
            channel: Discord channel to post to
            graph_files: List of (graph_type, file_path) tuples
            update_tracker: Optional UpdateTracker for timestamps
            
        Raises:
            DiscordError: If posting to Discord fails
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
                        file = discord.File(
                            io.BytesIO(content), 
                            filename=os.path.basename(file_path)
                        )
                        embed.set_image(url=f"attachment://{os.path.basename(file_path)}")
                        await channel.send(embed=embed, file=file)

                    logging.info(
                        self.translations["log_posted_message"].format(
                            filename=os.path.basename(file_path)
                        )
                    )

                except discord.Forbidden as e:
                    raise DiscordError("Missing permissions to post messages") from e
                except discord.HTTPException as e:
                    raise DiscordError(f"Failed to send message: {str(e)}") from e
                except IOError as e:
                    raise DiscordError(f"Failed to read graph file: {str(e)}") from e

        except Exception as e:
            logging.error("Critical error in post_graphs: %s", str(e))
            raise DiscordError("Failed to post graphs to Discord") from e
