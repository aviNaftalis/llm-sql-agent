"""Anthropic (Claude) backend — native tool-use via the Messages API.

Translates Claude's `tool_use` content blocks and `usage` into the normalized
`LLMResponse`. The default model is `claude-opus-4-8`; override with
LLM_MODEL (e.g. `claude-sonnet-4-6` for a cheaper run).
"""
from __future__ import annotations

from .base import LLMResponse, ToolCall, Usage

_MAX_TOKENS = 2048


class AnthropicClient:
    def __init__(self, model: str, settings):
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover - exercised only without the SDK
            raise RuntimeError(
                "The 'anthropic' package is required for the anthropic backend. "
                "Install it with: pip install -e \".[anthropic]\""
            ) from e
        self.model = model
        # The SDK retries 429/5xx with exponential backoff on its own.
        self._client = anthropic.Anthropic(
            max_retries=settings.max_retries,
            timeout=settings.request_timeout,
        )

    def chat(self, system, messages, tools=None) -> LLMResponse:
        kwargs = {
            "model": self.model,
            "max_tokens": _MAX_TOKENS,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        resp = self._client.messages.create(**kwargs)

        text_parts, tool_calls = [], []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input)))

        return LLMResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            usage=Usage(resp.usage.input_tokens, resp.usage.output_tokens),
            stop_reason=resp.stop_reason or "",
            raw=resp,
        )
