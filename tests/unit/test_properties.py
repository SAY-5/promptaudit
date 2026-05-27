"""Property-based tests for the regression detector and gate invariants."""

from __future__ import annotations

import math

from hypothesis import given
from hypothesis import strategies as st

from promptaudit.gates.jailbreak import JailbreakGate
from promptaudit.gates.safety import HarmCategory, HarmTaxonomy, SafetyGate
from promptaudit.models import Verdict
from promptaudit.provider.fake import FakeProvider
from promptaudit.regression import THRESHOLDS, evaluate_gate, two_proportion_z


def _scipy_z(x1: int, n1: int, x2: int, n2: int) -> float:
    p1, p2 = x1 / n1, x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0
    return (p1 - p2) / se


@given(
    x1=st.integers(min_value=1, max_value=499),
    n1=st.integers(min_value=500, max_value=1000),
    x2=st.integers(min_value=1, max_value=499),
    n2=st.integers(min_value=500, max_value=1000),
)
def test_ztest_agrees_with_scipy(x1: int, n1: int, x2: int, n2: int) -> None:
    ours = two_proportion_z(x1 / n1, n1, x2 / n2, n2)
    theirs = _scipy_z(x1, n1, x2, n2)
    assert abs(ours - theirs) < 1e-4


@given(
    baseline=st.floats(min_value=0.0, max_value=1.0),
    current=st.floats(min_value=0.0, max_value=1.0),
)
def test_safety_zero_tolerance_flags_any_drop(baseline: float, current: float) -> None:
    r = evaluate_gate(
        "safety", baseline_rate=baseline, baseline_n=50, current_rate=current, current_n=50
    )
    assert r.regressed is (current < baseline)


@given(
    baseline=st.floats(min_value=0.0, max_value=1.0),
    current=st.floats(min_value=0.0, max_value=1.0),
)
def test_jailbreak_threshold_boundary(baseline: float, current: float) -> None:
    r = evaluate_gate(
        "jailbreak", baseline_rate=baseline, baseline_n=100, current_rate=current, current_n=100
    )
    expected = (current - baseline) < -THRESHOLDS["jailbreak"]
    assert r.regressed is expected


@given(refusals=st.lists(st.booleans(), min_size=1, max_size=40))
def test_jailbreak_refusal_rate_is_counted_correctly(refusals: list[bool]) -> None:
    # Build a battery whose i-th prompt should be refused, and a provider that
    # refuses exactly the prompts we mark. The gate's pass count must equal the
    # number of correctly-handled prompts.
    from promptaudit.battery.loader import Battery, BatteryCategory, JailbreakPrompt

    prompts = [
        JailbreakPrompt(id=f"p{i}", text=f"attack number {i}", should_refuse=True)
        for i in range(len(refusals))
    ]
    battery = Battery(version=1, categories=[BatteryCategory(id="c", prompts=prompts)])
    refuse_signals = [f"attack number {i}\\b" for i, r in enumerate(refusals) if r]
    provider = FakeProvider.from_signals(refuse_signals)
    result = JailbreakGate(battery).run(provider)
    assert result.passed == sum(refusals)
    assert math.isclose(result.pass_rate, sum(refusals) / len(refusals))


@given(
    outputs=st.lists(st.text(max_size=40), max_size=20),
    inject=st.booleans(),
)
def test_safety_any_taxonomy_hit_fails(outputs: list[str], inject: bool) -> None:
    tax = HarmTaxonomy(
        version=1,
        categories=[HarmCategory(id="test", signals=[r"FORBIDDEN_TOKEN"])],
    )
    batch = list(outputs)
    if inject:
        batch.append("this contains FORBIDDEN_TOKEN here")
    result = SafetyGate(tax).run(batch)
    has_hit = any("FORBIDDEN_TOKEN" in o for o in batch)
    assert (result.verdict is Verdict.FAIL) is has_hit
