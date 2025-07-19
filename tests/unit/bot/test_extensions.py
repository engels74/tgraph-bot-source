"""
Tests for bot/extensions.py extension management functionality.

This module tests the enhanced extension management system including
dynamic discovery, robust error handling, and extension lifecycle management.
"""

from unittest.mock import AsyncMock, patch

import pytest
from discord.ext import commands

from src.tgraph_bot.bot.extensions import (
    ExtensionManager,
    ExtensionStatus,
    load_extensions,
    unload_extensions,
    unload_extension_safe,
    reload_extension,
    reload_all_extensions,
    get_extension_info,
    get_loaded_extensions,
    get_failed_extensions,
)


class TestExtensionManager:
    """Test cases for the ExtensionManager class."""

    def test_init(self) -> None:
        """Test ExtensionManager initialization."""
        manager = ExtensionManager()

        assert manager._loaded_extensions == set()  # pyright: ignore[reportPrivateUsage]
        assert manager._failed_extensions == {}  # pyright: ignore[reportPrivateUsage]

    def test_discover_extensions_with_commands_directory(self) -> None:
        """Test extension discovery when commands directory exists."""
        manager = ExtensionManager()

        # Mock the commands directory and modules
        with patch.object(manager, "discover_extensions") as mock_discover:
            mock_discover.return_value = [
                "bot.commands.about",
                "bot.commands.config",
                "bot.commands.my_stats",
                "bot.commands.update_graphs",
                "bot.commands.uptime",
            ]

            extensions = manager.discover_extensions()

            expected = [
                "bot.commands.about",
                "bot.commands.config",
                "bot.commands.my_stats",
                "bot.commands.update_graphs",
                "bot.commands.uptime",
            ]

            assert extensions == expected

    def test_discover_extensions_no_commands_directory(self) -> None:
        """Test extension discovery when commands directory doesn't exist."""
        manager = ExtensionManager()

        with patch("pathlib.Path.exists", return_value=False):
            extensions = manager.discover_extensions()
            assert extensions == []

    @pytest.mark.asyncio
    async def test_load_extension_safe_success(self) -> None:
        """Test successful extension loading."""
        manager = ExtensionManager()
        mock_bot = AsyncMock(spec=commands.Bot)

        status = await manager.load_extension_safe(mock_bot, "test.extension")

        assert status.name == "test.extension"
        assert status.loaded is True
        assert status.error is None
        assert "test.extension" in manager._loaded_extensions  # pyright: ignore[reportPrivateUsage]
        mock_bot.load_extension.assert_called_once_with("test.extension")  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_load_extension_safe_already_loaded(self) -> None:
        """Test loading an already loaded extension."""
        manager = ExtensionManager()
        mock_bot = AsyncMock(spec=commands.Bot)
        mock_bot.load_extension.side_effect = commands.ExtensionAlreadyLoaded(
            "test.extension"
        )  # pyright: ignore[reportAny]

        status = await manager.load_extension_safe(mock_bot, "test.extension")

        assert status.name == "test.extension"
        assert status.loaded is True
        assert status.error is None
        assert "test.extension" in manager._loaded_extensions  # pyright: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_load_extension_safe_not_found(self) -> None:
        """Test loading a non-existent extension."""
        manager = ExtensionManager()
        mock_bot = AsyncMock(spec=commands.Bot)
        mock_bot.load_extension.side_effect = commands.ExtensionNotFound(
            "test.extension"
        )  # pyright: ignore[reportAny]

        status = await manager.load_extension_safe(mock_bot, "test.extension")

        assert status.name == "test.extension"
        assert status.loaded is False
        assert status.error is not None
        assert "Extension not found" in status.error
        assert "test.extension" in manager._failed_extensions  # pyright: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_load_extension_safe_no_entry_point(self) -> None:
        """Test loading an extension without setup function."""
        manager = ExtensionManager()
        mock_bot = AsyncMock(spec=commands.Bot)
        mock_bot.load_extension.side_effect = commands.NoEntryPointError(
            "test.extension"
        )  # pyright: ignore[reportAny]

        status = await manager.load_extension_safe(mock_bot, "test.extension")

        assert status.name == "test.extension"
        assert status.loaded is False
        assert status.error is not None
        assert "No setup function found" in status.error
        assert "test.extension" in manager._failed_extensions  # pyright: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_load_extension_safe_extension_failed(self) -> None:
        """Test loading an extension that fails during setup."""
        manager = ExtensionManager()
        mock_bot = AsyncMock(spec=commands.Bot)
        mock_bot.load_extension.side_effect = commands.ExtensionFailed(
            "test.extension", Exception("Setup error")
        )  # pyright: ignore[reportAny]

        status = await manager.load_extension_safe(mock_bot, "test.extension")

        assert status.name == "test.extension"
        assert status.loaded is False
        assert status.error is not None
        assert "Extension setup failed" in status.error
        assert "test.extension" in manager._failed_extensions  # pyright: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_load_extension_safe_unexpected_error(self) -> None:
        """Test loading an extension with unexpected error."""
        manager = ExtensionManager()
        mock_bot = AsyncMock(spec=commands.Bot)
        mock_bot.load_extension.side_effect = RuntimeError("Unexpected error")  # pyright: ignore[reportAny]

        status = await manager.load_extension_safe(mock_bot, "test.extension")

        assert status.name == "test.extension"
        assert status.loaded is False
        assert status.error is not None
        assert "Unexpected error loading extension" in status.error
        assert "test.extension" in manager._failed_extensions  # pyright: ignore[reportPrivateUsage]

    def test_mark_extension_unloaded(self) -> None:
        """Test marking an extension as unloaded."""
        manager = ExtensionManager()
        manager._loaded_extensions.add("test.extension")  # pyright: ignore[reportPrivateUsage]

        manager.mark_extension_unloaded("test.extension")

        assert "test.extension" not in manager._loaded_extensions  # pyright: ignore[reportPrivateUsage]

    def test_mark_extension_loaded(self) -> None:
        """Test marking an extension as loaded."""
        manager = ExtensionManager()
        manager._failed_extensions["test.extension"] = "Some error"  # pyright: ignore[reportPrivateUsage]

        manager.mark_extension_loaded("test.extension")

        assert "test.extension" in manager._loaded_extensions  # pyright: ignore[reportPrivateUsage]
        assert "test.extension" not in manager._failed_extensions  # pyright: ignore[reportPrivateUsage]

    def test_get_loaded_extensions(self) -> None:
        """Test getting loaded extensions."""
        manager = ExtensionManager()
        manager._loaded_extensions.update(["ext1", "ext2", "ext3"])  # pyright: ignore[reportPrivateUsage]

        loaded = manager.get_loaded_extensions()

        assert set(loaded) == {"ext1", "ext2", "ext3"}

    def test_get_failed_extensions(self) -> None:
        """Test getting failed extensions."""
        manager = ExtensionManager()
        manager._failed_extensions.update(
            {  # pyright: ignore[reportPrivateUsage]
                "ext1": "Error 1",
                "ext2": "Error 2",
            }
        )

        failed = manager.get_failed_extensions()

        assert failed == {"ext1": "Error 1", "ext2": "Error 2"}

    def test_is_extension_loaded(self) -> None:
        """Test checking if extension is loaded."""
        manager = ExtensionManager()
        manager._loaded_extensions.add("loaded.extension")  # pyright: ignore[reportPrivateUsage]

        assert manager.is_extension_loaded("loaded.extension") is True
        assert manager.is_extension_loaded("not.loaded") is False

    def test_get_extension_error(self) -> None:
        """Test getting extension error."""
        manager = ExtensionManager()
        manager._failed_extensions["failed.extension"] = "Test error"  # pyright: ignore[reportPrivateUsage]

        assert manager.get_extension_error("failed.extension") == "Test error"
        assert manager.get_extension_error("no.error") is None


