# llm-sql-agent — one-command reproducibility.
#
# Quick start (needs ANTHROPIC_API_KEY — put it in a .env file at the repo root):
#   make setup && make db && make eval && make demos
#
# Use a cheaper model:
#   make eval MODEL=claude-sonnet-4-6

PY      := python3
VENV    := .venv
BIN     := $(VENV)/bin
PYTHON  := $(BIN)/python
PIP     := $(BIN)/pip

# Override on the command line, e.g. `make eval PROVIDER=anthropic MODEL=claude-sonnet-4-6`
PROVIDER ?= anthropic
MODEL    ?=

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Targets:"
	@echo "  setup       Create venv and install the package + deps"
	@echo "  db          Build the seeded SQLite database (deterministic)"
	@echo "  eval        Run the naive-vs-agent benchmark against Claude + render charts"
	@echo "  chart       Render results/*.png from the latest results"
	@echo "  test        Run the pytest suite (real-backend smoke test auto-skips w/o key)"
	@echo "  demo        Live single-question trace (reasoning -> tools -> answer)"
	@echo "  demos       Render results/demo_<id>.gif for the 3 showcase questions (needs agg)"
	@echo "  gif         Record results/demo.gif for the default demo question (needs agg)"
	@echo "  tape        Record results/demo.gif from demo.tape (needs VHS)"
	@echo "  clean       Remove venv, generated db, and caches"

$(VENV):
	$(PY) -m venv $(VENV)

.PHONY: setup
setup: $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[anthropic,dev]"
	@echo "Setup complete. Add ANTHROPIC_API_KEY to .env, then: make db && make eval"

.PHONY: db
db:
	$(PYTHON) -m data.seed

.PHONY: eval
eval:
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
	$(PYTHON) -m llm_sql_agent.cli ask "Total profit per category for completed orders, where profit = quantity * (unit_price - cost)."

.PHONY: demos
demos:
	@command -v agg >/dev/null || { echo "agg not found. Install: https://github.com/asciinema/agg/releases (single static binary, no root)"; exit 1; }
	$(PYTHON) scripts/render_demos.py

.PHONY: gif
gif:
	@command -v agg >/dev/null || { echo "agg not found. Install: https://github.com/asciinema/agg/releases (single static binary, no root)"; exit 1; }
	$(PYTHON) scripts/record_demo.py results/demo.cast $(PYTHON) -m llm_sql_agent.cli ask "Total profit per category for completed orders, where profit = quantity * (unit_price - cost)."
	agg --theme monokai --font-size 16 --idle-time-limit 1 --last-frame-duration 4 results/demo.cast results/demo.gif
	@echo "Wrote results/demo.gif"

.PHONY: tape
tape:
	@command -v vhs >/dev/null || { echo "VHS not found. Install: https://github.com/charmbracelet/vhs"; exit 1; }
	vhs demo.tape
	@echo "Wrote results/demo.gif"

.PHONY: clean
clean:
	rm -rf $(VENV) data/shop.db .pytest_cache build dist src/*.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
