"""Provider-agnostic LLM interface and backend factory."""
from __future__ import annotations

from .base import LLMClient, LLMResponse, ToolCall, Usage


def make_client(settings) -> LLMClient:
    """Construct the LLM backend named by settings.provider."""
    provider = settings.provider
    if provider == "anthropic":
        from .anthropic_client import AnthropicClient
        return AnthropicClient(model=settings.model, settings=settings)
    if provider == "claude_cli":
        from .claude_cli_client import ClaudeCLIClient
        return ClaudeCLIClient(model=settings.model, settings=settings)
    if provider == "ollama":
        from .ollama_client import OllamaClient
        return OllamaClient(model=settings.model, settings=settings)
    raise ValueError(
        f"unknown provider: {provider!r}. Supported: 'anthropic' (default), "
        "'claude_cli' (uses the local Claude Code CLI, no API key), 'ollama' (roadmap)."
    )


__all__ = ["LLMClient", "LLMResponse", "ToolCall", "Usage", "make_client"]
