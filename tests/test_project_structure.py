"""
Test project structure and dependencies for TGraph Bot.

This test module verifies that the project structure is correctly set up
and that all required dependencies are available and importable.
"""

import importlib
from pathlib import Path

import pytest


class TestProjectStructure:
    """Test the basic project structure and setup."""
    
    def test_project_root_exists(self) -> None:
        """Test that the project root directory exists."""
        project_root = Path(".")
        assert project_root.exists()
        assert project_root.is_dir()
    
    def test_bot_module_exists(self) -> None:
        """Test that the bot module directory exists."""
        bot_dir = Path("bot")
        assert bot_dir.exists()
        assert bot_dir.is_dir()
        
        # Check for __init__.py
        init_file = bot_dir / "__init__.py"
        assert init_file.exists()
        assert init_file.is_file()
    
    def test_bot_module_importable(self) -> None:
        """Test that the bot module can be imported."""
        try:
            import bot
            assert hasattr(bot, "__version__")
            assert hasattr(bot, "__author__")
        except ImportError as e:
            pytest.fail(f"Failed to import bot module: {e}")
    
    def test_main_module_exists(self) -> None:
        """Test that main.py exists."""
        main_file = Path("main.py")
        assert main_file.exists()
        assert main_file.is_file()
    
    def test_main_module_importable(self) -> None:
        """Test that main.py can be imported."""
        try:
            import main
            assert hasattr(main, "TGraphBot")
            assert hasattr(main, "main")
        except ImportError as e:
            pytest.fail(f"Failed to import main module: {e}")
    
    def test_extensions_module_exists(self) -> None:
        """Test that bot/extensions.py exists."""
        extensions_file = Path("bot/extensions.py")
        assert extensions_file.exists()
        assert extensions_file.is_file()
    
    def test_extensions_module_importable(self) -> None:
        """Test that bot.extensions can be imported."""
        try:
            from bot import extensions
            assert hasattr(extensions, "load_extensions")
            assert hasattr(extensions, "unload_extensions")
            assert hasattr(extensions, "reload_extension")
        except ImportError as e:
            pytest.fail(f"Failed to import bot.extensions module: {e}")


class TestDependencies:
    """Test that all required dependencies are available."""
    
    @pytest.mark.parametrize("module_name", [
        "discord",
        "discord.ext.commands",
        "pydantic",
        "matplotlib",
        "seaborn",
        "httpx",
        "yaml",
        "watchdog",
    ])
    def test_required_dependencies_importable(self, module_name: str) -> None:
        """Test that required dependencies can be imported."""
        try:
            _ = importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"Failed to import required dependency {module_name}: {e}")
    
    def test_discord_py_version(self) -> None:
        """Test that discord.py is the correct version."""
        try:
            import discord
            # Check that it's at least version 2.5.2
            version_parts = discord.__version__.split(".")
            major, minor = int(version_parts[0]), int(version_parts[1])
            assert major >= 2
            if major == 2:
                assert minor >= 5
        except ImportError as e:
            pytest.fail(f"Failed to import discord.py: {e}")
        except (ValueError, IndexError) as e:
            pytest.fail(f"Failed to parse discord.py version: {e}")


class TestCommandsStructure:
    """Test that the commands structure is properly set up."""
    
    def test_commands_directory_exists(self) -> None:
        """Test that bot/commands directory exists."""
        commands_dir = Path("bot/commands")
        assert commands_dir.exists()
        assert commands_dir.is_dir()
        
        # Check for __init__.py
        init_file = commands_dir / "__init__.py"
        assert init_file.exists()
        assert init_file.is_file()
    
    @pytest.mark.parametrize("command_file", [
        "about.py",
        "config.py", 
        "my_stats.py",
        "update_graphs.py",
        "uptime.py",
    ])
    def test_command_files_exist(self, command_file: str) -> None:
        """Test that individual command files exist."""
        command_path = Path("bot/commands") / command_file
        assert command_path.exists()
        assert command_path.is_file()
