# llm-sql-agent

**A natural-language question goes in, the right SQL comes out — and we measure how much an *agent* beats a one-shot prompt at getting it right.**

[Claude](https://www.anthropic.com/claude "Anthropic's Claude model family")
answers questions over a SQL database by inspecting the schema, writing a query,
running it, reading the error when it fails, and fixing it — a
[tool-calling](https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview "Tool use / function calling — the model emits structured calls your code executes")
agent loop. This repo builds that **two ways** — a **naive** one-shot prompt and an
**agentic** loop — and benchmarks them on a ground-truth eval set across
**accuracy, speed, and token cost**.

> **naive vs. agentic** is the comparison this project exists to make. *Naive* =
> one prompt, one query, no recovery. *Agentic* = the model drives tools over
> multiple steps and repairs its own mistakes. The whole point is to quantify the
> gap.

## Demo

Three complex questions, each answered live by the agent (schema inspection →
query → answer) on **Claude Opus 4.8**. Rendered with `make demos`.

**1. Profit per category** — multi-join + arithmetic
![profit per category](results/demo_h02.gif)

**2. Best-selling product within each category** — window function + ranking (CTE)
![best seller per category](results/demo_h13.gif)

**3. Above-average-spending customers** — CTE + subquery comparison
![above-average spenders](results/demo_h06.gif)

## Results

<!-- RESULTS -->
_Run `make eval` to generate `results/accuracy.png` and `results/latency_tokens.png`._

`make eval` runs all 35 graded questions (10 easy / 10 medium / 15 hard) twice —
naive and agent — and prints a per-tier table of **accuracy** (execution accuracy
+ agent repair rate), **speed** (p95 latency, steps), and **cost** (tokens, USD),
writing `results/benchmark_summary.json`. The agent trades more tokens and steps
for higher accuracy — the production trade-off this project is about.

### Model comparison: Opus 4.8 vs. Haiku 4.5

`make compare` runs the whole benchmark on two models and charts where the
capability gap actually shows up (typically the hard tier — joins, CTEs, window
functions), and what the agent loop recovers on the weaker model.

<!-- COMPARE -->
_Run `make compare` to generate `results/model_comparison.png`._

## The two approaches

### Naive baseline (`src/llm_sql_agent/naive.py`)
One completion: the whole schema is dumped into the prompt, the model returns a
single SQL string, executed **once**. No introspection, no retry. The control —
it captures the failure modes (hallucinated columns, missed joins, no recovery).

### Agentic loop (`src/llm_sql_agent/agent.py`)
```
reason → call a tool → observe result/error → repair → … → final answer
```
Tools (`src/llm_sql_agent/tools/`): `list_tables`, `describe_table`, `run_sql`.
The orchestration that makes it production-grade:

- **Self-repair** — a failed query's error is fed back so the model fixes it.
- **Guardrails** (`guardrails.py`) — `sqlparse`-validated single read-only
  `SELECT`/`WITH` only (writes rejected), an injected `LIMIT`, and a read-only
  SQLite connection (`mode=ro` + `PRAGMA query_only`). Even a buggy query can't
  mutate the database.
- **Step cap, retries, timeouts** — the loop is bounded; the SDK retries
  transient API errors with backoff; queries have a runaway backstop.
- **Tracing + cost accounting** (`tracing.py`) — every LLM/tool step is a timed
  span with token counts and an estimated USD cost.

## How it's measured

The eval set (`data/eval_set.jsonl`) is 35 graded questions. The metric is
**execution accuracy** (`evals/metrics.py`): run the gold and predicted queries
and compare result sets — order-insensitive unless the gold query has a top-level
`ORDER BY`. The harness also records p50/p95 latency, step count, tokens, and USD.

**Tested deterministically, no key required.** `tests/test_agent_loop.py` drives
the agent loop with a scripted LLM double (`tests/fakes.py`) over complex
multi-join / CTE / window-function questions and asserts it recovers from an
injected error and lands on a correct, executing query — and that speed/token
metrics are recorded. `tests/test_smoke_real.py` is a **key-gated** smoke test that
runs the real Claude backend and checks it produces valid, executing SQL (skipped
when `ANTHROPIC_API_KEY` is unset, so the offline suite stays green).

## Backends

One normalized interface (`src/llm_sql_agent/llm/base.py`); the agent and eval
code are backend-agnostic.

| Backend | Status | Notes |
|---|---|---|
| `anthropic` | ✅ default | Claude via the Messages API with **native tool-use**. `claude-opus-4-8` by default; `LLM_MODEL=claude-sonnet-4-6` for a cheaper run. Clean token/cost accounting. |
| `claude_cli` | ✅ | Claude via the local **`claude` CLI** (`claude -p`) — **no API key**, uses your Claude Code login. Drives the agent with a JSON-action protocol instead of native tool-use. The demo GIFs above were generated this way. (Token/cost figures include the CLI's own context overhead, so use `anthropic` for representative cost numbers.) |
| `ollama` | 🟡 roadmap | Local models, no key/cost. Shipped as a documented stub — the interface and tool registry are designed so it drops in with no changes elsewhere. |

## Quick start

Two ways to authenticate:

- **API key** — put `ANTHROPIC_API_KEY=sk-ant-...` in a `.env` file at the repo
  root (see `.env.example`); it's loaded automatically. Uses the `anthropic`
  backend (native tool-use, clean cost accounting).
- **No key** — if you have the [`claude` CLI](https://docs.claude.com/en/docs/claude-code)
  logged in, set `LLM_PROVIDER=claude_cli` and skip the key entirely.

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env   # or: export LLM_PROVIDER=claude_cli

make setup        # venv + install
make db           # build the deterministic SQLite database
make test         # offline suite (real-backend smoke test auto-skips)
make eval         # naive-vs-agent benchmark → table + charts
make compare      # benchmark Opus 4.8 vs Haiku 4.5 → comparison chart
make demos        # render the 3 showcase demo GIFs (needs `agg`)
make demo         # one live trace in the terminal
```

Cheaper model: `make eval MODEL=claude-sonnet-4-6`.

Charts land in `results/` as PNGs. On WSL, view them with
`explorer.exe results\accuracy.png`; on Linux/macOS use `xdg-open` / `open`.

## Layout

```
src/llm_sql_agent/
  agent.py        agentic loop (tool-calling + self-repair)
  naive.py        one-shot baseline
  guardrails.py   read-only SELECT validation + LIMIT injection
  db.py           read-only SQLite access
  tracing.py      span tracing + token/cost accounting
  tools/          list_tables / describe_table / run_sql + schemas
  llm/            base interface; anthropic backend; ollama (roadmap stub)
data/             schema.sql, deterministic seed.py, eval_set.jsonl (35 questions)
evals/            harness.py, metrics.py, plot.py
scripts/          record_demo.py, render_demos.py (asciicast -> GIF, no root)
tests/            guardrails, tools, metrics, agent-loop (scripted), real smoke
```

## Roadmap

- **Local Ollama backend** — open-model runs with no key/cost (stub in place).
- **LLM-judge eval track** — score the agent's natural-language answer, not just
  the SQL result set.
- **More failure modes in the eval set** — ambiguous questions, schema-change
  robustness, deeper multi-step reasoning.
