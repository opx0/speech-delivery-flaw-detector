.PHONY: setup contract check lint typecheck test web-check

setup:
	uv sync
	cd web && npm ci

# Regenerate the JSON Schema bundle, the example fixtures and the TypeScript types.
contract:
	uv run python scripts/export_contract.py
	cd web && npm run contract:ts

lint:
	uv run ruff format --check .
	uv run ruff check .

typecheck:
	uv run pyright

test:
	uv run pytest

web-check:
	cd web && npm run typecheck && npm run validate:fixtures

check: lint typecheck test web-check
