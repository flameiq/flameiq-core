"""flameiq v2 trend command.

Time-travel comparison and multi-run trend analysis.

Commands:
    flameiq trend --metric latency.p95 --last 30
    flameiq trend --from abc123 --to def456
    flameiq history [--last 20] [--branch main]

These are v2-only commands powered by persistent local run history.
"""

from __future__ import annotations

import json
import sys

import click

from flameiq.v2.analysis.engine import TrendAnalyzer
from flameiq.v2.config import load_config_v2
from flameiq.v2.storage.history import HistoryStore


@click.command("trend")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--metric", default=None, help="Metric to analyze (e.g. latency.p95). Omit to show all."
)
@click.option(  # type: ignore[misc]
    "--last", "n_runs", default=30, show_default=True, help="Number of recent runs to include."
)
@click.option("--branch", default=None, help="Filter to a specific branch.")  # type: ignore[misc]
@click.option("--from", "commit_a", default=None, help="Compare FROM this commit (requires --to).")  # type: ignore[misc]
@click.option("--to", "commit_b", default=None, help="Compare TO this commit (requires --from).")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--drift-threshold",
    default=5.0,
    show_default=True,
    help="Minimum cumulative % change to flag as drift.",
)
@click.option("--config", default="flameiq.yaml", show_default=True)  # type: ignore[misc]
@click.option("--json-output", "json_output", is_flag=True)  # type: ignore[misc]
def trend_cmd(
    metric: str | None,
    n_runs: int,
    branch: str | None,
    commit_a: str | None,
    commit_b: str | None,
    drift_threshold: float,
    config: str,
    json_output: bool,
) -> None:
    r"""Analyze performance trends and detect drift over time.

    \b
    Single metric trend:
      flameiq trend --metric latency.p95 --last 30

    All metrics trend:
      flameiq trend --last 20

    Time-travel comparison between two commits:
      flameiq trend --from abc123 --to def456

    Filter by branch:
      flameiq trend --metric latency.p95 --branch main
    """
    cfg = load_config_v2(config)
    store = HistoryStore(cfg.flameiq_dir)
    analyzer = TrendAnalyzer(store)

    # ── Time-travel mode
    if commit_a and commit_b:
        result = analyzer.compare_commits(commit_a, commit_b)
        if result is None:
            _err(json_output, f"No runs found for commits {commit_a} or {commit_b}.", 3)
        assert result is not None

        if json_output:
            click.echo(
                json.dumps(
                    {
                        "mode": "time_travel",
                        "from": commit_a,
                        "to": commit_b,
                        "metrics": result,
                    },
                    indent=2,
                )
            )
        else:
            click.echo(f"\nTime-travel comparison: {commit_a[:7]} → {commit_b[:7]}\n")
            _print_header(["METRIC", "FROM", "TO", "CHANGE"], [28, 12, 12, 12])
            click.echo("  " + "─" * 68)
            for key, d in sorted(result.items()):
                sign = "+" if d["change_percent"] >= 0 else ""
                _print_row(
                    [
                        key,
                        f"{d['commit_a_value']:.3f}",
                        f"{d['commit_b_value']:.3f}",
                        f"{sign}{d['change_percent']:.2f}%",
                    ],
                    [28, 12, 12, 12],
                )
            click.echo()
        return

    # ── Trend mode
    if metric:
        # Single metric
        report = analyzer.trend(
            metric,
            n=n_runs,
            branch=branch,
            drift_threshold_percent=drift_threshold,
        )
        if report is None:
            _err(json_output, f"Insufficient data for metric '{metric}' (need ≥2 runs).", 3)
        assert report is not None

        if json_output:
            click.echo(json.dumps(report.to_dict(), indent=2))
        else:
            _print_single_trend(report)
    else:
        # All metrics
        all_keys = store.all_metric_keys(n_runs)
        if not all_keys:
            _err(json_output, "No run history found. Run 'flameiq run --metrics <file>' first.", 3)

        reports = {}
        for key in sorted(all_keys):
            r = analyzer.trend(
                key, n=n_runs, branch=branch, drift_threshold_percent=drift_threshold
            )
            if r:
                reports[key] = r

        if json_output:
            click.echo(json.dumps({k: v.to_dict() for k, v in reports.items()}, indent=2))
        else:
            click.echo(f"\nTrend Analysis — last {n_runs} runs\n")
            _print_header(
                ["METRIC", "FIRST", "LAST", "TOTAL Δ", "SLOPE/RUN", "DRIFT"],
                [28, 10, 10, 10, 12, 18],
            )
            click.echo("  " + "─" * 96)
            for key, r in sorted(reports.items()):
                sign = "+" if r.overall_change_percent >= 0 else ""
                drift_str = (
                    f"{'▲' if r.drift.direction == 'worsening' else '▼'} "
                    f"{r.drift.cumulative_percent:+.1f}% [{r.drift.direction}]"
                    if r.drift.is_drifting
                    else "stable"
                )
                _print_row(
                    [
                        key,
                        f"{r.first_value:.2f}",
                        f"{r.last_value:.2f}",
                        f"{sign}{r.overall_change_percent:.1f}%",
                        f"{r.drift.slope_percent:+.3f}%",
                        drift_str,
                    ],
                    [28, 10, 10, 10, 12, 18],
                )
            click.echo()


