.PHONY: test lint format clean demo

test:
	pytest tests/ -v

lint:
	flake8 src/ tests/

format:
	black src/ tests/
	isort src/ tests/

demo:
	python -m src.cli examples/demo_bank_statement.csv tests/fixtures/sample_invoices/ --output demo_results.csv

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -f demo_results.csv results.csv
