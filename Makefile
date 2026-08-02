.DEFAULT_GOAL := help

.PHONY: help fmt lint build-web test e2e validation verify serve clean

help:
	@echo "Targets: fmt lint test e2e validation verify serve clean"

fmt:
	uv run ruff format .

lint:
	uv run ruff check .

build-web:
	uv run python scripts/build_web.py

test: build-web
	uv run pytest -q -m "not e2e"

e2e: build-web
	uv run pytest -q -m e2e --browser chromium --tracing retain-on-failure --video retain-on-failure --screenshot only-on-failure --output test-results

validation: build-web
	uv run pytest -q tests/explorer/test_scientific_matrix.py

verify:
	uv run ruff format --check .
	$(MAKE) lint
	uv run python scripts/verify_pyodide_vendor.py
	$(MAKE) test
	$(MAKE) e2e

serve: build-web
	uv run python -m http.server --bind 127.0.0.1 --directory .build/web 8000

clean:
	rm -rf .build .pytest_cache .ruff_cache .playwright .playwright-artifacts test-results
