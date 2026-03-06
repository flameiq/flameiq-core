# FlameIQ v1.0.0 — Developer Makefile
# Run `make help` to see all targets.

.PHONY: help install test test-unit test-statistical test-integration \
        lint format typecheck check docs docs-live build release-check \
        benchmark clean version

PYTHON  := python3
PYTEST  := $(PYTHON) -m pytest
RUFF    := $(PYTHON) -m ruff
MYPY    := $(PYTHON) -m mypy
SPHINX  := $(PYTHON) -m sphinx.cmd.build

# ── Help ──────────────────────────────────────────────────────────────────────
help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────────────────────────────
install:  ## Install all dependencies (dev + test + docs)
	$(PYTHON) -m pip install -e ".[dev,test,docs]"
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "\n✓ FlameIQ development environment ready."

# ── Tests ─────────────────────────────────────────────────────────────────────
test:  ## Full test suite with coverage report
	$(PYTEST) tests/ \
	  --cov=flameiq \
	  --cov-report=term-missing \
	  --cov-report=html:.coverage_html \
	  --cov-report=xml:coverage.xml

test-unit:  ## Unit tests only (fast, no I/O)
	$(PYTEST) tests/unit/ -m "unit" -x

test-statistical:  ## Statistical algorithm and determinism tests
	$(PYTEST) tests/statistical/ -m "statistical or determinism" -v

test-integration:  ## Integration and end-to-end tests
	$(PYTEST) tests/integration/ tests/e2e/ -m "integration" -v

test-fast:  ## Unit tests without coverage (fastest feedback loop)
	$(PYTEST) tests/unit/ -x -q --no-header

# ── Code quality ──────────────────────────────────────────────────────────────
lint:  ## Run ruff linter
	$(RUFF) check flameiq/ tests/

format:  ## Auto-format with ruff
	$(RUFF) format flameiq/ tests/
	$(RUFF) check --fix flameiq/ tests/

typecheck:  ## Run mypy strict type checking
	$(MYPY) flameiq/

check: lint typecheck test  ## Run all checks (lint + typecheck + full tests)
	@echo "\n✓ All checks passed."

# ── Documentation ─────────────────────────────────────────────────────────────
docs:  ## Build Sphinx HTML documentation
	$(SPHINX) -b html docs/source docs/build/html -W --keep-going
	@echo "\n✓ Docs built: docs/build/html/index.html"

docs-live:  ## Serve docs with auto-reload (requires sphinx-autobuild)
	sphinx-autobuild docs/source docs/build/html --port 8000 --open-browser

# ── Distribution ──────────────────────────────────────────────────────────────
build:  ## Build sdist and wheel
	$(PYTHON) -m build
	@echo "\n✓ Distributions built in dist/"

release-check:  ## Check distribution packages before upload
	$(PYTHON) -m twine check dist/*

# ── Utilities ─────────────────────────────────────────────────────────────────
clean:  ## Remove all build artefacts and caches
	rm -rf build/ dist/ *.egg-info/ .coverage .coverage_html/ coverage.xml
	rm -rf docs/build/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Clean."

version:  ## Print current package version
	@$(PYTHON) -c "import flameiq; print(flameiq.__version__)"
