"""flameiq report — generate a static HTML comparison report."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from flameiq.core.comparator import compare_snapshots
from flameiq.providers.registry import get_provider
from flameiq.reporting.html_generator import generate_report
from flameiq.storage.baseline_store import BaselineStore


@click.command()
@click.option(
    "--metrics",
    "-m",
    required=True,
    type=click.Path(exists=True),
    help="Metrics file for the current run.",
)
@click.option("--provider", "-p", default="json", show_default=True, help="Metric provider.")
@click.option(
    "--output",
    "-o",
    default=".flameiq/report.html",
    show_default=True,
    help="Output path for the HTML report.",
)
@click.pass_context
def report(
    ctx: click.Context,
    metrics: str,
    provider: str,
    output: str,
) -> None:
    """Generate a self-contained HTML performance comparison report.

    \b
    Exit codes:
      0  Report generated.
      2  No baseline available.
      3  Metrics file error.
    """
    store = BaselineStore()
    try:
        baseline_snap = store.load_baseline()
    except Exception as exc:
        click.echo(click.style(f"Error: {exc}", fg="red"), err=True)
        sys.exit(2)

    try:
        current_snap = get_provider(provider).load(metrics)
    except Exception as exc:
        click.echo(click.style(f"Error: {exc}", fg="red"), err=True)
        sys.exit(3)

    result = compare_snapshots(baseline_snap, current_snap)
    out_path = Path(output)

    try:
        generate_report(result, baseline_snap, current_snap, out_path)
        click.echo(click.style("✓ Report generated: ", fg="green", bold=True) + str(out_path))
    except Exception as exc:
        click.echo(click.style(f"Error generating report: {exc}", fg="red"), err=True)
        sys.exit(2)
