# llm-sql-agent — one-command reproducibility.
#
# No API key: the Claude backend uses your local `claude` CLI login.
#   make setup && make db && make demo
#
# Pick a model:  make eval MODEL=claude-haiku-4-5

PY      := python3
VENV    := .venv
BIN     := $(VENV)/bin
PYTHON  := $(BIN)/python
PIP     := $(BIN)/pip

PROVIDER ?= anthropic
MODEL    ?=

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Targets:"
	@echo "  setup     Create venv and install the package + deps"
	@echo "  db        Build the seeded SQLite database (deterministic)"
	@echo "  demo      Live one-shot-vs-agent showcase on one question"
	@echo "  eval      Naive-vs-agent benchmark (all 35 questions) + charts"
	@echo "  compare   Benchmark Opus 4.8 vs Haiku 4.5 + comparison chart"
	@echo "  test      Run the pytest suite (real-backend smoke test auto-skips w/o claude CLI)"
	@echo "  clean     Remove venv, generated db, and caches"

$(VENV):
	$(PY) -m venv $(VENV)

.PHONY: setup
setup: $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo "Setup complete (uses the local \`claude\` CLI, no API key). Next: make db && make demo"

.PHONY: db
db:
	$(PYTHON) -m data.seed

.PHONY: demo
demo:
	$(PYTHON) scripts/showcase.py --id h15 --model claude-haiku-4-5

.PHONY: eval
eval:
	$(PYTHON) -m evals.harness --provider $(PROVIDER) $(if $(MODEL),--model $(MODEL),)
	$(MAKE) chart

.PHONY: compare
compare:
	$(PYTHON) -m evals.harness --provider anthropic --model claude-opus-4-8
	$(PYTHON) -m evals.harness --provider anthropic --model claude-haiku-4-5
	$(PYTHON) -m evals.compare

.PHONY: chart
chart:
	$(PYTHON) -m evals.plot

.PHONY: test
test:
	$(BIN)/pytest -q

.PHONY: clean
clean:
	rm -rf $(VENV) data/shop.db .pytest_cache build dist src/*.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
