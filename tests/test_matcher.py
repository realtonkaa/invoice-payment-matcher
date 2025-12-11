"""
test_matcher.py — Tests for the subset-sum matching algorithm.

These are the most important tests in the suite. They verify that:
- Single invoice matches work
- Bundled payments (multiple invoices in one deposit) are found
- Tolerance parameter handles rounding differences
- Unmatched deposits are correctly identified
- Multiple deposits are processed without reusing invoices
"""

import pytest
from src.matcher import find_subset_sum, match_payments, suggest_partial_matches


# ---------------------------------------------------------------------------
# Tests for find_subset_sum
# ---------------------------------------------------------------------------

def test_find_subset_sum_single_exact():
    result = find_subset_sum([100.00, 200.00, 300.00], 200.00)
    assert result == [1]


def test_find_subset_sum_multi():
    result = find_subset_sum([100.00, 200.00, 300.00], 300.00)
    # Could be [2] (300) or [0, 1] (100+200) — both are valid
    assert result is not None
    total = sum([100.00, 200.00, 300.00][i] for i in result)
    assert abs(total - 300.00) <= 0.01


def test_find_subset_sum_within_tolerance():
    result = find_subset_sum([1500.00], 1500.01, tolerance=0.05)
    assert result is not None
    assert result == [0]


def test_find_subset_sum_exceeds_tolerance_returns_none():
    result = find_subset_sum([1500.00], 1500.10, tolerance=0.05)
    assert result is None


def test_find_subset_sum_empty_list():
    result = find_subset_sum([], 100.00)
    assert result is None


def test_find_subset_sum_no_match():
    result = find_subset_sum([10.00, 20.00, 30.00], 999.00)
    assert result is None


def test_find_subset_sum_large_set_dp():
    """Test the DP path (n > 20)."""
    # Create 25 amounts; target is the sum of the last two
    amounts = [float(i * 10) for i in range(1, 26)]  # 10, 20, ..., 250
    target = amounts[-1] + amounts[-2]  # 250 + 240 = 490
    result = find_subset_sum(amounts, target)
    assert result is not None
    total = sum(amounts[i] for i in result)
    assert abs(total - target) <= 0.01


def test_find_subset_sum_all_amounts_sum_to_target():
    amounts = [100.00, 200.00, 300.00]
    result = find_subset_sum(amounts, 600.00)
    assert result is not None
    assert sorted(result) == [0, 1, 2]


# ---------------------------------------------------------------------------
# Tests for match_payments — these match the spec exactly
# ---------------------------------------------------------------------------

def test_exact_match_single():
    deposits = [{"amount": 1500.00, "description": "WIRE - ACME"}]
    invoices = [{"amount": 1500.00, "client_name": "Acme Corp", "invoice_number": "001"}]
    matches = match_payments(deposits, invoices)
    assert len(matches) == 1
    assert matches[0]["status"] == "matched"


def test_bundled_payment():
    deposits = [{"amount": 3500.00, "description": "ACH - ACME"}]
    invoices = [
        {"amount": 1500.00, "client_name": "Acme", "invoice_number": "001"},
        {"amount": 2000.00, "client_name": "Acme", "invoice_number": "002"},
        {"amount": 800.00, "client_name": "Other", "invoice_number": "003"},
    ]
    matches = match_payments(deposits, invoices)
    assert matches[0]["status"] == "matched"
    assert len(matches[0]["matched_invoices"]) == 2


def test_tolerance():
    deposits = [{"amount": 1500.01, "description": "WIRE"}]
    invoices = [{"amount": 1500.00, "client_name": "Test", "invoice_number": "001"}]
    matches = match_payments(deposits, invoices, tolerance=0.05)
    assert matches[0]["status"] == "matched"


def test_unmatched():
    deposits = [{"amount": 9999.99, "description": "UNKNOWN"}]
    invoices = [{"amount": 100.00, "client_name": "Test", "invoice_number": "001"}]
    matches = match_payments(deposits, invoices)
    assert matches[0]["status"] == "unmatched"


def test_multiple_deposits():
    deposits = [
        {"amount": 1500.00, "description": "WIRE - A"},
        {"amount": 2000.00, "description": "ACH - B"},
    ]
    invoices = [
        {"amount": 1500.00, "client_name": "A", "invoice_number": "001"},
        {"amount": 2000.00, "client_name": "B", "invoice_number": "002"},
    ]
    matches = match_payments(deposits, invoices)
    assert all(m["status"] == "matched" for m in matches)


