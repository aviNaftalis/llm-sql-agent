"""Local Ollama backend — PLANNED (roadmap), not yet implemented.

The normalized `LLMClient` interface and the tool registry are designed so that
dropping a real implementation in here requires no changes elsewhere: translate
the Anthropic-shaped `messages`/`tools` into Ollama's `/api/chat` tool-calling
format, map the response's `tool_calls` and token counts back into
`LLMResponse`, and that's it. Tracked in the README roadmap.
"""
from __future__ import annotations

from .base import LLMResponse


class OllamaClient:
    def __init__(self, model: str, settings):
        self.model = model
        self._settings = settings

    def chat(self, system, messages, tools=None) -> LLMResponse:
        raise NotImplementedError(
            "The Ollama backend is planned but not implemented yet. "
            "Use LLM_PROVIDER=mock (keyless) or LLM_PROVIDER=anthropic today. "
            "See the README roadmap."
        )
