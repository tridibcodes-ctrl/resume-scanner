"""Text extraction from PDF and TXT files using pdfplumber."""

import re
import io
import pdfplumber
from pathlib import Path


def extract_text_from_pdf(file_path: str | Path) -> str:
    """
    Extract clean text from a PDF file using pdfplumber.
    
    Handles multi-page PDFs and normalizes whitespace 
    for downstream processing.
    """
    pages = []
    with pdfplumber.open(str(file_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                pages.append(text)

    raw_text = "\n".join(pages)
    return _normalize_text(raw_text)


def extract_text_from_pdf_bytes(file_bytes: bytes, filename: str = "upload.pdf") -> str:
    """Extract text from PDF bytes (for in-memory uploads)."""
    pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                pages.append(text)

    raw_text = "\n".join(pages)
    return _normalize_text(raw_text)


def extract_text_from_txt(file_path: str | Path) -> str:
    """Extract and normalize text from a plain text file."""
    path = Path(file_path)
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    return _normalize_text(raw_text)


def extract_text_from_txt_bytes(file_bytes: bytes) -> str:
    """Extract text from TXT bytes."""
    raw_text = file_bytes.decode("utf-8", errors="replace")
    return _normalize_text(raw_text)


def extract_text(file_path: str | Path) -> str:
    """
    Auto-detect file type and extract text.
    
    Supports: .pdf, .txt
    Raises ValueError for unsupported formats.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext == ".txt":
        return extract_text_from_txt(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Supported: .pdf, .txt")


def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    """Extract text from file bytes based on filename extension."""
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf_bytes(file_bytes, filename)
    elif ext == ".txt":
        return extract_text_from_txt_bytes(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Supported: .pdf, .txt")


# ─── Text Normalization ──────────────────────────────────────────────────────


def _normalize_text(text: str) -> str:
    """
    Normalize extracted text for downstream processing.
    
    - Replaces various unicode whitespace with standard space
    - Collapses multiple blank lines into a single blank line
    - Strips control characters (except newlines/tabs)
    - Strips leading/trailing whitespace
    """
    # Replace common unicode whitespace variants
    text = text.replace("\u00a0", " ")  # non-breaking space
    text = text.replace("\u200b", "")   # zero-width space
    text = text.replace("\ufeff", "")   # BOM
    text = text.replace("\r\n", "\n")   # Windows line endings
    text = text.replace("\r", "\n")     # Old Mac line endings

    # Remove control characters except newline and tab
    text = re.sub(r"[^\S\n\t]+", " ", text)

    # Collapse 3+ consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()
