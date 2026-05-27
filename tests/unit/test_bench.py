from pathlib import Path

from promptaudit.battery.loader import load_battery
from promptaudit.bench import run_bench, scale_battery, scale_evalset

BATTERY = Path(__file__).parents[2] / "batteries" / "jailbreaks.yaml"
TAXONOMY = Path(__file__).parents[2] / "batteries" / "harm_taxonomy.yaml"


def test_scale_battery_reaches_target_with_unique_ids():
    base = load_battery(BATTERY)
    scaled = scale_battery(base, 500)
    ids = scaled.prompt_ids()
    assert len(ids) == 500
    assert len(set(ids)) == 500
    # Category membership preserved.
    assert set(scaled.category_ids()).issubset(set(base.category_ids()))


def test_scale_evalset_references_are_correct():
    items = scale_evalset(50)
    assert len(items) == 50
    assert items[3].reference == str(3 + 4)


def test_run_bench_smoke_reports_throughput():
    result = run_bench(
        battery_path=BATTERY,
        taxonomy_path=TAXONOMY,
        battery_scale=40,
        quality_scale=40,
    )
    assert result.battery_prompts == 40
    assert result.quality_items == 40
    assert result.total_evals == 120  # 40 jailbreak + 40 quality + 40 safety outputs
    assert result.evals_per_sec > 0
    assert set(result.gate_seconds) == {"jailbreak", "quality", "safety"}
