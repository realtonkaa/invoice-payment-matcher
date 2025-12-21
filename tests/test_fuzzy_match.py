"""
test_fuzzy_match.py — Tests for fuzzy company name matching.
"""

import pytest
from src.fuzzy_match import (
    extract_company_name,
    normalise_name,
    similarity_score,
    find_best_match,
    match_deposit_to_invoices,
)


# ---------------------------------------------------------------------------
# Tests for extract_company_name
# ---------------------------------------------------------------------------

def test_extract_wire_transfer_prefix():
    result = extract_company_name("WIRE TRANSFER - ACME CORP")
    assert result.upper() == "ACME CORP"


def test_extract_ach_deposit_prefix():
    result = extract_company_name("ACH DEPOSIT - SMITH LLC")
    assert result.upper() == "SMITH LLC"


def test_extract_no_prefix():
    result = extract_company_name("JOHNSON AND ASSOCIATES")
    assert "JOHNSON" in result.upper()


def test_extract_strips_whitespace():
    result = extract_company_name("  WIRE TRANSFER -   ACME CORP  ")
    assert result.strip().upper() == "ACME CORP"


def test_extract_mixed_case_prefix():
    result = extract_company_name("wire transfer - Acme Corp")
    assert "Acme Corp" in result or "ACME CORP" in result.upper()


def test_extract_ach_credit():
    result = extract_company_name("ACH CREDIT - GLOBAL SOLUTIONS")
    assert "GLOBAL SOLUTIONS" in result.upper()


def test_extract_incoming_wire():
    result = extract_company_name("INCOMING WIRE - FIRST NATIONAL BANK")
    assert "FIRST NATIONAL BANK" in result.upper()


# ---------------------------------------------------------------------------
# Tests for normalise_name
# ---------------------------------------------------------------------------

def test_normalise_removes_llc():
    assert normalise_name("Acme LLC") == normalise_name("Acme")


def test_normalise_removes_inc():
    assert normalise_name("Smith Inc.") == normalise_name("Smith")


def test_normalise_removes_corp():
    assert normalise_name("Jones Corp") == normalise_name("Jones")


def test_normalise_lowercases():
    result = normalise_name("ACME CORP")
    assert result == result.lower()


def test_normalise_collapses_spaces():
    result = normalise_name("Acme   Corp")
    assert "  " not in result


# ---------------------------------------------------------------------------
# Tests for similarity_score
# ---------------------------------------------------------------------------

def test_identical_names_score_100():
    score = similarity_score("Acme Corp", "Acme Corp")
    assert score == 100


def test_same_names_different_case():
    score = similarity_score("ACME CORP", "acme corp")
    assert score >= 90


def test_entity_suffix_ignored():
    score = similarity_score("Acme LLC", "Acme Inc")
    # Both normalise to "acme", should be high similarity
    assert score >= 85


def test_clearly_different_names():
    score = similarity_score("Acme Corp", "Johnson Associates")
    assert score < 60


def test_partial_name_match():
    score = similarity_score("Smith", "Smith and Associates LLC")
    assert score >= 70


def test_empty_strings():
    score = similarity_score("", "")
    assert isinstance(score, int)


# ---------------------------------------------------------------------------
# Tests for find_best_match
# ---------------------------------------------------------------------------

def test_find_best_match_exact():
    result = find_best_match("Acme Corp", ["Acme Corp", "Smith LLC", "Jones Inc"])
    assert result is not None
    name, score = result
    assert name == "Acme Corp"
    assert score == 100


def test_find_best_match_fuzzy():
    result = find_best_match("ACME", ["Acme Corp", "Smith LLC"])
    assert result is not None
    name, score = result
    assert "Acme" in name


def test_find_best_match_below_threshold():
    result = find_best_match("ZZZZZ", ["Acme Corp", "Smith LLC"], threshold=80)
    assert result is None


def test_find_best_match_empty_candidates():
    result = find_best_match("Acme", [])
    assert result is None


def test_find_best_match_returns_best_not_first():
    candidates = ["Johnson Corp", "Johnson and Associates", "Acme LLC"]
    result = find_best_match("Johnson Associates", candidates)
    assert result is not None
    name, score = result
    assert "Johnson" in name


# ---------------------------------------------------------------------------
# Tests for match_deposit_to_invoices
# ---------------------------------------------------------------------------

def test_match_deposit_filters_by_name():
    deposit = {"description": "WIRE TRANSFER - ACME CORP", "amount": 1000.00}
    invoices = [
        {"client_name": "Acme Corp", "amount": 1000.00, "invoice_number": "001"},
        {"client_name": "Smith LLC", "amount": 1000.00, "invoice_number": "002"},
    ]
    result = match_deposit_to_invoices(deposit, invoices, threshold=70)
    names = [inv["client_name"] for inv in result]
    assert "Acme Corp" in names


def test_match_deposit_fallback_when_no_match():
    """If no invoice matches the name, all invoices are returned as fallback."""
    deposit = {"description": "WIRE TRANSFER - ZZZZZ UNKNOWN", "amount": 500.00}
    invoices = [
        {"client_name": "Acme Corp", "amount": 500.00, "invoice_number": "001"},
    ]
    result = match_deposit_to_invoices(deposit, invoices, threshold=70)
    # Fallback: return all invoices
    assert len(result) == 1


def test_match_deposit_no_description_returns_all():
    deposit = {"description": "", "amount": 500.00}
    invoices = [
        {"client_name": "Acme Corp", "amount": 500.00, "invoice_number": "001"},
        {"client_name": "Smith LLC", "amount": 250.00, "invoice_number": "002"},
    ]
    result = match_deposit_to_invoices(deposit, invoices)
    assert len(result) == 2
