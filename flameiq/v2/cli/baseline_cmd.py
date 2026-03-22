"""flameiq v2 baseline commands.

Manage named baselines explicitly.
No auto-promotion — trust through explicitness.

Commands:
    flameiq baseline set              — promote last run to baseline
    flameiq baseline set --name v1.2  — promote to named baseline
    flameiq baseline promote <src> <dst>
    flameiq baseline list
    flameiq baseline show [--name main]
    flameiq baseline delete <name>
"""

from __future__ import annotations

import json
import sys

import click

from flameiq.v2.config import load_config_v2
from flameiq.v2.storage.history import BaselineStoreV2, HistoryStore, rolling_median_baseline


@click.group("baseline")  # type: ignore[misc]
def baseline_grp_v2() -> None:
    """Manage performance baselines."""


@baseline_grp_v2.command("set")  # type: ignore[misc]
@click.option("--name", default="main", show_default=True, help="Name for this baseline.")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--strategy",
    default=None,
    type=click.Choice(["last_successful", "rolling_median"]),
    help="How to derive the baseline. Overrides config.",
)
@click.option("--window", default=None, type=int, help="Window size for rolling_median.")  # type: ignore[misc]
@click.option("--config", default="flameiq.yaml", show_default=True)  # type: ignore[misc]
@click.option("--json-output", "json_output", is_flag=True)  # type: ignore[misc]
def baseline_set(
    name: str, strategy: str | None, window: int | None, config: str, json_output: bool
) -> None:
    r"""Set or update a named baseline from recent run history.

    \b
    Strategies:
      last_successful   Use the most recent run.
      rolling_median    Compute median across last N runs (noise-resistant).

    \b
    Examples:
      flameiq baseline set
      flameiq baseline set --name release-1.2
      flameiq baseline set --strategy rolling_median --window 20
    """
    cfg = load_config_v2(config)
    store = HistoryStore(cfg.flameiq_dir)
    baseline_store = BaselineStoreV2(cfg.flameiq_dir)

    resolved_strategy = strategy or cfg.baseline.strategy
    resolved_window = window or cfg.baseline.window

    history = store.get_last_n(resolved_window + 5)
    if not history:
        _err(json_output, "No run history found. Run 'flameiq run --metrics <file>' first.", 3)

    if resolved_strategy == "last_successful":
        baseline = history[-1].run
        source = f"last run ({baseline.metadata.commit or 'unknown commit'})"
    else:
        if len(history) < 2:
            _err(json_output, "Need at least 2 runs for rolling_median strategy.", 3)
        baseline_result = rolling_median_baseline(history, window=resolved_window)
        if baseline_result is None:
            _err(json_output, "Could not compute rolling median — insufficient data.", 3)
        assert baseline_result is not None
        baseline = baseline_result
        source = f"rolling median of {min(len(history), resolved_window)} runs"

    path = baseline_store.save(baseline, name=name)

    if json_output:
        click.echo(
            json.dumps(
                {
                    "status": "ok",
                    "baseline_name": name,
                    "strategy": resolved_strategy,
                    "source": source,
                    "path": str(path),
                },
                indent=2,
            )
        )
    else:
        click.echo(f"✓ Baseline '{name}' set")
        click.echo(f"  strategy: {resolved_strategy}")
        click.echo(f"  source:   {source}")
        click.echo(f"  saved to: {path}")


@baseline_grp_v2.command("promote")  # type: ignore[misc]
@click.argument("source")  # type: ignore[misc]
@click.argument("destination")  # type: ignore[misc]
@click.option("--config", default="flameiq.yaml", show_default=True)  # type: ignore[misc]
@click.option("--json-output", "json_output", is_flag=True)  # type: ignore[misc]
def baseline_promote(source: str, destination: str, config: str, json_output: bool) -> None:
    r"""Promote a named baseline to another name.

    \b
    Example:
      flameiq baseline promote staging main
    """
    cfg = load_config_v2(config)
    baseline_store = BaselineStoreV2(cfg.flameiq_dir)

    if not baseline_store.promote(source, destination):
        _err(json_output, f"Baseline '{source}' not found.", 3)

    if json_output:
        click.echo(json.dumps({"status": "ok", "promoted": source, "to": destination}, indent=2))
    else:
        click.echo(f"✓ Baseline '{source}' promoted to '{destination}'")


@baseline_grp_v2.command("list")  # type: ignore[misc]
@click.option("--config", default="flameiq.yaml", show_default=True)  # type: ignore[misc]
@click.option("--json-output", "json_output", is_flag=True)  # type: ignore[misc]
def baseline_list(config: str, json_output: bool) -> None:
    """List all saved baselines."""
    cfg = load_config_v2(config)
    baseline_store = BaselineStoreV2(cfg.flameiq_dir)
    names = baseline_store.list_names()

    if json_output:
        click.echo(json.dumps({"baselines": names}, indent=2))
    else:
        if not names:
            click.echo("No baselines saved. Run 'flameiq baseline set' first.")
        else:
            click.echo(f"Baselines ({len(names)}):")
            for n in names:
                click.echo(f"  • {n}")


@baseline_grp_v2.command("show")  # type: ignore[misc]
@click.option("--name", default="main", show_default=True)  # type: ignore[misc]
@click.option("--config", default="flameiq.yaml", show_default=True)  # type: ignore[misc]
@click.option("--json-output", "json_output", is_flag=True)  # type: ignore[misc]
def baseline_show(name: str, config: str, json_output: bool) -> None:
    """Show metrics stored in a named baseline."""
    cfg = load_config_v2(config)
    baseline_store = BaselineStoreV2(cfg.flameiq_dir)

    run = baseline_store.load(name)
    if run is None:
        _err(json_output, f"Baseline '{name}' not found.", 3)
    assert run is not None

    flat = run.metrics.flat()

    if json_output:
        click.echo(json.dumps({"baseline": name, "metrics": flat}, indent=2))
    else:
        click.echo(f"\nBaseline: {name}")
        click.echo(f"  commit: {run.metadata.commit or '—'}")
        click.echo(f"  branch: {run.metadata.branch or '—'}")
        click.echo()
        click.echo("  Metrics:")
        for k, v in sorted(flat.items()):
            click.echo(f"    {k:<30} {v:.4f}")
        click.echo()


@baseline_grp_v2.command("delete")  # type: ignore[misc]
@click.argument("name")  # type: ignore[misc]
@click.option("--config", default="flameiq.yaml", show_default=True)  # type: ignore[misc]
@click.option("--json-output", "json_output", is_flag=True)  # type: ignore[misc]
def baseline_delete(name: str, config: str, json_output: bool) -> None:
    """Delete a named baseline."""
    cfg = load_config_v2(config)
    baseline_store = BaselineStoreV2(cfg.flameiq_dir)

    if not baseline_store.delete(name):
        _err(json_output, f"Baseline '{name}' not found.", 3)

    if json_output:
        click.echo(json.dumps({"status": "ok", "deleted": name}, indent=2))
    else:
        click.echo(f"✓ Baseline '{name}' deleted")


def _err(json_output: bool, msg: str, code: int) -> None:
    if json_output:
        click.echo(json.dumps({"status": "error", "message": msg}), err=True)
    else:
        click.echo(f"✗ {msg}", err=True)
    sys.exit(code)
