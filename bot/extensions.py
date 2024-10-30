# bot/extensions.py

"""
Extension management utilities for TGraph Bot.
Handles loading, unloading, and reloading of command extensions.
"""

import logging
import pathlib
from typing import List, Tuple
from discord.ext import commands

def get_extension_paths() -> List[str]:
    """Get a list of all extension paths in the commands directory.
    
    Returns
    -------
    List[str]
        List of extension paths in dot notation (e.g., 'bot.commands.about')
    """
    commands_dir = pathlib.Path(__file__).parent / "commands"
    if not commands_dir.exists():
        logging.error("Commands directory not found")
        return []

    extension_paths = []
    
    try:
        for file in commands_dir.rglob("*.py"):
            if not file.is_file():
                continue
            if file.stem.startswith("_"):
                continue
                
            # Convert path to module notation
            relative_path = file.relative_to(pathlib.Path(__file__).parent.parent)
            extension_path = ".".join(relative_path.with_suffix("").parts)
            extension_paths.append(extension_path)
    except Exception as e:
        logging.error(f"Error scanning commands directory: {e}")
        return []
        
    return extension_paths

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
    logging.info(bot.translations["log_loading_bot_commands"])
    success_count = failure_count = 0
    
    for extension_path in get_extension_paths():
        try:
            await bot.load_extension(extension_path)
            logging.info(
                bot.translations["log_registering_command"].format(
                    command_name=extension_path.split(".")[-1]
                )
            )
            success_count += 1
        except commands.ExtensionNotFound:
            logging.error(f"Extension not found: {extension_path}")
            failure_count += 1
        except commands.ExtensionAlreadyLoaded:
            logging.warning(f"Extension already loaded: {extension_path}")
            success_count += 1
        except Exception as e:
            logging.error(
                f"Failed to load extension {extension_path}: {str(e)}"
            )
            failure_count += 1
            
    logging.info(bot.translations["log_bot_commands_loaded"])
    return success_count, failure_count

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
    success_count = failure_count = 0
    logging.info(bot.translations["log_reloading_bot_commands"])
    
    for extension_path in get_extension_paths():
        try:
            await bot.reload_extension(extension_path)
            logging.info(
                bot.translations["log_reloading_command"].format(
                    command_name=extension_path.split(".")[-1]
                )
            )
            success_count += 1
        except commands.ExtensionNotFound:
            logging.error(f"Extension not found: {extension_path}")
            failure_count += 1
        except Exception as e:
            logging.error(
                f"Failed to reload extension {extension_path}: {str(e)}"
            )
            failure_count += 1
    
    logging.info(bot.translations["log_bot_commands_reloaded"])
    return success_count, failure_count

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
    success_count = failure_count = 0
    logging.info(bot.translations["log_unloading_bot_commands"])
    
    for extension_path in get_extension_paths():
        try:
            await bot.unload_extension(extension_path)
            logging.info(
                bot.translations["log_unloading_command"].format(
                    command_name=extension_path.split(".")[-1]
                )
            )
            success_count += 1
        except Exception as e:
            logging.error(
                f"Failed to unload extension {extension_path}: {str(e)}"
            )
            failure_count += 1
    
    logging.info(bot.translations["log_bot_commands_unloaded"])
    return success_count, failure_count
