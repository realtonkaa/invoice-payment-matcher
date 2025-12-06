"""
extractor.py — Extract structured invoice data from raw text.

Two strategies are provided:
1. Regex-based extraction — fast, no external API, works for standard invoice formats.
2. LLM-based extraction — uses OpenAI to handle unstructured or non-standard formats.

Both return a dict with keys: invoice_number, client_name, amount, date.
Missing fields are returned as None.
"""

import re
from typing import Optional, Dict


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_INVOICE_NUMBER_PATTERNS = [
    r"invoice\s*(?:number|no\.?|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-]*\d[A-Z0-9\-]*)",
    r"invoice\s*[:#]\s*([A-Z0-9][A-Z0-9\-]*\d[A-Z0-9\-]*)",
    r"inv\s*[#\-:]\s*([A-Z0-9][A-Z0-9\-]*)",
    r"bill\s*(?:number|no\.?)\s*[:\-]?\s*([A-Z0-9\-]+)",
]

_AMOUNT_PATTERNS = [
    r"(?:total|amount\s*due|balance\s*due|amount\s*payable|grand\s*total)\s*[:\-]?\s*\$?\s*([\d,]+\.?\d{0,2})",
    r"\$\s*([\d,]+\.\d{2})\s*(?:USD)?",
    r"([\d,]+\.\d{2})\s*(?:USD|dollars?)",
]

_DATE_PATTERNS = [
    r"(?:invoice\s*date|date\s*issued|issue\s*date|date)[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
    r"(?:invoice\s*date|date\s*issued|issue\s*date|date)[:\-]?\s*(\w+ \d{1,2},? \d{4})",
    r"(\d{4}-\d{2}-\d{2})",
]

_CLIENT_PATTERNS = [
    r"(?:bill(?:ed)?\s*to|client|customer|to)[:\-]?\s*\n?\s*([A-Za-z0-9 &,.']+(?:LLC|Inc\.?|Corp\.?|Ltd\.?|Associates?|Co\.?)?)",
    r"(?:bill(?:ed)?\s*to|client|customer)[:\-]?\s+([A-Za-z0-9 &,.']+)",
]


def _search_patterns(text: str, patterns: list) -> Optional[str]:
    """
    Try each regex pattern against the text (case-insensitive).
    Return the first captured group found, or None.
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def _parse_amount(raw: Optional[str]) -> Optional[float]:
    """Convert a raw amount string like '1,500.00' to a float."""
    if raw is None:
        return None
    cleaned = raw.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_invoice_data_regex(text: str) -> Dict:
    """
    Extract structured invoice data from raw text using regex patterns.

    Returns
    -------
    dict with keys: invoice_number, client_name, amount, date
    Any field that cannot be extracted is set to None.
    """
    raw_amount = _search_patterns(text, _AMOUNT_PATTERNS)
    return {
        "invoice_number": _search_patterns(text, _INVOICE_NUMBER_PATTERNS),
        "client_name": _search_patterns(text, _CLIENT_PATTERNS),
        "amount": _parse_amount(raw_amount),
        "date": _search_patterns(text, _DATE_PATTERNS),
    }


def extract_invoice_data_llm(text: str, model: str = "gpt-4o-mini") -> Dict:
    """
    Extract structured invoice data using an OpenAI language model.

    Falls back to regex extraction if the OpenAI package is not installed
    or if no API key is configured.

    Parameters
    ----------
    text : str
        Raw invoice text.
    model : str
        OpenAI model name.
    """
    try:
        import openai
        from src.config import config
    except ImportError:
        return extract_invoice_data_regex(text)

    if not config.has_openai_key():
        return extract_invoice_data_regex(text)

    client = openai.OpenAI(api_key=config.OPENAI_API_KEY)

    prompt = (
        "Extract the following fields from this invoice text and return them as a "
        "JSON object with keys: invoice_number, client_name, amount (as a number), date.\n"
        "If a field is not present, set it to null.\n\n"
        f"Invoice text:\n{text[:3000]}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        import json
        data = json.loads(response.choices[0].message.content)
        return {
            "invoice_number": data.get("invoice_number"),
            "client_name": data.get("client_name"),
            "amount": float(data["amount"]) if data.get("amount") is not None else None,
            "date": data.get("date"),
        }
    except Exception:
        # If LLM call fails for any reason, fall back to regex
        return extract_invoice_data_regex(text)


def extract_invoice_data(text: str, use_llm: bool = False) -> Dict:
    """
    Extract structured invoice data from raw text.

    Parameters
    ----------
    text : str
        Raw text extracted from an invoice file.
    use_llm : bool
        If True, attempt LLM-based extraction first (requires OpenAI API key).
        Falls back to regex if the LLM is unavailable.
    """
    if use_llm:
        return extract_invoice_data_llm(text)
    return extract_invoice_data_regex(text)
