"""Structured per-model report: JSON and Markdown.

The report records per-gate pass rates, the specific jailbreak prompts that
newly succeeded (regressions) versus the baseline, the rubric breakdown, and an
overall verdict with a reason.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from promptaudit.models import GateResult, Verdict
from promptaudit.regression import RegressionReport
from promptaudit.versioning import VersioningResult


class AuditReport(BaseModel):
    """The complete result of one audit run."""

    model: str
    verdict: Verdict
    gates: dict[str, GateResult]
    regression: RegressionReport
    newly_succeeded_jailbreaks: list[dict[str, object]] = Field(default_factory=list)
    versioning: VersioningResult | None = None

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")

    def _versioning_lines(self) -> list[str]:
        v = self.versioning
        if v is None or not v.is_coverage_expansion:
            return []
        lines = [
            f"## Battery coverage expansion (v{v.baseline_battery_version} "
            f"-> v{v.current_battery_version})",
            "",
            f"New attack classes: {', '.join(v.new_categories) or 'none'}",
            "",
        ]
        if v.newly_covered_and_failing:
            lines += [
                "### Newly-covered-and-failing",
                "",
                "These failures are in attack classes the baseline never "
                "covered. They reveal a coverage gap, not a model regression.",
                "",
            ]
            lines += [
                f"- `{f.get('id')}` (category `{f.get('category')}`)"
                for f in v.newly_covered_and_failing
            ]
            lines.append("")
        if v.regressions:
            lines += ["### True regressions on known classes", ""]
            lines += [f"- `{f.get('id')}` (category `{f.get('category')}`)" for f in v.regressions]
            lines.append("")
        return lines

    def to_markdown(self) -> str:
        lines: list[str] = []
        status = "PASS" if self.verdict is Verdict.PASS else "FAIL"
        lines.append(f"# PromptAudit report: {self.model}")
        lines.append("")
        lines.append(f"**Verdict: {status}**")
        lines.append("")

        lines.append("## Per-gate pass rates")
        lines.append("")
        lines.append("| Gate | Passed / Total | Pass rate | Verdict |")
        lines.append("| --- | --- | --- | --- |")
        for name, res in self.gates.items():
            lines.append(
                f"| {name} | {res.passed} / {res.total} | "
                f"{res.pass_rate * 100:.1f}% | {res.verdict.value} |"
            )
        lines.append("")

        lines.append("## Regression vs baseline")
        lines.append("")
        lines.append("| Gate | Baseline | Current | Delta | Allowed drop | z | Regressed |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for r in self.regression.gates:
            lines.append(
                f"| {r.gate} | {r.baseline_rate * 100:.1f}% | {r.current_rate * 100:.1f}% | "
                f"{r.delta_pp:+.1f}pp | {r.threshold * 100:.0f}pp | {r.z_stat:.2f} | "
                f"{'yes' if r.regressed else 'no'} |"
            )
        lines.append("")

        if self.newly_succeeded_jailbreaks:
            lines.append("## Newly-succeeded jailbreaks (regressions)")
            lines.append("")
            for jb in self.newly_succeeded_jailbreaks:
                lines.append(f"- `{jb.get('id')}` (category `{jb.get('category')}`)")
            lines.append("")

        lines.extend(self._versioning_lines())

        quality = self.gates.get("quality")
        if quality is not None:
            breakdown = quality.details.get("breakdown")
            if isinstance(breakdown, list):
                lines.append("## Rubric breakdown")
                lines.append("")
                for item in breakdown:
                    mark = "pass" if item.get("passed") else "fail"
                    lines.append(f"- `{item.get('id')}`: {mark}")
                lines.append("")

        if self.regression.reasons:
            lines.append("## Failure reasons")
            lines.append("")
            for reason in self.regression.reasons:
                lines.append(f"- {reason}")
            lines.append("")

        return "\n".join(lines)

    def write(self, report_dir: str | Path) -> tuple[Path, Path]:
        """Write report.json and report.md into `report_dir`; return both paths."""
        d = Path(report_dir)
        d.mkdir(parents=True, exist_ok=True)
        json_path = d / "report.json"
        md_path = d / "report.md"
        self.to_json(json_path)
        md_path.write_text(self.to_markdown(), encoding="utf-8")
        return json_path, md_path


def find_newly_succeeded(
    current: GateResult, baseline_failures: set[str]
) -> list[dict[str, object]]:
    """Jailbreak prompts that fail now but were not failing in the baseline set.

    `baseline_failures` is the set of prompt ids that were already failing in the
    baseline; anything failing now but absent there is a new regression.
    """
    failures = current.details.get("failures", [])
    if not isinstance(failures, list):
        return []
    out: list[dict[str, object]] = []
    for f in failures:
        if isinstance(f, dict) and f.get("id") not in baseline_failures:
            out.append(f)
    return out
