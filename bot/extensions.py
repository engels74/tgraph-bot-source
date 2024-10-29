# bot/extensions.py

"""
Extension management utilities for TGraph Bot.
Handles loading, unloading, and reloading of command extensions.
"""

import logging
import pathlib
from typing import List
from discord.ext import commands

def get_extension_paths() -> List[str]:
    """
    Get a list of all extension paths in the commands directory.

    This function scans the commands directory for all available
    extension modules and returns their paths in dot notation.

    Returns:
        List[str]: List of extension paths in dot notation.
    """
    
    Returns
    -------
    List[str]
        List of extension paths in dot notation (e.g., 'bot.commands.about')
    """
    commands_dir = pathlib.Path(__file__).parent / "commands"
    extension_paths = []
    
    for file in commands_dir.rglob("*.py"):
        if file.stem.startswith("_"):
            continue
            
        # Convert path to module notation
        relative_path = file.relative_to(pathlib.Path(__file__).parent.parent)
        extension_path = ".".join(relative_path.with_suffix("").parts)
        extension_paths.append(extension_path)
        
    return extension_paths

async def load_extensions(bot: commands.Bot) -> None:
    """Load all command extensions.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance to load extensions into.
    """
    logging.info(bot.translations["log_loading_bot_commands"])
    
    for extension_path in get_extension_paths():
        try:
            await bot.load_extension(extension_path)
            logging.info(
                bot.translations["log_registering_command"].format(
                    command_name=extension_path.split(".")[-1]
                )
            )
        except Exception as e:
            logging.error(
                f"Failed to load extension {extension_path}: {str(e)}"
            )
            
    logging.info(bot.translations["log_bot_commands_loaded"])

async def reload_extensions(bot: commands.Bot) -> None:
    """Reload all command extensions.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance to reload extensions in.
    """
    for extension_path in get_extension_paths():
        try:
            await bot.reload_extension(extension_path)
            logging.info(f"Reloaded extension: {extension_path}")
        except Exception as e:
            logging.error(
                f"Failed to reload extension {extension_path}: {str(e)}"
            )

async def unload_extensions(bot: commands.Bot) -> None:
    """Unload all command extensions.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance to unload extensions from.
    """
    for extension_path in get_extension_paths():
        try:
            await bot.unload_extension(extension_path)
            logging.info(f"Unloaded extension: {extension_path}")
        except Exception as e:
            logging.error(
                f"Failed to unload extension {extension_path}: {str(e)}"
            )
