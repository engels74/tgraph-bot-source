"""
General workflow utilities.

This module provides common utilities used across workflow scripts.
"""

import json
import sys
from pathlib import Path


import polib
import toml


def load_pyproject_toml() -> dict[str, dict[str, str]]:
    """
    Load and parse pyproject.toml file.
    
    Returns:
        Parsed pyproject.toml content
        
    Raises:
        FileNotFoundError: If pyproject.toml is not found
        toml.TomlDecodeError: If pyproject.toml is invalid
    """
    pyproject_path = Path('pyproject.toml')
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found")
    
    with open(pyproject_path, 'r') as f:
        return toml.load(f)


def get_current_version() -> str:
    """
    Get current version from pyproject.toml.
    
    Returns:
        Current version string
        
    Raises:
        KeyError: If version is not found in pyproject.toml
    """
    data = load_pyproject_toml()
    return str(data['project']['version'])


def check_translation_file(po_file_path: Path) -> tuple[int, int, float]:
    """
    Check translation file statistics.
    
    Args:
        po_file_path: Path to the .po file
        
    Returns:
        Tuple of (total_entries, translated_entries, percentage)
        
    Raises:
        FileNotFoundError: If the .po file doesn't exist
        Exception: If the .po file is invalid
    """
    if not po_file_path.exists():
        raise FileNotFoundError(f"Translation file not found: {po_file_path}")
    
    try:
        po = polib.pofile(str(po_file_path))
        total = len([e for e in po if not e.obsolete])
        translated = len([e for e in po if e.translated() and not e.obsolete])
        percentage = (translated / total * 100) if total > 0 else 0
        
        return total, translated, percentage
    except Exception as e:
        raise Exception(f"Error processing translation file {po_file_path}: {e}")


def get_all_translation_files(locale_dir: Path | None = None) -> list[Path]:
    """
    Get all translation files in the locale directory.
    
    Args:
        locale_dir: Path to the locale directory
        
    Returns:
        List of .po file paths
    """
    if locale_dir is None:
        locale_dir = Path('locale')

    if not locale_dir.exists():
        return []

    return list(locale_dir.glob('*/LC_MESSAGES/messages.po'))


def get_completed_languages(locale_dir: Path | None = None) -> list[str]:
    """
    Get list of languages with 100% translation completion.
    
    Args:
        locale_dir: Path to the locale directory
        
    Returns:
        List of language codes with complete translations
    """
    if locale_dir is None:
        locale_dir = Path('locale')

    completed: list[str] = []

    for po_file in get_all_translation_files(locale_dir):
        lang = po_file.parent.parent.name
        try:
            _, _, percentage = check_translation_file(po_file)
            if percentage == 100:
                completed.append(lang)
        except Exception:
            # Skip files that can't be processed
            continue
    
    return completed


def save_json_file(data: dict[str, str | int | float | bool | list[str] | dict[str, str]], file_path: Path) -> None:
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save
        file_path: Path to the output file
    """
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)


def load_json_file(file_path: Path) -> dict[str, str | int | float | bool | list[str] | dict[str, str]]:
    """
    Load data from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Loaded JSON data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file is invalid JSON
    """
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    
    with open(file_path, 'r') as f:
        return json.load(f)  # pyright: ignore[reportAny] # JSON loading returns Any by design


def validate_environment_variables(required_vars: list[str]) -> bool:
    """
    Validate that required environment variables are set.
    
    Args:
        required_vars: List of required environment variable names
        
    Returns:
        True if all variables are set, False otherwise
    """
    import os
    
    missing_vars: list[str] = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}",
              file=sys.stderr)
        return False
    
    return True


def create_directory_if_not_exists(dir_path: Path) -> None:
    """
    Create directory if it doesn't exist.
    
    Args:
        dir_path: Path to the directory
    """
    dir_path.mkdir(parents=True, exist_ok=True)


def get_translation_status_icon(percentage: float) -> str:
    """
    Get status icon based on translation percentage.
    
    Args:
        percentage: Translation completion percentage
        
    Returns:
        Appropriate emoji icon
    """
    if percentage == 100:
        return "🟢"
    elif percentage >= 80:
        return "🟡"
    else:
        return "🔴"


def format_percentage(percentage: float, decimal_places: int = 1) -> str:
    """
    Format percentage for display.
    
    Args:
        percentage: Percentage value
        decimal_places: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{percentage:.{decimal_places}f}%"


def safe_file_write(file_path: Path, content: str, encoding: str = 'utf-8') -> None:
    """
    Safely write content to a file.
    
    Args:
        file_path: Path to the file
        content: Content to write
        encoding: File encoding
    """
    # Create parent directory if it doesn't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write content
    with open(file_path, 'w', encoding=encoding) as f:
        _ = f.write(content)


def safe_file_read(file_path: Path, encoding: str = 'utf-8') -> str | None:
    """
    Safely read content from a file.
    
    Args:
        file_path: Path to the file
        encoding: File encoding
        
    Returns:
        File content or None if file doesn't exist
    """
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception:
        return None
