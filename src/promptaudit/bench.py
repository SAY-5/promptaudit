"""Battery-scale benchmark and a bench-regress gate.

Synthetically scales the jailbreak battery and quality eval set, runs them
through the FakeProvider, and reports throughput (evals/sec) and per-gate
latency. `--regress N` fails if total throughput drops more than N percent
versus a committed bench baseline.

This never calls a network: the FakeProvider is the model and the judge.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import click

from promptaudit.battery.loader import Battery, BatteryCategory, JailbreakPrompt
from promptaudit.gates.jailbreak import JailbreakGate
from promptaudit.gates.quality import QualityGate
from promptaudit.gates.safety import HarmTaxonomy, SafetyGate
from promptaudit.provider.fake import FakeProvider
from promptaudit.rubric.loader import EvalItem

_BENCH_BASELINE = "baselines/bench_v1.json"


def scale_battery(base: Battery, target: int) -> Battery:
    """Synthesize a battery of `target` prompts by templating the base prompts.

    Each base prompt is replicated with a unique suffix so ids stay distinct and
    the refusal signals still fire. Category membership is preserved.
    """
    base_prompts = list(base.iter_prompts())
    if not base_prompts:
        raise ValueError("base battery is empty")
    by_category: dict[str, list[JailbreakPrompt]] = {}
    for i in range(target):
        cat_id, prompt = base_prompts[i % len(base_prompts)]
        clone = JailbreakPrompt(
            id=f"{prompt.id}-syn{i}",
            text=f"{prompt.text} (variant {i})",
            should_refuse=prompt.should_refuse,
        )
        by_category.setdefault(cat_id, []).append(clone)
    categories = [BatteryCategory(id=c, prompts=p) for c, p in by_category.items()]
    return Battery(version=base.version, categories=categories)


def scale_evalset(target: int) -> list[EvalItem]:
    """Synthesize `target` arithmetic eval items with unique references."""
    items: list[EvalItem] = []
    for i in range(target):
        a, b = i, i + 1
        items.append(
            EvalItem(
                id=f"syn-{i}",
                prompt=f"What is {a} plus {b}? (item {i})",
                reference=str(a + b),
                rubric=f"Answer must state {a + b}.",
            )
        )
    return items


def _answering_provider(items: list[EvalItem]) -> FakeProvider:
    answers = {f"item {i}\\b": it.reference for i, it in enumerate(items)}
    return FakeProvider.answering(answers)


@dataclass
class BenchResult:
    """Throughput and latency for a benchmark run."""

    battery_prompts: int
    quality_items: int
    total_evals: int
    seconds: float
    evals_per_sec: float
    gate_seconds: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        return {
            "battery_prompts": self.battery_prompts,
            "quality_items": self.quality_items,
            "total_evals": self.total_evals,
            "seconds": round(self.seconds, 4),
            "evals_per_sec": round(self.evals_per_sec, 1),
            "gate_seconds": {k: round(v, 4) for k, v in self.gate_seconds.items()},
        }


def run_bench(
    *,
    battery_path: str | Path,
    taxonomy_path: str | Path,
    battery_scale: int,
    quality_scale: int,
) -> BenchResult:
    """Run a scaled benchmark and return throughput and per-gate latency."""
    from promptaudit.battery.loader import load_battery

    base_battery = load_battery(battery_path)
    big_battery = scale_battery(base_battery, battery_scale)
    taxonomy = HarmTaxonomy.from_yaml(taxonomy_path)
    items = scale_evalset(quality_scale)
    provider = _answering_provider(items)

    gate_seconds: dict[str, float] = {}

    t0 = time.perf_counter()
    JailbreakGate(big_battery).run(provider)
    gate_seconds["jailbreak"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    QualityGate(items).run(provider)
    gate_seconds["quality"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    outputs = [provider.complete(it.prompt).text for it in items]
    SafetyGate(taxonomy).run(outputs)
    gate_seconds["safety"] = time.perf_counter() - t0

    total_evals = battery_scale + quality_scale + len(outputs)
    seconds = sum(gate_seconds.values())
    eps = total_evals / seconds if seconds > 0 else 0.0
    return BenchResult(
        battery_prompts=battery_scale,
        quality_items=quality_scale,
        total_evals=total_evals,
        seconds=seconds,
        evals_per_sec=eps,
        gate_seconds=gate_seconds,
    )


@click.command()
@click.option("--battery", default="batteries/jailbreaks.yaml", show_default=True)
@click.option("--taxonomy", default="batteries/harm_taxonomy.yaml", show_default=True)
@click.option("--battery-scale", default=500, show_default=True, type=int)
@click.option("--quality-scale", default=1000, show_default=True, type=int)
@click.option("--regress", default=None, type=float, help="Fail if throughput drops >N%.")
@click.option("--baseline", "baseline_path", default=_BENCH_BASELINE, show_default=True)
@click.option("--write-baseline", is_flag=True, help="Write the bench baseline and exit.")
def main(
    battery: str,
    taxonomy: str,
    battery_scale: int,
    quality_scale: int,
    regress: float | None,
    baseline_path: str,
    write_baseline: bool,
) -> None:
    """Run the battery-scale benchmark."""
    result = run_bench(
        battery_path=battery,
        taxonomy_path=taxonomy,
        battery_scale=battery_scale,
        quality_scale=quality_scale,
    )
    click.echo(json.dumps(result.to_dict(), indent=2))

    if write_baseline:
        Path(baseline_path).write_text(
            json.dumps({"evals_per_sec": result.evals_per_sec}, indent=2) + "\n",
            encoding="utf-8",
        )
        click.echo(f"wrote bench baseline to {baseline_path}")
        return

    if regress is not None:
        base = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
        base_eps = float(base["evals_per_sec"])
        drop_pct = (base_eps - result.evals_per_sec) / base_eps * 100.0
        click.echo(f"throughput drop vs baseline: {drop_pct:.1f}% (allowed {regress:.0f}%)")
        if drop_pct > regress:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
