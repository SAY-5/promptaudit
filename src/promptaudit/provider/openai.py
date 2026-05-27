"""OpenAI provider stub.

This is a deliberate stub. CI never instantiates a real network provider; the
hermetic test suite uses FakeProvider exclusively. Wiring a real client here is
left to the operator running an audit against a live model.
"""

from __future__ import annotations

from promptaudit.provider.base import ProviderResponse


class OpenAIProvider:
    """Stub. Raises on use until an API client is wired in."""

    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model

    def complete(self, prompt: str) -> ProviderResponse:
        raise NotImplementedError(
            "OpenAIProvider is a stub. Wire in the OpenAI client to audit a live "
            "model, or use --provider fake for hermetic runs."
        )
