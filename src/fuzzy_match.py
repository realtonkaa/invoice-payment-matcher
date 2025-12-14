"""
fuzzy_match.py — Fuzzy string matching for company names.

Bank statement descriptions often include noise: "WIRE TRANSFER - ACME CORP",
"ACH DEPOSIT - SMITH LLC", "INTL WIRE FEE DEDUCTED - JOHNSON AND ASSOCIATES".
This module strips the noise and compares the core company name against invoice
client names using Levenshtein distance via the thefuzz library.
"""

import re
from typing import List, Dict, Optional, Tuple

try:
    from thefuzz import fuzz
except ImportError:
    # Graceful fallback if thefuzz is not installed
    fuzz = None


# Common prefixes to strip from bank description lines
_STRIP_PREFIXES = [
    r"wire\s+transfer\s*[-–]\s*",
    r"ach\s+deposit\s*[-–]\s*",
    r"ach\s+credit\s*[-–]\s*",
    r"intl\s+wire\s*[-–]\s*",
    r"domestic\s+wire\s*[-–]\s*",
    r"incoming\s+wire\s*[-–]\s*",
    r"dep\s*[-–]\s*",
    r"deposit\s*[-–]\s*",
    r"payment\s+from\s*[-–]?\s*",
    r"wire\s+from\s*[-–]?\s*",
    r"transfer\s+from\s*[-–]?\s*",
]

# Suffixes / noise patterns to strip after prefix removal
_STRIP_SUFFIXES = [
    r"\s+ref\s*#?\s*\w+",
    r"\s+\d{10,}",          # long account/reference numbers
    r"\s+\d{2}/\d{2}",      # date fragments
]

# Legal entity suffixes that don't add matching value
_ENTITY_NORMALISE = [
    (r"\bllc\.?", ""),
    (r"\binc\.?", ""),
    (r"\bcorp\.?", ""),
    (r"\bltd\.?", ""),
    (r"\bco\.?", ""),
    (r"\bassociates?\.?", ""),
    (r"\band\b", "&"),
]


def extract_company_name(description: str) -> str:
    """
    Extract the core company name from a bank statement description.

    Examples
    --------
    "WIRE TRANSFER - ACME CORP"          -> "ACME CORP"
    "ACH DEPOSIT - SMITH LLC"            -> "SMITH LLC"
    "INTL WIRE - JOHNSON AND ASSOCIATES" -> "JOHNSON AND ASSOCIATES"
    """
    text = description.strip()

    # Strip known prefixes (case-insensitive)
    for pattern in _STRIP_PREFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

    # Strip known suffixes / noise
    for pattern in _STRIP_SUFFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

    return text.strip()


def normalise_name(name: str) -> str:
    """
    Normalise a company name for comparison.
    Strips entity suffixes and converts to lower case.
    """
    text = name.lower().strip()
    for pattern, replacement in _ENTITY_NORMALISE:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def similarity_score(name_a: str, name_b: str) -> int:
    """
    Compute a fuzzy similarity score (0-100) between two company names.

    Uses thefuzz's token_sort_ratio which handles word order differences.
    Falls back to a simple equality check if thefuzz is not installed.
    """
    if fuzz is None:
        # Minimal fallback
        return 100 if normalise_name(name_a) == normalise_name(name_b) else 0

    norm_a = normalise_name(name_a)
    norm_b = normalise_name(name_b)
    return fuzz.token_sort_ratio(norm_a, norm_b)


def find_best_match(
    query: str,
    candidates: List[str],
    threshold: int = 70,
) -> Optional[Tuple[str, int]]:
    """
    Find the best-matching name from a list of candidates.

    Parameters
    ----------
    query : str
        The name to match (typically extracted from a bank description).
    candidates : list of str
        Names to compare against (typically invoice client names).
    threshold : int
        Minimum score (0-100) to consider a match valid.

    Returns
    -------
    (best_match, score) tuple, or None if no candidate meets the threshold.
    """
    best_name = None
    best_score = -1

    for candidate in candidates:
        score = similarity_score(query, candidate)
        if score > best_score:
            best_score = score
            best_name = candidate

    if best_score >= threshold:
        return best_name, best_score
    return None


def match_deposit_to_invoices(
    deposit: Dict,
    invoices: List[Dict],
    threshold: int = 70,
) -> List[Dict]:
    """
    Filter invoices to those whose client_name fuzzy-matches the deposit description.

    This is used as a pre-filter before subset-sum matching to reduce the
    search space and improve accuracy.

    Parameters
    ----------
    deposit : dict
        Deposit dict with at least a 'description' key.
    invoices : list of dict
        Invoice dicts with at least a 'client_name' key.
    threshold : int
        Minimum similarity score to include an invoice.

    Returns
    -------
    list of dict
        Filtered invoices that match the deposit description.
    """
    company = extract_company_name(deposit.get("description", ""))
    if not company:
        return invoices  # no description to match on, return all

    client_names = [inv.get("client_name", "") for inv in invoices]
    matched = []
    for inv, name in zip(invoices, client_names):
        if name and similarity_score(company, name) >= threshold:
            matched.append(inv)

    # If fuzzy filtering removed everything, return the full list as fallback
    return matched if matched else invoices
