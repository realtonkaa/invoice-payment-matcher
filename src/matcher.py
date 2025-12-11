"""
matcher.py — Core subset-sum matching algorithm.

The central problem in bank reconciliation is: given a deposit of amount D,
find the subset of outstanding invoices whose amounts sum to D (within a
small tolerance for rounding differences and wire fees).

This is a variant of the subset-sum problem. We use two strategies:
- Brute-force combinations for small invoice sets (n <= 20)
- Dynamic programming for larger sets

See docs/ALGORITHM.md for a detailed explanation.
"""

from itertools import combinations
from typing import List, Dict, Optional, Tuple


def find_subset_sum(
    amounts: List[float],
    target: float,
    tolerance: float = 0.01,
) -> Optional[List[int]]:
    """
    Find a subset of amounts that sums to target (within tolerance).

    Returns a list of indices into `amounts` that form the matching subset,
    or None if no such subset exists.

    Parameters
    ----------
    amounts : list of float
        Invoice amounts to search through.
    target : float
        The deposit amount to match.
    tolerance : float
        Maximum allowed difference between the subset sum and the target.
        Handles rounding differences and minor wire transfer fees.
    """
    n = len(amounts)
    if n == 0:
        return None

    # --- Brute-force approach for small sets ---
    # For n <= 20, we try every combination of 1..n elements.
    # The total number of subsets is 2^n, which is at most 2^20 = ~1M.
    # This is fast enough in practice and always finds the optimal solution.
    if n <= 20:
        for r in range(1, n + 1):
            for combo in combinations(range(n), r):
                subset_sum = sum(amounts[i] for i in combo)
                if abs(subset_sum - target) <= tolerance:
                    return list(combo)
        return None

    # --- Dynamic programming approach for larger sets ---
    # We work in integer cents to avoid floating-point accumulation errors.
    # dp maps each reachable sum (in cents) to the list of indices used to reach it.
    scale = 100
    target_scaled = round(target * scale)
    tol_scaled = round(tolerance * scale)
    amounts_scaled = [round(a * scale) for a in amounts]

    # Upper bound for sums we track (target + tolerance)
    upper = target_scaled + tol_scaled

    dp: Dict[int, List[int]] = {0: []}

    for i, amt in enumerate(amounts_scaled):
        # Iterate over a snapshot of current dp to avoid modifying it mid-loop
        new_dp: Dict[int, List[int]] = {}
        for s, indices in dp.items():
            new_s = s + amt
            if abs(new_s - target_scaled) <= tol_scaled:
                return indices + [i]
            if new_s <= upper and new_s not in dp and new_s not in new_dp:
                new_dp[new_s] = indices + [i]
        dp.update(new_dp)

    return None


def match_payments(
    deposits: List[Dict],
    invoices: List[Dict],
    tolerance: float = 0.01,
) -> List[Dict]:
    """
    Match each deposit to a subset of invoices whose amounts sum to the deposit.

    Each invoice is only used once across all matches (greedy assignment:
    deposits are processed in the order given).

    Parameters
    ----------
    deposits : list of dict
        Each dict must have an 'amount' key. May also have 'description' and 'date'.
    invoices : list of dict
        Each dict must have an 'amount' key. May also have 'client_name',
        'invoice_number', and 'date'.
    tolerance : float
        Passed through to find_subset_sum.

    Returns
    -------
    list of dict
        One result dict per deposit, with keys:
        deposit_amount, deposit_description, deposit_date,
        matched_invoices, total_matched, difference, status, confidence.
    """
    results = []
    used_invoices: set = set()

    for deposit in deposits:
        # Build the list of still-available invoices
        available: List[Tuple[int, Dict]] = [
            (i, inv) for i, inv in enumerate(invoices) if i not in used_invoices
        ]
        amounts = [inv["amount"] for _, inv in available]
        indices_map = [i for i, _ in available]

        subset = find_subset_sum(amounts, deposit["amount"], tolerance)

        if subset is not None:
            matched = []
            for local_idx in subset:
                orig_idx = indices_map[local_idx]
                used_invoices.add(orig_idx)
                matched.append(invoices[orig_idx])

            total_matched = sum(inv["amount"] for inv in matched)
            difference = round(deposit["amount"] - total_matched, 2)
            confidence = 1.0 if abs(difference) < 0.01 else 0.9

            results.append({
                "deposit_amount": deposit["amount"],
                "deposit_description": deposit.get("description", ""),
                "deposit_date": deposit.get("date"),
                "matched_invoices": matched,
                "total_matched": total_matched,
                "difference": difference,
                "status": "matched",
                "confidence": confidence,
            })
        else:
            results.append({
                "deposit_amount": deposit["amount"],
                "deposit_description": deposit.get("description", ""),
                "deposit_date": deposit.get("date"),
                "matched_invoices": [],
                "total_matched": 0,
                "difference": deposit["amount"],
                "status": "unmatched",
                "confidence": 0,
            })

    return results


def suggest_partial_matches(
    deposit: Dict,
    invoices: List[Dict],
    used_invoices: set,
    top_n: int = 3,
) -> List[Dict]:
    """
    For an unmatched deposit, suggest the closest invoice subsets.

    Finds the invoice subsets (up to size 3) whose sums are closest to
    the deposit amount, even if they don't fall within the standard tolerance.
    Useful for helping accountants identify near-misses.

    Parameters
    ----------
    deposit : dict
        The unmatched deposit.
    invoices : list of dict
        Full invoice list.
    used_invoices : set
        Indices of already-matched invoices to exclude.
    top_n : int
        Number of suggestions to return.

    Returns
    -------
    list of dict
        Each dict has keys: invoices, total, difference.
    """
    target = deposit["amount"]
    available = [
        (i, inv) for i, inv in enumerate(invoices) if i not in used_invoices
    ]

    candidates = []
    for r in range(1, min(4, len(available) + 1)):
        for combo in combinations(range(len(available)), r):
            subset_invs = [available[idx][1] for idx in combo]
            total = sum(inv["amount"] for inv in subset_invs)
            diff = abs(total - target)
            candidates.append({
                "invoices": subset_invs,
                "total": round(total, 2),
                "difference": round(diff, 2),
            })

    candidates.sort(key=lambda c: c["difference"])
    return candidates[:top_n]
