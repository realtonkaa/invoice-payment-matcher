"""
invoice_parser.py — Extract raw text from invoice files.

Supports:
- PDF files via pdfplumber (direct text extraction, fast and accurate)
- Image-based PDFs via pytesseract OCR (fallback for scanned documents)
- Plain .txt files (for testing without real PDFs)
"""

import os
from typing import Optional


def _extract_from_txt(filepath: str) -> str:
    """Read a plain text file and return its contents."""
    with open(filepath, "r", encoding="utf-8") as fh:
        return fh.read()


def _extract_from_pdf_pdfplumber(filepath: str) -> str:
    """
    Extract text from a PDF using pdfplumber.
    Returns the concatenated text of all pages.
    Returns an empty string if pdfplumber is not installed or extraction fails.
    """
    try:
        import pdfplumber
    except ImportError:
        return ""

    text_parts = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception:
        return ""

    return "\n".join(text_parts)


def _extract_from_pdf_ocr(filepath: str) -> str:
    """
    Extract text from a PDF by converting pages to images and running OCR.
    Used as a fallback when pdfplumber returns empty text (scanned PDFs).
    Returns an empty string if dependencies are not available.
    """
    try:
        import pytesseract
        from PIL import Image
        import pdfplumber
    except ImportError:
        return ""

    text_parts = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                img = page.to_image(resolution=200).original
                page_text = pytesseract.image_to_string(img)
                if page_text:
                    text_parts.append(page_text)
    except Exception:
        return ""

    return "\n".join(text_parts)


def extract_text(filepath: str) -> str:
    """
    Extract raw text from an invoice file.

    Strategy:
    1. If the file is a .txt, read it directly (for testing).
    2. If the file is a .pdf, try pdfplumber first.
    3. If pdfplumber returns no text (scanned document), fall back to OCR.

    Parameters
    ----------
    filepath : str
        Absolute or relative path to the invoice file.

    Returns
    -------
    str
        The extracted text, or an empty string if extraction fails.
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".txt":
        return _extract_from_txt(filepath)

    if ext == ".pdf":
        text = _extract_from_pdf_pdfplumber(filepath)
        if text.strip():
            return text
        # Fallback to OCR for scanned documents
        return _extract_from_pdf_ocr(filepath)

    # Unsupported format — return empty string and let the caller decide
    return ""


def extract_texts_from_directory(directory: str) -> dict:
    """
    Extract text from all supported invoice files in a directory.

    Returns a dict mapping filename -> extracted text.
    Supports .pdf and .txt files.
    """
    results = {}
    supported = {".pdf", ".txt"}

    for filename in sorted(os.listdir(directory)):
        ext = os.path.splitext(filename)[1].lower()
        if ext in supported:
            filepath = os.path.join(directory, filename)
            results[filename] = extract_text(filepath)

    return results
