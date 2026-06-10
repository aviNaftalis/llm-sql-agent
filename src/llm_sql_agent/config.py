"""Settings, .env loading, and the per-model price table.

Everything is env-driven. The backend is Claude (Anthropic) by default; a local
Ollama backend is on the roadmap. An ANTHROPIC_API_KEY is required — drop it in a
`.env` file at the repo root (gitignored) and it's loaded automatically.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# Repo root = three levels up from this file (src/llm_sql_agent/config.py).
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.path.join(_ROOT, "data", "shop.db")
EVAL_SET_PATH = os.path.join(_ROOT, "data", "eval_set.jsonl")
RESULTS_DIR = os.path.join(_ROOT, "results")
_DOTENV_PATH = os.path.join(_ROOT, ".env")

# USD per 1M tokens, (input, output). Used for cost accounting in tracing.py.
PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

_DEFAULT_MODEL = {
    "anthropic": "claude-opus-4-8",
    "ollama": "llama3.1",  # roadmap
}


def load_dotenv(path: str = _DOTENV_PATH) -> None:
    """Minimal .env loader (stdlib): KEY=VALUE lines, existing env wins."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("'\"")
            os.environ.setdefault(key, value)


def price_for(model: str) -> tuple[float, float]:
    """(input, output) USD per 1M tokens; 0 for unknown/local models."""
    return PRICES.get(model, (0.0, 0.0))


@dataclass(frozen=True)
class Settings:
    provider: str          # anthropic | ollama (roadmap)
    model: str
    db_path: str
    max_steps: int         # hard cap on agent reasoning steps
    max_rows: int          # row cap injected into tool queries (guardrail)
    request_timeout: float # per-LLM-call timeout (seconds)
    max_retries: int       # LLM call retries on transient errors


def load_settings(
    provider: str | None = None,
    model: str | None = None,
    db_path: str | None = None,
) -> Settings:
    load_dotenv()
    provider = provider or os.getenv("LLM_PROVIDER", "anthropic")
    model = model or os.getenv("LLM_MODEL") or _DEFAULT_MODEL.get(provider, "claude-opus-4-8")
    return Settings(
        provider=provider,
        model=model,
        db_path=db_path or os.getenv("DB_PATH", DEFAULT_DB_PATH),
        max_steps=int(os.getenv("AGENT_MAX_STEPS", "10")),
        max_rows=int(os.getenv("SQL_MAX_ROWS", "1000")),
        request_timeout=float(os.getenv("LLM_TIMEOUT", "60")),
        max_retries=int(os.getenv("LLM_MAX_RETRIES", "3")),
    )
