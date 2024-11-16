# bot/extensions.py

"""
Extension management utilities for TGraph Bot.
Handles loading, unloading, and reloading of command extensions.
"""

from discord.ext import commands
from typing import List, Tuple, Callable
import logging
import pathlib

def get_extension_paths() -> List[str]:
    """Get a list of all extension paths in the commands directory.
    
    Returns
    -------
    List[str]
        List of extension paths in dot notation (e.g., 'bot.commands.about').
        Returns an empty list if the commands directory cannot be found or 
        if there is an error scanning the directory.
    """
    commands_dir = pathlib.Path(__file__).parent / "commands"
    if not commands_dir.exists():
        logging.error("Commands directory not found")
        return []

    extension_paths = []
    
    try:
        for file in commands_dir.rglob("*.py"):
            if not file.is_file() or file.stem.startswith("_"):
                continue
                
            # Convert path to module notation
            relative_path = file.relative_to(pathlib.Path(__file__).parent.parent)
            extension_path = ".".join(relative_path.with_suffix("").parts)
            extension_paths.append(extension_path)
    except Exception as e:
        logging.error(f"Error scanning commands directory: {e}")
        return []
        
    return extension_paths

async def _process_extension_operation(
    bot: commands.Bot,
    operation: str,
    operation_func: Callable
) -> Tuple[int, int]:
    """
    Process extension operations (load/unload/reload) with consistent error handling.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance
    operation : str
        The type of operation being performed ('load', 'unload', or 'reload')
    operation_func : Callable
        The function to perform the operation
    
    Returns
    -------
    Tuple[int, int]
        Tuple containing (success_count, failure_count)
        
    Raises
    ------
    ValueError
        If bot instance is None or if operation is not valid
    """
    if not bot:
        raise ValueError("Bot instance cannot be None")

    # Validate operation parameter
    valid_operations = {"load", "reload", "unload"}
    if operation not in valid_operations:
        raise ValueError(f"Invalid operation: {operation}. Must be one of: {', '.join(valid_operations)}")

    # Use proper translation keys directly based on operation
    if operation == "load":
        logging.info(bot.translations["log_loading_bot_commands"])
    elif operation == "reload":
        logging.info(bot.translations["log_reloading_bot_commands"])
    else:  # unload
        logging.info(bot.translations["log_unloading_bot_commands"])

    success_count = failure_count = 0
    extension_paths = get_extension_paths()
    
    for extension_path in extension_paths:
        try:
            await operation_func(extension_path)
            # Use proper translation key for the operation
            if operation == "load":
                log_key = "log_registering_command"
            elif operation == "reload":
                log_key = "log_reloading_command"
            else:  # unload
                log_key = "log_unloading_command"
                
            logging.info(
                bot.translations[log_key].format(
                    command_name=extension_path.split(".")[-1]
                )
            )
            success_count += 1
        except commands.ExtensionNotFound:
            logging.error(f"Extension not found: {extension_path}")
            failure_count += 1
        except commands.ExtensionNotLoaded:
            logging.error(f"Extension not loaded: {extension_path}")
            failure_count += 1
        except commands.ExtensionAlreadyLoaded:
            logging.warning(f"Extension already loaded: {extension_path}")
            success_count += 1  # Count as success since it's available
        except commands.NoEntryPointError:
            logging.error(f"No entry point found in extension: {extension_path}")
            failure_count += 1
        except commands.ExtensionFailed as e:
            logging.error(f"Extension failed during {operation} of {extension_path}: {e}")
            failure_count += 1
        except Exception as e:
            logging.error(
                f"Failed to {operation} extension {extension_path}: {str(e)}"
            )
            failure_count += 1
    
    # Use proper translation key for completion
    if operation == "load":
        logging.info(bot.translations["log_bot_commands_loaded"])
    elif operation == "reload":
        logging.info(bot.translations["log_bot_commands_reloaded"])
    else:  # unload
        logging.info(bot.translations["log_bot_commands_unloaded"])

    return success_count, failure_count

async def load_extensions(bot: commands.Bot) -> Tuple[int, int]:
    """Load all command extensions.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance to load extensions into.
    
    Returns
    -------
    Tuple[int, int]
        Tuple containing (success_count, failure_count)
    """
    return await _process_extension_operation(bot, "load", bot.load_extension)

async def reload_extensions(bot: commands.Bot) -> Tuple[int, int]:
    """Reload all command extensions.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance to reload extensions in.
    
    Returns
    -------
    Tuple[int, int]
        Tuple containing (success_count, failure_count)
    """
    return await _process_extension_operation(bot, "reload", bot.reload_extension)

async def unload_extensions(bot: commands.Bot) -> Tuple[int, int]:
    """Unload all command extensions.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance to unload extensions from.
    
    Returns
    -------
    Tuple[int, int]
        Tuple containing (success_count, failure_count)
    """
    return await _process_extension_operation(bot, "unload", bot.unload_extension)
