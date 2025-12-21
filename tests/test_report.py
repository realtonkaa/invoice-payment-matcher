"""
test_report.py — Tests for report generation and CSV export.
"""

import os
import csv
import tempfile
import pytest

from src.report import export_csv, _confidence_label, _format_amount


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

MATCHED_RESULT = {
    "deposit_amount": 2500.00,
    "deposit_description": "WIRE TRANSFER - ACME CORP",
    "deposit_date": "2026-01-15",
    "matched_invoices": [
        {"invoice_number": "INV-001", "amount": 2500.00, "client_name": "Acme Corp"},
    ],
    "total_matched": 2500.00,
    "difference": 0.00,
    "status": "matched",
    "confidence": 1.0,
}

UNMATCHED_RESULT = {
    "deposit_amount": 9999.99,
    "deposit_description": "UNKNOWN DEPOSIT",
    "deposit_date": "2026-01-20",
    "matched_invoices": [],
    "total_matched": 0,
    "difference": 9999.99,
    "status": "unmatched",
    "confidence": 0,
}


# ---------------------------------------------------------------------------
# Tests for helper functions
# ---------------------------------------------------------------------------

def test_confidence_label_high():
    assert _confidence_label(1.0) == "HIGH"


def test_confidence_label_medium():
    assert _confidence_label(0.85) == "MEDIUM"


def test_confidence_label_low():
    assert _confidence_label(0.5) == "LOW"


def test_format_amount_standard():
    assert _format_amount(1500.00) == "$1,500.00"


def test_format_amount_large():
    assert _format_amount(1234567.89) == "$1,234,567.89"


def test_format_amount_zero():
    assert _format_amount(0.00) == "$0.00"


# ---------------------------------------------------------------------------
# Tests for CSV export
# ---------------------------------------------------------------------------

def test_export_csv_creates_file():
    results = [MATCHED_RESULT, UNMATCHED_RESULT]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as fh:
        path = fh.name
    try:
        export_csv(results, path)
        assert os.path.isfile(path)
    finally:
        os.unlink(path)


def test_export_csv_row_count():
    results = [MATCHED_RESULT, UNMATCHED_RESULT]
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as fh:
        path = fh.name
    try:
        export_csv(results, path)
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 2
    finally:
        os.unlink(path)


def test_export_csv_matched_row_fields():
    results = [MATCHED_RESULT]
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as fh:
        path = fh.name
    try:
        export_csv(results, path)
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        row = rows[0]
        assert row["status"] == "matched"
        assert float(row["deposit_amount"]) == 2500.00
        assert "INV-001" in row["matched_invoice_numbers"]
    finally:
        os.unlink(path)


def test_export_csv_unmatched_row():
    results = [UNMATCHED_RESULT]
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as fh:
        path = fh.name
    try:
        export_csv(results, path)
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        row = rows[0]
        assert row["status"] == "unmatched"
        assert row["matched_invoice_numbers"] == ""
    finally:
        os.unlink(path)


def test_export_csv_headers():
    results = [MATCHED_RESULT]
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as fh:
        path = fh.name
    try:
        export_csv(results, path)
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            headers = reader.fieldnames
        expected = [
            "deposit_amount", "deposit_date", "deposit_description",
            "status", "matched_invoice_numbers", "matched_invoice_amounts",
            "total_matched", "difference", "confidence",
        ]
        for h in expected:
            assert h in headers
    finally:
        os.unlink(path)


def test_export_csv_multiple_matched_invoices():
    result = {
        "deposit_amount": 3500.00,
        "deposit_description": "ACH - ACME",
        "deposit_date": "2026-01-18",
        "matched_invoices": [
            {"invoice_number": "INV-001", "amount": 1500.00},
            {"invoice_number": "INV-002", "amount": 2000.00},
        ],
        "total_matched": 3500.00,
        "difference": 0.00,
        "status": "matched",
        "confidence": 1.0,
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as fh:
        path = fh.name
    try:
        export_csv([result], path)
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        row = rows[0]
        assert "INV-001" in row["matched_invoice_numbers"]
        assert "INV-002" in row["matched_invoice_numbers"]
    finally:
        os.unlink(path)
