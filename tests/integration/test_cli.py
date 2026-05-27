from pathlib import Path

from click.testing import CliRunner

from promptaudit.cli import cli

ROOT = Path(__file__).parents[2]
BASELINE = ROOT / "baselines" / "model_v1.json"


def _run(args, cwd):
    runner = CliRunner()
    return runner.invoke(cli, args, catch_exceptions=False)


def test_run_clean_audit_exits_zero(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    result = _run(
        ["run", "--provider", "fake", "--baseline", str(BASELINE), "--report-dir", str(tmp_path)],
        ROOT,
    )
    assert result.exit_code == 0
    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "report.md").exists()


def test_audit_fails_when_model_stops_refusing(tmp_path):
    # A never-refusing model audited against the committed baseline must fail the
    # jailbreak gate (refusal rate collapses from 100%).
    from promptaudit.audit import audit
    from promptaudit.models import Verdict
    from promptaudit.provider import FakeProvider

    report = audit(
        FakeProvider.from_signals([]),  # never refuses
        baseline_path=BASELINE,
        battery_path=ROOT / "batteries" / "jailbreaks.yaml",
        taxonomy_path=ROOT / "batteries" / "harm_taxonomy.yaml",
        evalset_path=ROOT / "evalsets" / "quality_v1.jsonl",
    )
    assert report.verdict is Verdict.FAIL
    assert any("jailbreak" in r for r in report.regression.reasons)


def test_baseline_then_report_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    out = tmp_path / "b.json"
    r1 = _run(["baseline", "--provider", "fake", "--out", str(out)], ROOT)
    assert r1.exit_code == 0
    assert out.exists()

    rdir = tmp_path / "rep"
    _run(["run", "--provider", "fake", "--baseline", str(out), "--report-dir", str(rdir)], ROOT)
    r2 = _run(["report", "--report-json", str(rdir / "report.json")], ROOT)
    assert r2.exit_code == 0
    assert "PromptAudit report" in r2.output
