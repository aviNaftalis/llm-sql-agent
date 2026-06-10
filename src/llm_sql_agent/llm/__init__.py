"""Provider-agnostic LLM interface and backend factory."""
from __future__ import annotations

from .base import LLMClient, LLMResponse, ToolCall, Usage


def make_client(settings, oracle=None) -> LLMClient:
    """Construct the LLM backend named by settings.provider.

    `oracle` is only consumed by the mock backend (a question -> gold-SQL map
    that makes its scripted behavior deterministic); real backends ignore it.
    """
    provider = settings.provider
    if provider == "mock":
        from .mock_client import MockClient
        return MockClient(model=settings.model, oracle=oracle or {})
    if provider == "anthropic":
        from .anthropic_client import AnthropicClient
        return AnthropicClient(model=settings.model, settings=settings)
    if provider == "ollama":
        from .ollama_client import OllamaClient
        return OllamaClient(model=settings.model, settings=settings)
    raise ValueError(f"unknown provider: {provider!r}")


__all__ = ["LLMClient", "LLMResponse", "ToolCall", "Usage", "make_client"]