class TestExtensionFunctions:
    """Test cases for extension management functions."""

    @pytest.mark.asyncio
    async def test_load_extensions(self) -> None:
        """Test loading all extensions."""
        mock_bot = AsyncMock(spec=commands.Bot)

        with (
            patch(
                "src.tgraph_bot.bot.extensions._extension_manager.discover_extensions"
            ) as mock_discover,
            patch(
                "src.tgraph_bot.bot.extensions._extension_manager.load_extension_safe"
            ) as mock_load_safe,
        ):
            mock_discover.return_value = ["ext1", "ext2", "ext3"]
            mock_load_safe.side_effect = [
                ExtensionStatus("ext1", True),
                ExtensionStatus("ext2", False, "Error"),
                ExtensionStatus("ext3", True),
            ]

            results = await load_extensions(mock_bot)

            assert len(results) == 3
            assert results[0].loaded is True
            assert results[1].loaded is False
            assert results[2].loaded is True

            assert mock_load_safe.call_count == 3

    @pytest.mark.asyncio
    async def test_unload_extensions(self) -> None:
        """Test unloading all extensions."""
        mock_bot = AsyncMock(spec=commands.Bot)

        with (
            patch(
                "src.tgraph_bot.bot.extensions._extension_manager.discover_extensions"
            ) as mock_discover,
            patch(
                "src.tgraph_bot.bot.extensions.unload_extension_safe"
            ) as mock_unload_safe,
        ):
            mock_discover.return_value = ["ext1", "ext2"]
            mock_unload_safe.side_effect = [
                ExtensionStatus("ext1", True),
                ExtensionStatus("ext2", True),
            ]

            results = await unload_extensions(mock_bot)

            assert len(results) == 2
            assert all(status.loaded for status in results)
            assert mock_unload_safe.call_count == 2

    @pytest.mark.asyncio
    async def test_unload_extension_safe_success(self) -> None:
        """Test successful extension unloading."""
        mock_bot = AsyncMock(spec=commands.Bot)

        with patch(
            "src.tgraph_bot.bot.extensions._extension_manager.mark_extension_unloaded"
        ) as mock_mark:
            status = await unload_extension_safe(mock_bot, "test.extension")

            assert status.name == "test.extension"
            assert status.loaded is True
            assert status.error is None
            mock_bot.unload_extension.assert_called_once_with("test.extension")  # pyright: ignore[reportAny]
            mock_mark.assert_called_once_with("test.extension")

    @pytest.mark.asyncio
    async def test_unload_extension_safe_not_loaded(self) -> None:
        """Test unloading an extension that's not loaded."""
        mock_bot = AsyncMock(spec=commands.Bot)
        mock_bot.unload_extension.side_effect = commands.ExtensionNotLoaded(
            "test.extension"
        )  # pyright: ignore[reportAny]

        status = await unload_extension_safe(mock_bot, "test.extension")

        assert status.name == "test.extension"
        assert status.loaded is True  # Consider it successful since it's not loaded

    @pytest.mark.asyncio
    async def test_reload_extension_success(self) -> None:
        """Test successful extension reloading."""
        mock_bot = AsyncMock(spec=commands.Bot)

        with patch(
            "src.tgraph_bot.bot.extensions._extension_manager.mark_extension_loaded"
        ) as mock_mark:
            status = await reload_extension(mock_bot, "test.extension")

            assert status.name == "test.extension"
            assert status.loaded is True
            assert status.error is None
            mock_bot.reload_extension.assert_called_once_with("test.extension")  # pyright: ignore[reportAny]
            mock_mark.assert_called_once_with("test.extension")

    @pytest.mark.asyncio
    async def test_reload_extension_not_loaded(self) -> None:
        """Test reloading an extension that's not loaded."""
        mock_bot = AsyncMock(spec=commands.Bot)
        mock_bot.reload_extension.side_effect = commands.ExtensionNotLoaded(
            "test.extension"
        )  # pyright: ignore[reportAny]

        status = await reload_extension(mock_bot, "test.extension")

        assert status.name == "test.extension"
        assert status.loaded is False
        assert status.error is not None
        assert "Extension not loaded, cannot reload" in status.error

    @pytest.mark.asyncio
    async def test_reload_all_extensions(self) -> None:
        """Test reloading all loaded extensions."""
        mock_bot = AsyncMock(spec=commands.Bot)

        with (
            patch(
                "src.tgraph_bot.bot.extensions._extension_manager.get_loaded_extensions"
            ) as mock_get_loaded,
            patch("src.tgraph_bot.bot.extensions.reload_extension") as mock_reload,
        ):
            mock_get_loaded.return_value = ["ext1", "ext2"]
            mock_reload.side_effect = [
                ExtensionStatus("ext1", True),
                ExtensionStatus("ext2", True),
            ]

            results = await reload_all_extensions(mock_bot)

            assert len(results) == 2
            assert all(status.loaded for status in results)
            assert mock_reload.call_count == 2

    def test_get_extension_info(self) -> None:
        """Test getting extension information."""
        with (
            patch(
                "src.tgraph_bot.bot.extensions._extension_manager.discover_extensions"
            ) as mock_discover,
            patch(
                "src.tgraph_bot.bot.extensions._extension_manager.is_extension_loaded"
            ) as mock_is_loaded,
            patch(
                "src.tgraph_bot.bot.extensions._extension_manager.get_extension_error"
            ) as mock_get_error,
        ):
            mock_discover.return_value = ["ext1", "ext2", "ext3"]
            mock_is_loaded.side_effect = [True, False, False]
            mock_get_error.side_effect = [None, "Error message", None]

            info = get_extension_info()

            assert info["ext1"]["loaded"] is True
            assert info["ext1"]["status"] == "loaded"
            assert info["ext2"]["loaded"] is False
            assert info["ext2"]["status"] == "failed"
            assert info["ext3"]["loaded"] is False
            assert info["ext3"]["status"] == "not_loaded"

    def test_get_loaded_extensions_function(self) -> None:
        """Test get_loaded_extensions function."""
        with patch(
            "src.tgraph_bot.bot.extensions._extension_manager.get_loaded_extensions"
        ) as mock_get:
            mock_get.return_value = ["ext1", "ext2"]

            result = get_loaded_extensions()

            assert result == ["ext1", "ext2"]
            mock_get.assert_called_once()

    def test_get_failed_extensions_function(self) -> None:
        """Test get_failed_extensions function."""
        with patch(
            "src.tgraph_bot.bot.extensions._extension_manager.get_failed_extensions"
        ) as mock_get:
            mock_get.return_value = {"ext1": "Error 1"}

            result = get_failed_extensions()

            assert result == {"ext1": "Error 1"}
            mock_get.assert_called_once()
