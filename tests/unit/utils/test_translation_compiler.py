"""
Tests for translation compiler utilities.

This module tests the high-level translation compilation functionality
including batch processing, status checking, and validation.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from src.tgraph_bot.utils.i18n.translation_compiler import (
    CompilationResult,
    find_po_files,
    needs_compilation,
    compile_translation_file,
    compile_all_translations,
    get_compilation_status,
    validate_locale_structure,
)


class TestCompilationResult:
    """Test the CompilationResult class."""

    def test_empty_result(self) -> None:
        """Test empty compilation result."""
        result = CompilationResult()
        
        assert result.success_count == 0
        assert result.skip_count == 0
        assert result.failure_count == 0
        assert result.success_rate == 100.0
        assert "0 compiled, 0 skipped, 0 failed" in str(result)

    def test_result_with_data(self) -> None:
        """Test compilation result with data."""
        result = CompilationResult()
        result.total_files = 10
        result.compiled_files = [Path("file1.po"), Path("file2.po")]
        result.skipped_files = [Path("file3.po")]
        result.failed_files = [(Path("file4.po"), Exception("error"))]
        
        assert result.success_count == 2
        assert result.skip_count == 1
        assert result.failure_count == 1
        assert result.success_rate == 20.0
        assert "2 compiled, 1 skipped, 1 failed" in str(result)


class TestFindPoFiles:
    """Test the find_po_files function."""

    def create_test_structure(self, base_dir: Path) -> dict[str, Path]:
        """Create test locale structure."""
        locale_dir = base_dir / "locale"
        
        # English
        en_dir = locale_dir / "en" / "LC_MESSAGES"
        en_dir.mkdir(parents=True)
        en_po = en_dir / "messages.po"
        _ = en_po.write_text("# English", encoding='utf-8')

        # Danish
        da_dir = locale_dir / "da" / "LC_MESSAGES"
        da_dir.mkdir(parents=True)
        da_po = da_dir / "messages.po"
        _ = da_po.write_text("# Danish", encoding='utf-8')
        
        return {'locale_dir': locale_dir, 'en_po': en_po, 'da_po': da_po}

    def test_find_all_po_files(self, tmp_path: Path) -> None:
        """Test finding all .po files."""
        files = self.create_test_structure(tmp_path)
        
        po_files = find_po_files(files['locale_dir'])
        
        assert len(po_files) == 2
        assert files['en_po'] in po_files
        assert files['da_po'] in po_files

    def test_find_specific_language(self, tmp_path: Path) -> None:
        """Test finding .po files for specific language."""
        files = self.create_test_structure(tmp_path)
        
        po_files = find_po_files(files['locale_dir'], 'en')
        
        assert len(po_files) == 1
        assert files['en_po'] in po_files
        assert files['da_po'] not in po_files

    def test_nonexistent_locale_dir(self, tmp_path: Path) -> None:
        """Test handling of nonexistent locale directory."""
        nonexistent = tmp_path / "nonexistent"
        
        po_files = find_po_files(nonexistent)
        
        assert po_files == []

    def test_recursive_search(self, tmp_path: Path) -> None:
        """Test recursive search functionality."""
        # Create nested structure
        locale_dir = tmp_path / "locale"
        nested_dir = locale_dir / "en" / "LC_MESSAGES" / "nested"
        nested_dir.mkdir(parents=True)
        
        po_file = nested_dir / "nested.po"
        _ = po_file.write_text("# Nested", encoding='utf-8')

        # Recursive search should find it
        po_files = find_po_files(locale_dir, recursive=True)
        assert po_file in po_files

        # Non-recursive should not
        po_files = find_po_files(locale_dir, recursive=False)
        assert po_file not in po_files


class TestNeedsCompilation:
    """Test the needs_compilation function."""

    def test_no_mo_file(self, tmp_path: Path) -> None:
        """Test when .mo file doesn't exist."""
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Test", encoding='utf-8')
        mo_file = tmp_path / "messages.mo"
        
        assert needs_compilation(po_file, mo_file) is True

    def test_mo_file_older(self, tmp_path: Path) -> None:
        """Test when .mo file is older than .po file."""
        # Create .mo file first
        mo_file = tmp_path / "messages.mo"
        _ = mo_file.write_text("# Old", encoding='utf-8')

        # Wait and create newer .po file
        time.sleep(0.1)
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# New", encoding='utf-8')

        assert needs_compilation(po_file, mo_file) is True

    def test_mo_file_newer(self, tmp_path: Path) -> None:
        """Test when .mo file is newer than .po file."""
        # Create .po file first
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Old", encoding='utf-8')

        # Wait and create newer .mo file
        time.sleep(0.1)
        mo_file = tmp_path / "messages.mo"
        _ = mo_file.write_text("# New", encoding='utf-8')
        
        assert needs_compilation(po_file, mo_file) is False

    def test_default_mo_path(self, tmp_path: Path) -> None:
        """Test using default .mo file path."""
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Test", encoding='utf-8')

        # Should use .mo extension by default
        assert needs_compilation(po_file) is True


