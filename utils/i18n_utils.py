"""
String extraction utilities for internationalization (i18n).

This module provides functions to scan Python source files for translatable strings,
extract them to .pot template files, and update existing .po translation files
while preserving existing translations.

Usage Examples:
    Extract strings from source files:
        >>> from utils.i18n_utils import extract_strings_from_file
        >>> strings = extract_strings_from_file("bot/commands/about.py")
        >>> print(strings)
        [('Display information about the bot', 15, 'description')]

    Generate .pot file:
        >>> from utils.i18n_utils import generate_pot_file
        >>> generate_pot_file(".", "locale/messages.pot")

    Update .po files:
        >>> from utils.i18n_utils import update_po_file
        >>> update_po_file("locale/messages.pot", "locale/en/LC_MESSAGES/messages.po")
"""

from __future__ import annotations

import ast
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import override

logger = logging.getLogger(__name__)

# Translation function patterns to search for
TRANSLATION_FUNCTIONS = {
    "_",           # Standard gettext function
    "translate",   # Our custom translate function
    "t",          # Alias for translate
    "ngettext",   # Plural forms
    "nt",         # Alias for ngettext
}

# File patterns to include in extraction
PYTHON_FILE_PATTERNS = ["*.py"]

# Directories to exclude from extraction
EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".pytest_cache",
    "htmlcov",
    "node_modules",
    "venv",
    "env",
    ".venv",
    ".env",
}


class StringExtractor(ast.NodeVisitor):
    """AST visitor to extract translatable strings from Python source code."""

    def __init__(self, filename: str) -> None:
        """
        Initialize the string extractor.

        Args:
            filename: Name of the file being processed (for context)
        """
        self.filename: str = filename
        self.strings: list[tuple[str, int, str | None]] = []

    @override
    def visit_Call(self, node: ast.Call) -> None:
        """
        Visit function call nodes to find translation function calls.

        Args:
            node: AST Call node to examine
        """
        # Check if this is a call to a translation function
        func_name = self._get_function_name(node.func)

        if func_name in TRANSLATION_FUNCTIONS:
            # Extract string arguments (handle both single and plural forms)
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    string_value = arg.value
                    line_number = node.lineno
                    context = self._extract_context(node)

                    self.strings.append((string_value, line_number, context))
                    logger.debug(f"Found translatable string: '{string_value}' at line {line_number}")

        # Continue visiting child nodes
        self.generic_visit(node)

    def _get_function_name(self, func_node: ast.AST) -> str | None:
        """
        Extract function name from various AST node types.

        Args:
            func_node: AST node representing the function being called

        Returns:
            Function name if extractable, None otherwise
        """
        if isinstance(func_node, ast.Name):
            return func_node.id
        elif isinstance(func_node, ast.Attribute):
            return func_node.attr
        return None

    def _extract_context(self, node: ast.Call) -> str | None:
        """
        Extract context information for the translation string.

        Args:
            node: AST Call node

        Returns:
            Context string if available, None otherwise
        """
        # Look for context in keyword arguments
        for keyword in node.keywords:
            if keyword.arg == "context" and isinstance(keyword.value, ast.Constant):
                value: object = keyword.value.value  # ast.Constant.value is Any, so we type it as object
                if isinstance(value, str):
                    return value
        return None


