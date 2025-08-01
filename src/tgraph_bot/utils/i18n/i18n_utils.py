"""
String extraction utilities for internationalization (i18n).

This module provides functions to scan Python source files for translatable strings,
extract them to .pot template files, and update existing .po translation files
while preserving existing translations.

Usage Examples:
    Extract strings from source files:
        >>> from ...utils.i18n.i18n_utils import extract_strings_from_file
        >>> strings = extract_strings_from_file("bot/commands/about.py")
        >>> print(strings)
        [('Display information about the bot', 15, 'description')]

    Generate .pot file:
        >>> from ...utils.i18n.i18n_utils import generate_pot_file
        >>> generate_pot_file(".", "locale/messages.pot")

    Update .po files:
        >>> from ...utils.i18n.i18n_utils import update_po_file
        >>> update_po_file("locale/messages.pot", "locale/en/LC_MESSAGES/messages.po")
"""

from __future__ import annotations

import ast
import configparser
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, override

logger = logging.getLogger(__name__)


class WeblateConfig(NamedTuple):
    """Configuration data extracted from .weblate file."""

    url: str
    project: str
    component: str


# Translation function patterns to search for
TRANSLATION_FUNCTIONS = {
    "_",  # Standard gettext function
    "translate",  # Our custom translate function
    "t",  # Alias for translate
    "ngettext",  # Plural forms
    "nt",  # Alias for ngettext
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


def parse_weblate_config(config_path: Path | None = None) -> WeblateConfig | None:
    """
    Parse the .weblate configuration file to extract URL and component information.

    Args:
        config_path: Path to the .weblate configuration file (defaults to .weblate in project root)

    Returns:
        WeblateConfig object with parsed configuration, or None if parsing fails
    """
    if config_path is None:
        # Find project root by looking for .weblate file
        current_path = Path(__file__).resolve()
        for parent in [current_path] + list(current_path.parents):
            weblate_file = parent / ".weblate"
            if weblate_file.exists():
                config_path = weblate_file
                break

        if config_path is None:
            logger.warning("Could not find .weblate configuration file")
            return None

    if not config_path.exists():
        logger.warning(f"Weblate configuration file not found: {config_path}")
        return None

    try:
        config = configparser.ConfigParser()
        _ = config.read(config_path)

        # Extract base URL from [weblate] section
        if "weblate" not in config:
            logger.warning("Missing [weblate] section in configuration")
            return None

        weblate_section = config["weblate"]
        if "url" not in weblate_section:
            logger.warning("Missing 'url' in [weblate] section")
            return None

        base_url = weblate_section["url"].rstrip("/")

        # Find the main component section
        component_sections = [
            section for section in config.sections() if section.startswith("component ")
        ]

        if not component_sections:
            logger.warning("No component sections found in configuration")
            return None

        # Use the first component section (typically the main one)
        main_component_section = component_sections[0]
        component = config[main_component_section]

        # Extract project and component names from the section name
        # Format: 'component "project/component"' or similar
        section_name = main_component_section.replace('component "', "").replace(
            '"', ""
        )

        # Get project name from the section name or use a default
        if "/" in section_name:
            project_name = section_name.split("/")[0]
        else:
            project_name = section_name

        # Get component slug from the configuration
        component_slug = component.get("slug", "main")

        logger.debug(
            f"Parsed Weblate config: URL={base_url}, project={project_name}, component={component_slug}"
        )

        return WeblateConfig(
            url=base_url, project=project_name, component=component_slug
        )

    except Exception as e:
        logger.warning(f"Error parsing Weblate configuration: {e}")
        return None


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
                if isinstance(arg, ast.Constant):
                    # ast.Constant.value can be str, int, float, bool, None, bytes, or complex
                    # We only care about string values for translation extraction
                    value = arg.value
                    if isinstance(value, str):
                        string_value: str = value
                        line_number = node.lineno
                        context = self._extract_context(node)

                        self.strings.append((string_value, line_number, context))
                        logger.debug(
                            f"Found translatable string: '{string_value}' at line {line_number}"
                        )

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
                # ast.Constant.value can be various types, we only want strings
                value = keyword.value.value
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
        with open(filepath, "r", encoding="utf-8") as file:
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
    directory: Path, exclude_dirs: set[str] | None = None
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
    logger.info(
        f"Scanned {len(results)} files, found {total_strings} translatable strings"
    )

    return results


def generate_pot_header() -> str:
    """
    Generate the header for a .pot file.

    Returns:
        POT file header string
    """
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M%z")

    # Generate a more appropriate Language-Team placeholder based on actual config
    weblate_config = parse_weblate_config()
    if weblate_config:
        language_team_placeholder = f"LANGUAGE <{weblate_config.url}/projects/{weblate_config.project}/{weblate_config.component}/LANG/>"
        logger.debug(
            f"Using dynamic Language-Team placeholder: {language_team_placeholder}"
        )
    else:
        # Use the standard gettext placeholder if config parsing fails
        language_team_placeholder = "LANGUAGE <LL@li.org>"
        logger.debug("Using standard gettext Language-Team placeholder")

    return f"""# TGraph Bot - Tautulli Discord Graph Generator
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
"Language-Team: {language_team_placeholder}\\n"
"Language: \\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\\n"

"""


def generate_pot_file(
    source_directory: Path, output_file: Path, exclude_dirs: set[str] | None = None
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
        escaped_string = string_value.replace('"', '\\"').replace("\n", "\\n")
        content += f'msgid "{escaped_string}"\n'
        content += 'msgstr ""\n\n'

    # Write the .pot file
    _ = output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as file:
        _ = file.write(content)

    logger.info(
        f"Generated .pot file with {len(string_locations)} unique strings: {output_file}"
    )


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
        with open(po_file, "r", encoding="utf-8") as file:
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


def update_po_file(
    pot_file: Path, po_file: Path, preserve_translations: bool = True
) -> None:
    """
    Update a .po file with new strings from a .pot template while preserving existing translations.

    Args:
        pot_file: Path to the .pot template file
        po_file: Path to the .po file to update
        preserve_translations: Whether to preserve existing translations
    """
    # Parse existing translations if preserving them
    existing_translations: dict[str, str] = {}
    existing_x_generator: str | None = None

    if preserve_translations and po_file.exists():
        existing_translations = parse_po_file(po_file)

        # Also preserve the existing X-Generator header
        try:
            with open(po_file, "r", encoding="utf-8") as file:
                existing_content = file.read()
            x_gen_match = re.search(r'"X-Generator: ([^"]+)\\n"', existing_content)
            if x_gen_match:
                existing_x_generator = x_gen_match.group(1)
                logger.debug(f"Preserving existing X-Generator: {existing_x_generator}")
        except Exception as e:
            logger.debug(f"Could not extract existing X-Generator: {e}")

    # Read the .pot template
    if not pot_file.exists():
        raise FileNotFoundError(f"POT template file not found: {pot_file}")

    with open(pot_file, "r", encoding="utf-8") as file:
        pot_content = file.read()

    # Extract language from po file path for header
    language = "en"  # default
    if "LC_MESSAGES" in str(po_file):
        parts = po_file.parts
        for i, part in enumerate(parts):
            if part == "LC_MESSAGES" and i > 0:
                language = parts[i - 1]
                break

    # Generate updated .po content
    po_content = generate_po_header(language, existing_x_generator)

    # Process each msgid from the pot file, but skip the header's empty msgid
    msgid_pattern = re.compile(
        r'(#:.*?\n)?(msgid\s+"[^"]*"\nmsgstr\s+"")', re.MULTILINE | re.DOTALL
    )

    for match in msgid_pattern.finditer(pot_content):
        location_comment = match.group(1) or ""
        msgid_block = match.group(2)

        # Extract the msgid string
        msgid_match = re.search(r'msgid\s+"([^"]*)"', msgid_block)
        if msgid_match:
            msgid = msgid_match.group(1)

            # Skip the header's empty msgid (it's already included in generate_po_header)
            if msgid == "" and not location_comment.strip():
                continue

            # Use existing translation if available, otherwise empty
            msgstr = existing_translations.get(msgid, "")

            po_content += location_comment
            po_content += f'msgid "{msgid}"\n'
            po_content += f'msgstr "{msgstr}"\n\n'

    # Write the updated .po file
    _ = po_file.parent.mkdir(parents=True, exist_ok=True)
    with open(po_file, "w", encoding="utf-8") as file:
        _ = file.write(po_content)

    # Auto-fix English base language file for monolingual setup
    if language == "en":
        logger.debug("Detected English language file, applying base language fixes...")
        fix_english_base_file(po_file)

    logger.info(f"Updated .po file: {po_file}")


def generate_po_header(language: str, existing_x_generator: str | None = None) -> str:
    """
    Generate the header for a .po file.

    Args:
        language: Language code (e.g., 'en', 'da')
        existing_x_generator: Existing X-Generator value to preserve (optional)

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

    language_name, plural_form = language_info.get(
        language, (language.title(), "nplurals=2; plural=n != 1;")
    )

    # Use existing X-Generator value if available, otherwise default to Weblate 5.0
    x_generator = existing_x_generator if existing_x_generator else "Weblate 5.0"

    # Generate Language-Team URL dynamically from Weblate configuration
    weblate_config = parse_weblate_config()
    if weblate_config:
        language_team_url = f"{weblate_config.url}/projects/{weblate_config.project}/{weblate_config.component}/{language}/"
        logger.debug(f"Using dynamic Weblate URL for {language}: {language_team_url}")
    else:
        # Fallback to a generic placeholder if config parsing fails
        language_team_url = (
            f"https://weblate.example.org/projects/PROJECT/COMPONENT/{language}/"
        )
        logger.warning(
            f"Could not parse Weblate config, using placeholder URL for {language}"
        )

    return f"""# {language_name} translations for TGraph Bot
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
"Language-Team: {language_name} <{language_team_url}>\\n"
"Language: {language}\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: {plural_form}\\n"
"X-Generator: {x_generator}\\n"

"""


def compile_po_to_mo(po_file: Path, mo_file: Path | None = None) -> None:
    """
    Compile a .po file to .mo binary format.

    Args:
        po_file: Path to the .po file to compile
        mo_file: Path for the output .mo file (defaults to same location as .po)
    """
    if mo_file is None:
        mo_file = po_file.with_suffix(".mo")

    try:
        # Use msgfmt command to compile .po to .mo
        _ = subprocess.run(
            ["msgfmt", "-o", str(mo_file), str(po_file)],
            capture_output=True,
            text=True,
            check=True,
        )

        logger.info(f"Compiled {po_file} to {mo_file}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to compile {po_file}: {e.stderr}")  # pyright: ignore[reportAny] # subprocess.CalledProcessError.stderr can be None
        raise
    except FileNotFoundError:
        logger.warning(
            "msgfmt command not found. Install gettext tools to compile .po files."
        )
        raise


def fix_english_base_file(po_file: Path) -> None:
    """
    Fix English base language file by ensuring msgstr matches msgid.

    In monolingual gettext setup, the base language (English) should have
    msgstr values that match the msgid values for proper Weblate integration.

    Args:
        po_file: Path to the English .po file to fix
    """
    if not po_file.exists():
        logger.warning(f"English PO file does not exist: {po_file}")
        return

    try:
        with open(po_file, "r", encoding="utf-8") as file:
            content = file.read()

        # Track changes
        changes_made = 0
        lines = content.split("\n")
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
                        logger.debug(f"Fixed English translation: '{current_msgid}'")

            i += 1

        if changes_made > 0:
            # Write back the fixed content
            with open(po_file, "w", encoding="utf-8") as file:
                _ = file.write("\n".join(lines))
            logger.info(f"Fixed {changes_made} empty English translations in {po_file}")

    except Exception as e:
        logger.error(f"Error fixing English base file {po_file}: {e}")
