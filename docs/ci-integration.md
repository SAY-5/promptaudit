# CI integration

PromptAudit is a pre-merge gate. A model repo calls the composite action on each
pull request; the action runs the gates, posts the report as a PR comment, and
sets the check status. A regression fails the check and blocks the merge.

## Composite action

`.github/actions/promptaudit-action/action.yml` exposes:

| Input | Default | Purpose |
| --- | --- | --- |
| provider | fake | provider name (fake for hermetic CI) |
| baseline | (required) | committed baseline JSON |
| battery | batteries/jailbreaks.yaml | jailbreak battery |
| taxonomy | batteries/harm_taxonomy.yaml | harm taxonomy |
| evalset | evalsets/quality_v1.jsonl | quality eval set |
| report-dir | reports | output directory |
| comment-on-pr | true | post the report as a PR comment |

Output `verdict` is `pass` or `fail`.

## Example workflow

```yaml
name: gate
on: [pull_request]
permissions:
  contents: read
  pull-requests: write
jobs:
  promptaudit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: ./.github/actions/promptaudit-action
        with:
          baseline: baselines/model_v1.json
```

## Hermetic guarantee

CI uses the FakeProvider exclusively and never calls a real LLM. The
`action-self-test` job in this repo runs the gate against the FakeProvider and
asserts a pass, so the action itself is covered.
