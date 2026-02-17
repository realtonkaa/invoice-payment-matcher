# Invoice Payment Matcher

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)

A Python CLI tool that automatically matches bank deposits to invoice PDFs using subset-sum algorithms, OCR text extraction, and fuzzy name matching.

---

## Why I Built This

I watched a small business owner spend three hours every month manually matching bank deposits to invoices. She would open a spreadsheet, scan through PDFs, and try to figure out which invoices a client had bundled into a single payment. A deposit of $4,250 might be two invoices ($2,500 + $1,750), or three smaller ones, and she had no systematic way to find the right combination.

This is a textbook subset-sum problem, which is a well-studied problem in computer science. I built this tool to automate the reconciliation process using algorithms that solve exactly that kind of combinatorial search. The result is a CLI tool that takes a bank statement CSV and a folder of invoice PDFs, then produces a report telling you which invoices correspond to which deposits.

---

## Features

- Parse bank statement CSV files with auto-detection of column names
- Extract text from invoice PDFs using pdfplumber, with OCR fallback via pytesseract
- Regex-based extraction of invoice number, client name, amount, and date
- Optional LLM-assisted extraction for unstructured invoice formats
- Subset-sum matching algorithm with tolerance for rounding differences
- Fuzzy company name matching to link bank descriptions to invoice clients
- Rich terminal output with color-coded confidence scores
- CSV export of matched and unmatched results
- End-to-end test with sample data included

---

## Installation

```bash
git clone https://github.com/realtonkaa/invoice-payment-matcher.git
cd invoice-payment-matcher
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

For OCR support, install Tesseract separately:
- macOS: `brew install tesseract`
- Ubuntu: `sudo apt install tesseract-ocr`
- Windows: Download installer from https://github.com/UB-Mannheim/tesseract/wiki

---

## Usage

### Basic usage

```bash
python -m src.cli bank_statement.csv invoices/ --output results.csv
```

### With tolerance for rounding differences

```bash
python -m src.cli bank_statement.csv invoices/ --tolerance 0.05
```

### With LLM-assisted extraction (requires OpenAI key)

```bash
export OPENAI_API_KEY=sk-...
python -m src.cli bank_statement.csv invoices/ --use-llm
```

### Run with example data

```bash
python -m src.cli examples/demo_bank_statement.csv tests/fixtures/sample_invoices/ --output demo_results.csv
```

---

## How It Works

See [docs/ALGORITHM.md](docs/ALGORITHM.md) for the full explanation. The short version:

1. **Parse bank statement** — load the CSV, detect date/description/amount columns, filter for credit transactions only.
2. **Extract invoice data** — read each PDF (or .txt for testing), pull out the invoice number, client name, and amount using regex.
3. **Fuzzy name matching** — strip common prefixes from bank descriptions ("WIRE TRANSFER - ", "ACH DEPOSIT - ") and compare the remaining company name to invoice client names using Levenshtein distance.
4. **Subset-sum matching** — for each deposit, find the subset of invoice amounts that sums to the deposit total (within tolerance). Uses brute-force combinations for up to 20 invoices, dynamic programming for larger sets.
5. **Generate report** — display matched and unmatched results in the terminal with colored confidence scores, and optionally export to CSV.

---

## Example Output

```
Invoice Payment Matcher — Reconciliation Report
================================================

MATCHED DEPOSITS

  Deposit       Description                    Matched Invoices          Total     Diff   Confidence
  $2,500.00     WIRE TRANSFER - ACME CORP      INV-001 ($2,500.00)       $2,500    $0.00  HIGH
  $3,750.00     ACH DEPOSIT - SMITH LLC        INV-002 ($1,750.00)       $3,750    $0.00  HIGH
                                               INV-003 ($2,000.00)
  $4,200.00     WIRE TRANSFER - JOHNSON        INV-004 ($1,200.00)       $4,200    $0.00  HIGH
                                               INV-005 ($3,000.00)

UNMATCHED DEPOSITS

  Deposit       Description                    Note
  $9,999.99     UNKNOWN DEPOSIT                No matching invoice combination found