@click.command("history")  # type: ignore[misc]
@click.option("--last", "n_runs", default=20, show_default=True, help="Number of runs to show.")  # type: ignore[misc]
@click.option("--branch", default=None, help="Filter by branch.")  # type: ignore[misc]
@click.option("--config", default="flameiq.yaml", show_default=True)  # type: ignore[misc]
@click.option("--json-output", "json_output", is_flag=True)  # type: ignore[misc]
def history_cmd(n_runs: int, branch: str | None, config: str, json_output: bool) -> None:
    r"""Show recent run history.

    \b
    Examples:
      flameiq history
      flameiq history --last 50
      flameiq history --branch main
    """
    cfg = load_config_v2(config)
    store = HistoryStore(cfg.flameiq_dir)
    entries = store.get_last_n(n_runs, branch=branch)

    if not entries:
        msg = "No run history found."
        if json_output:
            click.echo(json.dumps({"runs": []}))
        else:
            click.echo(f"  {msg}")
        return

    if json_output:
        out = []
        for e in entries:
            flat = e.run.metrics.flat()
            out.append(
                {
                    "run_id": e.run_id,
                    "commit": e.commit,
                    "branch": e.branch,
                    "environment": e.environment,
                    "timestamp": e.timestamp,
                    "metrics": flat,
                }
            )
        click.echo(json.dumps({"runs": out}, indent=2))
        return

    total = store.count(branch=branch)
    click.echo(f"\nRun History — showing {len(entries)} of {total} runs\n")
    _print_header(
        ["COMMIT", "BRANCH", "ENV", "TIMESTAMP", "p95 LAT", "THROUGHPUT"], [10, 16, 10, 20, 10, 12]
    )
    click.echo("  " + "─" * 86)
    for e in entries:
        flat = e.run.metrics.flat()
        lat = flat.get("latency.p95")
        tput = flat.get("throughput")
        _print_row(
            [
                (e.commit[:7] if e.commit else "—"),
                (e.branch or "—"),
                (e.environment or "—"),
                e.timestamp[:16],
                (f"{lat:.1f}ms" if lat else "—"),
                (f"{tput:.0f}" if tput else "—"),
            ],
            [10, 16, 10, 20, 10, 12],
        )
    click.echo()


# ── Print helpers ─────────────────────────────────────────────────────────────


def _print_single_trend(report: object) -> None:
    from flameiq.v2.analysis.engine import TrendReport

    assert isinstance(report, TrendReport)

    drift = report.drift
    click.echo(f"\nTrend: {report.metric}")
    click.echo(f"  runs:           {len(report.points)}")
    click.echo(f"  first value:    {report.first_value:.4f}")
    click.echo(f"  last value:     {report.last_value:.4f}")
    click.echo(f"  overall change: {report.overall_change_percent:+.2f}%")
    click.echo(f"  slope/run:      {drift.slope_percent:+.4f}%")
    click.echo(f"  R²:             {drift.confidence:.3f}")
    if drift.is_drifting:
        click.echo(
            f"  ⚠ DRIFT: {drift.direction.upper()}  cumulative {drift.cumulative_percent:+.1f}%"
        )
    else:
        click.echo("  ✓ STABLE — no significant drift detected")

    click.echo(f"\n  {'TIMESTAMP':<20} {'COMMIT':<10} {'VALUE':>12}  ΔFIRST")
    click.echo("  " + "─" * 54)
    for p in report.points:
        sign = "+" if p.change_from_first >= 0 else ""
        click.echo(
            f"  {p.timestamp[:16]:<20} {(p.commit[:7] if p.commit else '—'):<10} "
            f"{p.value:>12.4f}  {sign}{p.change_from_first:.2f}%"
        )
    click.echo()


def _print_header(cells: list[str], widths: list[int]) -> None:
    click.echo(
        "  "
        + "  ".join(
            c.ljust(w) if i == 0 else c.rjust(w)
            for i, (c, w) in enumerate(zip(cells, widths, strict=False))
        )
    )


def _print_row(cells: list[str], widths: list[int]) -> None:
    click.echo(
        "  "
        + "  ".join(
            c.ljust(w) if i == 0 else c.rjust(w)
            for i, (c, w) in enumerate(zip(cells, widths, strict=False))
        )
    )


def _err(json_output: bool, msg: str, code: int) -> None:
    if json_output:
        click.echo(json.dumps({"status": "error", "message": msg}), err=True)
    else:
        click.echo(f"✗ {msg}", err=True)
    sys.exit(code)
