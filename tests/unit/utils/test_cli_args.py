"""Unit tests for CLI argument parsing."""

from pathlib import Path
from unittest.mock import patch

import pytest
import os

from src.tgraph_bot.utils.cli.args import (
    DefaultPaths,
    ParsedArgs,
    PathValidationError,
    create_argument_parser,
    ensure_directories_exist,
    get_parsed_args,
    parse_arguments,
    validate_config_file_path,
    validate_folder_path,
)


class TestDefaultPaths:
    """Test the DefaultPaths dataclass."""

    def test_default_values(self) -> None:
        """Test that default paths are correctly set."""
        defaults = DefaultPaths()
        assert defaults.CONFIG_FILE == Path("data/config/config.yml")
        assert defaults.DATA_FOLDER == Path("data")
        assert defaults.LOG_FOLDER == Path("data/logs")


class TestPathValidation:
    """Test path validation functions."""

    def test_validate_config_file_path_valid(self, tmp_path: Path) -> None:
        """Test validation of a valid config file path."""
        # Create a valid config file
        config_file = tmp_path / "config.yml"
        _ = config_file.touch()

        result = validate_config_file_path(str(config_file))
        assert result == config_file.resolve()

    def test_validate_config_file_path_nonexistent_but_valid_parent(
        self, tmp_path: Path
    ) -> None:
        """Test validation of a nonexistent config file with valid parent directory."""
        # Parent directory exists but file doesn't
        config_file = tmp_path / "config.yml"

        result = validate_config_file_path(str(config_file))
        assert result == config_file.resolve()

    def test_validate_config_file_path_invalid_parent(self) -> None:
        """Test validation of a config file with nonexistent parent directory."""
        # Parent directory doesn't exist
        config_file = Path("/nonexistent/directory/config.yml")

        with pytest.raises(PathValidationError) as exc_info:
            _ = validate_config_file_path(str(config_file))

        assert "Parent directory for config file does not exist" in str(exc_info.value)

    def test_validate_config_file_path_is_directory(self, tmp_path: Path) -> None:
        """Test validation of a path that is a directory instead of a file."""
        with pytest.raises(PathValidationError) as exc_info:
            _ = validate_config_file_path(str(tmp_path))

        assert "Config file path exists but is not a file" in str(exc_info.value)

    def test_validate_config_file_path_invalid_characters(self) -> None:
        """Test validation of a path with invalid characters."""
        invalid_path = "\0invalid\0path"

        with pytest.raises(PathValidationError) as exc_info:
            _ = validate_config_file_path(invalid_path)

        assert "Invalid config file path" in str(exc_info.value)

    def test_validate_folder_path_valid_existing(self, tmp_path: Path) -> None:
        """Test validation of a valid existing folder path."""
        result = validate_folder_path(str(tmp_path), "test folder")
        assert result == tmp_path.resolve()

    def test_validate_folder_path_valid_nonexistent(self, tmp_path: Path) -> None:
        """Test validation of a valid nonexistent folder path."""
        folder = tmp_path / "new_folder"

        result = validate_folder_path(str(folder), "test folder")
        assert result == folder.resolve()

    def test_validate_folder_path_is_file(self, tmp_path: Path) -> None:
        """Test validation of a path that is a file instead of a directory."""
        file_path = tmp_path / "file.txt"
        _ = file_path.touch()

        with pytest.raises(PathValidationError) as exc_info:
            _ = validate_folder_path(str(file_path), "test folder")

        assert "Test folder path exists but is not a directory" in str(exc_info.value)

    def test_validate_folder_path_invalid_characters(self) -> None:
        """Test validation of a folder path with invalid characters."""
        invalid_path = "\0invalid\0path"

        with pytest.raises(PathValidationError) as exc_info:
            _ = validate_folder_path(invalid_path, "test folder")

        assert "Invalid test folder path" in str(exc_info.value)


class TestArgumentParser:
    """Test argument parser creation and configuration."""

    def test_create_argument_parser(self) -> None:
        """Test that argument parser is created with correct configuration."""
        parser = create_argument_parser()

        # Check parser properties
        assert parser.prog == "tgraph-bot"
        assert parser.description is not None
        assert "TGraph Bot" in parser.description
        assert parser.epilog is not None
        assert "Examples:" in parser.epilog

        # Check that all required arguments are present
        actions = {action.dest: action for action in parser._actions}

        assert "config_file" in actions
        assert "data_folder" in actions
        assert "log_folder" in actions
        assert "version" in actions

        # Check default values
        config_action = actions["config_file"]
        data_action = actions["data_folder"]
        log_action = actions["log_folder"]
        # Use getattr to avoid Any type warnings
        assert getattr(config_action, "default", None) == "data/config/config.yml"
        assert getattr(data_action, "default", None) == "data"
        assert getattr(log_action, "default", None) == "data/logs"

    def test_parser_help_text(self) -> None:
        """Test that help text is properly configured."""
        parser = create_argument_parser()

        # Get help text for each argument
        for action in parser._actions:
            if action.dest in ["config_file", "data_folder", "log_folder"]:
                assert action.help is not None
                assert len(action.help) > 0
                assert action.metavar == "PATH"


