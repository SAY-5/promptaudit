"""Load a rubric-scored quality eval set from JSONL."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


class EvalItem(BaseModel):
    """A single rubric-scored quality task."""

    id: str
    prompt: str
    reference: str
    rubric: str = ""


def load_evalset(path: str | Path) -> list[EvalItem]:
    """Parse a JSONL eval set; blank lines are skipped."""
    items: list[EvalItem] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(EvalItem.model_validate(json.loads(line)))
    return items
