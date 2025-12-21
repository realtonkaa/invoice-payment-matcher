"""
report.py — Generate reconciliation reports.

Provides:
- Rich terminal output with coloured confidence scores
- CSV export of matched and unmatched results
"""

import csv
from typing import List, Dict, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    from rich import box
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False


def _confidence_label(confidence: float) -> str:
    if confidence >= 1.0:
        return "HIGH"
    elif confidence >= 0.8:
        return "MEDIUM"
    else:
        return "LOW"


def _confidence_style(confidence: float) -> str:
    if confidence >= 1.0:
        return "bold green"
    elif confidence >= 0.8:
        return "yellow"
    else:
        return "bold red"


def _format_amount(amount: float) -> str:
    return f"${amount:,.2f}"


def print_report(results: List[Dict], console=None) -> None:
    """
    Print a reconciliation report to the terminal using rich formatting.

    Parameters
    ----------
    results : list of dict
        Output of matcher.match_payments().
    console : rich.console.Console, optional
        Use a custom console (useful for testing/capturing output).
    """
    if not _RICH_AVAILABLE:
        _print_report_plain(results)
        return

    if console is None:
        console = Console()

    matched = [r for r in results if r["status"] == "matched"]
    unmatched = [r for r in results if r["status"] == "unmatched"]

    console.print()
    console.print(
        "[bold cyan]Invoice Payment Matcher — Reconciliation Report[/bold cyan]"
    )
    console.print("[cyan]" + "=" * 52 + "[/cyan]")

    # --- Matched table ---
    if matched:
        console.print()
        console.print("[bold green]MATCHED DEPOSITS[/bold green]")
        console.print()

        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        table.add_column("Deposit", style="white", justify="right")
        table.add_column("Date", style="dim")
        table.add_column("Description", style="white")
        table.add_column("Matched Invoices", style="white")
        table.add_column("Total", justify="right")
        table.add_column("Diff", justify="right")
        table.add_column("Confidence")

        for r in matched:
            invoice_lines = []
            for inv in r["matched_invoices"]:
                inv_no = inv.get("invoice_number") or "?"
                inv_amt = _format_amount(inv["amount"])
                invoice_lines.append(f"{inv_no} ({inv_amt})")
            inv_str = "\n".join(invoice_lines) if invoice_lines else "-"

            conf_label = _confidence_label(r["confidence"])
            conf_style = _confidence_style(r["confidence"])

            table.add_row(
                _format_amount(r["deposit_amount"]),
                str(r["deposit_date"] or ""),
                r["deposit_description"],
                inv_str,
                _format_amount(r["total_matched"]),
                _format_amount(abs(r["difference"])),
                Text(conf_label, style=conf_style),
            )

        console.print(table)

    # --- Unmatched table ---
    if unmatched:
        console.print()
        console.print("[bold red]UNMATCHED DEPOSITS[/bold red]")
        console.print()

        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        table.add_column("Deposit", style="white", justify="right")
        table.add_column("Date", style="dim")
        table.add_column("Description", style="white")
        table.add_column("Note", style="dim red")

        for r in unmatched:
            table.add_row(
                _format_amount(r["deposit_amount"]),
                str(r["deposit_date"] or ""),
                r["deposit_description"],
                "No matching invoice combination found",
            )

        console.print(table)

    # --- Summary ---
    console.print()
    console.print(
        f"[bold]Summary:[/bold] [green]{len(matched)} matched[/green], "
        f"[red]{len(unmatched)} unmatched[/red]"
    )
    console.print()


def _print_report_plain(results: List[Dict]) -> None:
    """Fallback plain-text report when rich is not installed."""
    matched = [r for r in results if r["status"] == "matched"]
    unmatched = [r for r in results if r["status"] == "unmatched"]

    print("\nInvoice Payment Matcher — Reconciliation Report")
    print("=" * 50)

    if matched:
        print("\nMATCHED DEPOSITS")
        for r in matched:
            inv_nos = [inv.get("invoice_number", "?") for inv in r["matched_invoices"]]
            print(
                f"  {_format_amount(r['deposit_amount'])}  |  "
                f"{r['deposit_description']}  |  "
                f"Invoices: {', '.join(inv_nos)}  |  "
                f"Diff: {_format_amount(abs(r['difference']))}  |  "
                f"Confidence: {_confidence_label(r['confidence'])}"
            )

    if unmatched:
        print("\nUNMATCHED DEPOSITS")
        for r in unmatched:
            print(
                f"  {_format_amount(r['deposit_amount'])}  |  "
                f"{r['deposit_description']}  |  No match found"
            )

    print(f"\nSummary: {len(matched)} matched, {len(unmatched)} unmatched\n")


def export_csv(results: List[Dict], filepath: str) -> None:
    """
    Export reconciliation results to a CSV file.

    The CSV contains one row per deposit. Matched invoices are listed as
    comma-separated values in a single cell.

    Parameters
    ----------
    results : list of dict
        Output of matcher.match_payments().
    filepath : str
        Path to write the CSV file.
    """
    fieldnames = [
        "deposit_amount",
        "deposit_date",
        "deposit_description",
        "status",
        "matched_invoice_numbers",
        "matched_invoice_amounts",
        "total_matched",
        "difference",
        "confidence",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()

        for r in results:
            inv_numbers = ";".join(
                str(inv.get("invoice_number", "")) for inv in r["matched_invoices"]
            )
            inv_amounts = ";".join(
                str(inv["amount"]) for inv in r["matched_invoices"]
            )
            writer.writerow({
                "deposit_amount": r["deposit_amount"],
                "deposit_date": r["deposit_date"],
                "deposit_description": r["deposit_description"],
                "status": r["status"],
                "matched_invoice_numbers": inv_numbers,
                "matched_invoice_amounts": inv_amounts,
                "total_matched": r["total_matched"],
                "difference": r["difference"],
                "confidence": r["confidence"],
            })
