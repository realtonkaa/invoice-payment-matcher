# Contributing

This is a personal project but issues and PRs are welcome.

## Getting started

```bash
git clone https://github.com/realtonkaa/invoice-payment-matcher.git
cd invoice-payment-matcher
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Running tests

```bash
pytest tests/
```

## Code style

- PEP 8 formatting (run `black src/ tests/` to auto-format)
- Type hints on all public functions
- Docstrings for new functions

## Submitting changes

- One change per PR
- Tests should pass
- Describe what and why in the PR description

## Reporting issues

Please include:
- Steps to reproduce
- Expected vs actual behaviour
- Python version, OS
- Any relevant CSV snippet or invoice sample (anonymise if needed)
