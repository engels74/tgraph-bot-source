#!/usr/bin/env python3
"""
Validate Weblate configuration for TGraph Bot.

This script checks the .weblate configuration file to ensure it's properly
configured for the project structure and validates that all referenced files
and directories exist.

Usage:
    python scripts/weblate/validate_config.py
"""

from __future__ import annotations

import configparser
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def validate_weblate_config(config_path: Path | None = None) -> bool:
    """
    Validate the Weblate configuration file.

    Args:
        config_path: Path to the .weblate configuration file

    Returns:
        True if configuration is valid, False otherwise
    """
    if config_path is None:
        config_path = Path(".weblate")

    if not config_path.exists():
        logger.error(f"Weblate configuration file not found: {config_path}")
        return False

    try:
        config = configparser.ConfigParser()
        _ = config.read(config_path)

        # Validate main weblate section
        if "weblate" not in config:
            logger.error("Missing [weblate] section in configuration")
            return False

        weblate_section = config["weblate"]
        if "url" not in weblate_section:
            logger.error("Missing 'url' in [weblate] section")
            return False

        logger.info(f"Weblate URL: {weblate_section['url']}")

        # Validate components
        components = [
            section
            for section in config.sections()
            if section.startswith("component ")
        ]

        if not components:
            logger.error("No components found in configuration")
            return False

        logger.info(f"Found {len(components)} component(s)")

        all_valid = True
        for component_section in components:
            component_name = component_section.replace('component "', "").replace(
                '"', ""
            )
            logger.info(f"Validating component: {component_name}")

            component = config[component_section]

            # Check required fields
            required_fields = [
                "name",
                "slug",
                "repo",
                "push",
                "branch",
                "filemask",
                "template",
                "file_format",
            ]

            for field in required_fields:
                if field not in component:
                    logger.error(
                        f"Missing required field '{field}' in component {component_name}"
                    )
                    all_valid = False
                    continue

                logger.debug(f"  {field}: {component[field]}")

            # Validate file paths
            if "template" in component:
                template_path = Path(component["template"])
                if not template_path.exists():
                    logger.warning(f"Template file not found: {template_path}")
                    # This is a warning, not an error, as the file might not exist yet
                else:
                    logger.info(f"  Template file exists: {template_path}")

            # Validate filemask pattern
            if "filemask" in component:
                filemask = component["filemask"]
                if "*" not in filemask:
                    logger.warning(f"Filemask doesn't contain wildcard: {filemask}")

                # Check if the directory structure exists
                if "locale/" in filemask:
                    locale_dir = Path("locale")
                    if not locale_dir.exists():
                        logger.warning(f"Locale directory not found: {locale_dir}")
                    else:
                        logger.info(f"  Locale directory exists: {locale_dir}")

        return all_valid

    except Exception as e:
        logger.error(f"Error reading configuration file: {e}")
        return False


def check_locale_structure() -> bool:
    """
    Check if the locale directory structure is properly set up.

    Returns:
        True if structure is valid, False otherwise
    """
    locale_dir = Path("locale")

    if not locale_dir.exists():
        logger.error("Locale directory does not exist")
        return False

    # Check for messages.pot template
    pot_file = locale_dir / "messages.pot"
    if not pot_file.exists():
        logger.warning(f"Template file not found: {pot_file}")
        logger.info("Run 'python scripts/i18n/extract_strings.py' to generate it")
    else:
        logger.info(f"Template file exists: {pot_file}")

    # Check for language directories
    language_dirs = [
        d for d in locale_dir.iterdir() if d.is_dir() and d.name != "__pycache__"
    ]

    if not language_dirs:
        logger.warning("No language directories found in locale/")
        return True  # This is OK for a new project

    logger.info(f"Found {len(language_dirs)} language directories:")

    for lang_dir in language_dirs:
        logger.info(f"  {lang_dir.name}")

        # Check LC_MESSAGES structure
        lc_messages = lang_dir / "LC_MESSAGES"
        if not lc_messages.exists():
            logger.warning(f"Missing LC_MESSAGES directory: {lc_messages}")
            continue

        # Check for .po file
        po_file = lc_messages / "messages.po"
        if not po_file.exists():
            logger.warning(f"Missing .po file: {po_file}")
        else:
            logger.info(f"    .po file exists: {po_file}")

        # Check for .mo file
        mo_file = lc_messages / "messages.mo"
        if not mo_file.exists():
            logger.info(f"    .mo file not found: {mo_file} (will be generated)")
        else:
            logger.info(f"    .mo file exists: {mo_file}")

    return True


def main() -> int:
    """
    Main function to validate Weblate configuration.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("Validating Weblate configuration...")

    try:
        # Validate configuration file
        config_valid = validate_weblate_config()

        # Check locale structure
        locale_valid = check_locale_structure()

        if config_valid and locale_valid:
            logger.info("✅ Weblate configuration is valid!")
            logger.info(
                "You can now set up your project on Weblate using this configuration."
            )
            return 0
        else:
            logger.error(
                "❌ Weblate configuration has issues that need to be addressed."
            )
            return 1

    except KeyboardInterrupt:
        logger.info("Validation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
