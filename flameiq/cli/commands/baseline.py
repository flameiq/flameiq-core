"""flameiq baseline — manage baseline snapshots."""

from __future__ import annotations

import sys

import click

from flameiq.providers.registry import get_provider
from flameiq.storage.baseline_store import BaselineStore


@click.group()
def baseline() -> None:
    """Manage FlameIQ baseline snapshots."""


@baseline.command("set")
@click.option(
    "--metrics",
    "-m",
    required=True,
    type=click.Path(exists=True),
    help="Metrics file to set as the new baseline.",
)
@click.option("--provider", "-p", default="json", show_default=True, help="Metric provider.")
@click.option("--tag", default=None, help="Tag this baseline (e.g. 'v1.0.0').")
@click.pass_context
def baseline_set(ctx: click.Context, metrics: str, provider: str, tag: str | None) -> None:
    r"""Set a new baseline from a metrics file.

    \b
    Exit codes:
      0  Baseline set successfully.
      3  Metrics file error.
    """
    try:
        snapshot = get_provider(provider).load(metrics)
    except Exception as exc:
        click.echo(click.style(f"Error: {exc}", fg="red"), err=True)
        sys.exit(3)

    if tag:
        snapshot.metadata.tags["release"] = tag

    store = BaselineStore()
    store.save_baseline(snapshot)

    flat = snapshot.metrics.flat()
    click.echo(click.style("✓ Baseline set", fg="green", bold=True))
    click.echo(f"  Commit:  {snapshot.metadata.commit or '(none)'}")
    click.echo(f"  Branch:  {snapshot.metadata.branch or '(none)'}")
    if tag:
        click.echo(f"  Tag:     {tag}")
    click.echo(f"  Metrics: {len(flat)} value(s) stored")


@baseline.command("show")
def baseline_show() -> None:
    """Display the current baseline snapshot."""
    store = BaselineStore()
    try:
        snap = store.load_baseline()
    except Exception as exc:
        click.echo(click.style(f"Error: {exc}", fg="red"), err=True)
        sys.exit(2)

    click.echo(click.style("\nCurrent Baseline", bold=True))
    click.echo(f"  Commit:      {snap.metadata.commit or '—'}")
    click.echo(f"  Branch:      {snap.metadata.branch or '—'}")
    click.echo(f"  Environment: {snap.metadata.environment.value}")
    click.echo(f"  Timestamp:   {snap.metadata.timestamp.isoformat()}")
    click.echo(f"  Run ID:      {snap.metadata.run_id}")
    if snap.metadata.tags:
        click.echo(f"  Tags:        {snap.metadata.tags}")
    click.echo("")
    click.echo("  Metrics:")
    for k, v in snap.metrics.flat().items():
        click.echo(f"    {k:<24} {v:.4f}")
    click.echo("")


@baseline.command("promote")
def baseline_promote() -> None:
    """Promote the last run result as the new baseline.

    Use after a successful comparison to advance the baseline.
    Alias: run 'flameiq baseline set' with your latest metrics file.
    """
    click.echo(
        click.style("ℹ", fg="blue") + " Run: flameiq baseline set --metrics <latest_metrics.json>"
    )


@baseline.command("clear")
@click.confirmation_option(prompt="Delete baseline and all history? This cannot be undone.")
def baseline_clear() -> None:
    """Clear all stored baselines and history. Destructive."""
    store = BaselineStore()
    try:
        store.clear()
        click.echo(click.style("✓ Baseline storage cleared.", fg="green"))
    except Exception as exc:
        click.echo(click.style(f"Error: {exc}", fg="red"), err=True)
        sys.exit(2)
