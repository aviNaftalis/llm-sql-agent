# llm-sql-agent — one-command reproducibility.
#
# Quick start (no API key needed):
#   make setup && make db && make eval && make demo
#
# Real-model headline numbers (needs ANTHROPIC_API_KEY in your environment/.env):
#   make eval-real PROVIDER=anthropic

PY      := python3
VENV    := .venv
BIN     := $(VENV)/bin
PYTHON  := $(BIN)/python
PIP     := $(BIN)/pip

# Override on the command line, e.g. `make eval-real PROVIDER=anthropic MODEL=claude-sonnet-4-6`
PROVIDER ?= mock
MODEL    ?=

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Targets:"
	@echo "  setup       Create venv and install the package + deps"
	@echo "  db          Build the seeded SQLite database (deterministic)"
	@echo "  eval        Run the benchmark on the MOCK backend (keyless, reproducible)"
	@echo "  eval-real   Run on a real backend: make eval-real PROVIDER=anthropic"
	@echo "  chart       Render results/*.png from the latest results"
	@echo "  test        Run the pytest suite (incl. the benchmark-as-tests)"
	@echo "  demo        Live single-question trace (reasoning -> tools -> answer)"
	@echo "  clean       Remove venv, generated db, and caches"

$(VENV):
	$(PY) -m venv $(VENV)

.PHONY: setup
setup: $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[anthropic,dev]" || $(PIP) install -e ".[dev]"
	@echo "Setup complete. Next: make db && make eval"

.PHONY: db
db:
	$(PYTHON) -m data.seed

.PHONY: eval
eval:
	LLM_PROVIDER=mock $(PYTHON) -m evals.harness --provider mock
	$(MAKE) chart

.PHONY: eval-real
eval-real:
	$(PYTHON) -m evals.harness --provider $(PROVIDER) $(if $(MODEL),--model $(MODEL),)
	$(MAKE) chart

.PHONY: chart
chart:
	$(PYTHON) -m evals.plot

.PHONY: test
test:
	$(BIN)/pytest -q

.PHONY: demo
demo:
	$(PYTHON) -m llm_sql_agent.cli ask "Top 3 products by revenue in 2024 (completed orders), with category"

.PHONY: clean
clean:
	rm -rf $(VENV) data/shop.db .pytest_cache build dist src/*.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
