"""flameiq v2 drift command.

Detect gradual performance degradation across multiple runs.
Catches slow regressions that never trigger single-run thresholds.

Usage:
    flameiq drift
    flameiq drift --window 50 --threshold 3.0
    flameiq drift --branch main --json-output
"""

from __future__ import annotations

import json
import sys

import click

from flameiq.v2.analysis.engine import DriftAnalyzer
from flameiq.v2.config import load_config_v2
from flameiq.v2.storage.history import HistoryStore


@click.command("drift")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--window",
    default=None,
    type=int,
    help="Number of recent runs to analyze. Default from config.",
)
@click.option(  # type: ignore[misc]
    "--threshold",
    "threshold_percent",
    default=None,
    type=float,
    help="Minimum cumulative % change to flag drift. Default from config.",
)
@click.option(  # type: ignore[misc]
    "--min-runs", default=None, type=int, help="Minimum runs required before drift is flagged."
)
@click.option("--branch", default=None, help="Filter to a specific branch.")  # type: ignore[misc]
@click.option("--config", default="flameiq.yaml", show_default=True)  # type: ignore[misc]
@click.option("--json-output", "json_output", is_flag=True)  # type: ignore[misc]
@click.option("--fail-on-drift", is_flag=True, help="Exit with code 5 if drift is detected.")  # type: ignore[misc]
def drift_cmd(
    window: int | None,
    threshold_percent: float | None,
    min_runs: int | None,
    branch: str | None,
    config: str,
    json_output: bool,
    fail_on_drift: bool,
) -> None:
    r"""Detect gradual performance drift across many runs.

    \b
    Drift is flagged when:
      • Cumulative change ≥ threshold_percent (default 5%)
      • Linear fit R² ≥ 0.30 (trend is real, not noise)
      • At least min_runs data points available

    \b
    This catches slow regressions: e.g., +1% latency per commit
    for 20 commits = +20% total — never triggering a single-run gate.

    \b
    Exit codes:
      0  no drift detected
      5  drift detected (only when --fail-on-drift is set)
    """
    cfg = load_config_v2(config)
    store = HistoryStore(cfg.flameiq_dir)

    resolved_window = window or cfg.drift.window
    resolved_threshold = threshold_percent or cfg.drift.threshold_percent
    resolved_min_runs = min_runs or cfg.drift.min_runs

    analyzer = DriftAnalyzer(store)
    summary = analyzer.analyze(
        n=resolved_window,
        branch=branch,
        drift_threshold_percent=resolved_threshold,
        min_runs=resolved_min_runs,
    )

    if json_output:
        click.echo(json.dumps(summary.to_dict(), indent=2))
    else:
        _print_drift_summary(summary, resolved_window, resolved_threshold)

    if fail_on_drift and summary.has_drifting_metrics:
        sys.exit(5)
    sys.exit(0)


def _print_drift_summary(summary: object, window: int, threshold: float) -> None:
    from flameiq.v2.analysis.engine import DriftSummary

    assert isinstance(summary, DriftSummary)

    click.echo(f"\nDrift Analysis — last {window} runs  (threshold: {threshold:.1f}%  R² ≥ 0.30)\n")

    if not summary.details:
        click.echo("  No metrics with sufficient history for drift analysis.")
        click.echo()
        return

    # Header
    col_w = [28, 12, 12, 8, 20]
    headers = ["METRIC", "SLOPE/RUN", "CUMULATIVE", "R²", "STATUS"]
    click.echo(
        "  "
        + "  ".join(
            h.ljust(col_w[i]) if i == 0 else h.rjust(col_w[i]) for i, h in enumerate(headers)
        )
    )
    click.echo("  " + "─" * 82)

    for key, dr in sorted(summary.details.items()):
        if dr.is_drifting:
            direction_icon = "▲ " if dr.direction == "worsening" else "▼ "
            status_str = f"{direction_icon}{dr.direction.upper()}"
        else:
            status_str = "✓ stable"
        click.echo(
            "  "
            + "  ".join(
                [
                    key.ljust(col_w[0]),
                    f"{dr.slope_percent:+.4f}%".rjust(col_w[1]),
                    f"{dr.cumulative_percent:+.2f}%".rjust(col_w[2]),
                    f"{dr.confidence:.2f}".rjust(col_w[3]),
                    status_str.rjust(col_w[4]),
                ]
            )
        )

    click.echo()

    if summary.has_drifting_metrics:
        click.echo(
            f"  ⚠  Drifting metrics ({len(summary.drifting_metrics)}): "
            f"{', '.join(summary.drifting_metrics)}"
        )
    else:
        click.echo(f"  ✓  All {len(summary.stable_metrics)} metric(s) stable — no drift detected")
    click.echo()
