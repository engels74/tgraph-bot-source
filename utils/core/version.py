"""
Version utilities for TGraph Bot.

This module provides centralized version information by reading from pyproject.toml
with fallback mechanisms for robust version retrieval across different deployment scenarios.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_project_version() -> str:
    """
    Get the project version from pyproject.toml.

    This function uses caching to avoid repeatedly reading the file
    and provides fallbacks for robust version detection.

    Returns:
        Version string (e.g., "1.0.0")

    Raises:
        RuntimeError: If version cannot be determined from any source
    """
    # Try importlib.metadata first (standard approach for installed packages)
    try:
        from importlib.metadata import version

        return version("tgraph-bot")
    except Exception:
        # Package might not be installed, fallback to pyproject.toml
        logger.debug("importlib.metadata failed, falling back to pyproject.toml")

    # Try reading from pyproject.toml directly
    try:
        import tomllib  # Python 3.11+ built-in

        return _read_version_with_tomllib(tomllib)
    except ImportError:
        try:
            import tomli as tomllib  # pyright: ignore[reportMissingImports]

            return _read_version_with_tomllib(tomllib)
        except ImportError:
            # Final fallback using toml library (already in dependencies)
            import toml

            return _read_version_with_toml(toml)


def _read_version_with_tomllib(tomllib_module: Any) -> str:  # pyright: ignore[reportExplicitAny,reportAny] # multiple TOML libraries with different signatures
    """Read version using tomllib/tomli."""
    pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        # Try relative to this file's location (for different working directories)
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    if not pyproject_path.exists():
        raise RuntimeError("pyproject.toml not found")

    try:
        with open(pyproject_path, "rb") as f:
            data: dict[str, Any] = tomllib_module.load(f)  # pyright: ignore[reportAny,reportExplicitAny] # TOML parsing returns nested dicts

        # Type-safe access to nested dict structure
        project_data = data.get("project")
        if not isinstance(project_data, dict):
            raise KeyError("project section not found or invalid")

        version = project_data.get("version")  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType] # dict from TOML data
        if not isinstance(version, str):
            raise KeyError("version field not found or not a string")

        return version
    except (KeyError, OSError) as e:
        raise RuntimeError(f"Failed to read version from pyproject.toml: {e}") from e


def _read_version_with_toml(toml_module: Any) -> str:  # pyright: ignore[reportExplicitAny,reportAny] # multiple TOML libraries with different signatures
    """Read version using toml library (fallback)."""
    pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        # Try relative to this file's location
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    if not pyproject_path.exists():
        raise RuntimeError("pyproject.toml not found")

    try:
        with open(pyproject_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = toml_module.load(f)  # pyright: ignore[reportAny,reportExplicitAny] # TOML parsing returns nested dicts

        # Type-safe access to nested dict structure
        project_data = data.get("project")
        if not isinstance(project_data, dict):
            raise KeyError("project section not found or invalid")

        version = project_data.get("version")  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType] # dict from TOML data
        if not isinstance(version, str):
            raise KeyError("version field not found or not a string")

        return version
    except (KeyError, OSError) as e:
        raise RuntimeError(f"Failed to read version from pyproject.toml: {e}") from e


def get_version_info() -> dict[str, str]:
    """
    Get comprehensive version information.

    Returns:
        Dictionary with version information including:
        - version: Project version
        - source: Source of version information
    """
    try:
        version = get_project_version()

        # Determine source
        try:
            from importlib.metadata import version as meta_version

            if meta_version("tgraph-bot") == version:
                source = "importlib.metadata"
            else:
                source = "pyproject.toml"
        except Exception:
            source = "pyproject.toml"

        return {"version": version, "source": source}
    except RuntimeError as e:
        logger.error(f"Failed to get version information: {e}")
        return {"version": "unknown", "source": "error"}


# Convenience alias for the most common use case
def get_version() -> str:
    """Get the project version with error handling."""
    try:
        return get_project_version()
    except RuntimeError:
        logger.warning("Could not determine project version, using fallback")
        return "1.0.0"  # Fallback version
