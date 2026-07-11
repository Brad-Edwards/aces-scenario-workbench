.PHONY: hooks lint format test check

# Activate + verify commit-time pre-commit hooks for THIS clone. Must be re-run
# on every fresh clone: .git/hooks is not versioned (ADR-079).
hooks:
	scripts/install-hooks.sh

lint:
	uv run ruff check .

format:
	uv run ruff format .

test:
	uv run pytest

# CI-equivalent local gate.
check:
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest
