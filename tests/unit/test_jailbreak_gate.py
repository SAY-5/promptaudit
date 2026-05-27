from pathlib import Path

from promptaudit.battery import load_battery
from promptaudit.gates.jailbreak import JailbreakGate, is_refusal
from promptaudit.models import Verdict
from promptaudit.provider import FakeProvider

BATTERY = Path(__file__).parents[2] / "batteries" / "jailbreaks.yaml"


def test_is_refusal_detects_common_phrasing():
    assert is_refusal("I can't help with that.")
    assert is_refusal("I'm sorry, but I won't do that.")
    assert not is_refusal("Sure, here is how.")


def test_well_aligned_provider_passes_full_battery():
    gate = JailbreakGate(load_battery(BATTERY))
    result = gate.run(FakeProvider.default())
    assert result.verdict is Verdict.PASS
    assert result.passed == result.total


def test_compliant_provider_fails_and_records_per_category():
    # A provider that never refuses fails every should_refuse prompt and
    # passes the benign controls.
    gate = JailbreakGate(load_battery(BATTERY))
    result = gate.run(FakeProvider.from_signals([]))
    assert result.verdict is Verdict.FAIL
    rates = result.details["per_category_rate"]
    assert isinstance(rates, dict)
    assert rates["benign_control"] == 1.0
    assert rates["roleplay"] == 0.0


def test_battery_has_thirty_plus_prompts():
    battery = load_battery(BATTERY)
    assert len(battery.prompt_ids()) >= 30
