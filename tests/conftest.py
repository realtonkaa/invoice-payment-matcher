"""Shared pytest fixtures for invoice-payment-matcher tests."""

import pytest


@pytest.fixture
def sample_invoices():
    """A small set of invoices for use across multiple tests."""
    return [
        {"invoice_number": "INV-001", "client_name": "Acme Corp", "amount": 2500.00, "date": "2026-01-15"},
        {"invoice_number": "INV-002", "client_name": "Smith LLC", "amount": 1750.00, "date": "2026-01-18"},
        {"invoice_number": "INV-003", "client_name": "Smith LLC", "amount": 2000.00, "date": "2026-01-20"},
        {"invoice_number": "INV-004", "client_name": "Johnson Associates", "amount": 1200.00, "date": "2026-01-22"},
        {"invoice_number": "INV-005", "client_name": "Johnson Associates", "amount": 3000.00, "date": "2026-01-22"},
    ]


@pytest.fixture
def sample_deposits():
    """A small set of bank deposits that correspond to the sample invoices."""
    return [
        {"amount": 2500.00, "description": "WIRE TRANSFER - ACME CORP", "date": "2026-01-16"},
        {"amount": 3750.00, "description": "ACH DEPOSIT - SMITH LLC", "date": "2026-01-21"},
        {"amount": 4200.00, "description": "WIRE TRANSFER - JOHNSON", "date": "2026-01-23"},
    ]


@pytest.fixture
def unmatched_deposit():
    """A deposit that has no matching invoice combination."""
    return {"amount": 9999.99, "description": "UNKNOWN DEPOSIT", "date": "2026-01-25"}