def extract_strings_from_file(filepath: Path) -> list[tuple[str, int, str | None]]:
    """
    Extract translatable strings from a single Python file.

    Args:
        filepath: Path to the Python file to process

    Returns:
        List of tuples containing (string, line_number, context)

    Raises:
        FileNotFoundError: If the file doesn't exist
        SyntaxError: If the file contains invalid Python syntax
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()

        # Parse the file into an AST
        tree = ast.parse(content, filename=str(filepath))
        
        # Extract strings using our visitor
        extractor = StringExtractor(str(filepath))
        extractor.visit(tree)
        
        logger.info(f"Extracted {len(extractor.strings)} strings from {filepath}")
        return extractor.strings

    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        raise
    except SyntaxError as e:
        logger.error(f"Syntax error in {filepath}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}")
        raise


def scan_directory_for_strings(
    directory: Path,
    exclude_dirs: set[str] | None = None
) -> dict[str, list[tuple[str, int, str | None]]]:
    """
    Scan a directory recursively for translatable strings in Python files.

    Args:
        directory: Root directory to scan
        exclude_dirs: Set of directory names to exclude from scanning

    Returns:
        Dictionary mapping file paths to lists of extracted strings
    """
    if exclude_dirs is None:
        exclude_dirs = EXCLUDED_DIRS

    results: dict[str, list[tuple[str, int, str | None]]] = {}
    
    for pattern in PYTHON_FILE_PATTERNS:
        for filepath in directory.rglob(pattern):
            # Skip files in excluded directories
            if any(part in exclude_dirs for part in filepath.parts):
                continue
                
            try:
                strings = extract_strings_from_file(filepath)
                if strings:
                    # Use relative path as key
                    relative_path = filepath.relative_to(directory)
                    results[str(relative_path)] = strings
            except Exception as e:
                logger.warning(f"Skipping {filepath} due to error: {e}")
                continue

    total_strings = sum(len(strings) for strings in results.values())
    logger.info(f"Scanned {len(results)} files, found {total_strings} translatable strings")
    
    return results


def generate_pot_header() -> str:
    """
    Generate the header for a .pot file.

    Returns:
        POT file header string
    """
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M%z")
    
    return f'''# TGraph Bot - Tautulli Discord Graph Generator
# Copyright (C) {now.year} engels74
# This file is distributed under the same license as the TGraph Bot package.
# engels74 <141435164+engels74@users.noreply.github.com>, {now.year}.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TGraph Bot 1.0.0\\n"
"Report-Msgid-Bugs-To: https://github.com/engels74/tgraph-bot-source/issues\\n"
"POT-Creation-Date: {timestamp}\\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"
"Last-Translator: engels74 <141435164+engels74@users.noreply.github.com>\\n"
"Language-Team: LANGUAGE <LL@li.org>\\n"
"Language: \\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\\n"

'''


def generate_pot_file(
    source_directory: Path,
    output_file: Path,
    exclude_dirs: set[str] | None = None
) -> None:
    """
    Generate a .pot template file from extracted strings.

    Args:
        source_directory: Directory to scan for translatable strings
        output_file: Path where the .pot file should be written
        exclude_dirs: Set of directory names to exclude from scanning
    """
    # Extract all strings from the source directory
    all_strings = scan_directory_for_strings(source_directory, exclude_dirs)
    
    # Collect unique strings with their locations
    string_locations: dict[str, list[tuple[str, int]]] = {}
    
    for filepath, strings in all_strings.items():
        for string_value, line_number, _context in strings:
            if string_value not in string_locations:
                string_locations[string_value] = []
            string_locations[string_value].append((filepath, line_number))
    
    # Generate the .pot file content
    content = generate_pot_header()
    
    for string_value in sorted(string_locations.keys()):
        locations = string_locations[string_value]
        
        # Add location comments
        for filepath, line_number in locations:
            content += f"#: {filepath}:{line_number}\n"
        
        # Add the msgid and empty msgstr
        escaped_string = string_value.replace('"', '\\"').replace('\n', '\\n')
        content += f'msgid "{escaped_string}"\n'
        content += 'msgstr ""\n\n'
    
    # Write the .pot file
    _ = output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as file:
        _ = file.write(content)
    
    logger.info(f"Generated .pot file with {len(string_locations)} unique strings: {output_file}")


def parse_po_file(po_file: Path) -> dict[str, str]:
    """
    Parse a .po file and extract existing translations.

    Args:
        po_file: Path to the .po file to parse

    Returns:
        Dictionary mapping msgid strings to msgstr translations
    """
    translations: dict[str, str] = {}

    if not po_file.exists():
        logger.warning(f"PO file does not exist: {po_file}")
        return translations

    try:
        with open(po_file, 'r', encoding='utf-8') as file:
            content = file.read()

        # Simple regex-based parsing for msgid/msgstr pairs
        # This handles basic cases but may need enhancement for complex multiline strings
        msgid_pattern = re.compile(r'msgid\s+"([^"]*)"', re.MULTILINE)
        msgstr_pattern = re.compile(r'msgstr\s+"([^"]*)"', re.MULTILINE)

        msgids: list[str] = msgid_pattern.findall(content)
        msgstrs: list[str] = msgstr_pattern.findall(content)

        # Pair up msgids with their corresponding msgstrs
        for msgid, msgstr in zip(msgids, msgstrs, strict=False):
            if msgid and msgstr:  # Skip empty strings
                translations[msgid] = msgstr

        logger.info(f"Parsed {len(translations)} translations from {po_file}")
        return translations

    except Exception as e:
        logger.error(f"Error parsing PO file {po_file}: {e}")
        return translations


def update_po_file(pot_file: Path, po_file: Path, preserve_translations: bool = True) -> None:
    """
    Update a .po file with new strings from a .pot template while preserving existing translations.

    Args:
        pot_file: Path to the .pot template file
        po_file: Path to the .po file to update
        preserve_translations: Whether to preserve existing translations
    """
    # Parse existing translations if preserving them
    existing_translations: dict[str, str] = {}
    if preserve_translations and po_file.exists():
        existing_translations = parse_po_file(po_file)

    # Read the .pot template
    if not pot_file.exists():
        raise FileNotFoundError(f"POT template file not found: {pot_file}")

    with open(pot_file, 'r', encoding='utf-8') as file:
        pot_content = file.read()

    # Extract language from po file path for header
    language = "en"  # default
    if "LC_MESSAGES" in str(po_file):
        parts = po_file.parts
        for i, part in enumerate(parts):
            if part == "LC_MESSAGES" and i > 0:
                language = parts[i-1]
                break

    # Generate updated .po content
    po_content = generate_po_header(language)

    # Process each msgid from the pot file
    msgid_pattern = re.compile(r'(#:.*?\n)?(msgid\s+"[^"]*"\nmsgstr\s+"")', re.MULTILINE | re.DOTALL)

    for match in msgid_pattern.finditer(pot_content):
        location_comment = match.group(1) or ""
        msgid_block = match.group(2)

        # Extract the msgid string
        msgid_match = re.search(r'msgid\s+"([^"]*)"', msgid_block)
        if msgid_match:
            msgid = msgid_match.group(1)

            # Use existing translation if available, otherwise empty
            msgstr = existing_translations.get(msgid, "")

            po_content += location_comment
            po_content += f'msgid "{msgid}"\n'
            po_content += f'msgstr "{msgstr}"\n\n'

    # Write the updated .po file
    _ = po_file.parent.mkdir(parents=True, exist_ok=True)
    with open(po_file, 'w', encoding='utf-8') as file:
        _ = file.write(po_content)

    logger.info(f"Updated .po file: {po_file}")


def generate_po_header(language: str) -> str:
    """
    Generate the header for a .po file.

    Args:
        language: Language code (e.g., 'en', 'da')

    Returns:
        PO file header string
    """
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M%z")

    # Language-specific plural forms and names
    language_info = {
        "en": ("English", "nplurals=2; plural=n != 1;"),
        "da": ("Danish", "nplurals=2; plural=n != 1;"),
        "de": ("German", "nplurals=2; plural=n != 1;"),
        "fr": ("French", "nplurals=2; plural=n > 1;"),
        "es": ("Spanish", "nplurals=2; plural=n != 1;"),
    }

    language_name, plural_form = language_info.get(language, (language.title(), "nplurals=2; plural=n != 1;"))

    return f'''# {language_name} translations for TGraph Bot
# Copyright (C) {now.year} engels74
# This file is distributed under the same license as the TGraph Bot package.
# engels74 <141435164+engels74@users.noreply.github.com>, {now.year}.
#
msgid ""
msgstr ""
"Project-Id-Version: TGraph Bot 1.0.0\\n"
"Report-Msgid-Bugs-To: https://github.com/engels74/tgraph-bot-source/issues\\n"
"POT-Creation-Date: {timestamp}\\n"
"PO-Revision-Date: {timestamp}\\n"
"Last-Translator: engels74 <141435164+engels74@users.noreply.github.com>\\n"
"Language-Team: {language_name} <https://hosted.weblate.org/projects/tgraph-bot/tgraph-bot/{language}/\\n"
"Language: {language}\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: {plural_form}\\n"
"X-Generator: Weblate 5.0\\n"

'''


def compile_po_to_mo(po_file: Path, mo_file: Path | None = None) -> None:
    """
    Compile a .po file to .mo binary format.

    Args:
        po_file: Path to the .po file to compile
        mo_file: Path for the output .mo file (defaults to same location as .po)
    """
    if mo_file is None:
        mo_file = po_file.with_suffix('.mo')

    try:
        # Use msgfmt command to compile .po to .mo
        _ = subprocess.run(
            ['msgfmt', '-o', str(mo_file), str(po_file)],
            capture_output=True,
            text=True,
            check=True
        )

        logger.info(f"Compiled {po_file} to {mo_file}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to compile {po_file}: {e.stderr}")  # pyright: ignore[reportAny] # subprocess.CalledProcessError.stderr can be None
        raise
    except FileNotFoundError:
        logger.warning("msgfmt command not found. Install gettext tools to compile .po files.")
        raise
