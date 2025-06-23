"""
Command-line argument parsing for TGraph Bot.

This module provides functionality for parsing command-line arguments
to configure custom paths for config files, data folders, and log folders.
"""

import argparse
import sys
from pathlib import Path
from typing import NamedTuple

from utils.core.version import get_version


class PathValidationError(Exception):
    """Raised when a path validation fails."""

    pass


class ParsedArgs(NamedTuple):
    """Container for parsed command-line arguments."""

    config_file: Path
    data_folder: Path
    log_folder: Path


class DefaultPaths:
    """Default paths for TGraph Bot."""

    CONFIG_FILE: Path = Path("config.yml")
    DATA_FOLDER: Path = Path("data")
    LOG_FOLDER: Path = Path("logs")


def validate_config_file_path(config_file_str: str) -> Path:
    """
    Validate configuration file path.

    Args:
        config_file_str: String path to configuration file

    Returns:
        Resolved Path object for the configuration file

    Raises:
        PathValidationError: If the configuration file path is invalid
    """
    try:
        # Expand tilde if present, then resolve
        config_file = Path(config_file_str).expanduser().resolve()
    except (OSError, ValueError) as e:
        raise PathValidationError(f"Invalid config file path: {e}") from e

    # Check if the path is a directory
    if config_file.exists() and config_file.is_dir():
        raise PathValidationError(
            f"Config file path exists but is not a file: {config_file}"
        )

    # Check if parent directory exists
    if not config_file.parent.exists():
        raise PathValidationError(
            f"Parent directory for config file does not exist: {config_file.parent}"
        )

    return config_file


def validate_folder_path(path_str: str, folder_name: str) -> Path:
    """
    Validate and resolve a folder path.

    Args:
        path_str: String representation of the folder path
        folder_name: Name of the folder (for error messages)

    Returns:
        Resolved absolute path to the folder

    Raises:
        PathValidationError: If the path is invalid
    """
    try:
        # Expand tilde if present
        path = Path(path_str).expanduser().resolve()
    except (OSError, ValueError) as e:
        raise PathValidationError(f"Invalid {folder_name} path: {e}") from e

    # If the path exists, it must be a directory
    if path.exists() and not path.is_dir():
        raise PathValidationError(
            f"{folder_name.capitalize()} path exists but is not a directory: {path}"
        )

    return path


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser for TGraph Bot.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="tgraph-bot",
        description="TGraph Bot - Discord bot for Tautulli graph generation and posting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tgraph-bot
    Run with default paths

  tgraph-bot --config-file /etc/tgraph/config.yml
    Use custom config file location

  tgraph-bot --data-folder /var/lib/tgraph/data --log-folder /var/log/tgraph
    Use custom data and log directories

  tgraph-bot --config-file ~/tgraph/config.yml --data-folder ~/tgraph/data --log-folder ~/tgraph/logs
    Use custom paths in home directory
""",
    )

    defaults = DefaultPaths()

    _ = parser.add_argument(
        "--config-file",
        type=str,
        default=str(defaults.CONFIG_FILE),
        help=(
            "Path to the configuration file (default: %(default)s). "
            "The parent directory must exist, but the file will be created if it doesn't exist."
        ),
        metavar="PATH",
    )

    _ = parser.add_argument(
        "--data-folder",
        type=str,
        default=str(defaults.DATA_FOLDER),
        help=(
            "Path to the data folder for storing generated graphs (default: %(default)s). "
            "The directory will be created if it doesn't exist."
        ),
        metavar="PATH",
    )

    _ = parser.add_argument(
        "--log-folder",
        type=str,
        default=str(defaults.LOG_FOLDER),
        help=(
            "Path to the log folder for storing application logs (default: %(default)s). "
            "The directory will be created if it doesn't exist."
        ),
        metavar="PATH",
    )

    _ = parser.add_argument(
        "--version", action="version", version=f"%(prog)s {get_version()}"
    )

    return parser


def parse_arguments(args: list[str] | None = None) -> ParsedArgs:
    """
    Parse command-line arguments.

    Args:
        args: List of arguments to parse (defaults to sys.argv[1:])

    Returns:
        ParsedArgs containing validated and resolved paths

    Raises:
        SystemExit: If argument parsing fails or --help is requested
        PathValidationError: If path validation fails
    """
    parser = create_argument_parser()

    # Parse arguments
    parsed = parser.parse_args(args)

    # Validate and resolve paths
    try:
        # Use getattr to access attributes with proper types - argparse guarantees these are strings
        config_file_str: str = getattr(parsed, "config_file", "")
        data_folder_str: str = getattr(parsed, "data_folder", "")
        log_folder_str: str = getattr(parsed, "log_folder", "")

        if not config_file_str or not data_folder_str or not log_folder_str:
            raise ValueError("Missing required arguments from parser")

        config_file = validate_config_file_path(config_file_str)
        data_folder = validate_folder_path(data_folder_str, "data folder")
        log_folder = validate_folder_path(log_folder_str, "log folder")
    except PathValidationError as e:
        # Print error to stderr and exit with error code
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    return ParsedArgs(
        config_file=config_file, data_folder=data_folder, log_folder=log_folder
    )


def ensure_directories_exist(parsed_args: ParsedArgs) -> None:
    """
    Ensure that the data and log directories exist.

    Creates directories if they don't exist. Does not create the config file.

    Args:
        parsed_args: Parsed command-line arguments

    Raises:
        OSError: If directory creation fails
    """
    # Create data folder if it doesn't exist
    parsed_args.data_folder.mkdir(parents=True, exist_ok=True)

    # Create log folder if it doesn't exist
    parsed_args.log_folder.mkdir(parents=True, exist_ok=True)


def get_parsed_args() -> ParsedArgs:
    """
    Parse arguments and ensure directories exist.

    This is a convenience function that combines argument parsing
    and directory creation.

    Returns:
        ParsedArgs containing validated paths with directories created

    Raises:
        SystemExit: If argument parsing fails
        PathValidationError: If path validation fails
        OSError: If directory creation fails
    """
    parsed_args = parse_arguments()
    ensure_directories_exist(parsed_args)
    return parsed_args
