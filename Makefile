SHELL := /bin/sh

BADGE_OUTPUT ?= .github/assets/spec-coverage-badge.svg

.PHONY: test pre-commit lint lint-fix badge test-mcp-e2e

test:
	pytest tests/ -v -rs

pre-commit:
	pre-commit run --all-files

lint:
	ruff check src/ tests/ examples/
	mypy src/
	black --check src/ tests/ examples/

lint-fix:
	ruff check --fix src/ tests/ examples/
	black src/ tests/ examples/

badge:
	SPECLEFT_BADGE_OUTPUT="$(BADGE_OUTPUT)" python3 scripts/update_spec_coverage_badge.py

test-mcp-e2e: ## Run MCP stdio E2E against an installed wheel in a clean container
	python -m build
	docker build -f mcp/test-mcp.Dockerfile -t specleft-mcp-e2e .
	docker run --rm specleft-mcp-e2e
