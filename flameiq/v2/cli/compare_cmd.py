"""flameiq v2 compare command.

Compare current run against baseline with full v2 analysis:
  - Threshold-based regression detection
  - Budget ceiling enforcement
  - Optional statistical significance (Mann-Whitney U + bootstrap CI)
  - Correlation summary when regressions detected

Exit codes:
  0  PASS
  1  REGRESSION (threshold exceeded)
  2  CONFIG ERROR
  3  INVALID METRICS
  4  BUDGET BREACH

Usage:
    flameiq compare
    flameiq compare --baseline main
    flameiq compare --metrics benchmark.json --statistical
    flameiq compare --json-output
    flameiq compare --no-fail
"""

from __future__ import annotations

import json
import sys

import click

from flameiq.v2.analysis.engine import CorrelationAnalyzer
from flameiq.v2.config import load_config_v2
from flameiq.v2.regression import EXIT_PASS, RegressionEngine
from flameiq.v2.schema import ingest_metrics_file
from flameiq.v2.storage.history import BaselineStoreV2, HistoryStore, rolling_median_baseline


@click.command("compare")  # type: ignore[misc]
@click.option("--metrics", default=None, help="Metrics file (uses last recorded run if omitted).")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--baseline",
    "baseline_name",
    default=None,
    help="Named baseline to compare against. Default from config.",
)
@click.option(  # type: ignore[misc]
    "--statistical", is_flag=True, help="Enable Mann-Whitney U + bootstrap CI statistical analysis."
)
@click.option("--config", default="flameiq.yaml", show_default=True)  # type: ignore[misc]
@click.option("--json-output", "json_output", is_flag=True, help="Emit JSON output.")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--no-fail",
    "no_fail",
    is_flag=True,
    help="Always exit 0 (report regressions but do not fail CI).",
)
def compare_cmd_v2(
    metrics: str | None,
    baseline_name: str | None,
    statistical: bool,
    config: str,
    json_output: bool,
    no_fail: bool,
) -> None:
    r"""Compare current run against baseline.

    \b
    Detects regressions (threshold breach), budget violations,
    and optionally runs statistical significance testing.

    \b
    Exit codes:
      0  pass
      1  regression detected
      2  configuration error
      3  invalid metrics / missing data
      4  budget breach
    """
    cfg = load_config_v2(config)
    store = HistoryStore(cfg.flameiq_dir)
    baseline_store = BaselineStoreV2(cfg.flameiq_dir)

    # ── Resolve current run
    if metrics:
        from pathlib import Path

        if not Path(metrics).exists():
            _err(json_output, f"Metrics file not found: {metrics}", 3)
        try:
            current = ingest_metrics_file(metrics)
        except Exception as exc:
            _err(json_output, f"Failed to parse metrics: {exc}", 3)
    else:
        entries = store.get_last_n(1)
        if not entries:
            _err(json_output, "No runs recorded. Run 'flameiq run --metrics <file>' first.", 3)
        current = entries[-1].run

    # ── Resolve baseline
    name = baseline_name or cfg.baseline.name
    baseline = baseline_store.load(name)

    if baseline is None:
        # Fall back to rolling median from history
        history = store.get_last_n(cfg.baseline.window + 5)
        if len(history) < 2:
            _err(
                json_output,
                f"No baseline named '{name}' and insufficient history for rolling median. "
                "Run 'flameiq baseline set' first.",
                3,
            )
        baseline = rolling_median_baseline(history, window=cfg.baseline.window)
        if baseline is None:
            _err(json_output, "Could not compute rolling median baseline.", 3)
        assert baseline is not None

    # ── Run comparison
    use_stat = statistical or cfg.statistics.enabled
    engine = RegressionEngine(
        thresholds=cfg.thresholds,
        budgets=cfg.budgets,
        statistical_mode=use_stat,
        confidence=cfg.statistics.confidence,
        noise_tolerance=cfg.statistics.noise_tolerance,
    )

    result = engine.compare(baseline, current)

    # ── Correlation analysis on regression
    corr_narrative = ""
    if result.regressions and cfg.correlation.enabled:
        history_entries = store.get_last_n(cfg.drift.window)
        if len(history_entries) >= 4:
            mid = len(history_entries) // 2
            corr = CorrelationAnalyzer(store).analyze_between(
                baseline_entries=history_entries[:mid],
                current_entries=history_entries[mid:],
                change_threshold=cfg.correlation.change_threshold,
            )
            corr_narrative = corr.narrative

    # ── Output
    if json_output:
        out = result.to_dict()
        if corr_narrative:
            out["correlation_narrative"] = corr_narrative
        click.echo(json.dumps(out, indent=2))
    else:
        _print_result(result, corr_narrative)

    if no_fail:
        sys.exit(0)
    sys.exit(result.exit_code)


