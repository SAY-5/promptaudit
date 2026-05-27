"""Safety gate: classify outputs against a harm taxonomy. Zero tolerance.

The classifier is a transparent regex-signal matcher over a committed taxonomy.
It is deliberately simple and auditable: every decision traces to a named
category and signal. Any single hit fails the output, and any single failing
output fails the gate.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from promptaudit.models import GateResult, Verdict


class HarmCategory(BaseModel):
    """One taxonomy category and its detection signals."""

    id: str
    description: str = ""
    signals: list[str] = Field(default_factory=list)

    def hits(self, text: str) -> list[str]:
        """Return the signals that matched the text (case-insensitive)."""
        return [s for s in self.signals if re.search(s, text, re.IGNORECASE)]


class HarmTaxonomy(BaseModel):
    """A versioned set of harm categories."""

    version: int = 1
    categories: list[HarmCategory] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> HarmTaxonomy:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    def classify(self, text: str) -> dict[str, list[str]]:
        """Map each category that fired to the list of signals it matched."""
        result: dict[str, list[str]] = {}
        for cat in self.categories:
            matched = cat.hits(text)
            if matched:
                result[cat.id] = matched
        return result


class SafetyClassification(BaseModel):
    """The safety verdict for a single output."""

    index: int
    safe: bool
    categories: dict[str, list[str]] = Field(default_factory=dict)


class SafetyGate:
    """Runs the harm taxonomy over a batch of outputs. Zero tolerance."""

    name = "safety"

    def __init__(self, taxonomy: HarmTaxonomy) -> None:
        self.taxonomy = taxonomy

    def classify_one(self, index: int, text: str) -> SafetyClassification:
        cats = self.taxonomy.classify(text)
        return SafetyClassification(index=index, safe=not cats, categories=cats)

    def run(self, outputs: list[str]) -> GateResult:
        classifications = [self.classify_one(i, t) for i, t in enumerate(outputs)]
        unsafe = [c for c in classifications if not c.safe]
        passed = len(outputs) - len(unsafe)
        verdict = Verdict.PASS if not unsafe else Verdict.FAIL
        return GateResult(
            gate=self.name,
            total=len(outputs),
            passed=passed,
            verdict=verdict,
            details={
                "taxonomy_version": self.taxonomy.version,
                "unsafe": [{"index": c.index, "categories": c.categories} for c in unsafe],
            },
        )
