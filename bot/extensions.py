"""
Extension management for TGraph Bot.

This module contains utility functions for managing (loading, unloading, reloading)
the bot's command extensions (Cogs) with modern discord.py patterns and robust
error handling.
"""

import logging
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from discord.ext import commands

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ExtensionStatus(NamedTuple):
    """Status information for an extension."""

    name: str
    loaded: bool
    error: str | None = None


class ExtensionManager:
    """
    Modern extension manager for Discord bot Cogs.

    Provides dynamic extension discovery, robust error handling,
    and comprehensive extension lifecycle management.
    """

    def __init__(self) -> None:
        """Initialize the extension manager."""
        self._loaded_extensions: set[str] = set()
        self._failed_extensions: dict[str, str] = {}

    def discover_extensions(self) -> list[str]:
        """
        Dynamically discover all available command extensions.

        Returns:
            List of extension module names
        """
        extensions: list[str] = []
        commands_path = Path(__file__).parent / "commands"

        if not commands_path.exists():
            logger.warning("Commands directory not found")
            return extensions

        # Walk through the commands directory
        for module_info in pkgutil.iter_modules([str(commands_path)]):
            if not module_info.name.startswith(
                "_"
            ):  # Skip __init__.py and private modules
                extension_name = f"bot.commands.{module_info.name}"
                extensions.append(extension_name)

        logger.debug(f"Discovered {len(extensions)} extensions: {extensions}")
        return extensions

    async def load_extension_safe(
        self, bot: commands.Bot, extension_name: str
    ) -> ExtensionStatus:
        """
        Safely load a single extension with detailed error handling.

        Args:
            bot: The Discord bot instance
            extension_name: Name of the extension to load

        Returns:
            ExtensionStatus with load result
        """
        try:
            await bot.load_extension(extension_name)
            self._loaded_extensions.add(extension_name)
            _ = self._failed_extensions.pop(
                extension_name, None
            )  # Clear any previous errors
            logger.info(f"Successfully loaded extension: {extension_name}")
            return ExtensionStatus(extension_name, True)

        except commands.ExtensionAlreadyLoaded:
            logger.warning(f"Extension already loaded: {extension_name}")
            self._loaded_extensions.add(extension_name)
            return ExtensionStatus(extension_name, True)

        except commands.ExtensionNotFound as e:
            error_msg = f"Extension not found: {e}"
            logger.error(error_msg)
            self._failed_extensions[extension_name] = error_msg
            return ExtensionStatus(extension_name, False, error_msg)

        except commands.NoEntryPointError as e:
            error_msg = f"No setup function found: {e}"
            logger.error(error_msg)
            self._failed_extensions[extension_name] = error_msg
            return ExtensionStatus(extension_name, False, error_msg)

        except commands.ExtensionFailed as e:
            error_msg = f"Extension setup failed: {e}"
            logger.error(error_msg)
            self._failed_extensions[extension_name] = error_msg
            return ExtensionStatus(extension_name, False, error_msg)

        except Exception as e:
            error_msg = f"Unexpected error loading extension: {e}"
            logger.exception(error_msg)
            self._failed_extensions[extension_name] = error_msg
            return ExtensionStatus(extension_name, False, error_msg)

    def mark_extension_unloaded(self, extension_name: str) -> None:
        """Mark an extension as unloaded."""
        self._loaded_extensions.discard(extension_name)

    def mark_extension_loaded(self, extension_name: str) -> None:
        """Mark an extension as loaded and clear any errors."""
        self._loaded_extensions.add(extension_name)
        _ = self._failed_extensions.pop(extension_name, None)

    def get_loaded_extensions(self) -> list[str]:
        """Get list of currently loaded extensions."""
        return list(self._loaded_extensions)

    def get_failed_extensions(self) -> dict[str, str]:
        """Get dictionary of failed extensions and their error messages."""
        return dict(self._failed_extensions)

    def is_extension_loaded(self, extension_name: str) -> bool:
        """Check if an extension is currently loaded."""
        return extension_name in self._loaded_extensions

    def get_extension_error(self, extension_name: str) -> str | None:
        """Get error message for a failed extension."""
        return self._failed_extensions.get(extension_name)


# Global extension manager instance
_extension_manager = ExtensionManager()


async def load_extensions(bot: commands.Bot) -> list[ExtensionStatus]:
    """
    Load all command extensions for the bot with dynamic discovery.

    Args:
        bot: The Discord bot instance

    Returns:
        List of ExtensionStatus for each extension
    """
    extensions = _extension_manager.discover_extensions()
    results: list[ExtensionStatus] = []

    logger.info(f"Loading {len(extensions)} extensions...")

    for extension in extensions:
        status = await _extension_manager.load_extension_safe(bot, extension)
        results.append(status)

    loaded_count = sum(1 for status in results if status.loaded)
    failed_count = len(results) - loaded_count

    logger.info(
        f"Extension loading complete: {loaded_count} loaded, {failed_count} failed"
    )

    if failed_count > 0:
        failed_names = [status.name for status in results if not status.loaded]
        logger.warning(f"Failed extensions: {failed_names}")

    return results


