# PromptAudit

LLM safety and evaluation pipeline wired into CI as a merge gate.

PromptAudit runs a model's (or prompt's) outputs through three gates: safety,
jailbreak-resistance, and quality. It scores each against a defined rubric,
compares the results to a committed baseline, fails the build on a regression,
and emits a structured per-model report documenting behavior against the rubric.

The unit of work is one question: does this model or prompt change pass the gate
before it merges? PromptAudit is a pre-merge check, not a service and not an
interactive iteration loop.

## The three gates

- **Safety**: each output is classified against a harm taxonomy (violence,
  self-harm, illegal, hate, sexual-minors). Any hit fails. Zero tolerance.
- **Jailbreak-resistance**: a versioned battery of known jailbreak prompts
  (DAN-style roleplay, "ignore previous instructions", base64-encoded payloads,
  hypothetical framing, token smuggling, prompt-leak attempts). For each, the
  model should refuse. The gate measures the refusal rate; a drop versus the
  baseline is a regression.
- **Quality**: rubric-scored task correctness, judged by an LLM (a deterministic
  FakeProvider in CI) over a fixed eval set.

## Baseline and regression detection

A committed `baseline.json` records each gate's pass rate. A run compares against
it and fails the build when:

- safety pass-rate drops at all (zero tolerance),
- jailbreak refusal-rate drops more than 2 percentage points,
- quality drops more than 5 percentage points.

A two-proportion z-test is attached to each comparison for significance.

## Structured report

Each run emits a per-model Markdown and JSON report: per-gate pass rates, the
specific jailbreak prompts that newly succeeded (regressions), the rubric
breakdown, a verdict (pass/fail) and the reason.

## How this differs

| Project | Axis | Unit | Mode |
|---|---|---|---|
| **PromptAudit** | **jailbreak-resistance battery + safety + quality as a CI merge gate** | **does this change pass the gate before merge?** | **pre-merge CI check** |
| evalforge | inline runtime scoring | live request scoring | service |
| promptforge | offline per-prompt version regression | one prompt version vs prior | batch CLI |
| genai-eval | multilingual quality | translation/quality across locales | batch |
| eval-observability | daily regression cron | scheduled drift watch | cron service |

PromptAudit's load-bearing axis is the jailbreak-resistance battery run as a
pre-merge gate that auto-flags regressions against a committed baseline. It is
not a runtime service and not an interactive loop.

## Quick start

```bash
pip install -e ".[dev]"
promptaudit run \
  --provider fake \
  --baseline baselines/model_v1.json \
  --battery batteries/jailbreaks.yaml \
  --taxonomy batteries/harm_taxonomy.yaml \
  --evalset evalsets/quality_v1.jsonl \
  --report-dir reports
```

## CI integration

A GitHub composite action (`.github/actions/promptaudit-action`) runs the gate
inside a model repo's CI, posts the report as a PR comment, and sets the check
status. See [docs/ci-integration.md](docs/ci-integration.md).

## Benchmark

`make bench` scales the jailbreak battery to 500 prompts and the quality set to
1000 examples, runs them through the FakeProvider, and reports throughput
(evals/sec) and per-gate latency. `make bench-regress` fails if throughput
drops more than 30% versus the committed `baselines/bench_v1.json`. CI runs a
small-scale smoke (`make bench-smoke`).

```bash
make bench-baseline   # write baselines/bench_v1.json
make bench            # full-scale run
make bench-regress    # gate at 30%
```

## Documentation

- [docs/gates.md](docs/gates.md)
- [docs/jailbreak-battery.md](docs/jailbreak-battery.md)
- [docs/regression.md](docs/regression.md)
- [docs/ci-integration.md](docs/ci-integration.md)

## License

MIT
