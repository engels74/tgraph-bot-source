"""
Extension management for TGraph Bot.

This module contains utility functions for managing (loading, unloading, reloading)
the bot's command extensions (Cogs).
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord.ext import commands

logger = logging.getLogger(__name__)


async def load_extensions(bot: "commands.Bot") -> None:
    """
    Load all command extensions for the bot.
    
    Args:
        bot: The Discord bot instance
    """
    extensions = [
        "bot.commands.about",
        "bot.commands.config", 
        "bot.commands.my_stats",
        "bot.commands.update_graphs",
        "bot.commands.uptime",
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            logger.info(f"Loaded extension: {extension}")
        except Exception as e:
            logger.error(f"Failed to load extension {extension}: {e}")


async def unload_extensions(bot: "commands.Bot") -> None:
    """
    Unload all command extensions from the bot.
    
    Args:
        bot: The Discord bot instance
    """
    extensions = [
        "bot.commands.about",
        "bot.commands.config",
        "bot.commands.my_stats", 
        "bot.commands.update_graphs",
        "bot.commands.uptime",
    ]
    
    for extension in extensions:
        try:
            await bot.unload_extension(extension)
            logger.info(f"Unloaded extension: {extension}")
        except Exception as e:
            logger.error(f"Failed to unload extension {extension}: {e}")


async def reload_extension(bot: "commands.Bot", extension_name: str) -> bool:
    """
    Reload a specific extension.
    
    Args:
        bot: The Discord bot instance
        extension_name: Name of the extension to reload
        
    Returns:
        True if successful, False otherwise
    """
    try:
        await bot.reload_extension(extension_name)
        logger.info(f"Reloaded extension: {extension_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to reload extension {extension_name}: {e}")
        return False
