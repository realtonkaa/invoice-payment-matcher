"""
test_bank_parser.py — Tests for bank CSV parsing.

Tests cover:
- Standard column names
- Auto-detection of alternative column names
- Filtering for credits only
- Handling of numeric edge cases
"""

import os
import tempfile
import pytest

from src.bank_parser import parse_bank_csv, _detect_column, _normalise


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_BANK_CSV = os.path.join(FIXTURES_DIR, "sample_bank.csv")


# ---------------------------------------------------------------------------
# Helper: write a temporary CSV and return its path
# ---------------------------------------------------------------------------

def write_temp_csv(content: str) -> str:
    """Write content to a temp CSV and return the file path."""
    fh = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    )
    fh.write(content)
    fh.close()
    return fh.name


# ---------------------------------------------------------------------------
# Tests for helper utilities
# ---------------------------------------------------------------------------

def test_normalise_strips_whitespace():
    assert _normalise("  Date  ") == "date"


def test_normalise_lowercases():
    assert _normalise("Transaction Date") == "transaction date"


def test_detect_column_found():
    cols = ["Date", "Description", "Amount"]
    result = _detect_column(cols, {"date", "transaction date"})
    assert result == "Date"


def test_detect_column_not_found():
    cols = ["Foo", "Bar"]
    result = _detect_column(cols, {"date"})
    assert result is None


# ---------------------------------------------------------------------------
# Tests against the sample fixture CSV
# ---------------------------------------------------------------------------

def test_parse_sample_csv_loads():
    txns = parse_bank_csv(SAMPLE_BANK_CSV)
    assert len(txns) > 0


def test_parse_sample_csv_all_are_credits():
    txns = parse_bank_csv(SAMPLE_BANK_CSV, filter_credits=True)
    # All rows in the fixture have Type=Credit, so all should be returned
    assert all(t["amount"] > 0 for t in txns)


def test_parse_sample_csv_amounts():
    txns = parse_bank_csv(SAMPLE_BANK_CSV)
    amounts = {round(t["amount"], 2) for t in txns}
    assert 2500.00 in amounts
    assert 1750.00 in amounts


def test_parse_sample_csv_has_descriptions():
    txns = parse_bank_csv(SAMPLE_BANK_CSV)
    for t in txns:
        assert isinstance(t["description"], str)
        assert len(t["description"]) > 0


def test_parse_sample_csv_has_dates():
    txns = parse_bank_csv(SAMPLE_BANK_CSV)
    for t in txns:
        assert t["date"] is not None


# ---------------------------------------------------------------------------
# Tests with in-memory CSV data
# ---------------------------------------------------------------------------

def test_standard_columns():
    csv_data = "Date,Description,Amount,Type\n2026-01-01,ACME CORP,1000.00,Credit\n"
    path = write_temp_csv(csv_data)
    try:
        txns = parse_bank_csv(path)
        assert len(txns) == 1
        assert txns[0]["amount"] == 1000.00
        assert txns[0]["description"] == "ACME CORP"
    finally:
        os.unlink(path)


def test_alternative_column_names():
    csv_data = (
        "Transaction Date,Narrative,Value,Dr/Cr\n"
        "2026-01-01,SMITH LLC,500.00,Credit\n"
    )
    path = write_temp_csv(csv_data)
    try:
        txns = parse_bank_csv(path)
        assert len(txns) == 1
        assert txns[0]["amount"] == 500.00
    finally:
        os.unlink(path)


def test_filter_debits_excluded():
    csv_data = (
        "Date,Description,Amount,Type\n"
        "2026-01-01,DEPOSIT,1000.00,Credit\n"
        "2026-01-02,PAYMENT,-500.00,Debit\n"
    )
    path = write_temp_csv(csv_data)
    try:
        txns = parse_bank_csv(path, filter_credits=True)
        assert len(txns) == 1
        assert txns[0]["amount"] == 1000.00
    finally:
        os.unlink(path)


def test_no_filter_includes_all_rows():
    csv_data = (
        "Date,Description,Amount\n"
        "2026-01-01,DEPOSIT,1000.00\n"
        "2026-01-02,PAYMENT,-500.00\n"
    )
    path = write_temp_csv(csv_data)
    try:
        txns = parse_bank_csv(path, filter_credits=False)
        assert len(txns) == 2
    finally:
        os.unlink(path)


def test_filters_by_positive_amount_when_no_type_column():
    csv_data = (
        "Date,Description,Amount\n"
        "2026-01-01,DEPOSIT,1000.00\n"
        "2026-01-02,FEE,-25.00\n"
    )
    path = write_temp_csv(csv_data)
    try:
        txns = parse_bank_csv(path, filter_credits=True)
        assert len(txns) == 1
        assert txns[0]["amount"] == 1000.00
    finally:
        os.unlink(path)


def test_invalid_amount_rows_skipped():
    csv_data = (
        "Date,Description,Amount,Type\n"
        "2026-01-01,ACME,INVALID,Credit\n"
        "2026-01-02,SMITH,750.00,Credit\n"
    )
    path = write_temp_csv(csv_data)
    try:
        txns = parse_bank_csv(path)
        assert len(txns) == 1
        assert txns[0]["amount"] == 750.00
    finally:
        os.unlink(path)


def test_missing_amount_column_raises():
    csv_data = "Date,Description,Notes\n2026-01-01,ACME,test\n"
    path = write_temp_csv(csv_data)
    try:
        with pytest.raises(ValueError, match="amount column"):
            parse_bank_csv(path)
    finally:
        os.unlink(path)
