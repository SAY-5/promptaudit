# Trend tracking

The per-run gate catches cliffs: a sharp refusal-rate drop versus the baseline.
It cannot catch slow drift, where each individual run stays within the per-run
tolerance but the rate erodes over many runs. Trend tracking closes that gap.

## History

Pass `--history history.jsonl` to `promptaudit run` and each run appends its
per-category pass rates:

```json
{"timestamp": "2026-05-20T00:00:00+00:00", "rates": {"jailbreak.roleplay": 0.99, "safety": 1.0, "quality": 1.0}}
```

Keys are gate-level (`safety`, `jailbreak`, `quality`) plus per-category
jailbreak entries namespaced `jailbreak.<category>`.

## Trend command

```bash
promptaudit trend --history history.jsonl --category jailbreak.roleplay --last-n 10
```

It reads the last N entries for the category, fits a least-squares slope over
evenly-spaced runs, and classifies the trend as improving, flat, or degrading.

## Slow-regression

A `slow-regression` is flagged when the slope is degrading and the cumulative
first-to-last drop over the window exceeds the per-run jailbreak tolerance
(2pp), while no single step did. This is the drift the gate alone misses. The
command exits 2 on a slow-regression so it can gate a scheduled job.

### Worked example

Six runs with refusal rate 100, 99, 98, 97, 96, 95 percent. Each step is a 1pp
drop, within the 2pp per-run gate, so every individual run passes. The trend
fits a slope of -0.01 per run and flags `slow-regression`, since the cumulative
5pp drift is a sustained degradation.

```
category: jailbreak.roleplay
runs: 6
slope: -0.01000 per run (degrading)
slow-regression: yes (sustained drift below the per-run gate)
```