class TestCompileTranslationFile:
    """Test the compile_translation_file function."""

    def test_successful_compilation(self, tmp_path: Path) -> None:
        """Test successful compilation."""
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Test", encoding='utf-8')
        
        with patch('src.tgraph_bot.utils.i18n.translation_compiler.compile_po_to_mo') as mock_compile:
            result = compile_translation_file(po_file)
            
            assert result is True
            mock_compile.assert_called_once()

    def test_skip_up_to_date(self, tmp_path: Path) -> None:
        """Test skipping up-to-date files."""
        # Create .po file first
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Old", encoding='utf-8')

        # Create newer .mo file
        time.sleep(0.1)
        mo_file = tmp_path / "messages.mo"
        _ = mo_file.write_text("# New", encoding='utf-8')

        with patch('src.tgraph_bot.utils.i18n.translation_compiler.compile_po_to_mo') as mock_compile:
            result = compile_translation_file(po_file, mo_file)

            assert result is False
            mock_compile.assert_not_called()

    def test_force_compilation(self, tmp_path: Path) -> None:
        """Test forced compilation."""
        # Create .po file first
        po_file = tmp_path / "messages.po"
        _ = po_file.write_text("# Old", encoding='utf-8')

        # Create newer .mo file
        time.sleep(0.1)
        mo_file = tmp_path / "messages.mo"
        _ = mo_file.write_text("# New", encoding='utf-8')
        
        with patch('src.tgraph_bot.utils.i18n.translation_compiler.compile_po_to_mo') as mock_compile:
            result = compile_translation_file(po_file, mo_file, force=True)
            
            assert result is True
            mock_compile.assert_called_once()


class TestCompileAllTranslations:
    """Test the compile_all_translations function."""

    def create_test_structure(self, base_dir: Path) -> dict[str, Path]:
        """Create test locale structure."""
        locale_dir = base_dir / "locale"
        
        # English
        en_dir = locale_dir / "en" / "LC_MESSAGES"
        en_dir.mkdir(parents=True)
        en_po = en_dir / "messages.po"
        _ = en_po.write_text("# English", encoding='utf-8')

        # Danish
        da_dir = locale_dir / "da" / "LC_MESSAGES"
        da_dir.mkdir(parents=True)
        da_po = da_dir / "messages.po"
        _ = da_po.write_text("# Danish", encoding='utf-8')
        
        return {'locale_dir': locale_dir, 'en_po': en_po, 'da_po': da_po}

    def test_compile_all_success(self, tmp_path: Path) -> None:
        """Test successful compilation of all files."""
        files = self.create_test_structure(tmp_path)
        
        with patch('src.tgraph_bot.utils.i18n.translation_compiler.compile_translation_file') as mock_compile:
            mock_compile.return_value = True
            
            result = compile_all_translations(files['locale_dir'])
            
            assert result.success_count == 2
            assert result.skip_count == 0
            assert result.failure_count == 0
            assert mock_compile.call_count == 2

    def test_compile_specific_language(self, tmp_path: Path) -> None:
        """Test compilation of specific language."""
        files = self.create_test_structure(tmp_path)
        
        with patch('src.tgraph_bot.utils.i18n.translation_compiler.compile_translation_file') as mock_compile:
            mock_compile.return_value = True
            
            result = compile_all_translations(files['locale_dir'], language='en')
            
            assert result.success_count == 1
            assert mock_compile.call_count == 1

    def test_compile_with_failures(self, tmp_path: Path) -> None:
        """Test compilation with some failures."""
        files = self.create_test_structure(tmp_path)

        def mock_compile_side_effect(po_file: Path, **_kwargs: object) -> bool:
            # Check if this is the English language directory specifically
            if '/en/LC_MESSAGES/' in str(po_file):
                return True
            else:
                raise Exception("Compilation failed")

        with patch('src.tgraph_bot.utils.i18n.translation_compiler.compile_translation_file') as mock_compile:
            mock_compile.side_effect = mock_compile_side_effect

            result = compile_all_translations(files['locale_dir'])

            assert result.success_count == 1
            assert result.failure_count == 1


class TestGetCompilationStatus:
    """Test the get_compilation_status function."""

    def test_compilation_status(self, tmp_path: Path) -> None:
        """Test getting compilation status."""
        locale_dir = tmp_path / "locale"
        en_dir = locale_dir / "en" / "LC_MESSAGES"
        en_dir.mkdir(parents=True)
        
        # Create .po file without .mo file
        po_file = en_dir / "messages.po"
        _ = po_file.write_text("# Test", encoding='utf-8')

        status = get_compilation_status(locale_dir)

        assert status['total_files'] == 1
        assert len(status['missing_mo']) == 1
        assert len(status['needs_compilation']) == 0
        assert len(status['up_to_date']) == 0


class TestValidateLocaleStructure:
    """Test the validate_locale_structure function."""

    def test_valid_structure(self, tmp_path: Path) -> None:
        """Test validation of valid locale structure."""
        locale_dir = tmp_path / "locale"
        en_dir = locale_dir / "en" / "LC_MESSAGES"
        en_dir.mkdir(parents=True)

        po_file = en_dir / "messages.po"
        _ = po_file.write_text("# Test", encoding='utf-8')
        
        validation = validate_locale_structure(locale_dir)
        
        assert validation['valid'] is True
        assert len(validation['languages']) == 1
        assert 'en' in validation['languages']
        assert validation['po_files'] == 1

    def test_nonexistent_locale_dir(self, tmp_path: Path) -> None:
        """Test validation of nonexistent locale directory."""
        nonexistent = tmp_path / "nonexistent"
        
        validation = validate_locale_structure(nonexistent)
        
        assert validation['valid'] is False
        assert len(validation['errors']) > 0

    def test_missing_lc_messages(self, tmp_path: Path) -> None:
        """Test validation with missing LC_MESSAGES directory."""
        locale_dir = tmp_path / "locale"
        en_dir = locale_dir / "en"
        en_dir.mkdir(parents=True)
        
        validation = validate_locale_structure(locale_dir)
        
        assert len(validation['warnings']) > 0
        assert any('LC_MESSAGES' in warning for warning in validation['warnings'])
