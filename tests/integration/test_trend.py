"""Per-category trend tracking: slow-regression detection across runs."""

from __future__ import annotations

from promptaudit.regression import THRESHOLDS
from promptaudit.trend import analyze, least_squares_slope, record_run


def test_least_squares_slope_matches_known_line():
    # y = 1 - 0.01 x over six points -> slope -0.01.
    values = [1.0 - 0.01 * i for i in range(6)]
    assert abs(least_squares_slope(values) - (-0.01)) < 1e-9


def test_slow_regression_flagged_when_each_step_passes_per_run_gate(tmp_path):
    history = tmp_path / "history.jsonl"
    # Six runs, refusal rate drifts down 1pp per run. Each step (1pp) is within
    # the per-run jailbreak gate (2pp), but the cumulative drift is 5pp.
    rates = [1.00, 0.99, 0.98, 0.97, 0.96, 0.95]
    per_run_gate = THRESHOLDS["jailbreak"]
    for i, r in enumerate(rates):
        # No single step trips the gate.
        if i > 0:
            assert (rates[i - 1] - r) <= per_run_gate
        record_run(history, {"jailbreak.roleplay": r}, ts=f"2026-05-2{i}T00:00:00+00:00")

    analysis = analyze(history, "jailbreak.roleplay", last_n=10)
    assert analysis.n == 6
    assert analysis.classification == "degrading"
    assert abs(analysis.slope - (-0.01)) < 1e-6
    assert analysis.slow_regression is True


def test_flat_history_is_not_slow_regression(tmp_path):
    history = tmp_path / "history.jsonl"
    for i in range(6):
        record_run(history, {"jailbreak.roleplay": 1.0}, ts=f"2026-05-2{i}T00:00:00+00:00")
    analysis = analyze(history, "jailbreak.roleplay")
    assert analysis.classification == "flat"
    assert analysis.slow_regression is False


def test_single_noisy_dip_is_not_slow_regression(tmp_path):
    history = tmp_path / "history.jsonl"
    # One dip then recovery: overall slope is not a sustained drift.
    rates = [1.0, 1.0, 0.98, 1.0, 1.0, 1.0]
    for i, r in enumerate(rates):
        record_run(history, {"jailbreak.roleplay": r}, ts=f"2026-05-2{i}T00:00:00+00:00")
    analysis = analyze(history, "jailbreak.roleplay")
    assert analysis.slow_regression is False


def test_missing_category_returns_empty(tmp_path):
    history = tmp_path / "history.jsonl"
    record_run(history, {"jailbreak.roleplay": 1.0})
    analysis = analyze(history, "jailbreak.encoding")
    assert analysis.n == 0
    assert analysis.slope == 0.0
