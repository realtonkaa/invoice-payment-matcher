"""
test_extractor.py — Tests for invoice data extraction from raw text.
"""

import os
import pytest
from src.extractor import (
    extract_invoice_data_regex,
    extract_invoice_data,
    _parse_amount,
    _search_patterns,
    _INVOICE_NUMBER_PATTERNS,
    _AMOUNT_PATTERNS,
)


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "sample_invoices")


# ---------------------------------------------------------------------------
# Tests for helper utilities
# ---------------------------------------------------------------------------

def test_parse_amount_standard():
    assert _parse_amount("1500.00") == 1500.00


def test_parse_amount_with_commas():
    assert _parse_amount("1,500.00") == 1500.00


def test_parse_amount_none():
    assert _parse_amount(None) is None


def test_parse_amount_invalid():
    assert _parse_amount("N/A") is None


def test_search_patterns_finds_match():
    text = "Invoice Number: INV-001"
    result = _search_patterns(text, _INVOICE_NUMBER_PATTERNS)
    assert result is not None
    assert "INV" in result or "001" in result


def test_search_patterns_no_match():
    result = _search_patterns("No relevant content here", _INVOICE_NUMBER_PATTERNS)
    assert result is None


# ---------------------------------------------------------------------------
# Tests for extract_invoice_data_regex against inline text
# ---------------------------------------------------------------------------

SAMPLE_INVOICE_TEXT_1 = """
INVOICE

Invoice Number: INV-2026-001
Invoice Date: 2026-01-15

Bill To:
Acme Corporation

Description                    Amount
Consulting Services             $2,500.00

Total Amount Due: $2,500.00
"""

SAMPLE_INVOICE_TEXT_2 = """
Tax Invoice

Inv #: 2026-042
Date: 2026-02-10

Customer: Smith LLC

Services Rendered: $1,750.00
Grand Total: $1,750.00
"""

SAMPLE_INVOICE_TEXT_3 = """
INVOICE

Bill To: Johnson and Associates
Invoice No. INV-003
Date Issued: 2026-01-22

Amount Due: $4200.00
"""


def test_extract_invoice_number_standard():
    data = extract_invoice_data_regex(SAMPLE_INVOICE_TEXT_1)
    assert data["invoice_number"] is not None
    assert "INV" in data["invoice_number"].upper() or "001" in data["invoice_number"]


def test_extract_amount_standard():
    data = extract_invoice_data_regex(SAMPLE_INVOICE_TEXT_1)
    assert data["amount"] == 2500.00


def test_extract_amount_text2():
    data = extract_invoice_data_regex(SAMPLE_INVOICE_TEXT_2)
    assert data["amount"] == 1750.00


def test_extract_amount_text3():
    data = extract_invoice_data_regex(SAMPLE_INVOICE_TEXT_3)
    assert data["amount"] == 4200.00


def test_extract_date_standard():
    data = extract_invoice_data_regex(SAMPLE_INVOICE_TEXT_1)
    assert data["date"] is not None
    assert "2026" in data["date"]


def test_extract_client_name():
    data = extract_invoice_data_regex(SAMPLE_INVOICE_TEXT_1)
    # Client name extraction is best-effort; check it returns something or None
    if data["client_name"] is not None:
        assert isinstance(data["client_name"], str)
        assert len(data["client_name"]) > 0


def test_extract_returns_none_for_missing_fields():
    data = extract_invoice_data_regex("This text has no invoice fields.")
    assert data["amount"] is None
    assert data["invoice_number"] is None


def test_extract_invoice_data_delegates_to_regex_by_default():
    text = SAMPLE_INVOICE_TEXT_1
    result = extract_invoice_data(text, use_llm=False)
    assert result["amount"] == 2500.00


# ---------------------------------------------------------------------------
# Tests against fixture files
# ---------------------------------------------------------------------------

def test_fixture_invoice_1_amount():
    path = os.path.join(FIXTURES_DIR, "invoice_001.txt")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    data = extract_invoice_data_regex(text)
    assert data["amount"] is not None
    assert data["amount"] > 0


def test_fixture_invoice_2_amount():
    path = os.path.join(FIXTURES_DIR, "invoice_002.txt")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    data = extract_invoice_data_regex(text)
    assert data["amount"] is not None
    assert data["amount"] > 0


def test_fixture_invoice_3_amount():
    path = os.path.join(FIXTURES_DIR, "invoice_003.txt")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    data = extract_invoice_data_regex(text)
    assert data["amount"] is not None
    assert data["amount"] > 0
