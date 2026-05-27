"""Battery versioning: tell a coverage expansion apart from a true regression.

When a model is audited against a battery version newer than the one its
baseline was recorded against, any failing prompt in a category the baseline
never covered is a coverage expansion that revealed a gap, not a model
regression. We label these `newly-covered-and-failing` and report them in a
distinct section.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from promptaudit.models import GateResult


class VersioningResult(BaseModel):
    """Split of jailbreak failures by whether the category is newly covered."""

    baseline_battery_version: int
    current_battery_version: int
    new_categories: list[str] = Field(default_factory=list)
    newly_covered_and_failing: list[dict[str, object]] = Field(default_factory=list)
    regressions: list[dict[str, object]] = Field(default_factory=list)

    @property
    def is_coverage_expansion(self) -> bool:
        return self.current_battery_version > self.baseline_battery_version


def classify_failures(
    jailbreak_result: GateResult,
    *,
    baseline_battery_version: int,
    baseline_categories: set[str],
) -> VersioningResult:
    """Partition jailbreak failures into regressions vs newly-covered failures."""
    raw_version = jailbreak_result.details.get("battery_version", 1)
    current_version = int(raw_version) if isinstance(raw_version, int | str) else 1
    failures_raw = jailbreak_result.details.get("failures", [])
    failures = (
        [f for f in failures_raw if isinstance(f, dict)] if isinstance(failures_raw, list) else []
    )

    rates = jailbreak_result.details.get("per_category_rate", {})
    current_categories = set(rates) if isinstance(rates, dict) else set()
    new_categories = sorted(current_categories - baseline_categories)

    newly: list[dict[str, object]] = []
    regressions: list[dict[str, object]] = []
    for f in failures:
        category = f.get("category")
        if category in new_categories:
            newly.append(f)
        else:
            regressions.append(f)

    return VersioningResult(
        baseline_battery_version=baseline_battery_version,
        current_battery_version=current_version,
        new_categories=new_categories,
        newly_covered_and_failing=newly,
        regressions=regressions,
    )
