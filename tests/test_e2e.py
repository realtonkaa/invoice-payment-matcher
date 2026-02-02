"""
test_e2e.py — End-to-end integration test using sample fixture data.

Runs the full pipeline: bank CSV -> invoice text extraction -> matching -> report.
"""

import os
import csv
import tempfile
import pytest

from src.bank_parser import parse_bank_csv
from src.invoice_parser import extract_texts_from_directory
from src.extractor import extract_invoice_data
from src.matcher import match_payments
from src.report import export_csv


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_BANK_CSV = os.path.join(FIXTURES_DIR, "sample_bank.csv")
SAMPLE_INVOICES_DIR = os.path.join(FIXTURES_DIR, "sample_invoices")


def build_invoices(directory: str, use_llm: bool = False):
    """Extract and parse all invoices from a directory."""
    raw_texts = extract_texts_from_directory(directory)
    invoices = []
    for filename, text in raw_texts.items():
        if not text.strip():
            continue
        data = extract_invoice_data(text, use_llm=use_llm)
        if data.get("amount") is not None:
            data["_source_file"] = filename
            invoices.append(data)
    return invoices


class TestEndToEnd:
    """Full pipeline integration tests."""

    def test_pipeline_loads_deposits(self):
        deposits = parse_bank_csv(SAMPLE_BANK_CSV)
        assert len(deposits) == 4
        amounts = [d["amount"] for d in deposits]
        assert 2500.00 in amounts
        assert 1750.00 in amounts
        assert 4200.00 in amounts
        assert 3100.00 in amounts

    def test_pipeline_loads_invoices(self):
        invoices = build_invoices(SAMPLE_INVOICES_DIR)
        assert len(invoices) == 3
        amounts = {inv["amount"] for inv in invoices}
        assert 2500.00 in amounts
        assert 1750.00 in amounts
        assert 4200.00 in amounts

    def test_pipeline_matches_known_deposits(self):
        deposits = parse_bank_csv(SAMPLE_BANK_CSV)
        invoices = build_invoices(SAMPLE_INVOICES_DIR)
        results = match_payments(deposits, invoices)

        matched = [r for r in results if r["status"] == "matched"]
        unmatched = [r for r in results if r["status"] == "unmatched"]

        # Three deposits should match (2500, 1750, 4200)
        # One deposit (3100) has no corresponding invoice
        assert len(matched) == 3
        assert len(unmatched) == 1

    def test_pipeline_unmatched_deposit_is_3100(self):
        deposits = parse_bank_csv(SAMPLE_BANK_CSV)
        invoices = build_invoices(SAMPLE_INVOICES_DIR)
        results = match_payments(deposits, invoices)

        unmatched = [r for r in results if r["status"] == "unmatched"]
        assert len(unmatched) == 1
        assert unmatched[0]["deposit_amount"] == 3100.00

    def test_pipeline_matched_confidence(self):
        deposits = parse_bank_csv(SAMPLE_BANK_CSV)
        invoices = build_invoices(SAMPLE_INVOICES_DIR)
        results = match_payments(deposits, invoices)

        matched = [r for r in results if r["status"] == "matched"]
        for r in matched:
            assert r["confidence"] >= 0.9

    def test_pipeline_csv_export(self):
        deposits = parse_bank_csv(SAMPLE_BANK_CSV)
        invoices = build_invoices(SAMPLE_INVOICES_DIR)
        results = match_payments(deposits, invoices)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as fh:
            path = fh.name

        try:
            export_csv(results, path)
            with open(path, newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))

            assert len(rows) == 4  # one row per deposit

            statuses = [r["status"] for r in rows]
            assert statuses.count("matched") == 3
            assert statuses.count("unmatched") == 1
        finally:
            os.unlink(path)

    def test_pipeline_no_invoices_reused(self):
        deposits = parse_bank_csv(SAMPLE_BANK_CSV)
        invoices = build_invoices(SAMPLE_INVOICES_DIR)
        results = match_payments(deposits, invoices)

        # Collect all matched invoice source files
        used_files = []
        for r in results:
            for inv in r["matched_invoices"]:
                used_files.append(inv.get("_source_file"))

        # No file should appear more than once
        assert len(used_files) == len(set(used_files))
