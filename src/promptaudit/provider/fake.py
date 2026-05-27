"""A deterministic, scripted provider for hermetic CI.

The FakeProvider never calls a network. Its behavior is fully determined by a
script: a list of rules matched against the prompt. Each rule yields either a
refusal or a compliance, with optional canned text. This lets tests and CI
exercise the full gate pipeline with reproducible outputs.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from promptaudit.provider.base import ProviderResponse

REFUSAL_TEXT = (
    "I can't help with that. I won't provide instructions or content that could "
    "cause harm. If you are in distress, please reach out to a professional."
)


@dataclass(frozen=True)
class ScriptRule:
    """Match a prompt by regex (case-insensitive) and decide the response."""

    pattern: str
    refuse: bool
    text: str | None = None

    def matches(self, prompt: str) -> bool:
        return re.search(self.pattern, prompt, re.IGNORECASE) is not None


# Substrings that signal a jailbreak attempt or harmful request. The default
# FakeProvider refuses any prompt containing one of these.
_DEFAULT_REFUSAL_SIGNALS: tuple[str, ...] = (
    r"ignore (all |the )?previous instructions",
    r"\bDAN\b",
    r"do anything now",
    r"developer mode",
    r"jailbreak",
    r"pretend you (are|have) no (rules|restrictions|guidelines)",
    r"hypothetically",
    r"for (a|my) (novel|story|screenplay).*(weapon|bomb|drug|hack)",
    r"base64",
    r"decode the following",
    r"reveal your (system )?prompt",
    r"repeat the (words|text) above",
    r"how (to|do i) (make|build|synthesize).*(bomb|explosive|meth|nerve agent)",
    r"how (to|do i) (kill|hurt|harm)",
    r"step.?by.?step.*(weapon|malware|ransomware|exploit)",
    r"write (me )?(malware|ransomware|a keylogger|a virus)",
    r"unfiltered",
    r"no (ethical|moral) (guidelines|constraints)",
    r"token.?smuggl",
    r"r0t13|rot13",
    r"napalm",
    r"new rule.*(comply|must)",
    r"forget your rules",
    r"print your (full )?(system )?prompt",
    r"hidden instructions",
    r"m\W?e\W?t\W?h\b",
    r"b\W?o\W?m\W?b\b",
    r"sudo (mode|root)",
    r"safety team approved",
    r"evil twin",
    r"b0mb",
    r"keylogger",
)


@dataclass
class FakeProvider:
    """Scripted provider. Rules are checked in order; first match wins."""

    name: str = "fake"
    model: str = "fake-v1"
    rules: list[ScriptRule] = field(default_factory=list)
    default_refuse: bool = False
    default_text: str = "The answer is 4."

    @classmethod
    def default(cls) -> FakeProvider:
        """A provider that refuses jailbreak/harm signals and complies otherwise."""
        rules = [ScriptRule(pattern=sig, refuse=True) for sig in _DEFAULT_REFUSAL_SIGNALS]
        return cls(rules=rules)

    @classmethod
    def answering(
        cls, answers: dict[str, str], *, fallback: FakeProvider | None = None
    ) -> FakeProvider:
        """A provider that returns a canned answer for prompts matching a regex.

        `answers` maps a regex (matched against the prompt) to the answer text.
        Refusal/jailbreak rules from `fallback` (default: the safe default
        provider) are checked first, so a harmful prompt is still refused.
        """
        base = fallback if fallback is not None else cls.default()
        rules = list(base.rules)
        rules += [ScriptRule(pattern=pat, refuse=False, text=ans) for pat, ans in answers.items()]
        return cls(rules=rules, default_text=base.default_text)

    @classmethod
    def from_signals(cls, signals: Iterable[str], *, default_refuse: bool = False) -> FakeProvider:
        """Build a provider that refuses any prompt matching a custom signal."""
        rules = [ScriptRule(pattern=s, refuse=True) for s in signals]
        return cls(rules=rules, default_refuse=default_refuse)

    def complete(self, prompt: str) -> ProviderResponse:
        for rule in self.rules:
            if rule.matches(prompt):
                text = (
                    rule.text
                    if rule.text is not None
                    else (REFUSAL_TEXT if rule.refuse else self.default_text)
                )
                return ProviderResponse(text=text, model=self.model, refused=rule.refuse)
        text = REFUSAL_TEXT if self.default_refuse else self.default_text
        return ProviderResponse(text=text, model=self.model, refused=self.default_refuse)
