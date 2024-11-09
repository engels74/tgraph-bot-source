# graphs/user_graph_manager.py

from .graph_modules.data_fetcher import DataFetcher
from .graph_modules.graph_factory import GraphFactory
from .graph_modules.utils import ensure_folder_exists
from config.modules.sanitizer import sanitize_user_id, InvalidUserIdError
from datetime import datetime
from typing import Dict, Any, List, Optional
import asyncio
import logging
import os

# Define graphs that should be excluded for individual users
EXCLUDED_USER_GRAPHS = {"top_10_users"}

class UserGraphManagerError(Exception):
    """Base exception for UserGraphManager errors."""
    pass

class UserGraphManager:
    def __init__(self, config: Dict[str, Any], translations: Dict[str, str], img_folder: str):
        self.config = config
        self.translations = translations
        self.img_folder = img_folder
        self.graph_factory = GraphFactory(config, translations, img_folder)
        self.data_fetcher = DataFetcher(config)

    def _sanitize_user_id(self, user_id: Any) -> str:
        """
        Sanitize and validate the user ID.
        
        Args:
            user_id: The user ID to sanitize
            
        Returns:
            str: A sanitized user ID safe for use in filenames and API calls
            
        Raises:
            InvalidUserIdError: If user_id is invalid or cannot be sanitized
        """
        if not user_id:
            raise InvalidUserIdError("User ID cannot be empty")
            
        try:
            return sanitize_user_id(str(user_id))
        except InvalidUserIdError as e:
            logging.error(f"Invalid user ID: {e}")
            raise

    async def generate_user_graphs(self, user_id: Any) -> List[str]:
        """
        Generate graphs for a specific user.
        
        Args:
            user_id: The ID of the user to generate graphs for
            
        Returns:
            A list of file paths for the generated graphs
            
        Raises:
            UserGraphManagerError: If graph generation fails
            InvalidUserIdError: If user_id is invalid
        """
        try:
            # Validate and sanitize user_id early
            safe_user_id = self._sanitize_user_id(user_id)
            
            # Create dated and user-specific folders
            today = datetime.today().strftime("%Y-%m-%d")
            user_folder = os.path.join(self.img_folder, today, f"user_{safe_user_id}")
            ensure_folder_exists(user_folder)

            graph_files = []
            
            # Fetch all graph data with error handling
            try:
                graph_data = await self.data_fetcher.fetch_all_graph_data(safe_user_id)
            except Exception as e:
                error_msg = self.translations.get(
                    "error_fetch_user_data",
                    "Failed to fetch data for user {user_id}: {error}"
                ).format(user_id=safe_user_id, error=str(e))
                logging.error(error_msg)
                raise UserGraphManagerError("Failed to fetch user data") from e

            if not graph_data:
                error_msg = self.translations.get(
                    "error_fetch_user_data",
                    "Failed to fetch data for user {user_id}"
                ).format(user_id=safe_user_id)
                logging.error(error_msg)
                raise UserGraphManagerError(error_msg)

            async def generate_graph(graph_type: str, graph_instance: Any) -> Optional[str]:
                """Generate a single graph with error handling."""
                if graph_type in EXCLUDED_USER_GRAPHS:
                    return None
                    
                try:
                    # Set the data in the graph instance
                    graph_instance.data = graph_data.get(graph_type)
                    if graph_instance.data is None:
                        logging.warning(f"No data available for {graph_type}")
                        return None
                        
                    # Generate the graph
                    file_path = await graph_instance.generate(self.data_fetcher, safe_user_id)
                    if file_path:
                        graph_filename = os.path.basename(file_path)
                        logging.debug(f"Generated graph: {graph_filename}")
                        return file_path
                        
                except Exception as e:
                    error_msg = self.translations.get(
                        "error_generating_user_graph",
                        "Error generating {graph_type} for user {user_id}: {error}"
                    ).format(graph_type=graph_type, user_id=safe_user_id, error=str(e))
                    logging.error(error_msg)
                    raise UserGraphManagerError(error_msg) from e
                    
                return None

            # Generate all graphs concurrently with timeout
            try:
                async with asyncio.timeout(30):  # Add timeout for graph generation
                    tasks = [
                        generate_graph(graph_type, graph_instance)
                        for graph_type, graph_instance in self.graph_factory.create_all_graphs().items()
                        if graph_type not in EXCLUDED_USER_GRAPHS
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results and handle any exceptions
                    for result in results:
                        if isinstance(result, Exception):
                            logging.error(f"Error generating graph: {result}")
                        elif result:
                            graph_files.append(result)
                            
            except asyncio.TimeoutError as e:
                error_msg = f"Graph generation timed out for user {safe_user_id}"
                logging.error(error_msg)
                raise UserGraphManagerError(error_msg) from e

            if graph_files:
                logging.info(self.translations.get(
                    "log_generated_graph_files",
                    "Generated {count} graph files"
                ).format(count=len(graph_files)))

                logging.info(self.translations.get(
                    "log_generated_user_graphs",
                    "Generated graphs for user ID: {user_id}"
                ).format(user_id=safe_user_id))

            return graph_files

        except InvalidUserIdError:
            raise
        except UserGraphManagerError:
            raise
        except Exception as e:
            error_msg = self.translations.get(
                "error_user_graphs_generation",
                "Error generating graphs for user {user_id}: {error}"
            ).format(user_id=safe_user_id if 'safe_user_id' in locals() else user_id, error=str(e))
            logging.error(error_msg)
            raise UserGraphManagerError(error_msg) from e

async def generate_user_graphs(
    user_id: Any,
    config: Dict[str, Any],
    translations: Dict[str, str],
    img_folder: str
) -> List[str]:
    """
    Generate graphs for a specific user using the UserGraphManager.
    
    Args:
        user_id: The ID of the user to generate graphs for
        config: The configuration dictionary
        translations: The translations dictionary
        img_folder: The folder to save the graphs in
        
    Returns:
        A list of file paths for the generated graphs
        
    Raises:
        UserGraphManagerError: If graph generation fails
    """
    try:
        user_graph_manager = UserGraphManager(config, translations, img_folder)
        return await user_graph_manager.generate_user_graphs(user_id)
    except Exception as e:
        logging.error(f"Failed to generate user graphs: {str(e)}")
        raise UserGraphManagerError(f"Failed to generate user graphs: {str(e)}") from e
