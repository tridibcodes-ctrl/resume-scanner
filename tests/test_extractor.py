"""Tests for the text extraction service."""

import pytest
from pathlib import Path

from services.extractor import (
    extract_text_from_txt,
    extract_text,
    _normalize_text,
)

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data" / "resumes"


class TestNormalizeText:
    """Test text normalization."""

    def test_collapses_whitespace(self):
        text = "Hello   world\t\tthere"
        result = _normalize_text(text)
        assert "   " not in result

    def test_collapses_multiple_newlines(self):
        text = "Line 1\n\n\n\n\nLine 2"
        result = _normalize_text(text)
        assert result == "Line 1\n\nLine 2"

    def test_strips_bom(self):
        text = "\ufeffHello world"
        result = _normalize_text(text)
        assert result == "Hello world"

    def test_handles_windows_line_endings(self):
        text = "Line 1\r\nLine 2\r\nLine 3"
        result = _normalize_text(text)
        assert "\r" not in result
        assert "Line 1\nLine 2\nLine 3" == result

    def test_strips_leading_trailing(self):
        text = "\n\n  Hello  \n\n"
        result = _normalize_text(text)
        assert result == "Hello"


class TestTxtExtraction:
    """Test plain text file extraction."""

    def test_extract_sample_resume(self):
        """Verify sample TXT resume produces non-empty text."""
        sample = SAMPLE_DIR / "alice_johnson_senior_dev.txt"
        if not sample.exists():
            pytest.skip("Sample data not found")

        text = extract_text_from_txt(sample)
        assert len(text) > 100
        assert "Alice Johnson" in text
        assert "alice.johnson@email.com" in text

    def test_extract_all_samples(self):
        """Verify all sample resumes produce non-empty text."""
        if not SAMPLE_DIR.exists():
            pytest.skip("Sample data directory not found")

        for txt_file in SAMPLE_DIR.glob("*.txt"):
            text = extract_text_from_txt(txt_file)
            assert len(text) > 50, f"Empty extraction from {txt_file.name}"


class TestExtractDispatch:
    """Test the auto-detect extraction function."""

    def test_unsupported_format_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            extract_text(Path("resume.docx"))

    def test_txt_dispatch(self):
        sample = SAMPLE_DIR / "alice_johnson_senior_dev.txt"
        if not sample.exists():
            pytest.skip("Sample data not found")
        text = extract_text(sample)
        assert "Alice Johnson" in text
