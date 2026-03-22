"""flameiq v2 report command.

Generates a rich, self-contained offline HTML performance report.
Includes: comparison, drift, correlation, trend charts, run history.

Usage:
    flameiq report
    flameiq report --output report.html
    flameiq report --last 50 --metric latency.p95 --metric throughput
"""

from __future__ import annotations

import sys

import click

from flameiq.v2.analysis.engine import CorrelationAnalyzer, DriftAnalyzer, TrendAnalyzer
from flameiq.v2.config import load_config_v2
from flameiq.v2.regression import RegressionEngine
from flameiq.v2.reporting.html_generator import generate_report
from flameiq.v2.storage.history import BaselineStoreV2, HistoryStore, rolling_median_baseline


@click.command("report")  # type: ignore[misc]
@click.option("--output", default=None, help="Output path for HTML report.")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--last",
    "n_runs",
    default=30,
    show_default=True,
    help="Number of recent runs to include in trend charts.",
)
@click.option(  # type: ignore[misc]
    "--metric",
    "metrics",
    multiple=True,
    help="Specific metrics to chart. Repeatable. Default: all.",
)
@click.option(  # type: ignore[misc]
    "--baseline", "baseline_name", default=None, help="Named baseline for comparison section."
)
@click.option("--title", default="FlameIQ Performance Report", show_default=True)  # type: ignore[misc]
@click.option("--branch", default=None, help="Filter history to a branch.")  # type: ignore[misc]
@click.option("--config", default="flameiq.yaml", show_default=True)  # type: ignore[misc]
def report_cmd_v2(
    output: str | None,
    n_runs: int,
    metrics: tuple[str, ...],
    baseline_name: str | None,
    title: str,
    branch: str | None,
    config: str,
) -> None:
    r"""Generate a rich offline HTML performance report.

    \b
    The report includes:
      • Baseline vs current comparison table
      • Drift analysis across recent runs
      • Metric correlation findings
      • Time-series trend charts per metric
      • Run history table

    \b
    Examples:
      flameiq report
      flameiq report --output perf-report.html --last 50
      flameiq report --metric latency.p95 --metric throughput
    """
    cfg = load_config_v2(config)
    out_path = output or cfg.report_path
    store = HistoryStore(cfg.flameiq_dir)
    baseline_store = BaselineStoreV2(cfg.flameiq_dir)

    history = store.get_last_n(n_runs, branch=branch)
    if not history:
        click.echo("✗ No run history. Run 'flameiq run --metrics <file>' first.", err=True)
        sys.exit(3)

    # ── Resolve baseline and build comparison
    name = baseline_name or cfg.baseline.name
    baseline = baseline_store.load(name)
    if baseline is None and len(history) >= 2:
        baseline = rolling_median_baseline(history, window=cfg.baseline.window)

    comparison = None
    if baseline is not None and history:
        current = history[-1].run
        engine = RegressionEngine(
            thresholds=cfg.thresholds,
            budgets=cfg.budgets,
        )
        comparison = engine.compare(baseline, current)

    # ── Trend reports
    analyzer = TrendAnalyzer(store)
    metric_keys = list(metrics) if metrics else sorted(store.all_metric_keys(n_runs))
    trend_reports = []
    for key in metric_keys:
        report = analyzer.trend(
            key,
            n=n_runs,
            branch=branch,
            drift_threshold_percent=cfg.drift.threshold_percent,
        )
        if report:
            trend_reports.append(report)

    # ── Drift analysis
    drift_summary = None
    if cfg.drift.enabled:
        drift_analyzer = DriftAnalyzer(store)
        drift_summary = drift_analyzer.analyze(
            n=n_runs,
            branch=branch,
            drift_threshold_percent=cfg.drift.threshold_percent,
            min_runs=cfg.drift.min_runs,
        )

    # ── Correlation
    correlation = None
    if cfg.correlation.enabled and len(history) >= 4:
        mid = len(history) // 2
        corr_analyzer = CorrelationAnalyzer(store)
        correlation = corr_analyzer.analyze_between(
            baseline_entries=history[:mid],
            current_entries=history[mid:],
            change_threshold=cfg.correlation.change_threshold,
        )

    # ── Generate HTML
    out = generate_report(
        output_path=out_path,
        comparison=comparison,
        trend_reports=trend_reports,
        drift_summary=drift_summary,
        correlation=correlation,
        history=history,
        title=title,
    )

    click.echo(f"✓ Report generated: {out}")
    click.echo(
        f"  {len(trend_reports)} metric trend(s) · {len(history)} runs · "
        f"{'drift analysis included' if drift_summary else 'no drift data'}"
    )