class TestParseArguments:
    """Test argument parsing functionality."""

    def test_parse_arguments_defaults(self, tmp_path: Path) -> None:
        """Test parsing with default arguments."""
        # Create the expected directory structure for new defaults
        config_dir = tmp_path / "data" / "config"
        _ = config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.yml"
        _ = config_file.touch()

        # Temporarily change to the temp directory to test default behavior
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Test with empty args (defaults)
            result = parse_arguments([])

            assert result.config_file == config_file.resolve()
            assert result.data_folder == (tmp_path / "data").resolve()
            assert result.log_folder == (tmp_path / "data" / "logs").resolve()
        finally:
            # Always restore the original working directory
            os.chdir(original_cwd)

    def test_parse_arguments_custom_paths(self, tmp_path: Path) -> None:
        """Test parsing with custom path arguments."""
        config_file = tmp_path / "custom_config.yml"
        data_folder = tmp_path / "custom_data"
        log_folder = tmp_path / "custom_logs"

        # Create parent directory for config file
        _ = config_file.parent.mkdir(parents=True, exist_ok=True)

        args = [
            "--config-file",
            str(config_file),
            "--data-folder",
            str(data_folder),
            "--log-folder",
            str(log_folder),
        ]

        result = parse_arguments(args)

        assert result.config_file == config_file.resolve()
        assert result.data_folder == data_folder.resolve()
        assert result.log_folder == log_folder.resolve()

    def test_parse_arguments_relative_paths(self, tmp_path: Path) -> None:
        """Test parsing with relative path arguments."""
        # We need to patch both cwd and resolve to properly test relative paths
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            # Create a custom Path class that resolves relative to tmp_path
            def custom_resolve(self: Path) -> Path:
                if self.is_absolute():
                    return self
                # Resolve relative to our mocked cwd
                return (tmp_path / self).resolve()

            with patch.object(Path, "resolve", custom_resolve):
                args = [
                    "--config-file",
                    "./config/app.yml",
                    "--data-folder",
                    "./data",
                    "--log-folder",
                    "./logs",
                ]

                # Create parent directory for config
                _ = (tmp_path / "config").mkdir(exist_ok=True)

                result = parse_arguments(args)

                assert result.config_file == (tmp_path / "config/app.yml").resolve()
                assert result.data_folder == (tmp_path / "data").resolve()
                assert result.log_folder == (tmp_path / "logs").resolve()

    def test_parse_arguments_home_directory(self, tmp_path: Path) -> None:
        """Test parsing with home directory paths."""

        # Mock expanduser to expand ~ to our tmp_path
        def mock_expanduser(self: Path) -> Path:
            path_str = str(self)
            if path_str.startswith("~"):
                # Replace ~ with our tmp_path
                expanded = path_str.replace("~", str(tmp_path), 1)
                return Path(expanded)
            return self

        with patch.object(Path, "expanduser", mock_expanduser):
            args = [
                "--config-file",
                "~/tgraph/config.yml",
                "--data-folder",
                "~/tgraph/data",
                "--log-folder",
                "~/tgraph/logs",
            ]

            # Create parent directory
            _ = (tmp_path / "tgraph").mkdir(exist_ok=True)

            result = parse_arguments(args)

            assert result.config_file == (tmp_path / "tgraph/config.yml").resolve()
            assert result.data_folder == (tmp_path / "tgraph/data").resolve()
            assert result.log_folder == (tmp_path / "tgraph/logs").resolve()

    def test_parse_arguments_invalid_config_path(self) -> None:
        """Test parsing with invalid config file path."""
        args = ["--config-file", "/nonexistent/directory/config.yml"]

        with pytest.raises(SystemExit) as exc_info:
            _ = parse_arguments(args)

        assert exc_info.value.code == 1

    def test_parse_arguments_help(self) -> None:
        """Test that --help exits with code 0."""
        with pytest.raises(SystemExit) as exc_info:
            _ = parse_arguments(["--help"])

        assert exc_info.value.code == 0

    def test_parse_arguments_version(self) -> None:
        """Test that --version exits with code 0."""
        with pytest.raises(SystemExit) as exc_info:
            _ = parse_arguments(["--version"])

        assert exc_info.value.code == 0


