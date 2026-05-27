"""Load and validate the jailbreak battery from YAML."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class JailbreakPrompt(BaseModel):
    """A single battery prompt with its expected behavior."""

    id: str
    text: str
    should_refuse: bool = True


class BatteryCategory(BaseModel):
    """A named attack class and its prompts."""

    id: str
    description: str = ""
    prompts: list[JailbreakPrompt] = Field(default_factory=list)


class Battery(BaseModel):
    """A versioned collection of attack categories."""

    version: int = 1
    categories: list[BatteryCategory] = Field(default_factory=list)

    def iter_prompts(self) -> Iterator[tuple[str, JailbreakPrompt]]:
        """Yield (category_id, prompt) pairs across the whole battery."""
        for cat in self.categories:
            for prompt in cat.prompts:
                yield cat.id, prompt

    def prompt_ids(self) -> list[str]:
        return [p.id for _, p in self.iter_prompts()]

    def category_ids(self) -> list[str]:
        return [c.id for c in self.categories]


def load_battery(path: str | Path) -> Battery:
    """Parse a battery YAML file into a validated `Battery`."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    version = int(raw.get("version", 1))
    cats_raw = raw.get("categories", {})
    categories: list[BatteryCategory] = []
    # Support the mapping form `categories: {id: {description, prompts}}`.
    for cat_id, body in cats_raw.items():
        categories.append(
            BatteryCategory(
                id=cat_id,
                description=body.get("description", ""),
                prompts=[JailbreakPrompt.model_validate(p) for p in body.get("prompts", [])],
            )
        )
    return Battery(version=version, categories=categories)
