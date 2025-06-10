# Translation Guide for TGraph Bot

This document explains how to contribute translations to TGraph Bot using Weblate, our collaborative translation platform.

## Overview

TGraph Bot uses [Weblate](https://weblate.org/) for managing translations. Weblate is a web-based translation tool that makes it easy for translators to contribute without needing technical knowledge of Git or gettext.

## Getting Started with Weblate

### 1. Access the Translation Project

Visit our Weblate project at: https://hosted.weblate.org/projects/tgraph-bot/

### 2. Create an Account

If you don't have a Weblate account:
1. Click "Register" on the Weblate homepage
2. Fill in your details or sign in with GitHub/Google
3. Verify your email address

### 3. Join the Translation Team

1. Navigate to the TGraph Bot project
2. Select the language you want to translate
3. Click "Start translating" to begin

## Translation Components

Our project has two main translation components:

### TGraph Bot (Main Interface)
- **Purpose**: Bot commands, messages, and user interface text
- **Files**: `locale/*/LC_MESSAGES/messages.po`
- **Template**: `locale/messages.pot`
- **Priority**: High - these are the strings users see most

### TGraph Bot README (Documentation)
- **Purpose**: README file translations for different languages
- **Files**: `docs/README.*.md`
- **Template**: `README.md`
- **Priority**: Medium - helps non-English users understand the project

## Translation Workflow

### For Translators

1. **Choose Your Language**
   - Select your target language from the project page
   - If your language isn't available, request it by opening an issue

2. **Translate Strings**
   - Click on untranslated strings (marked in red)
   - Enter your translation in the text field
   - Use the suggestions and machine translations as starting points
   - Save your translation

3. **Review and Improve**
   - Review existing translations for accuracy
   - Vote on suggested translations
   - Add comments for context when needed

4. **Quality Checks**
   - Weblate automatically runs quality checks
   - Fix any issues highlighted in red
   - Ensure formatting placeholders (like `{name}`) are preserved

### For Developers

1. **Extract New Strings**
   ```bash
   # Extract translatable strings from source code
   python scripts/extract_strings.py
   
   # Update existing translation files
   python scripts/update_translations.py
   ```

2. **Test Translations**
   ```bash
   # Test with a specific language
   python -c "import i18n; i18n.setup_i18n('da'); print(i18n._('Hello, world!'))"
   ```

3. **Compile Translations**
   ```bash
   # Compile .po files to .mo for production
   python scripts/update_translations.py --compile
   ```

## Supported Languages

Currently supported languages:
- **English (en)** - Base language
- **Danish (da)** - Primary target language

To request a new language:
1. Open an issue on GitHub
2. Specify the language code (e.g., 'fr' for French)
3. We'll add it to the Weblate configuration

## Translation Guidelines

### General Principles

1. **Consistency**: Use consistent terminology throughout
2. **Context**: Consider the context where the text appears
3. **Tone**: Match the friendly, helpful tone of the original
4. **Technical Terms**: Keep technical terms in English when appropriate

### Formatting Rules

1. **Placeholders**: Always preserve formatting placeholders
   - `{name}` → `{name}` (keep exactly as is)
   - `%s` → `%s` (keep exactly as is)

2. **Discord Formatting**: Preserve Discord markdown
   - `**bold**` → `**bold**`
   - `*italic*` → `*italic*`
   - `` `code` `` → `` `code` ``

3. **Line Breaks**: Preserve line breaks in multi-line strings

### Examples

```
Original: "Hello, {name}! Welcome to TGraph Bot."
Danish: "Hej, {name}! Velkommen til TGraph Bot."

Original: "**Error**: Could not connect to Tautulli API"
Danish: "**Fejl**: Kunne ikke forbinde til Tautulli API"
```

## Quality Assurance

### Automatic Checks

Weblate runs several automatic quality checks:
- **Format consistency**: Ensures placeholders are preserved
- **Punctuation**: Checks for consistent punctuation
- **Whitespace**: Validates spacing and line breaks
- **Python format**: Validates Python string formatting

### Manual Review

1. **Peer Review**: Other translators can review and vote on translations
2. **Context Comments**: Add comments to explain difficult translations
3. **Suggestions**: Use the suggestion system for alternative translations

## Getting Help

### Translation Questions
- Use Weblate's comment system for specific strings
- Join our Discord server for real-time discussion
- Open GitHub issues for broader translation questions

### Technical Issues
- Report Weblate bugs to the Weblate team
- Report project-specific issues on our GitHub repository

### Resources
- [Weblate Documentation](https://docs.weblate.org/)
- [GNU gettext Manual](https://www.gnu.org/software/gettext/manual/)
- [Discord Markdown Guide](https://support.discord.com/hc/en-us/articles/210298617)

## Contributing

### For New Contributors
1. Start with short, simple strings
2. Read existing translations for context
3. Don't hesitate to ask questions
4. Use the suggestion system when unsure

### For Experienced Translators
1. Help review other translations
2. Maintain translation glossaries
3. Provide feedback on translation quality
4. Help onboard new translators

## Maintenance

### Regular Tasks
- **Weekly**: Review new strings and update translations
- **Monthly**: Quality review of existing translations
- **Release**: Ensure all strings are translated before releases

### Automation
- String extraction runs automatically on code changes
- Translation files are updated via Weblate integration
- Compiled .mo files are generated during deployment

Thank you for helping make TGraph Bot accessible to users worldwide! 🌍
