"""flameiq diff — compare two arbitrary snapshot files."""

from __future__ import annotations

import json
import sys

import click

from flameiq.core.comparator import compare_snapshots
from flameiq.core.models import ComparisonResult, RegressionStatus
from flameiq.providers.registry import get_provider


@click.command()
@click.argument("file_a", type=click.Path(exists=True))
@click.argument("file_b", type=click.Path(exists=True))
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
def diff(
    ctx: click.Context,
    file_a: str,
    file_b: str,
    provider: str,
    fail_on_regression: bool,
    as_json: bool,
    threshold: tuple[str, ...],
) -> None:
    r"""Compare two arbitrary metrics snapshot files directly.

    FILE_A is treated as the reference (baseline) snapshot and FILE_B is
    treated as the target (current) snapshot.

    \b
    Exit codes:
      0  No regression detected.
      1  Regression detected (when --fail-on-regression).
      2  Configuration or threshold error.
      3  Metrics file error.
    """
    # Parse inline threshold overrides
    threshold_config: dict[str, str | float] = {}
    for t in threshold:
        if "=" not in t:
            _err(as_json, f"Invalid --threshold format '{t}'. Use KEY=VALUE.")
            sys.exit(2)
        k, v = t.split("=", 1)
        threshold_config[k.strip()] = v.strip()

    try:
        provider_impl = get_provider(provider)
    except Exception as exc:
        _err(as_json, str(exc))
        sys.exit(2)

    try:
        snapshot_a = provider_impl.load(file_a)
    except Exception as exc:
        _err(as_json, str(exc))
        sys.exit(3)

    try:
        snapshot_b = provider_impl.load(file_b)
    except Exception as exc:
        _err(as_json, str(exc))
        sys.exit(3)

    result = compare_snapshots(
        snapshot_a,
        snapshot_b,
        threshold_config=threshold_config or None,
    )

    if as_json:
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        _print_table(result)

    if fail_on_regression:
        sys.exit(result.exit_code)


def _print_table(result: ComparisonResult) -> None:
    """Format and print the comparison results table to stdout.

    Args:
        result: The computed ComparisonResult object.
    """
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
    """Print an error message either as JSON or formatted text to stderr.

    Args:
        as_json: If True, prints JSON object to stdout.
        message: The error message string.
    """
    if as_json:
        click.echo(json.dumps({"status": "error", "message": message}))
    else:
        click.echo(click.style(f"Error: {message}", fg="red"), err=True)
