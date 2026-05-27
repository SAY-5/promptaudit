from promptaudit.models import Verdict
from promptaudit.regression import evaluate, evaluate_gate, two_proportion_z


def test_safety_zero_tolerance_any_drop_regresses():
    r = evaluate_gate("safety", baseline_rate=1.0, baseline_n=8, current_rate=0.875, current_n=8)
    assert r.regressed is True


def test_jailbreak_small_drop_within_threshold_ok():
    # 1pp drop is within the 2pp allowance.
    r = evaluate_gate(
        "jailbreak", baseline_rate=1.0, baseline_n=100, current_rate=0.99, current_n=100
    )
    assert r.regressed is False


def test_jailbreak_drop_beyond_threshold_regresses():
    r = evaluate_gate(
        "jailbreak", baseline_rate=1.0, baseline_n=100, current_rate=0.95, current_n=100
    )
    assert r.regressed is True


def test_quality_drop_within_five_pp_ok():
    r = evaluate_gate(
        "quality", baseline_rate=1.0, baseline_n=100, current_rate=0.96, current_n=100
    )
    assert r.regressed is False


def test_improvement_never_regresses():
    r = evaluate_gate("jailbreak", baseline_rate=0.9, baseline_n=50, current_rate=1.0, current_n=50)
    assert r.regressed is False
    assert r.delta_pp > 0


def test_evaluate_rolls_up_to_fail_with_reason():
    gates = [
        evaluate_gate("safety", baseline_rate=1.0, baseline_n=8, current_rate=0.9, current_n=8),
        evaluate_gate(
            "jailbreak", baseline_rate=1.0, baseline_n=30, current_rate=1.0, current_n=30
        ),
    ]
    report = evaluate(gates)
    assert report.verdict is Verdict.FAIL
    assert any("safety" in reason for reason in report.reasons)


def test_z_stat_degenerate_inputs_return_zero():
    assert two_proportion_z(1.0, 0, 1.0, 10) == 0.0
    assert two_proportion_z(0.0, 10, 0.0, 10) == 0.0
