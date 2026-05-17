"""Command-line entry point for QuantSpec."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import typer

from quant_spec import __version__
from quant_spec.ai.client import LLMMode, LLMModeError
from quant_spec.ai.spec_generator import SpecValidationError
from quant_spec.io.storage import ArtifactStorage
from quant_spec.models.decision import DecisionStatus
from quant_spec.pipeline.runner import (
    BriefValidationError,
    MissingArtifactError,
    load_persisted_brief,
    run_pipeline,
    stage_backtest,
    stage_decision,
    stage_gates,
    stage_report,
    stage_spec,
)

app = typer.Typer(
    no_args_is_help=True,
    help="QuantSpec command-line interface.",
)


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
) -> None:
    """Show package metadata and top-level CLI help."""
    if version:
        typer.echo(f"quant-spec {__version__}")
        raise typer.Exit()


@app.command(name="init")
def init_command(hypothesis_id: str) -> None:
    """Create a demo brief template in the hypotheses directory."""

    storage = ArtifactStorage()
    brief_path = storage.artifact_path(hypothesis_id, "brief.yaml")
    storage.ensure_layout(hypothesis_id)
    if brief_path.exists():
        _fail(f"brief already exists: {brief_path}", 74)
    content = f"""id: {hypothesis_id}
created_at: '2020-01-01T00:00:00Z'
author: operator
market:
  symbol: DEMO_INTRADAY
  asset_class: demo
  pip_size: 0.01
timeframe: DEMO_M15
central_hypothesis: Synthetic intraday demo hypothesis.
risk_constraints:
  max_daily_risk_pct: 5.0
  risk_per_trade_pct: 0.5
  max_trades_per_day: 1
  must_have_stop_loss: true
  intraday_only: true
periods:
  insample:
    start: 2020-01-01
    end: 2020-12-31
  outsample:
    start: 2021-01-01
    end: 2021-12-31
data:
  source: fixture
  path: quant_spec/data/fixtures/{hypothesis_id}/trades.csv
notes: Synthetic data only. Not a trading recommendation.
"""
    brief_path.write_text(content, encoding="utf-8", newline="\n")
    typer.echo(str(brief_path))


@app.command()
def validate(target: str) -> None:
    """Validate a brief path or persisted hypothesis id."""

    storage = ArtifactStorage()
    try:
        brief = load_persisted_brief(target, storage)
    except BriefValidationError as exc:
        _fail(str(exc), 64)
    typer.echo(f"valid: {brief.id}")


@app.command()
def spec(
    target: str,
    llm_mode: str = typer.Option("fixture", "--llm-mode"),
) -> None:
    """Generate spec.md for a brief path or persisted hypothesis id."""

    storage = ArtifactStorage()
    try:
        brief = load_persisted_brief(target, storage)
        path = stage_spec(brief, storage, _llm_mode(llm_mode))
    except BriefValidationError as exc:
        _fail(str(exc), 64)
    except SpecValidationError as exc:
        _fail(str(exc), 65)
    except (OSError, MissingArtifactError) as exc:
        _fail(str(exc), 74)
    except LLMModeError as exc:
        _fail(str(exc), 1)
    typer.echo(str(path))


@app.command()
def backtest(target: str) -> None:
    """Run deterministic evaluation for a persisted hypothesis."""

    storage = ArtifactStorage()
    try:
        brief = load_persisted_brief(target, storage)
        result = stage_backtest(brief, storage)
    except BriefValidationError as exc:
        _fail(str(exc), 64)
    except (OSError, MissingArtifactError) as exc:
        _fail(str(exc), 74)
    results_path = storage.artifact_path(result.hypothesis_id, "results.json")
    typer.echo(f"results: {results_path}")


@app.command()
def gates(target: str) -> None:
    """Evaluate quality gates for a persisted hypothesis."""

    storage = ArtifactStorage()
    try:
        brief = load_persisted_brief(target, storage)
        result_payload = storage.read_json(brief.id, "results.json")
        from quant_spec.models.results import BacktestResult

        report = stage_gates(BacktestResult.model_validate(result_payload), storage)
    except BriefValidationError as exc:
        _fail(str(exc), 64)
    except (OSError, MissingArtifactError) as exc:
        _fail(str(exc), 74)
    typer.echo(f"gates: {storage.artifact_path(report.hypothesis_id, 'gates.json')}")
    if report.summary == "FAIL":
        raise typer.Exit(2)


@app.command()
def report(
    target: str,
    llm_mode: str = typer.Option("fixture", "--llm-mode"),
) -> None:
    """Generate report.md for a persisted hypothesis."""

    storage = ArtifactStorage()
    try:
        brief = load_persisted_brief(target, storage)
        path = stage_report(brief, storage, _llm_mode(llm_mode))
    except BriefValidationError as exc:
        _fail(str(exc), 64)
    except (OSError, MissingArtifactError) as exc:
        _fail(str(exc), 74)
    except LLMModeError as exc:
        _fail(str(exc), 1)
    typer.echo(str(path))


@app.command()
def decision(target: str) -> None:
    """Generate decision.md for a persisted hypothesis."""

    storage = ArtifactStorage()
    try:
        brief = load_persisted_brief(target, storage)
        record = stage_decision(brief.id, storage)
    except BriefValidationError as exc:
        _fail(str(exc), 64)
    except (OSError, MissingArtifactError) as exc:
        _fail(str(exc), 74)
    typer.echo(str(storage.artifact_path(record.hypothesis_id, "decision.md")))
    if record.status == DecisionStatus.CLOSED_BY_GATE:
        raise typer.Exit(2)


@app.command()
def run(
    brief_path: Path,
    llm_mode: str = typer.Option("fixture", "--llm-mode"),
) -> None:
    """Run the complete offline pipeline for a brief YAML file."""

    try:
        result = run_pipeline(brief_path, _llm_mode(llm_mode))
    except BriefValidationError as exc:
        _fail(str(exc), 64)
    except SpecValidationError as exc:
        _fail(str(exc), 65)
    except (OSError, MissingArtifactError) as exc:
        _fail(str(exc), 74)
    except LLMModeError as exc:
        _fail(str(exc), 1)
    typer.echo(f"decision: {result.artifacts['decision']}")
    typer.echo(f"status: {result.decision.status.value}")
    if result.decision.status == DecisionStatus.CLOSED_BY_GATE:
        raise typer.Exit(2)


def _llm_mode(value: str) -> LLMMode:
    if value not in {"fixture", "live"}:
        _fail("--llm-mode must be fixture or live", 1)
    return cast(LLMMode, value)


def _fail(message: str, code: int) -> None:
    typer.secho(message, err=True, fg=typer.colors.RED)
    raise typer.Exit(code)
