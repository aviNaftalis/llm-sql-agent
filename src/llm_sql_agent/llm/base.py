"""The normalized LLM interface every backend implements.

Messages and tools use the Anthropic tool-use shape (text / tool_use /
tool_result content blocks) as the internal lingua franca — the Anthropic
backend passes them through almost verbatim, the mock backend interprets them,
and a future Ollama backend translates them. `chat()` always returns the same
normalized `LLMResponse` regardless of provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    stop_reason: str = ""
    raw: Any = None


class LLMClient(Protocol):
    model: str

    def chat(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """One model turn. `tools` present => tool-calling (agent) mode."""
        ...
