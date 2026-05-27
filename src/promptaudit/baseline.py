"""Committed baselines: load, build, compare, and update.

A baseline is a small JSON file recording each gate's pass rate and sample size
plus the battery/taxonomy versions it was measured against. A run compares its
fresh `GateResult`s to the baseline via the regression module.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from promptaudit.models import GateResult
from promptaudit.regression import GateRegression, RegressionReport, evaluate, evaluate_gate


class GateBaseline(BaseModel):
    """Recorded pass rate and sample size for one gate."""

    rate: float = Field(ge=0.0, le=1.0)
    n: int = Field(ge=0)


class Baseline(BaseModel):
    """A committed baseline for a model."""

    model: str
    battery_version: int = 1
    taxonomy_version: int = 1
    gates: dict[str, GateBaseline] = Field(default_factory=dict)

    @classmethod
    def from_json(cls, path: str | Path) -> Baseline:
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")

    @classmethod
    def from_results(
        cls,
        model: str,
        results: dict[str, GateResult],
        *,
        battery_version: int = 1,
        taxonomy_version: int = 1,
    ) -> Baseline:
        gates = {
            name: GateBaseline(rate=res.pass_rate, n=res.total) for name, res in results.items()
        }
        return cls(
            model=model,
            battery_version=battery_version,
            taxonomy_version=taxonomy_version,
            gates=gates,
        )

    def compare(self, results: dict[str, GateResult]) -> RegressionReport:
        """Compare fresh results to this baseline and return the regression report."""
        regressions: list[GateRegression] = []
        for name, res in results.items():
            base = self.gates.get(name)
            if base is None:
                # A gate with no baseline cannot regress; treat as informational.
                regressions.append(
                    evaluate_gate(
                        name,
                        baseline_rate=res.pass_rate,
                        baseline_n=res.total,
                        current_rate=res.pass_rate,
                        current_n=res.total,
                    )
                )
                continue
            regressions.append(
                evaluate_gate(
                    name,
                    baseline_rate=base.rate,
                    baseline_n=base.n,
                    current_rate=res.pass_rate,
                    current_n=res.total,
                )
            )
        return evaluate(regressions)