Summary: 3 matched, 1 unmatched
```

---

## Troubleshooting

**`pdfplumber` raises an error on some PDFs**

Some PDFs are encrypted or password-protected. pdfplumber can't read these — you'll need to decrypt them first (e.g. with `qpdf --decrypt`). The tool will skip files it can't parse and print a warning.

**Tesseract not found**

If you see `TesseractNotFoundError`, Tesseract is not installed or not on your PATH. Install it:
- macOS: `brew install tesseract`
- Ubuntu: `sudo apt install tesseract-ocr`
- Windows: installer at https://github.com/UB-Mannheim/tesseract/wiki

**Amount column not detected in bank CSV**

The tool looks for columns named things like "Amount", "Credit", "Debit", or "Transaction Amount". If your CSV uses a non-standard name, you'll see a `ValueError`. Open the CSV and check the column headers — you may need to rename the column before running the tool.

**No invoices extracted from directory**

This usually means the invoice PDFs have no extractable text (scanned images). Try running with pytesseract installed, or check that the files in the directory are actually PDFs/TXTs and not empty.

**Tolerance too tight**

If you have deposits that should match but don't, try increasing `--tolerance`:

```bash
python -m src.cli bank.csv invoices/ --tolerance 0.05
```

A tolerance of `0.05` handles rounding differences up to 5 cents. For wire transfers with fees deducted, you may need `--tolerance 15.00`.

---

## Limitations

- The subset-sum problem is NP-complete. The DP approach handles large invoice sets reasonably well, but for very large sets (hundreds of invoices per client), performance will degrade.
- OCR accuracy depends on invoice scan quality. Blurry or rotated scans may require manual review.
- Fuzzy name matching can produce false positives if company names are very similar. The confidence score helps flag these cases.
- The tool assumes deposits and invoices are in the same currency.
- LLM extraction requires an OpenAI API key and incurs API costs.

---

## What I Learned

Building this project taught me several things I hadn't encountered before in textbook exercises:

**Subset-sum in practice is messier than in theory.** Real bank data has rounding differences (a deposit of $1,500.01 should match an invoice of $1,500.00), wire transfer fees deducted from the payment, and clients who partially pay invoices. The tolerance parameter handles the first case, but the others require more sophisticated matching.

**Column name auto-detection is harder than it looks.** Bank CSV exports use dozens of different column naming conventions. I wrote a small detection function that checks for common patterns and falls back gracefully, which turned out to be one of the most useful pieces of the codebase.

**Rich makes terminal output genuinely pleasant.** I had avoided building CLI tools because I assumed the output would be ugly. The rich library produces tables and color output that are actually readable.

**OCR is a last resort, not a first choice.** pdfplumber extracts text directly from PDFs that were generated digitally (most modern invoices). pytesseract is only needed for scanned images, and its accuracy is significantly lower. The fallback chain matters.

---

## Demo Walkthrough

Run the tool against the included example data:

```bash
python -m src.cli examples/demo_bank_statement.csv tests/fixtures/sample_invoices/ --output demo_results.csv
```

This reads 8 bank deposits and 3 sample invoices. You should see three matched deposits
($2,500 matching INV-2026-001, $1,750 matching INV-2026-002, $4,200 matching INV-2026-003)
and the remaining deposits listed as unmatched since no corresponding invoices are in the
sample set.

The CSV at `demo_results.csv` will contain all results with matched invoice numbers and
confidence scores.

---

## Tech Stack

- Python 3.10+
- pdfplumber — PDF text extraction
- pytesseract + Pillow — OCR for scanned invoices
- pandas — CSV parsing and data manipulation
- thefuzz + python-Levenshtein — fuzzy string matching
- rich — terminal output formatting
- openai — optional LLM-assisted extraction
- pytest — testing

---

## Built With Claude

I used [Claude](https://claude.ai) (Anthropic's AI assistant) as a coding partner on this project. Claude helped me with:

- Understanding the subset-sum problem and its connection to bank reconciliation (it pointed me to a JPMorgan research paper on the topic)
- Writing the dynamic programming variant of the matching algorithm for larger invoice sets
- Generating realistic test fixture data (sample invoices, bank statements)
- Setting up the PDF extraction pipeline with pdfplumber and OCR fallback

The core problem identification ("small business owners waste hours matching payments to invoices") came from talking to actual business owners. The algorithm design, architecture decisions, and project direction were all mine. Claude helped me implement ideas faster and taught me concepts I wouldn't have learned as quickly on my own. I think that's what AI tools are for -- amplifying what you can do, not replacing the thinking.

---

## License

MIT License. See LICENSE for details.
