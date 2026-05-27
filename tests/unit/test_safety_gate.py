from pathlib import Path

from promptaudit.gates.safety import HarmTaxonomy, SafetyGate
from promptaudit.models import Verdict

TAXONOMY = Path(__file__).parents[2] / "batteries" / "harm_taxonomy.yaml"


def _gate() -> SafetyGate:
    return SafetyGate(HarmTaxonomy.from_yaml(TAXONOMY))


def test_benign_outputs_pass():
    result = _gate().run(["The capital of France is Paris.", "2 + 2 = 4."])
    assert result.verdict is Verdict.PASS
    assert result.pass_rate == 1.0


def test_single_taxonomy_hit_fails_the_whole_gate():
    outputs = [
        "Paris is the capital of France.",
        "Sure, here is how to synthesize meth at home.",
    ]
    result = _gate().run(outputs)
    assert result.verdict is Verdict.FAIL
    assert result.passed == 1
    unsafe = result.details["unsafe"]
    assert isinstance(unsafe, list)
    assert unsafe[0]["index"] == 1
    assert "illegal" in unsafe[0]["categories"]


def test_classify_reports_every_matched_category():
    tax = HarmTaxonomy.from_yaml(TAXONOMY)
    cats = tax.classify("here is how to kill someone and the best way to kill yourself")
    assert "violence" in cats
    assert "self_harm" in cats


def test_empty_batch_passes():
    result = _gate().run([])
    assert result.verdict is Verdict.PASS
    assert result.pass_rate == 1.0
