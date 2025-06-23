"""
Tests for translation compilation functionality.

This module tests the compilation of .po files to .mo format including
version checking, batch compilation, and error handling.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from utils.i18n.i18n_utils import compile_po_to_mo


class TestCompilePoToMo:
    """Test the compile_po_to_mo function."""

    def test_compile_po_to_mo_success(self, tmp_path: Path) -> None:
        """Test successful compilation of .po to .mo file."""
        # Create a simple .po file
        po_file = tmp_path / "messages.po"
        po_content = '''# Test translation file
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"

msgid "Hello"
msgstr "Hej"
'''
        _ = po_file.write_text(po_content, encoding='utf-8')

        mo_file = tmp_path / "messages.mo"

        # Mock subprocess.run to simulate successful msgfmt execution
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            compile_po_to_mo(po_file, mo_file)
            
            # Verify msgfmt was called with correct arguments
            mock_run.assert_called_once_with(
                ['msgfmt', '-o', str(mo_file), str(po_file)],
                capture_output=True,
                text=True,
                check=True
            )

    def test_compile_po_to_mo_default_output(self, tmp_path: Path) -> None:
        """Test compilation with default .mo file path."""
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Empty po file", encoding='utf-8')

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            compile_po_to_mo(po_file)
            
            # Should use .mo extension in same directory
            expected_mo = po_file.with_suffix('.mo')
            mock_run.assert_called_once_with(
                ['msgfmt', '-o', str(expected_mo), str(po_file)],
                capture_output=True,
                text=True,
                check=True
            )

    def test_compile_po_to_mo_msgfmt_error(self, tmp_path: Path) -> None:
        """Test handling of msgfmt compilation errors."""
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Invalid po file", encoding='utf-8')

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, 'msgfmt', stderr='Invalid format'
            )
            
            with pytest.raises(subprocess.CalledProcessError):
                compile_po_to_mo(po_file)

    def test_compile_po_to_mo_msgfmt_not_found(self, tmp_path: Path) -> None:
        """Test handling when msgfmt command is not found."""
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Test po file", encoding='utf-8')

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("msgfmt not found")
            
            with pytest.raises(FileNotFoundError):
                compile_po_to_mo(po_file)


class TestCompilationScript:
    """Test the compilation script functionality."""

    def create_test_locale_structure(self, base_dir: Path) -> dict[str, Path]:
        """
        Create a test locale directory structure.

        Args:
            base_dir: Base directory to create structure in

        Returns:
            Dictionary mapping language codes to .po file paths
        """
        locale_dir = base_dir / "locale"
        
        # Create English locale
        en_dir = locale_dir / "en" / "LC_MESSAGES"
        en_dir.mkdir(parents=True)
        en_po = en_dir / "messages.po"
        _ = en_po.write_text('''# English translations
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"

msgid "Hello"
msgstr "Hello"
''', encoding='utf-8')

        # Create Danish locale
        da_dir = locale_dir / "da" / "LC_MESSAGES"
        da_dir.mkdir(parents=True)
        da_po = da_dir / "messages.po"
        _ = da_po.write_text('''# Danish translations
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"

msgid "Hello"
msgstr "Hej"
''', encoding='utf-8')

        return {
            'en': en_po,
            'da': da_po,
            'locale_dir': locale_dir
        }

    def test_find_po_files_all_languages(self, tmp_path: Path) -> None:
        """Test finding all .po files in locale directory."""
        from scripts.i18n.compile_translations import find_po_files
        
        files = self.create_test_locale_structure(tmp_path)
        locale_dir = files['locale_dir']
        
        po_files = find_po_files(locale_dir)
        
        assert len(po_files) == 2
        assert files['en'] in po_files
        assert files['da'] in po_files

    def test_find_po_files_specific_language(self, tmp_path: Path) -> None:
        """Test finding .po files for specific language."""
        from scripts.i18n.compile_translations import find_po_files
        
        files = self.create_test_locale_structure(tmp_path)
        locale_dir = files['locale_dir']
        
        po_files = find_po_files(locale_dir, 'en')
        
        assert len(po_files) == 1
        assert files['en'] in po_files
        assert files['da'] not in po_files

    def test_needs_compilation_no_mo_file(self, tmp_path: Path) -> None:
        """Test that compilation is needed when .mo file doesn't exist."""
        from scripts.i18n.compile_translations import needs_compilation
        
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Test", encoding='utf-8')
        mo_file = tmp_path / "messages.mo"

        assert needs_compilation(po_file, mo_file) is True

    def test_needs_compilation_mo_older(self, tmp_path: Path) -> None:
        """Test that compilation is needed when .mo file is older than .po."""
        from scripts.i18n.compile_translations import needs_compilation

        # Create .mo file first
        mo_file = tmp_path / "messages.mo"
        _ = mo_file.write_text("# Old mo file", encoding='utf-8')

        # Wait a bit and create .po file
        time.sleep(0.1)
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# New po file", encoding='utf-8')
        
        assert needs_compilation(po_file, mo_file) is True

    def test_needs_compilation_mo_newer(self, tmp_path: Path) -> None:
        """Test that compilation is not needed when .mo file is newer than .po."""
        from scripts.i18n.compile_translations import needs_compilation
        
        # Create .po file first
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Old po file", encoding='utf-8')

        # Wait a bit and create .mo file
        time.sleep(0.1)
        mo_file = tmp_path / "messages.mo"
        _ = mo_file.write_text("# New mo file", encoding='utf-8')
        
        assert needs_compilation(po_file, mo_file) is False

    def test_compile_file_success(self, tmp_path: Path) -> None:
        """Test successful compilation of a single file."""
        from scripts.i18n.compile_translations import compile_file

        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Test po file", encoding='utf-8')

        with patch('scripts.i18n.compile_translations.compile_po_to_mo') as mock_compile:
            result = compile_file(po_file)

            assert result is True
            mock_compile.assert_called_once()

    def test_compile_file_up_to_date(self, tmp_path: Path) -> None:
        """Test skipping compilation when file is up to date."""
        from scripts.i18n.compile_translations import compile_file

        # Create .po file first
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Old po file", encoding='utf-8')

        # Create newer .mo file
        time.sleep(0.1)
        mo_file = tmp_path / "messages.mo"
        _ = mo_file.write_text("# New mo file", encoding='utf-8')

        with patch('scripts.i18n.compile_translations.compile_po_to_mo') as mock_compile:
            result = compile_file(po_file)

            assert result is False
            mock_compile.assert_not_called()

    def test_compile_file_force(self, tmp_path: Path) -> None:
        """Test forced compilation even when file is up to date."""
        from scripts.i18n.compile_translations import compile_file

        # Create .po file first
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Old po file", encoding='utf-8')

        # Create newer .mo file
        time.sleep(0.1)
        mo_file = tmp_path / "messages.mo"
        _ = mo_file.write_text("# New mo file", encoding='utf-8')

        with patch('scripts.i18n.compile_translations.compile_po_to_mo') as mock_compile:
            result = compile_file(po_file, force=True)

            assert result is True
            mock_compile.assert_called_once()

    def test_compile_file_dry_run(self, tmp_path: Path) -> None:
        """Test dry run mode doesn't actually compile."""
        from scripts.i18n.compile_translations import compile_file

        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Test po file", encoding='utf-8')

        with patch('scripts.i18n.compile_translations.compile_po_to_mo') as mock_compile:
            result = compile_file(po_file, dry_run=True)

            assert result is True
            mock_compile.assert_not_called()
