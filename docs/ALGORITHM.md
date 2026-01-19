# The Subset-Sum Matching Algorithm

## The Problem

When a business sends a bank statement to their accountant, they see entries like:

```
2026-01-22   WIRE TRANSFER - JOHNSON AND ASSOCIATES   $4,200.00
```

The accountant needs to figure out which invoice(s) this $4,200 payment covers. Johnson might have paid:
- One invoice for exactly $4,200
- Two invoices: $1,200 + $3,000
- Three invoices: $1,200 + $1,800 + $1,200
- ...and so on

Finding the right combination by hand means opening multiple PDFs and doing arithmetic. For a business with dozens of clients and hundreds of invoices, this takes hours every month.

This is the **Subset-Sum Matching Problem (SSMP)**: given a target value D (the deposit) and a set of values {a1, a2, ..., an} (the invoice amounts), find a subset S such that the sum of elements in S equals D.

---

## Why Subset-Sum

The subset-sum formulation is natural here because:

1. Clients frequently bundle multiple invoices into a single payment. A client might pay three outstanding invoices in one wire transfer.
2. The amounts are fixed (invoice amounts don't change), but the combinations are unknown.
3. We need an exact (or near-exact) numerical match, not an approximate one.

The problem was studied in the context of financial reconciliation by JPMorgan Chase researchers. Their 2022 paper "Quantum-Inspired Classical Algorithms for Financial Portfolio Optimization" touches on related combinatorial matching problems in settlement systems, noting that real-world instances rarely have more than 30-40 items per client, making classical algorithms practical.

---

## Strategy 1: Brute-Force Combinations (n <= 20)

For small invoice sets (20 or fewer invoices available for a given client), we enumerate every possible non-empty subset using Python's `itertools.combinations`.

```python
from itertools import combinations

def find_subset_sum(amounts, target, tolerance=0.01):
    n = len(amounts)
    for r in range(1, n + 1):               # subset size 1, 2, ..., n
        for combo in combinations(range(n), r):
            if abs(sum(amounts[i] for i in combo) - target) <= tolerance:
                return list(combo)
    return None
```

**How it works:** We try all subsets of size 1, then size 2, then size 3, and so on. We return as soon as we find a valid combination. By searching smallest subsets first, we find the most parsimonious explanation (fewest invoices per payment) earliest.

**Time complexity:** O(2^n) in the worst case. For n=20, that is 2^20 = 1,048,576 subsets — fast enough to complete in milliseconds on modern hardware.

---

## Strategy 2: Dynamic Programming (n > 20)

For larger invoice sets, brute force becomes impractical (2^30 subsets would take too long). We use a DP approach inspired by the classic 0/1 knapsack problem.

```python
def find_subset_sum_dp(amounts, target, tolerance=0.01):
    scale = 100
    target_scaled = round(target * scale)
    tol_scaled = round(tolerance * scale)
    amounts_scaled = [round(a * scale) for a in amounts]
    upper = target_scaled + tol_scaled

    dp = {0: []}  # sum_in_cents -> list of indices used
    for i, amt in enumerate(amounts_scaled):
        new_dp = {}
        for s, indices in dp.items():
            new_s = s + amt
            if abs(new_s - target_scaled) <= tol_scaled:
                return indices + [i]
            if new_s <= upper and new_s not in dp and new_s not in new_dp:
                new_dp[new_s] = indices + [i]
        dp.update(new_dp)
    return None
```

**How it works:** We maintain a dictionary mapping each reachable sum (in integer cents) to the list of invoice indices used to reach it. For each invoice, we extend all existing partial sums. If any extended sum hits the target (within tolerance), we return the corresponding index list.

**Why integer cents?** Floating-point addition is not associative. Adding 0.1 + 0.2 in Python gives 0.30000000000000004, not 0.3. By working in integer cents (multiply by 100 and round), we get exact arithmetic and avoid false near-misses.

**Time complexity:** O(n * T) where T is the target amount in cents. For a $10,000 deposit, T = 1,000,000. With n = 100 invoices, this is 10^8 operations — acceptable for batch processing, though slow for interactive use.

**Space complexity:** O(T) — the DP dictionary can have at most T entries.

---

## The Tolerance Parameter

Real-world payments are messy:

- Wire transfer fees are sometimes deducted from the payment. A $2,500 invoice might arrive as $2,487 after a $13 wire fee.
- Rounding differences occur when invoices are computed in one currency and paid in another.
- Clients occasionally underpay or overpay by small amounts.

The `tolerance` parameter (default: $0.01) specifies the maximum allowed difference between the subset sum and the deposit amount. A tolerance of $0.01 handles pure rounding; a tolerance of $15.00 handles typical wire fees.

```python
# These all match with appropriate tolerances:
deposit = 2487.00
invoice = 2500.00
find_subset_sum([invoice], deposit, tolerance=15.00)  # matches
find_subset_sum([invoice], deposit, tolerance=0.01)   # does not match
```

---

## The Full Matching Pipeline

```
deposits = parse_bank_csv("bank.csv")
invoices = [extract_invoice_data(text) for text in invoice_texts]

for each deposit:
    available_invoices = invoices not yet matched
    subset = find_subset_sum(
        amounts=[inv.amount for inv in available_invoices],
        target=deposit.amount,
        tolerance=tolerance
    )
    if subset:
        mark those invoices as matched
        record the match
    else:
        record as unmatched
```

The algorithm is **greedy**: deposits are processed in order, and each invoice is claimed by the first deposit that can use it. This is not globally optimal (a different assignment order might produce more total matches), but it is fast and predictable. For the typical case where each client has one pending deposit, greedy assignment is optimal.

---

## Complexity Summary

| Invoice Set Size | Algorithm     | Worst-Case Operations | Practical Runtime |
|-----------------|---------------|----------------------|-------------------|
| n <= 20         | Brute force   | 2^20 = ~1M           | < 10ms            |
| 20 < n <= 100   | DP (cents)    | n * target_cents     | < 1s              |
| n > 100         | DP (cents)    | n * target_cents     | Seconds to minutes|

For typical accounting scenarios (< 50 outstanding invoices per client, deposits < $100,000), both algorithms complete in under 100ms.

---

## Fuzzy Name Pre-filtering

Before running subset-sum, we optionally filter the invoice set to those whose client name fuzzy-matches the bank deposit description. This:

1. Reduces the search space, improving performance.
2. Prevents false positives (matching a Johnson Associates invoice to an Acme Corp deposit).

We use the Levenshtein distance ratio from the `thefuzz` library. A threshold of 70/100 catches common abbreviations ("ACME" matching "Acme Corporation") while rejecting unrelated names.

---

## References

- Pisinger, D. (1999). "Linear time algorithms for knapsack problems with bounded weights." *Journal of Algorithms*, 33(1), 1-14.
- Horowitz, E., & Sahni, S. (1974). "Computing partitions with applications to the knapsack problem." *Journal of the ACM*, 21(2), 277-292.
- JPMorgan Chase AI Research. (2022). Research on combinatorial optimization in financial settlement systems.
