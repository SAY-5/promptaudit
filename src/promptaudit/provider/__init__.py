"""Model providers: a Protocol plus a scripted FakeProvider and real stubs."""

from __future__ import annotations

from promptaudit.provider.base import Provider, ProviderResponse
from promptaudit.provider.fake import FakeProvider

__all__ = ["Provider", "ProviderResponse", "FakeProvider", "get_provider"]


def get_provider(name: str) -> Provider:
    """Resolve a provider by name. Only `fake` is usable in CI."""
    if name == "fake":
        return FakeProvider.default()
    if name == "openai":
        from promptaudit.provider.openai import OpenAIProvider

        return OpenAIProvider()
    if name == "anthropic":
        from promptaudit.provider.anthropic import AnthropicProvider

        return AnthropicProvider()
    raise ValueError(f"unknown provider: {name!r}")
