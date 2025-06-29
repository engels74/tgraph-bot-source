"""
Global path management for TGraph Bot.

This module provides a centralized way to access and manage application paths
that are configured via command-line arguments.
"""

from pathlib import Path


class PathConfig:
    """Singleton class to manage application paths."""

    _instance: "PathConfig | None" = None
    _initialized: bool = False

    def __new__(cls) -> "PathConfig":
        """Ensure only one instance of PathConfig exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize path configuration (only runs once)."""
        if not self._initialized:
            self._config_file: Path = Path("config.yml")
            self._data_folder: Path = Path("data")
            self._log_folder: Path = Path("logs")
            PathConfig._initialized = True

    def set_paths(self, config_file: Path, data_folder: Path, log_folder: Path) -> None:
        """
        Set the application paths.

        This should be called once at application startup after parsing
        command-line arguments.

        Args:
            config_file: Path to the configuration file
            data_folder: Path to the data folder
            log_folder: Path to the log folder
        """
        self._config_file = config_file
        self._data_folder = data_folder
        self._log_folder = log_folder

    @property
    def config_file(self) -> Path:
        """Get the configuration file path."""
        return self._config_file

    @property
    def data_folder(self) -> Path:
        """Get the data folder path."""
        return self._data_folder

    @property
    def log_folder(self) -> Path:
        """Get the log folder path."""
        return self._log_folder

    def get_graph_path(self, *subdirs: str) -> Path:
        """
        Get a path within the data folder for graphs.

        Args:
            *subdirs: Subdirectory components to append

        Returns:
            Path object for the requested graph subdirectory
        """
        path = self._data_folder / "graphs"
        for subdir in subdirs:
            path = path / subdir
        return path

    def get_scheduler_state_path(self) -> Path:
        """
        Get the path for the scheduler state file.

        Returns:
            Path to the scheduler state file
        """
        return self._data_folder / "scheduler_state.json"


# Global instance for easy access
_path_config = PathConfig()


def get_path_config() -> PathConfig:
    """
    Get the global PathConfig instance.

    Returns:
        The singleton PathConfig instance
    """
    return _path_config