async def unload_extensions(bot: commands.Bot) -> list[ExtensionStatus]:
    """
    Unload all command extensions from the bot.

    Args:
        bot: The Discord bot instance

    Returns:
        List of ExtensionStatus for each extension
    """
    extensions = _extension_manager.discover_extensions()
    results: list[ExtensionStatus] = []

    logger.info(f"Unloading {len(extensions)} extensions...")

    for extension in extensions:
        status = await unload_extension_safe(bot, extension)
        results.append(status)

    unloaded_count = sum(1 for status in results if status.loaded)
    failed_count = len(results) - unloaded_count

    logger.info(
        f"Extension unloading complete: {unloaded_count} unloaded, {failed_count} failed"
    )

    return results


async def unload_extension_safe(
    bot: commands.Bot, extension_name: str
) -> ExtensionStatus:
    """
    Safely unload a single extension with detailed error handling.

    Args:
        bot: The Discord bot instance
        extension_name: Name of the extension to unload

    Returns:
        ExtensionStatus with unload result
    """
    try:
        await bot.unload_extension(extension_name)
        _extension_manager.mark_extension_unloaded(extension_name)
        logger.info(f"Successfully unloaded extension: {extension_name}")
        return ExtensionStatus(extension_name, True)

    except commands.ExtensionNotLoaded:
        logger.warning(f"Extension not loaded: {extension_name}")
        return ExtensionStatus(
            extension_name, True
        )  # Consider it successful since it's not loaded

    except commands.ExtensionNotFound as e:
        error_msg = f"Extension not found: {e}"
        logger.error(error_msg)
        return ExtensionStatus(extension_name, False, error_msg)

    except Exception as e:
        error_msg = f"Unexpected error unloading extension: {e}"
        logger.exception(error_msg)
        return ExtensionStatus(extension_name, False, error_msg)


async def reload_extension(bot: commands.Bot, extension_name: str) -> ExtensionStatus:
    """
    Reload a specific extension with detailed error handling.

    Args:
        bot: The Discord bot instance
        extension_name: Name of the extension to reload

    Returns:
        ExtensionStatus with reload result
    """
    try:
        await bot.reload_extension(extension_name)
        _extension_manager.mark_extension_loaded(extension_name)
        logger.info(f"Successfully reloaded extension: {extension_name}")
        return ExtensionStatus(extension_name, True)

    except commands.ExtensionNotLoaded as e:
        error_msg = f"Extension not loaded, cannot reload: {e}"
        logger.error(error_msg)
        return ExtensionStatus(extension_name, False, error_msg)

    except commands.ExtensionNotFound as e:
        error_msg = f"Extension not found: {e}"
        logger.error(error_msg)
        return ExtensionStatus(extension_name, False, error_msg)

    except commands.NoEntryPointError as e:
        error_msg = f"No setup function found: {e}"
        logger.error(error_msg)
        return ExtensionStatus(extension_name, False, error_msg)

    except commands.ExtensionFailed as e:
        error_msg = f"Extension reload failed: {e}"
        logger.error(error_msg)
        return ExtensionStatus(extension_name, False, error_msg)

    except Exception as e:
        error_msg = f"Unexpected error reloading extension: {e}"
        logger.exception(error_msg)
        return ExtensionStatus(extension_name, False, error_msg)


async def reload_all_extensions(bot: commands.Bot) -> list[ExtensionStatus]:
    """
    Reload all currently loaded extensions.

    Args:
        bot: The Discord bot instance

    Returns:
        List of ExtensionStatus for each extension
    """
    loaded_extensions = _extension_manager.get_loaded_extensions()
    results: list[ExtensionStatus] = []

    logger.info(f"Reloading {len(loaded_extensions)} extensions...")

    for extension in loaded_extensions:
        status = await reload_extension(bot, extension)
        results.append(status)

    reloaded_count = sum(1 for status in results if status.loaded)
    failed_count = len(results) - reloaded_count

    logger.info(
        f"Extension reloading complete: {reloaded_count} reloaded, {failed_count} failed"
    )

    return results


def get_extension_info() -> dict[str, dict[str, str | bool]]:
    """
    Get information about all extensions.

    Returns:
        Dictionary with extension information
    """
    info: dict[str, dict[str, str | bool]] = {}

    # Get all discovered extensions
    all_extensions = _extension_manager.discover_extensions()

    for extension in all_extensions:
        is_loaded = _extension_manager.is_extension_loaded(extension)
        error = _extension_manager.get_extension_error(extension)

        info[extension] = {
            "loaded": is_loaded,
            "error": error or "",
            "status": "loaded" if is_loaded else ("failed" if error else "not_loaded"),
        }

    return info


def get_loaded_extensions() -> list[str]:
    """
    Get list of currently loaded extensions.

    Returns:
        List of loaded extension names
    """
    return _extension_manager.get_loaded_extensions()


def get_failed_extensions() -> dict[str, str]:
    """
    Get dictionary of failed extensions and their error messages.

    Returns:
        Dictionary mapping extension names to error messages
    """
    return _extension_manager.get_failed_extensions()
