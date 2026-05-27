"""Battery versioning: newly-covered-and-failing vs true regression."""

from __future__ import annotations

from pathlib import Path

from promptaudit.audit import audit
from promptaudit.gates.jailbreak import JailbreakGate
from promptaudit.models import Verdict
from promptaudit.provider import FakeProvider
from promptaudit.rubric import load_evalset
from promptaudit.versioning import classify_failures

ROOT = Path(__file__).parents[2]
BASELINE = ROOT / "baselines" / "model_v1.json"
BATTERY_V1 = ROOT / "batteries" / "jailbreaks.yaml"
BATTERY_V2 = ROOT / "batteries" / "jailbreaks_v2.yaml"
TAXONOMY = ROOT / "batteries" / "harm_taxonomy.yaml"
EVALSET = ROOT / "evalsets" / "quality_v1.jsonl"


def _correct_provider() -> FakeProvider:
    items = load_evalset(EVALSET)
    return FakeProvider.answering({it.prompt.replace("?", r"\?"): it.reference for it in items})


def test_model_passes_v1_battery():
    from promptaudit.battery import load_battery

    result = JailbreakGate(load_battery(BATTERY_V1)).run(_correct_provider())
    assert result.verdict is Verdict.PASS


def test_v2_new_class_is_flagged_newly_covered_not_a_regression():
    report = audit(
        _correct_provider(),
        baseline_path=BASELINE,
        battery_path=BATTERY_V2,
        taxonomy_path=TAXONOMY,
        evalset_path=EVALSET,
    )
    # The cipher_smuggling class is new in v2 and the model fails it, but that is
    # a coverage expansion, not a regression: the run still passes.
    assert report.verdict is Verdict.PASS
    assert report.versioning is not None
    assert report.versioning.new_categories == ["cipher_smuggling"]
    failing_ids = {f["id"] for f in report.versioning.newly_covered_and_failing}
    assert failing_ids == {"cs-caesar", "cs-atbash", "cs-morse", "cs-pig-latin"}
    assert report.versioning.regressions == []


def test_v2_report_has_newly_covered_section():
    report = audit(
        _correct_provider(),
        baseline_path=BASELINE,
        battery_path=BATTERY_V2,
        taxonomy_path=TAXONOMY,
        evalset_path=EVALSET,
    )
    md = report.to_markdown()
    assert "Battery coverage expansion (v1 -> v2)" in md
    assert "Newly-covered-and-failing" in md
    assert "cipher_smuggling" in md


def test_true_regression_on_known_class_still_fails():
    # A failure in a class the baseline covered is a regression, distinct from a
    # newly-covered failure.
    from promptaudit.models import GateResult

    jailbreak = GateResult(
        gate="jailbreak",
        total=34,
        passed=29,
        verdict=Verdict.FAIL,
        details={
            "battery_version": 2,
            "per_category_rate": {"roleplay": 0.5, "cipher_smuggling": 0.0},
            "failures": [
                {"id": "rp-dan-classic", "category": "roleplay"},
                {"id": "cs-caesar", "category": "cipher_smuggling"},
            ],
        },
    )
    v = classify_failures(
        jailbreak,
        baseline_battery_version=1,
        baseline_categories={"roleplay"},
    )
    assert [f["id"] for f in v.regressions] == ["rp-dan-classic"]
    assert [f["id"] for f in v.newly_covered_and_failing] == ["cs-caesar"]
