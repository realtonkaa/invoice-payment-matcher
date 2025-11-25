"""
bank_parser.py — Parse bank statement CSV files.

Handles auto-detection of column names across different bank export formats.
Filters for credit transactions only (positive amounts representing deposits).
"""

import pandas as pd
from typing import List, Dict, Optional


# Common column name variants used by different banks
_DATE_VARIANTS = {"date", "transaction date", "trans date", "posted date", "value date"}
_DESC_VARIANTS = {
    "description", "memo", "narrative", "details", "transaction description",
    "payee", "reference", "trans description", "particulars",
}
_AMOUNT_VARIANTS = {"amount", "credit", "debit", "transaction amount", "value"}
_TYPE_VARIANTS = {"type", "transaction type", "trans type", "dr/cr", "credit/debit"}


def _normalise(name: str) -> str:
    """Lower-case and strip whitespace for fuzzy column matching."""
    return name.strip().lower()


def _detect_column(columns: List[str], variants: set) -> Optional[str]:
    """
    Find the first column whose normalised name appears in the variants set.
    Returns the original (un-normalised) column name, or None if not found.
    """
    for col in columns:
        if _normalise(col) in variants:
            return col
    return None


def _detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Auto-detect which columns represent date, description, amount, and type.
    Returns a mapping of logical name -> actual column name in the DataFrame.
    """
    cols = list(df.columns)
    return {
        "date": _detect_column(cols, _DATE_VARIANTS),
        "description": _detect_column(cols, _DESC_VARIANTS),
        "amount": _detect_column(cols, _AMOUNT_VARIANTS),
        "type": _detect_column(cols, _TYPE_VARIANTS),
    }


def _is_credit(row: pd.Series, type_col: Optional[str], amount_col: str) -> bool:
    """
    Determine whether a transaction row represents a credit (deposit).

    Logic:
    - If a 'type' column exists, look for 'credit' in the value.
    - Otherwise, treat positive amounts as credits.
    """
    if type_col and pd.notna(row[type_col]):
        return "credit" in str(row[type_col]).lower()
    try:
        return float(row[amount_col]) > 0
    except (ValueError, TypeError):
        return False


def parse_bank_csv(filepath: str, filter_credits: bool = True) -> List[Dict]:
    """
    Parse a bank statement CSV and return a list of transaction dicts.

    Each dict has keys: date, description, amount.

    Parameters
    ----------
    filepath : str
        Path to the CSV file.
    filter_credits : bool
        If True (default), return only credit/deposit transactions.
    """
    df = pd.read_csv(filepath)

    # Strip leading/trailing whitespace from column names
    df.columns = [c.strip() for c in df.columns]

    mapping = _detect_columns(df)

    amount_col = mapping["amount"]
    if amount_col is None:
        raise ValueError(
            f"Could not detect an amount column in {filepath}. "
            f"Columns found: {list(df.columns)}"
        )

    # Coerce amount to float, drop rows where it cannot be parsed
    df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce")
    df = df.dropna(subset=[amount_col])

    transactions = []
    for _, row in df.iterrows():
        if filter_credits and not _is_credit(row, mapping["type"], amount_col):
            continue

        amount = float(row[amount_col])
        # If we're filtering by the Type column, credits may have been stored as
        # negative numbers in some exports — take abs value in that case.
        if mapping["type"] and amount < 0:
            amount = abs(amount)

        txn = {
            "amount": amount,
            "description": str(row[mapping["description"]]).strip() if mapping["description"] else "",
            "date": str(row[mapping["date"]]).strip() if mapping["date"] else None,
        }
        transactions.append(txn)

    return transactions
