#!/usr/bin/env python3
"""
Fix English PO file for proper monolingual setup.

This script identifies empty msgstr entries in the English PO file and populates
them with their corresponding msgid values, which is needed for proper monolingual
gettext setup where English serves as both source and base language.
"""

import re
import sys
from pathlib import Path


def fix_english_po_file(po_file_path: Path) -> None:
    """
    Fix English PO file by populating empty msgstr entries.
    
    Args:
        po_file_path: Path to the English messages.po file
    """
    if not po_file_path.exists():
        print(f"Error: PO file not found at {po_file_path}")
        sys.exit(1)
    
    # Read the file
    content = po_file_path.read_text(encoding='utf-8')
    
    # Split into lines for processing
    lines = content.split('\n')
    
    # Track changes
    changes_made = 0
    current_msgid = ""
    in_msgid = False
    
    # Process line by line
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for msgid start
        if line.startswith('msgid "'):
            # Extract msgid content
            msgid_match = re.match(r'msgid "(.*)"', line)
            if msgid_match:
                current_msgid = msgid_match.group(1)
                in_msgid = True
            else:
                current_msgid = ""
                in_msgid = False
        
        # Handle multiline msgid
        elif in_msgid and line.startswith('"') and line.endswith('"'):
            # Append to current msgid (remove quotes)
            current_msgid += line[1:-1]
        
        # Check for msgstr start
        elif line.startswith('msgstr "'):
            in_msgid = False
            
            # Check if msgstr is empty
            msgstr_match = re.match(r'msgstr "(.*)"', line)
            if msgstr_match and msgstr_match.group(1) == "":
                # Skip empty msgid (header entry)
                if current_msgid != "":
                    # Replace empty msgstr with msgid content
                    lines[i] = f'msgstr "{current_msgid}"'
                    changes_made += 1
                    print(f"Fixed: '{current_msgid}'")
        
        i += 1
    
    if changes_made > 0:
        # Write back the fixed content
        po_file_path.write_text('\n'.join(lines), encoding='utf-8')
        print(f"\nCompleted! Fixed {changes_made} empty msgstr entries.")
        print(f"Updated file: {po_file_path}")
    else:
        print("No empty msgstr entries found. File is already correct.")


def main():
    """Main entry point."""
    # Default path to English PO file
    po_file = Path(__file__).parent.parent / "locale" / "en" / "LC_MESSAGES" / "messages.po"
    
    # Allow custom path as command line argument
    if len(sys.argv) > 1:
        po_file = Path(sys.argv[1])
    
    print(f"Fixing English PO file: {po_file}")
    print("-" * 50)
    
    fix_english_po_file(po_file)


if __name__ == "__main__":
    main() 