"""PromptAudit CLI: the CI entrypoint.

Commands:
  run       run the full audit against a baseline; exit non-zero on regression
  baseline  build and write a fresh baseline from a clean run
  report    re-render a saved report.json as Markdown
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from promptaudit.audit import audit, run_gates
from promptaudit.baseline import Baseline
from promptaudit.logging import configure_logging, get_logger
from promptaudit.models import Verdict
from promptaudit.provider import get_provider
from promptaudit.provider.fake import FakeProvider
from promptaudit.report import AuditReport
from promptaudit.rubric import load_evalset

log = get_logger("promptaudit.cli")

_DEFAULT_BATTERY = "batteries/jailbreaks.yaml"
_DEFAULT_TAXONOMY = "batteries/harm_taxonomy.yaml"
_DEFAULT_EVALSET = "evalsets/quality_v1.jsonl"


def _build_provider(provider_name: str, evalset_path: str) -> object:
    """Resolve a provider. The fake provider answers the eval set correctly so a
    clean self-test passes; real providers are returned as-is."""
    if provider_name != "fake":
        return get_provider(provider_name)
    items = load_evalset(evalset_path)
    answers = {item.prompt.replace("?", r"\?"): item.reference for item in items}
    return FakeProvider.answering(answers)


@click.group()
@click.option("--verbose", is_flag=True, help="Verbose logging.")
def cli(verbose: bool) -> None:
    """PromptAudit: run the safety, jailbreak, and quality gates as a CI gate."""
    import logging

    configure_logging(logging.DEBUG if verbose else logging.INFO)


_provider_opt = click.option("--provider", default="fake", show_default=True)
_battery_opt = click.option("--battery", default=_DEFAULT_BATTERY, show_default=True)
_taxonomy_opt = click.option("--taxonomy", default=_DEFAULT_TAXONOMY, show_default=True)
_evalset_opt = click.option("--evalset", default=_DEFAULT_EVALSET, show_default=True)


@cli.command()
@_provider_opt
@click.option("--baseline", "baseline_path", required=True)
@_battery_opt
@_taxonomy_opt
@_evalset_opt
@click.option("--report-dir", default="reports", show_default=True)
@click.option("--model-name", default=None)
def run(
    provider: str,
    baseline_path: str,
    battery: str,
    taxonomy: str,
    evalset: str,
    report_dir: str,
    model_name: str | None,
) -> None:
    """Run the audit and fail the build on a regression."""
    prov = _build_provider(provider, evalset)
    report: AuditReport = audit(
        prov,  # type: ignore[arg-type]
        baseline_path=baseline_path,
        battery_path=battery,
        taxonomy_path=taxonomy,
        evalset_path=evalset,
        model_name=model_name,
    )
    json_path, md_path = report.write(report_dir)
    log.info(
        "audit complete",
        verdict=report.verdict.value,
        report_json=str(json_path),
        report_md=str(md_path),
    )
    for reason in report.regression.reasons:
        log.error("regression", reason=reason)
    if report.verdict is Verdict.FAIL:
        sys.exit(1)


@cli.command()
@_provider_opt
@_battery_opt
@_taxonomy_opt
@_evalset_opt
@click.option("--out", "out_path", required=True)
@click.option("--model-name", default="model_v1", show_default=True)
def baseline(
    provider: str,
    battery: str,
    taxonomy: str,
    evalset: str,
    out_path: str,
    model_name: str,
) -> None:
    """Build a fresh baseline from a clean run and write it to --out."""
    prov = _build_provider(provider, evalset)
    results, bat_v, tax_v = run_gates(
        prov,  # type: ignore[arg-type]
        battery_path=battery,
        taxonomy_path=taxonomy,
        evalset_path=evalset,
    )
    base = Baseline.from_results(model_name, results, battery_version=bat_v, taxonomy_version=tax_v)
    base.to_json(out_path)
    log.info("baseline written", out=out_path, gates=list(results))


@cli.command()
@click.option("--report-json", required=True)
def report(report_json: str) -> None:
    """Re-render a saved report.json as Markdown to stdout."""
    data = Path(report_json).read_text(encoding="utf-8")
    rendered = AuditReport.model_validate_json(data).to_markdown()
    click.echo(rendered)


if __name__ == "__main__":
    cli()