def test_invoices_not_reused():
    """An invoice matched to deposit 1 should not be available for deposit 2."""
    deposits = [
        {"amount": 1000.00, "description": "FIRST"},
        {"amount": 1000.00, "description": "SECOND"},
    ]
    invoices = [
        {"amount": 1000.00, "client_name": "A", "invoice_number": "001"},
    ]
    matches = match_payments(deposits, invoices)
    statuses = {m["status"] for m in matches}
    # One match, one unmatched — the invoice cannot be used twice
    assert "matched" in statuses
    assert "unmatched" in statuses


def test_result_structure():
    deposits = [{"amount": 500.00, "description": "TEST", "date": "2026-01-01"}]
    invoices = [{"amount": 500.00, "client_name": "X", "invoice_number": "INV-1"}]
    matches = match_payments(deposits, invoices)
    r = matches[0]
    assert "deposit_amount" in r
    assert "deposit_description" in r
    assert "deposit_date" in r
    assert "matched_invoices" in r
    assert "total_matched" in r
    assert "difference" in r
    assert "status" in r
    assert "confidence" in r


def test_confidence_exact():
    deposits = [{"amount": 750.00}]
    invoices = [{"amount": 750.00, "client_name": "X", "invoice_number": "INV-1"}]
    matches = match_payments(deposits, invoices)
    assert matches[0]["confidence"] == 1.0


def test_confidence_within_tolerance():
    deposits = [{"amount": 750.05}]
    invoices = [{"amount": 750.00, "client_name": "X", "invoice_number": "INV-1"}]
    matches = match_payments(deposits, invoices, tolerance=0.10)
    assert matches[0]["confidence"] == 0.9


def test_difference_computed_correctly():
    deposits = [{"amount": 1500.05}]
    invoices = [{"amount": 1500.00, "client_name": "X", "invoice_number": "INV-1"}]
    matches = match_payments(deposits, invoices, tolerance=0.10)
    assert abs(matches[0]["difference"] - 0.05) < 0.001


def test_zero_difference_exact_match():
    deposits = [{"amount": 1200.00}]
    invoices = [{"amount": 1200.00, "client_name": "X", "invoice_number": "INV-1"}]
    matches = match_payments(deposits, invoices)
    assert matches[0]["difference"] == 0.0


def test_three_invoice_bundle():
    deposits = [{"amount": 6000.00}]
    invoices = [
        {"amount": 1000.00, "client_name": "X", "invoice_number": "INV-1"},
        {"amount": 2000.00, "client_name": "X", "invoice_number": "INV-2"},
        {"amount": 3000.00, "client_name": "X", "invoice_number": "INV-3"},
        {"amount": 9999.00, "client_name": "Y", "invoice_number": "INV-4"},
    ]
    matches = match_payments(deposits, invoices)
    assert matches[0]["status"] == "matched"
    assert len(matches[0]["matched_invoices"]) == 3


def test_empty_invoices():
    deposits = [{"amount": 500.00}]
    matches = match_payments(deposits, [])
    assert matches[0]["status"] == "unmatched"


def test_empty_deposits():
    invoices = [{"amount": 100.00}]
    matches = match_payments([], invoices)
    assert matches == []


# ---------------------------------------------------------------------------
# Tests for suggest_partial_matches
# ---------------------------------------------------------------------------

def test_suggest_partial_matches_returns_list():
    deposit = {"amount": 9999.99}
    invoices = [
        {"amount": 100.00, "invoice_number": "1"},
        {"amount": 200.00, "invoice_number": "2"},
    ]
    suggestions = suggest_partial_matches(deposit, invoices, set())
    assert isinstance(suggestions, list)


def test_suggest_partial_matches_sorted_by_difference():
    deposit = {"amount": 300.00}
    invoices = [
        {"amount": 100.00, "invoice_number": "1"},
        {"amount": 200.00, "invoice_number": "2"},
        {"amount": 500.00, "invoice_number": "3"},
    ]
    suggestions = suggest_partial_matches(deposit, invoices, set())
    assert suggestions[0]["difference"] <= suggestions[-1]["difference"]
