"""
cli.py — Command-line interface for invoice-payment-matcher.

Usage:
    python -m src.cli bank_file.csv invoices_dir/ [options]

Options:
    --output FILE       Write results to CSV (default: results.csv)
    --tolerance FLOAT   Matching tolerance in dollars (default: 0.01)
    --use-llm           Use LLM for invoice data extraction (requires OPENAI_API_KEY)
    --no-filter         Do not filter bank CSV for credits only
    --quiet             Suppress terminal report (useful for scripting)
"""

import argparse
import os
import sys

from src.bank_parser import parse_bank_csv
from src.invoice_parser import extract_texts_from_directory
from src.extractor import extract_invoice_data
from src.matcher import match_payments, suggest_partial_matches
from src.report import print_report, export_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="invoice-matcher",
        description="Match bank deposits to invoice PDFs using subset-sum algorithms.",
    )
    parser.add_argument(
        "bank_file",
        help="Path to bank statement CSV file.",
    )
    parser.add_argument(
        "invoices_dir",
        help="Directory containing invoice PDF or TXT files.",
    )
    parser.add_argument(
        "--output",
        default="results.csv",
        metavar="FILE",
        help="Output CSV file path (default: results.csv).",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        metavar="FLOAT",
        help="Dollar tolerance for matching (default: 0.01).",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        default=False,
        help="Use LLM for invoice extraction (requires OPENAI_API_KEY).",
    )
    parser.add_argument(
        "--no-filter",
        action="store_true",
        default=False,
        help="Include all transactions (do not filter for credits only).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress terminal output.",
    )
    return parser


def run(args=None) -> int:
    """
    Main entry point. Returns exit code (0 = success, 1 = error).
    """
    parser = build_parser()
    parsed = parser.parse_args(args)

    # --- Validate inputs ---
    if not os.path.isfile(parsed.bank_file):
        print(f"Error: bank file not found: {parsed.bank_file}", file=sys.stderr)
        return 1

    if not os.path.isdir(parsed.invoices_dir):
        print(f"Error: invoices directory not found: {parsed.invoices_dir}", file=sys.stderr)
        return 1

    # --- Parse bank statement ---
    try:
        deposits = parse_bank_csv(
            parsed.bank_file,
            filter_credits=not parsed.no_filter,
        )
    except Exception as exc:
        print(f"Error parsing bank file: {exc}", file=sys.stderr)
        return 1

    if not deposits:
        print("No deposit transactions found in bank file.", file=sys.stderr)
        return 1

    # --- Extract invoice data ---
    raw_texts = extract_texts_from_directory(parsed.invoices_dir)
    invoices = []
    for filename, text in raw_texts.items():
        if not text.strip():
            continue
        data = extract_invoice_data(text, use_llm=parsed.use_llm)
        if data.get("amount") is not None:
            data["_source_file"] = filename
            invoices.append(data)

    if not invoices:
        print("No invoice data could be extracted from the invoices directory.", file=sys.stderr)
        return 1

    # --- Match ---
    results = match_payments(deposits, invoices, tolerance=parsed.tolerance)

    # Add partial match suggestions for unmatched deposits
    used = set()
    for r in results:
        if r["status"] == "matched":
            for inv in r["matched_invoices"]:
                if inv in invoices:
                    used.add(invoices.index(inv))

    for r in results:
        if r["status"] == "unmatched":
            deposit = {
                "amount": r["deposit_amount"],
                "description": r["deposit_description"],
            }
            r["suggestions"] = suggest_partial_matches(deposit, invoices, used)

    # --- Output ---
    if not parsed.quiet:
        print_report(results)

    export_csv(results, parsed.output)

    if not parsed.quiet:
        matched_count = sum(1 for r in results if r["status"] == "matched")
        unmatched_count = len(results) - matched_count
        print(f"Results saved to: {parsed.output}")
        print(f"Matched: {matched_count}  Unmatched: {unmatched_count}")

    return 0


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()
