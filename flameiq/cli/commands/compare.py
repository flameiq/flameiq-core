"""flameiq compare — compare current metrics against baseline."""

from __future__ import annotations

import json
import sys

import click

from flameiq.core.comparator import compare_snapshots
from flameiq.core.models import RegressionStatus
from flameiq.providers.registry import get_provider
from flameiq.storage.baseline_store import BaselineStore


@click.command()
@click.option(
    "--metrics",
    "-m",
    required=True,
    type=click.Path(exists=True),
    help="Metrics file for the current run.",
)
@click.option("--provider", "-p", default="json", show_default=True, help="Metric provider to use.")
@click.option(
    "--fail-on-regression/--no-fail-on-regression",
    default=True,
    show_default=True,
    help="Exit with code 1 if regression detected.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output result as JSON (for CI pipelines).",
)
@click.option(
    "--threshold",
    "-t",
    multiple=True,
    metavar="KEY=VALUE",
    help="Override threshold, e.g. --threshold latency.p95=10%",
)
@click.pass_context
def compare(
    ctx: click.Context,
    metrics: str,
    provider: str,
    fail_on_regression: bool,
    as_json: bool,
    threshold: tuple[str, ...],
) -> None:
    """Compare the current metrics against the stored baseline.

    \b
    Exit codes:
      0  No regression detected.
      1  Regression detected (when --fail-on-regression).
      2  Baseline or configuration error.
      3  Metrics file error.
    """
    # Parse inline threshold overrides
    threshold_config: dict[str, str] = {}
    for t in threshold:
        if "=" not in t:
            _err(as_json, f"Invalid --threshold format '{t}'. Use KEY=VALUE.")
            sys.exit(2)
        k, v = t.split("=", 1)
        threshold_config[k.strip()] = v.strip()

    store = BaselineStore()
    try:
        baseline_snap = store.load_baseline()
    except Exception as exc:
        _err(as_json, str(exc))
        sys.exit(2)

    try:
        current_snap = get_provider(provider).load(metrics)
    except Exception as exc:
        _err(as_json, str(exc))
        sys.exit(3)

    result = compare_snapshots(
        baseline_snap,
        current_snap,
        threshold_config=threshold_config or None,
    )

    if as_json:
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        _print_table(result)

    if fail_on_regression:
        sys.exit(result.exit_code)


def _print_table(result: object) -> None:
    from flameiq.core.models import ComparisonResult

    assert isinstance(result, ComparisonResult)

    click.echo("")
    # Header
    click.echo(
        f"  {'Metric':<22} {'Baseline':>12} {'Current':>12} "
        f"{'Change':>10} {'Threshold':>10}  Status"
    )
    click.echo("  " + "─" * 78)

    for d in result.diffs:
        chg = f"{d.change_percent:+.2f}%"
        thr = f"±{d.threshold_percent:.1f}%"
        if d.is_regression:
            status_str = click.style("REGRESSION", fg="red", bold=True)
            chg_str = click.style(chg, fg="red")
        elif d.is_warning:
            status_str = click.style("WARNING", fg="yellow")
            chg_str = click.style(chg, fg="yellow")
        else:
            status_str = click.style("PASS", fg="green")
            chg_str = click.style(chg, fg="green")

        click.echo(
            f"  {d.metric_key:<22} {d.baseline_value:>12.4f} "
            f"{d.current_value:>12.4f} {chg_str:>10}  {thr:>10}  {status_str}"
        )

    click.echo("")
    if result.status == RegressionStatus.REGRESSION:
        click.echo(
            click.style(
                f"  ✗ REGRESSION — {len(result.regressions)} metric(s) exceeded threshold.",
                fg="red",
                bold=True,
            )
        )
    elif result.warnings:
        click.echo(
            click.style(
                f"  ⚠ WARNING — {len(result.warnings)} metric(s) approaching threshold.",
                fg="yellow",
            )
        )
    else:
        click.echo(
            click.style(
                f"  ✓ PASS — all {len(result.diffs)} metric(s) within threshold.",
                fg="green",
                bold=True,
            )
        )
    click.echo("")


def _err(as_json: bool, message: str) -> None:
    if as_json:
        click.echo(json.dumps({"status": "error", "message": message}))
    else:
        click.echo(click.style(f"Error: {message}", fg="red"), err=True)
