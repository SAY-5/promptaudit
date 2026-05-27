from pathlib import Path

from promptaudit.gates.quality import (
    QualityGate,
    build_judge_prompt,
    parse_judgment,
    reference_containment_judge,
)
from promptaudit.models import Verdict
from promptaudit.provider import FakeProvider
from promptaudit.rubric import load_evalset
from promptaudit.rubric.loader import EvalItem

EVALSET = Path(__file__).parents[2] / "evalsets" / "quality_v1.jsonl"


def _correct_provider(items: list[EvalItem]) -> FakeProvider:
    answers = {item.prompt.replace("?", r"\?"): item.reference for item in items}
    return FakeProvider.answering(answers)


def test_parse_judgment():
    assert parse_judgment("PASS\nlooks good")
    assert not parse_judgment("FAIL: missing reference")


def test_reference_containment_numeric_match():
    item = EvalItem(id="x", prompt="speed?", reference="300000")
    assert reference_containment_judge(item, "about 300,000 km/s")
    assert not reference_containment_judge(item, "very fast")


def test_correct_model_passes_quality_gate():
    items = load_evalset(EVALSET)
    gate = QualityGate(items)
    result = gate.run(_correct_provider(items))
    assert result.verdict is Verdict.PASS
    assert result.passed == result.total


def test_wrong_model_fails_quality_gate():
    items = load_evalset(EVALSET)
    gate = QualityGate(items, threshold=0.9)
    # The safe default provider answers everything with "The answer is 4.",
    # which satisfies only the arithmetic item.
    result = gate.run(FakeProvider.default())
    assert result.verdict is Verdict.FAIL
    assert result.passed < result.total


def test_llm_judge_wiring_with_fake_provider():
    items = load_evalset(EVALSET)[:2]
    judge_provider = FakeProvider.from_signals([])  # answers "The answer is 4."
    # Force the judge to always say PASS via an explicit answer rule.
    judge_provider = FakeProvider.answering({r"grading judge": "PASS"})
    gate = QualityGate.with_llm_judge(items, judge_provider)
    result = gate.run(_correct_provider(items))
    assert result.verdict is Verdict.PASS
    assert build_judge_prompt(items[0], "x").startswith("You are a grading judge")
