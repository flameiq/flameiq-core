"""flameiq v2 run command.

Records a performance snapshot into persistent local history.
Supports commit/branch metadata, environment tags.

Usage:
    flameiq run --metrics benchmark.json
    flameiq run --metrics benchmark.json --commit abc123 --branch main --env staging
    flameiq run --metrics benchmark.json --json-output
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import click

from flameiq.v2.config import load_config_v2
from flameiq.v2.schema import ingest_metrics_file
from flameiq.v2.storage.history import HistoryStore


def _git_info() -> tuple[str, str]:
    """Try to auto-detect git commit and branch. Returns ('', '') on failure."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return commit, branch
    except Exception:
        return "", ""


@click.command("run")  # type: ignore[misc]
@click.option("--metrics", required=True, help="Path to metrics JSON file.")  # type: ignore[misc]
@click.option("--commit", default=None, help="Git commit SHA (auto-detected if omitted).")  # type: ignore[misc]
@click.option("--branch", default=None, help="Git branch name (auto-detected if omitted).")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--env", default="ci", show_default=True, help="Environment label (ci, staging, local …)."
)
@click.option("--config", default="flameiq.yaml", show_default=True, help="Path to flameiq.yaml.")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--json-output", "json_output", is_flag=True, help="Emit JSON instead of human output."
)
def run_cmd_v2(
    metrics: str,
    commit: str | None,
    branch: str | None,
    env: str,
    config: str,
    json_output: bool,
) -> None:
    r"""Record a performance snapshot into local history.

    \b
    The run is stored in .flameiq/history/ and indexed for future
    comparison, trend analysis, and drift detection.

    \b
    Examples:
      flameiq run --metrics benchmark.json
      flameiq run --metrics out.json --commit abc123 --branch main
      flameiq run --metrics out.json --env staging --json-output
    """
    cfg = load_config_v2(config)
    store = HistoryStore(cfg.flameiq_dir)

    # Auto-detect git metadata when not supplied
    auto_commit, auto_branch = _git_info()
    resolved_commit = commit or auto_commit
    resolved_branch = branch or auto_branch

    # Check metrics file exists
    metrics_path = Path(metrics)
    if not metrics_path.exists():
        msg = f"Metrics file not found: {metrics}"
        if json_output:
            click.echo(json.dumps({"status": "error", "message": msg}), err=True)
        else:
            click.echo(f"✗ {msg}", err=True)
        sys.exit(3)

    try:
        run = ingest_metrics_file(
            str(metrics_path),
            commit=resolved_commit,
            branch=resolved_branch,
            env=env,
        )
    except Exception as exc:
        msg = f"Failed to parse metrics: {exc}"
        if json_output:
            click.echo(json.dumps({"status": "error", "message": msg}), err=True)
        else:
            click.echo(f"✗ {msg}", err=True)
        sys.exit(3)

    try:
        store.record(run)
    except Exception as exc:
        msg = f"Failed to store run: {exc}"
        if json_output:
            click.echo(json.dumps({"status": "error", "message": msg}), err=True)
        else:
            click.echo(f"✗ {msg}", err=True)
        sys.exit(2)

    flat = run.metrics.flat()
    metric_count = len(flat)

    if json_output:
        click.echo(
            json.dumps(
                {
                    "status": "ok",
                    "run_id": run.run_id,
                    "commit": resolved_commit,
                    "branch": resolved_branch,
                    "environment": env,
                    "metrics_recorded": metric_count,
                    "flameiq_dir": str(cfg.flameiq_dir),
                },
                indent=2,
            )
        )
    else:
        click.echo(f"✓ Run recorded  [run_id={run.run_id[:12]}…]")
        if resolved_commit:
            click.echo(f"  commit:  {resolved_commit}")
        if resolved_branch:
            click.echo(f"  branch:  {resolved_branch}")
        click.echo(f"  env:     {env}")
        click.echo(f"  metrics: {metric_count} captured")
        click.echo(f"  stored:  {cfg.flameiq_dir}/history/")
