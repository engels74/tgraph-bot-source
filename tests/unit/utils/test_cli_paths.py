"""Unit tests for CLI paths management."""

from pathlib import Path

from utils.cli.paths import PathConfig, get_path_config


class TestPathConfig:
    """Test the PathConfig singleton class."""

    def test_singleton_behavior(self) -> None:
        """Test that PathConfig follows singleton pattern."""
        instance1 = PathConfig()
        instance2 = PathConfig()
        
        # Both instances should be the same object
        assert instance1 is instance2
        
        # Getting through the convenience function should also return same instance
        instance3 = get_path_config()
        assert instance1 is instance3

    def test_default_initialization(self) -> None:
        """Test that PathConfig initializes with default paths."""
        config = PathConfig()
        
        assert config.config_file == Path("config.yml")
        assert config.data_folder == Path("data")
        assert config.log_folder == Path("logs")

    def test_set_paths(self, tmp_path: Path) -> None:
        """Test setting custom paths."""
        config = get_path_config()
        
        custom_config = tmp_path / "custom_config.yml"
        custom_data = tmp_path / "custom_data"
        custom_logs = tmp_path / "custom_logs"
        
        config.set_paths(
            config_file=custom_config,
            data_folder=custom_data,
            log_folder=custom_logs
        )
        
        assert config.config_file == custom_config
        assert config.data_folder == custom_data
        assert config.log_folder == custom_logs

    def test_get_graph_path_no_subdirs(self, tmp_path: Path) -> None:
        """Test getting graph path without subdirectories."""
        config = get_path_config()
        config.set_paths(
            config_file=tmp_path / "config.yml",
            data_folder=tmp_path / "data",
            log_folder=tmp_path / "logs"
        )
        
        graph_path = config.get_graph_path()
        assert graph_path == tmp_path / "data" / "graphs"

    def test_get_graph_path_with_subdirs(self, tmp_path: Path) -> None:
        """Test getting graph path with subdirectories."""
        config = get_path_config()
        config.set_paths(
            config_file=tmp_path / "config.yml",
            data_folder=tmp_path / "data",
            log_folder=tmp_path / "logs"
        )
        
        # Test with single subdirectory
        graph_path = config.get_graph_path("2025-01-21")
        assert graph_path == tmp_path / "data" / "graphs" / "2025-01-21"
        
        # Test with multiple subdirectories
        graph_path = config.get_graph_path("2025-01-21", "users", "test_user")
        expected = tmp_path / "data" / "graphs" / "2025-01-21" / "users" / "test_user"
        assert graph_path == expected

    def test_get_graph_path_empty_subdirs(self, tmp_path: Path) -> None:
        """Test getting graph path with empty string subdirectories."""
        config = get_path_config()
        config.set_paths(
            config_file=tmp_path / "config.yml",
            data_folder=tmp_path / "data",
            log_folder=tmp_path / "logs"
        )
        
        # Empty strings should still create path components
        graph_path = config.get_graph_path("", "users", "")
        expected = tmp_path / "data" / "graphs" / "" / "users" / ""
        assert graph_path == expected

    def test_get_scheduler_state_path(self, tmp_path: Path) -> None:
        """Test getting scheduler state file path."""
        config = get_path_config()
        config.set_paths(
            config_file=tmp_path / "config.yml",
            data_folder=tmp_path / "data",
            log_folder=tmp_path / "logs"
        )
        
        state_path = config.get_scheduler_state_path()
        assert state_path == tmp_path / "data" / "scheduler_state.json"

    def test_paths_remain_after_reset(self, tmp_path: Path) -> None:
        """Test that paths remain set after multiple set_paths calls."""
        config = get_path_config()
        
        # First set of paths
        config.set_paths(
            config_file=tmp_path / "config1.yml",
            data_folder=tmp_path / "data1",
            log_folder=tmp_path / "logs1"
        )
        
        assert config.data_folder == tmp_path / "data1"
        
        # Second set of paths
        config.set_paths(
            config_file=tmp_path / "config2.yml",
            data_folder=tmp_path / "data2",
            log_folder=tmp_path / "logs2"
        )
        
        assert config.config_file == tmp_path / "config2.yml"
        assert config.data_folder == tmp_path / "data2"
        assert config.log_folder == tmp_path / "logs2"

    def test_paths_are_path_objects(self, tmp_path: Path) -> None:
        """Test that all path properties return Path objects."""
        config = get_path_config()
        config.set_paths(
            config_file=tmp_path / "config.yml",
            data_folder=tmp_path / "data",
            log_folder=tmp_path / "logs"
        )
        
        assert isinstance(config.config_file, Path)
        assert isinstance(config.data_folder, Path)
        assert isinstance(config.log_folder, Path)
        assert isinstance(config.get_graph_path(), Path)
        assert isinstance(config.get_scheduler_state_path(), Path)


class TestGetPathConfig:
    """Test the get_path_config convenience function."""

    def test_returns_singleton_instance(self) -> None:
        """Test that get_path_config returns the singleton instance."""
        config1 = get_path_config()
        config2 = get_path_config()
        
        assert config1 is config2
        assert isinstance(config1, PathConfig)

    def test_modifications_persist(self, tmp_path: Path) -> None:
        """Test that modifications through get_path_config persist."""
        config1 = get_path_config()
        config1.set_paths(
            config_file=tmp_path / "test.yml",
            data_folder=tmp_path / "test_data",
            log_folder=tmp_path / "test_logs"
        )
        
        # Get the config again
        config2 = get_path_config()
        
        # Should have the same paths
        assert config2.config_file == tmp_path / "test.yml"
        assert config2.data_folder == tmp_path / "test_data"
        assert config2.log_folder == tmp_path / "test_logs"


class TestPathConfigIntegration:
    """Integration tests for PathConfig with actual file system operations."""

    def test_paths_can_be_created(self, tmp_path: Path) -> None:
        """Test that paths from PathConfig can be used to create directories."""
        config = get_path_config()
        config.set_paths(
            config_file=tmp_path / "config.yml",
            data_folder=tmp_path / "data",
            log_folder=tmp_path / "logs"
        )
        
        # Create directories using the paths
        config.data_folder.mkdir(parents=True, exist_ok=True)
        config.log_folder.mkdir(parents=True, exist_ok=True)
        
        graph_path = config.get_graph_path("2025-01-21")
        graph_path.mkdir(parents=True, exist_ok=True)
        
        # Verify directories exist
        assert config.data_folder.exists()
        assert config.log_folder.exists()
        assert graph_path.exists()
        
        # Create a file in the scheduler state path location
        state_path = config.get_scheduler_state_path()
        state_path.parent.mkdir(parents=True, exist_ok=True)
        _ = state_path.write_text('{"test": true}')
        
        assert state_path.exists()
        assert state_path.read_text() == '{"test": true}'

    def test_relative_paths_resolved(self) -> None:
        """Test that relative paths are properly handled."""
        config = get_path_config()
        
        # Set relative paths
        config.set_paths(
            config_file=Path("./config/app.yml"),
            data_folder=Path("./data"),
            log_folder=Path("./logs")
        )
        
        # Paths should still be usable (not necessarily absolute in the property)
        assert config.config_file == Path("./config/app.yml")
        assert config.data_folder == Path("./data")
        assert config.log_folder == Path("./logs") 