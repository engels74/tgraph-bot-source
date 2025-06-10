# Translation Compilation Guide

This document explains how to compile translation files from `.po` (Portable Object) format to `.mo` (Machine Object) binary format for runtime use in TGraph Bot.

## Overview

Translation compilation is the process of converting human-readable `.po` files into binary `.mo` files that can be efficiently loaded by the application at runtime. This process is essential for the internationalization (i18n) system to work properly.

## Quick Start

### Compile All Translations

```bash
# Compile all .po files to .mo format
python scripts/compile_translations.py

# Compile with verbose output
python scripts/compile_translations.py --verbose
```

### Compile Specific Language

```bash
# Compile only English translations
python scripts/compile_translations.py --language en

# Compile only Danish translations
python scripts/compile_translations.py --language da
```

### Force Recompilation

```bash
# Force recompilation even if .mo files are newer
python scripts/compile_translations.py --force

# Check which files need compilation without compiling
python scripts/compile_translations.py --check-only
```

## Compilation Process

### Automatic Version Checking

The compilation system automatically checks file modification times:

- **Compile**: If `.po` file is newer than `.mo` file
- **Skip**: If `.mo` file is newer than `.po` file
- **Force**: Use `--force` to override version checking

### File Structure

```
locale/
├── en/
│   └── LC_MESSAGES/
│       ├── messages.po    # Source translation file
│       └── messages.mo    # Compiled binary file
├── da/
│   └── LC_MESSAGES/
│       ├── messages.po
│       └── messages.mo
└── messages.pot           # Template file
```

## Command-Line Tools

### compile_translations.py

Main compilation script with comprehensive options:

```bash
python scripts/compile_translations.py [OPTIONS]

Options:
  --locale-dir PATH     Locale directory path (default: locale)
  --language LANG       Compile specific language only
  --force              Force recompilation
  --check-only         Check which files need compilation
  --verbose            Enable verbose logging
  --dry-run            Show what would be done
  --help               Show help message
```

### Examples

```bash
# Basic compilation
python scripts/compile_translations.py

# Compile specific language with verbose output
python scripts/compile_translations.py --language en --verbose

# Check compilation status
python scripts/compile_translations.py --check-only

# Dry run to see what would be compiled
python scripts/compile_translations.py --dry-run

# Force recompilation of all files
python scripts/compile_translations.py --force
```

## Python API

### Basic Usage

```python
from utils.translation_compiler import compile_all_translations
from pathlib import Path

# Compile all translations
result = compile_all_translations(Path('locale'))
print(f"Compiled {result.success_count} files")

# Compile specific language
result = compile_all_translations(Path('locale'), language='en')

# Force compilation
result = compile_all_translations(Path('locale'), force=True)
```

### Single File Compilation

```python
from utils.translation_compiler import compile_translation_file
from pathlib import Path

po_file = Path('locale/en/LC_MESSAGES/messages.po')
success = compile_translation_file(po_file)
if success:
    print("File compiled successfully")
else:
    print("File was up to date")
```

### Check Compilation Status

```python
from utils.translation_compiler import get_compilation_status
from pathlib import Path

status = get_compilation_status(Path('locale'))
print(f"Total files: {status['total_files']}")
print(f"Need compilation: {len(status['needs_compilation'])}")
print(f"Up to date: {len(status['up_to_date'])}")
```

### Validate Locale Structure

```python
from utils.translation_compiler import validate_locale_structure
from pathlib import Path

validation = validate_locale_structure(Path('locale'))
if validation['valid']:
    print(f"Found {len(validation['languages'])} languages")
else:
    print("Validation errors:", validation['errors'])
```

## Integration with Development Workflow

### Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: compile-translations
        name: Compile translation files
        entry: python scripts/compile_translations.py
        language: system
        files: '\.po$'
        pass_filenames: false
```

### Build Scripts

Include in your build process:

```bash
#!/bin/bash
# build.sh

echo "Compiling translations..."
python scripts/compile_translations.py --verbose

if [ $? -ne 0 ]; then
    echo "Translation compilation failed!"
    exit 1
fi

echo "Translation compilation completed successfully"
```

### Makefile Integration

```makefile
.PHONY: compile-translations
compile-translations:
	python scripts/compile_translations.py --verbose

.PHONY: check-translations
check-translations:
	python scripts/compile_translations.py --check-only

.PHONY: force-compile-translations
force-compile-translations:
	python scripts/compile_translations.py --force --verbose
```

## Troubleshooting

### Common Issues

#### msgfmt Command Not Found

**Error**: `FileNotFoundError: msgfmt not found`

**Solution**: Install gettext tools:

```bash
# Ubuntu/Debian
sudo apt-get install gettext

# macOS with Homebrew
brew install gettext

# Windows with Chocolatey
choco install gettext
```

#### Permission Errors

**Error**: `PermissionError: [Errno 13] Permission denied`

**Solution**: Check file permissions:

```bash
# Make sure you have write permissions to the locale directory
chmod -R u+w locale/

# Or run with appropriate permissions
sudo python scripts/compile_translations.py
```

#### Invalid .po File Format

**Error**: `subprocess.CalledProcessError: msgfmt failed`

**Solution**: Validate .po file syntax:

```bash
# Check .po file syntax
msgfmt --check locale/en/LC_MESSAGES/messages.po

# Or use the validation in the script
python scripts/compile_translations.py --check-only --verbose
```

### Debugging

Enable verbose logging for detailed information:

```bash
python scripts/compile_translations.py --verbose
```

Use dry-run mode to see what would be compiled:

```bash
python scripts/compile_translations.py --dry-run --verbose
```

## Best Practices

### Development

1. **Compile after translation updates**: Always compile after updating .po files
2. **Version control**: Commit both .po and .mo files to version control
3. **Automated compilation**: Include compilation in your CI/CD pipeline
4. **Regular validation**: Periodically validate locale structure

### Production

1. **Pre-deployment compilation**: Ensure all translations are compiled before deployment
2. **Fallback handling**: Application should handle missing .mo files gracefully
3. **Performance monitoring**: Monitor translation loading performance
4. **Cache invalidation**: Clear translation caches after updates

### Maintenance

1. **Regular updates**: Keep translations up to date with source changes
2. **Quality checks**: Validate translation completeness and accuracy
3. **Backup**: Maintain backups of translation files
4. **Documentation**: Keep translation documentation current

## Related Documentation

- [Translation Guide](TRANSLATION.md) - How to contribute translations
- [Weblate Setup](WEBLATE_SETUP.md) - Collaborative translation platform
- [I18n Development](../README.md#internationalization) - Developer guide for i18n
