"""Provider protocol and response model."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ProviderResponse(BaseModel):
    """A single model completion."""

    text: str
    model: str = "unknown"
    refused: bool = Field(
        default=False,
        description="Whether the provider self-reports a refusal. Gates may also "
        "detect refusals from the text itself.",
    )


@runtime_checkable
class Provider(Protocol):
    """Minimal interface a model provider must satisfy."""

    name: str

    def complete(self, prompt: str) -> ProviderResponse:
        """Return a completion for a single prompt."""
        ...