# ── Formatting helpers ────────────────────────────────────────────────────────


def _print_result(result: object, corr_narrative: str) -> None:
    from flameiq.v2.regression import ComparisonResult

    assert isinstance(result, ComparisonResult)

    # Status banner
    icon = "✓" if result.exit_code == 0 else "✗"
    status_label = result.status.upper().replace("_", " ")
    click.echo(f"\n{icon} {status_label}")
    if result.baseline_commit:
        click.echo(
            f"  baseline: {result.baseline_commit}  →  current: {result.current_commit or '—'}"
        )
    click.echo()

    # Metrics table header
    col_w = [28, 12, 12, 10, 10, 12]
    headers = ["METRIC", "BASELINE", "CURRENT", "CHANGE", "THRESHOLD", "STATUS"]
    _row(headers, col_w, header=True)
    click.echo("  " + "─" * (sum(col_w) + len(col_w) * 2))

    for m in sorted(result.metrics, key=lambda x: x.metric):
        sign = "+" if m.change_percent >= 0 else ""
        change_str = f"{sign}{m.change_percent:.1f}%"
        thr_str = f"{m.threshold_percent:+.0f}%" if m.threshold_percent is not None else "—"
        status_str = m.status.upper().replace("_", " ")
        _row(
            [
                m.metric,
                f"{m.baseline_value:.3f}",
                f"{m.current_value:.3f}",
                change_str,
                thr_str,
                status_str,
            ],
            col_w,
            highlight=m.status != "pass",
        )

    click.echo()

    # Statistical details
    if result.statistical:
        click.echo("  Statistical analysis:")
        for s in result.statistical:
            sig = "significant" if s.significant else "not significant"
            click.echo(
                f"    {s.metric:<28} p={s.p_value:.4f}  effect={s.effect_label}  "
                f"CI=[{s.ci_lower:.2f}, {s.ci_upper:.2f}]  {sig}"
            )
        click.echo()

    # Summary
    if result.regressions:
        click.echo(f"  ✗ Regressions ({len(result.regressions)}): {', '.join(result.regressions)}")
    if result.budget_breaches:
        count = len(result.budget_breaches)
        names = ", ".join(result.budget_breaches)
        click.echo(f"  ⚠ Budget breaches ({count}): {names}")
    if corr_narrative:
        click.echo(f"\n  Correlation: {corr_narrative}")
    if result.exit_code == EXIT_PASS:
        click.echo("  All metrics within acceptable bounds.\n")
    click.echo()


def _row(
    cells: list[str], widths: list[int], header: bool = False, highlight: bool = False
) -> None:
    line = "  " + "  ".join(
        str(c).ljust(w) if i == 0 else str(c).rjust(w)
        for i, (c, w) in enumerate(zip(cells, widths, strict=False))
    )
    click.echo(line)


def _err(json_output: bool, msg: str, code: int) -> None:
    if json_output:
        click.echo(json.dumps({"status": "error", "message": msg}), err=True)
    else:
        click.echo(f"✗ {msg}", err=True)
    sys.exit(code)
