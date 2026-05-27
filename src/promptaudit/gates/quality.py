"""Quality gate: rubric-scored task correctness via an LLM judge.

The model under test answers each eval prompt; a judge then scores the answer
against the reference and rubric. In CI the judge is a deterministic
FakeProvider: it emits "PASS" when the reference is satisfied and "FAIL"
otherwise, so the whole pipeline runs without a network.

The judge contract: given a judge prompt, the provider returns a completion
whose text begins with PASS or FAIL. `parse_judgment` extracts the verdict.
"""

from __future__ import annotations

from collections.abc import Callable

from promptaudit.models import GateResult, Verdict
from promptaudit.provider.base import Provider
from promptaudit.rubric.loader import EvalItem

JudgeFn = Callable[[EvalItem, str], bool]


def build_judge_prompt(item: EvalItem, answer: str) -> str:
    """Construct the prompt sent to the judge provider."""
    return (
        "You are a grading judge. Decide if the ANSWER satisfies the RUBRIC for "
        "the given QUESTION, using REFERENCE as the gold answer. Reply with PASS "
        "or FAIL on the first line.\n"
        f"QUESTION: {item.prompt}\n"
        f"REFERENCE: {item.reference}\n"
        f"RUBRIC: {item.rubric}\n"
        f"ANSWER: {answer}\n"
    )


def parse_judgment(text: str) -> bool:
    """True if the judge said PASS."""
    return text.strip().upper().startswith("PASS")


def reference_containment_judge(item: EvalItem, answer: str) -> bool:
    """A deterministic judge: the reference must appear in the answer.

    Used as the default hermetic judge. Numeric references match on digits only
    so that "300000" matches "about 300,000 km/s".
    """
    ref = item.reference.strip().lower()
    ans = answer.strip().lower()
    if ref.replace(",", "").isdigit():
        digits_ans = "".join(c for c in ans if c.isdigit())
        return ref in digits_ans
    return ref in ans


class QualityGate:
    """Scores model answers against a rubric eval set."""

    name = "quality"

    def __init__(
        self,
        evalset: list[EvalItem],
        *,
        threshold: float = 1.0,
        judge: JudgeFn = reference_containment_judge,
    ) -> None:
        self.evalset = evalset
        self.threshold = threshold
        self.judge = judge

    @classmethod
    def with_llm_judge(
        cls, evalset: list[EvalItem], judge_provider: Provider, *, threshold: float = 1.0
    ) -> QualityGate:
        """Build a gate whose judge is an LLM provider (FakeProvider in CI)."""

        def judge(item: EvalItem, answer: str) -> bool:
            resp = judge_provider.complete(build_judge_prompt(item, answer))
            return parse_judgment(resp.text)

        return cls(evalset, threshold=threshold, judge=judge)

    def run(self, provider: Provider) -> GateResult:
        breakdown: list[dict[str, object]] = []
        passed = 0
        for item in self.evalset:
            answer = provider.complete(item.prompt).text
            ok = self.judge(item, answer)
            if ok:
                passed += 1
            breakdown.append({"id": item.id, "passed": ok})
        total = len(self.evalset)
        rate = 1.0 if total == 0 else passed / total
        verdict = Verdict.PASS if rate >= self.threshold else Verdict.FAIL
        return GateResult(
            gate=self.name,
            total=total,
            passed=passed,
            verdict=verdict,
            details={"threshold": self.threshold, "breakdown": breakdown},
        )
