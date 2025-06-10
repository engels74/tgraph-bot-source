# Weblate Setup Guide for Developers

This guide explains how to set up and configure Weblate for the TGraph Bot project.

## Overview

Weblate is configured via the `.weblate` file in the project root. This file defines:
- Project components (bot interface and documentation)
- File paths and patterns for translation files
- Workflow settings and quality checks
- Repository integration settings

## Initial Setup

### 1. Weblate Project Creation

1. **Sign up for Weblate**
   - Visit https://hosted.weblate.org/
   - Create an account or sign in with GitHub

2. **Create New Project**
   - Click "Add new project"
   - Use the `.weblate` configuration file to set up components
   - Configure repository access (GitHub integration)

3. **Import Configuration**
   - Upload the `.weblate` file or manually configure components
   - Verify file paths and repository settings

### 2. Repository Integration

The configuration includes:
```ini
repo = https://github.com/engels74/tgraph-bot-source.git
push = git@github.com:engels74/tgraph-bot-source.git
branch = main
```

**Important**: Translations target the `main` branch, even though development happens on feature branches.

### 3. Component Configuration

#### TGraph Bot Component
- **Purpose**: Main bot interface translations
- **Files**: `locale/*/LC_MESSAGES/messages.po`
- **Template**: `locale/messages.pot`
- **Quality Checks**: Python format validation, consistency checks

#### README Component  
- **Purpose**: Documentation translations
- **Files**: `docs/README.*.md`
- **Template**: `README.md`
- **Format**: Markdown

## Workflow Integration

### For Developers

1. **Extract Strings**
   ```bash
   # Extract new translatable strings
   python scripts/extract_strings.py
   
   # This updates locale/messages.pot
   ```

2. **Update Translations**
   ```bash
   # Update all .po files with new strings
   python scripts/update_translations.py
   
   # Compile to .mo files for production
   python scripts/update_translations.py --compile
   ```

3. **Validate Configuration**
   ```bash
   # Check Weblate configuration
   python scripts/validate_weblate_config.py
   ```

### For Translators

1. **Access Weblate**
   - Visit the project URL on hosted.weblate.org
   - Select your language
   - Start translating

2. **Translation Process**
   - Weblate automatically syncs with the repository
   - Changes are committed back to the main branch
   - Quality checks run automatically

## Quality Assurance

### Automatic Checks

The configuration enables several quality checks:
- **Format consistency**: Ensures Python format strings are preserved
- **Punctuation**: Validates punctuation consistency
- **Whitespace**: Checks spacing and line breaks
- **Translation completeness**: Tracks translation progress

### Manual Review

- **Peer review**: Translators can review each other's work
- **Voting system**: Community can vote on translation quality
- **Comments**: Context and discussion for difficult translations

## File Structure

```
locale/
├── messages.pot              # Template file (source strings)
├── en/LC_MESSAGES/
│   ├── messages.po          # English translations
│   └── messages.mo          # Compiled binary (generated)
└── da/LC_MESSAGES/
    ├── messages.po          # Danish translations
    └── messages.mo          # Compiled binary (generated)

docs/
├── README.md                # Main documentation (template)
├── README.da.md            # Danish documentation
└── TRANSLATION.md          # Translation guide
```

## Adding New Languages

1. **Request Language**
   - Open GitHub issue requesting new language
   - Specify language code (ISO 639-1)

2. **Update Configuration**
   - Language regex in `.weblate` supports standard codes
   - No configuration changes needed for most languages

3. **Create Directory Structure**
   ```bash
   # Example for French (fr)
   mkdir -p locale/fr/LC_MESSAGES
   
   # Initialize .po file
   python scripts/update_translations.py --language fr
   ```

## Troubleshooting

### Common Issues

1. **File Not Found Errors**
   - Ensure `locale/messages.pot` exists
   - Run string extraction if missing

2. **Permission Issues**
   - Check GitHub repository access
   - Verify SSH key configuration for push access

3. **Format Validation Errors**
   - Ensure Python format strings are preserved
   - Check for missing placeholders like `{name}`

### Validation Commands

```bash
# Check configuration
python scripts/validate_weblate_config.py

# Test translation loading
python -c "import i18n; i18n.setup_i18n('da'); print(i18n._('Test'))"

# Verify file structure
find locale -name "*.po" -o -name "*.pot"
```

## Maintenance

### Regular Tasks

1. **Weekly**: Extract new strings from code changes
2. **Before releases**: Ensure translations are up to date
3. **Monthly**: Review translation quality and completeness

### Automation Opportunities

- **CI/CD Integration**: Automatic string extraction on commits
- **Release Automation**: Compile translations during deployment
- **Quality Monitoring**: Track translation coverage metrics

## Security Considerations

- **Repository Access**: Weblate needs push access to commit translations
- **Branch Protection**: Consider protecting main branch with required reviews
- **Contributor Management**: Monitor translator access and permissions

## Support

### Getting Help

- **Weblate Documentation**: https://docs.weblate.org/
- **Project Issues**: Use GitHub issues for project-specific problems
- **Translation Questions**: Use Weblate's comment system

### Contact

- **Project Maintainer**: engels74
- **Repository**: https://github.com/engels74/tgraph-bot-source
- **Weblate Project**: https://hosted.weblate.org/projects/tgraph-bot/

---

This setup enables collaborative translation management while maintaining code quality and project workflow integration.
