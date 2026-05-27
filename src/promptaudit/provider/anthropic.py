"""Anthropic provider stub.

This is a deliberate stub. CI never instantiates a real network provider; the
hermetic test suite uses FakeProvider exclusively. Wiring a real client here is
left to the operator running an audit against a live model.
"""

from __future__ import annotations

from promptaudit.provider.base import ProviderResponse


class AnthropicProvider:
    """Stub. Raises on use until an API client is wired in."""

    name = "anthropic"

    def __init__(self, model: str = "claude-3-5-haiku") -> None:
        self.model = model

    def complete(self, prompt: str) -> ProviderResponse:
        raise NotImplementedError(
            "AnthropicProvider is a stub. Wire in the Anthropic client to audit a "
            "live model, or use --provider fake for hermetic runs."
        )
