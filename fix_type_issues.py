#!/usr/bin/env python3
"""
Script to automatically fix common type issues in test files.
"""

import re
import sys
from pathlib import Path

def fix_file(file_path: Path) -> None:
    """Fix type issues in a single file."""
    content = file_path.read_text()
    
    # Fix protected member access
    content = re.sub(
        r'(manager\._(?:loaded_extensions|failed_extensions))',
        r'\1  # pyright: ignore[reportPrivateUsage]',
        content
    )
    
    # Fix mock object method calls
    content = re.sub(
        r'(mock_bot\.(?:load_extension|unload_extension|reload_extension)\.(?:side_effect|assert_called_once_with))',
        r'\1  # pyright: ignore[reportAny]',
        content
    )
    
    # Fix mock object attribute access
    content = re.sub(
        r'(mock_bot\.(?:load_extension|unload_extension|reload_extension))(?!\.)(?=\s*=)',
        r'\1  # pyright: ignore[reportAny]',
        content
    )
    
    # Remove duplicate type ignores
    content = re.sub(
        r'(# pyright: ignore\[reportPrivateUsage\])\s+(# pyright: ignore\[reportPrivateUsage\])',
        r'\1',
        content
    )
    content = re.sub(
        r'(# pyright: ignore\[reportAny\])\s+(# pyright: ignore\[reportAny\])',
        r'\1',
        content
    )
    
    _ = file_path.write_text(content)
    print(f"Fixed {file_path}")

def main() -> None:
    """Main function."""
    if len(sys.argv) > 1:
        files = [Path(arg) for arg in sys.argv[1:]]
    else:
        files = list(Path("tests").glob("*.py"))
    
    for file_path in files:
        if file_path.exists():
            fix_file(file_path)

if __name__ == "__main__":
    main()