class TestEnsureDirectoriesExist:
    """Test directory creation functionality."""

    def test_ensure_directories_exist_creates_directories(self, tmp_path: Path) -> None:
        """Test that directories are created when they don't exist."""
        config_file = tmp_path / "config.yml"
        data_folder = tmp_path / "data"
        log_folder = tmp_path / "logs"

        parsed_args = ParsedArgs(
            config_file=config_file, data_folder=data_folder, log_folder=log_folder
        )

        # Ensure directories don't exist initially
        assert not data_folder.exists()
        assert not log_folder.exists()

        ensure_directories_exist(parsed_args)

        # Verify directories were created
        assert data_folder.exists()
        assert data_folder.is_dir()
        assert log_folder.exists()
        assert log_folder.is_dir()

    def test_ensure_directories_exist_preserves_existing(self, tmp_path: Path) -> None:
        """Test that existing directories are preserved."""
        config_file = tmp_path / "config.yml"
        data_folder = tmp_path / "data"
        log_folder = tmp_path / "logs"

        # Create directories with content
        _ = data_folder.mkdir()
        test_file = data_folder / "test.txt"
        _ = test_file.write_text("test content")

        _ = log_folder.mkdir()

        parsed_args = ParsedArgs(
            config_file=config_file, data_folder=data_folder, log_folder=log_folder
        )

        ensure_directories_exist(parsed_args)

        # Verify directories still exist with content
        assert data_folder.exists()
        assert test_file.exists()
        assert test_file.read_text() == "test content"
        assert log_folder.exists()

    def test_ensure_directories_exist_nested_paths(self, tmp_path: Path) -> None:
        """Test that nested directory paths are created."""
        config_file = tmp_path / "config.yml"
        data_folder = tmp_path / "deep/nested/data"
        log_folder = tmp_path / "deep/nested/logs"

        parsed_args = ParsedArgs(
            config_file=config_file, data_folder=data_folder, log_folder=log_folder
        )

        ensure_directories_exist(parsed_args)

        # Verify nested directories were created
        assert data_folder.exists()
        assert data_folder.is_dir()
        assert log_folder.exists()
        assert log_folder.is_dir()


class TestGetParsedArgs:
    """Test the convenience function get_parsed_args."""

    def test_get_parsed_args_integration(self, tmp_path: Path) -> None:
        """Test the full integration of parsing and directory creation."""
        config_file = tmp_path / "config.yml"
        data_folder = tmp_path / "data"
        log_folder = tmp_path / "logs"

        # Create config file parent directory
        _ = config_file.parent.mkdir(parents=True, exist_ok=True)

        args = [
            "--config-file",
            str(config_file),
            "--data-folder",
            str(data_folder),
            "--log-folder",
            str(log_folder),
        ]

        with patch("sys.argv", ["tgraph-bot"] + args):
            result = get_parsed_args()

        # Verify arguments were parsed correctly
        assert result.config_file == config_file.resolve()
        assert result.data_folder == data_folder.resolve()
        assert result.log_folder == log_folder.resolve()

        # Verify directories were created
        assert data_folder.exists()
        assert log_folder.exists()

    def test_get_parsed_args_error_handling(self) -> None:
        """Test that get_parsed_args properly handles errors."""
        args = ["--config-file", "/nonexistent/directory/config.yml"]

        with patch("sys.argv", ["tgraph-bot"] + args):
            with pytest.raises(SystemExit) as exc_info:
                _ = get_parsed_args()

            assert exc_info.value.code == 1


class TestParsedArgs:
    """Test the ParsedArgs NamedTuple."""

    def test_parsed_args_creation(self, tmp_path: Path) -> None:
        """Test creating ParsedArgs instances."""
        config_file = tmp_path / "config.yml"
        data_folder = tmp_path / "data"
        log_folder = tmp_path / "logs"

        parsed_args = ParsedArgs(
            config_file=config_file, data_folder=data_folder, log_folder=log_folder
        )

        assert parsed_args.config_file == config_file
        assert parsed_args.data_folder == data_folder
        assert parsed_args.log_folder == log_folder

    def test_parsed_args_immutable(self, tmp_path: Path) -> None:
        """Test that ParsedArgs is immutable."""
        parsed_args = ParsedArgs(
            config_file=tmp_path / "config.yml",
            data_folder=tmp_path / "data",
            log_folder=tmp_path / "logs",
        )

        # This should fail because NamedTuple is immutable
        with pytest.raises(AttributeError):
            parsed_args.config_file = tmp_path / "other.yml"  # pyright: ignore[reportAttributeAccessIssue]
