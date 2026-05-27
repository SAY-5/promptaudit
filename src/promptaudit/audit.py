"""Audit orchestration: run all three gates and assemble a report.

This ties the gates, baseline, regression, and report modules together so the
CLI and tests share one code path.
"""

from __future__ import annotations

from pathlib import Path

from promptaudit.baseline import Baseline
from promptaudit.battery import load_battery
from promptaudit.gates.jailbreak import JailbreakGate
from promptaudit.gates.quality import QualityGate
from promptaudit.gates.safety import HarmTaxonomy, SafetyGate
from promptaudit.models import GateResult
from promptaudit.provider.base import Provider
from promptaudit.report import AuditReport, find_newly_succeeded
from promptaudit.rubric import load_evalset


def run_gates(
    provider: Provider,
    *,
    battery_path: str | Path,
    taxonomy_path: str | Path,
    evalset_path: str | Path,
    quality_threshold: float = 1.0,
) -> tuple[dict[str, GateResult], int, int]:
    """Run safety, jailbreak, and quality gates. Returns results + versions."""
    battery = load_battery(battery_path)
    taxonomy = HarmTaxonomy.from_yaml(taxonomy_path)
    evalset = load_evalset(evalset_path)

    jailbreak = JailbreakGate(battery).run(provider)
    quality = QualityGate(evalset, threshold=quality_threshold).run(provider)
    # Safety classifies the model's answers to the quality prompts and to every
    # battery prompt, so it sees the full surface of model output.
    outputs = [provider.complete(item.prompt).text for item in evalset]
    outputs += [provider.complete(p.text).text for _, p in battery.iter_prompts()]
    safety = SafetyGate(taxonomy).run(outputs)

    results = {"safety": safety, "jailbreak": jailbreak, "quality": quality}
    return results, battery.version, taxonomy.version


def audit(
    provider: Provider,
    *,
    baseline_path: str | Path,
    battery_path: str | Path,
    taxonomy_path: str | Path,
    evalset_path: str | Path,
    model_name: str | None = None,
    quality_threshold: float = 1.0,
) -> AuditReport:
    """Run the full audit and compare to a committed baseline."""
    results, _bat_v, _tax_v = run_gates(
        provider,
        battery_path=battery_path,
        taxonomy_path=taxonomy_path,
        evalset_path=evalset_path,
        quality_threshold=quality_threshold,
    )
    baseline = Baseline.from_json(baseline_path)
    regression = baseline.compare(results)

    newly = find_newly_succeeded(results["jailbreak"], baseline_failures=set())
    name = model_name or baseline.model
    return AuditReport(
        model=name,
        verdict=regression.verdict,
        gates=results,
        regression=regression,
        newly_succeeded_jailbreaks=newly,
    )
