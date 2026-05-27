from pathlib import Path

from promptaudit.baseline import Baseline
from promptaudit.models import GateResult, Verdict
from promptaudit.report import AuditReport, find_newly_succeeded

BASELINE = Path(__file__).parents[2] / "baselines" / "model_v1.json"


def _result(gate: str, passed: int, total: int, details=None) -> GateResult:
    return GateResult(
        gate=gate,
        passed=passed,
        total=total,
        verdict=Verdict.PASS if passed == total else Verdict.FAIL,
        details=details or {},
    )


def test_committed_baseline_loads():
    b = Baseline.from_json(BASELINE)
    assert b.model == "model_v1"
    assert set(b.gates) == {"safety", "jailbreak", "quality"}


def test_baseline_compare_clean_run_passes():
    b = Baseline.from_json(BASELINE)
    results = {
        "safety": _result("safety", 8, 8),
        "jailbreak": _result("jailbreak", 30, 30),
        "quality": _result("quality", 8, 8),
    }
    report = b.compare(results)
    assert report.verdict is Verdict.PASS


def test_baseline_compare_jailbreak_regression_fails():
    b = Baseline.from_json(BASELINE)
    results = {
        "safety": _result("safety", 8, 8),
        "jailbreak": _result("jailbreak", 27, 30),  # 90%, a 10pp drop
        "quality": _result("quality", 8, 8),
    }
    report = b.compare(results)
    assert report.verdict is Verdict.FAIL


def test_roundtrip_baseline(tmp_path):
    b = Baseline.from_json(BASELINE)
    out = tmp_path / "b.json"
    b.to_json(out)
    assert Baseline.from_json(out) == b


def test_find_newly_succeeded():
    current = _result(
        "jailbreak",
        28,
        30,
        details={"failures": [{"id": "new-1", "category": "roleplay"}, {"id": "old-1"}]},
    )
    new = find_newly_succeeded(current, baseline_failures={"old-1"})
    assert len(new) == 1
    assert new[0]["id"] == "new-1"


def test_report_markdown_renders_verdict_and_tables():
    b = Baseline.from_json(BASELINE)
    results = {
        "safety": _result("safety", 8, 8),
        "jailbreak": _result("jailbreak", 30, 30, details={"failures": []}),
        "quality": _result("quality", 8, 8, details={"breakdown": [{"id": "q1", "passed": True}]}),
    }
    reg = b.compare(results)
    report = AuditReport(model="model_v1", verdict=reg.verdict, gates=results, regression=reg)
    md = report.to_markdown()
    assert "PromptAudit report: model_v1" in md
    assert "Verdict: PASS" in md
    assert "Per-gate pass rates" in md
