"""FlameIQ static HTML report generator.

Produces a fully self-contained, offline-capable HTML report.

- No CDN dependencies.
- No JavaScript frameworks.
- Pure HTML5 + CSS + minimal vanilla JS for the bar chart.
- Single file output — share via email, artifacts, or S3.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from flameiq.core.models import ComparisonResult
    from flameiq.schema.v1.models import PerformanceSnapshot

_VERSION = "1.0.0"

# Colour palette
_NAVY = "#1B2B4B"
_FLAME = "#E05A2B"
_PASS_COLOR = "#1A7A4A"
_REGRESSION_COLOR = "#C0392B"
_WARNING_COLOR = "#D35400"
_BG = "#F5F6F8"
_SURFACE = "#FFFFFF"
_BORDER = "#E2E8F0"


def generate_report(
    result: ComparisonResult,
    baseline: PerformanceSnapshot,
    current: PerformanceSnapshot,
    output_path: Path,
) -> None:
    """Generate and write a self-contained HTML comparison report.

    Args:
        result:      The comparison result from
                     :func:`~flameiq.core.comparator.compare_snapshots`.
        baseline:    The baseline snapshot.
        current:     The current snapshot being evaluated.
        output_path: Filesystem path to write the ``.html`` file.
    """
    html = _render(result, baseline, current)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def _render(
    result: ComparisonResult,
    baseline: PerformanceSnapshot,
    current: PerformanceSnapshot,
) -> str:
    from flameiq.core.models import RegressionStatus

    status_color = {
        RegressionStatus.PASS: _PASS_COLOR,
        RegressionStatus.REGRESSION: _REGRESSION_COLOR,
        RegressionStatus.WARNING: _WARNING_COLOR,
        RegressionStatus.INSUFFICIENT_DATA: "#4A5568",
    }.get(result.status, _PASS_COLOR)

    # Table rows
    rows_html = ""
    for d in result.diffs:
        if d.is_regression:
            row_cls = "regression"
            chg = f"{d.change_percent:+.2f}%"
        elif d.is_warning:
            row_cls = "warning"
            chg = f"{d.change_percent:+.2f}%"
        else:
            row_cls = "pass"
            chg = f"{d.change_percent:+.2f}%"

        rows_html += f"""
        <tr class="{row_cls}">
          <td class="mono">{d.metric_key}</td>
          <td class="num">{d.baseline_value:.4f}</td>
          <td class="num">{d.current_value:.4f}</td>
          <td class="num chg">{chg}</td>
          <td class="num">±{d.threshold_percent:.1f}%</td>
          <td class="badge {row_cls}">{d.status_label}</td>
        </tr>"""

    # Bar chart data (change_percent, capped ±50 for display)
    chart_labels = [f'"{d.metric_key}"' for d in result.diffs]
    chart_values = [max(-50, min(50, d.change_percent)) for d in result.diffs]
    chart_colors = [
        f'"{_REGRESSION_COLOR}"'
        if d.is_regression
        else f'"{_WARNING_COLOR}"'
        if d.is_warning
        else f'"{_PASS_COLOR}"'
        for d in result.diffs
    ]

    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    b_env = baseline.metadata.environment.value
    c_env = current.metadata.environment.value

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FlameIQ Report — {result.status.value.upper()}</title>
  <style>
    :root {{
      --navy:{_NAVY}; --flame:{_FLAME}; --pass:{_PASS_COLOR};
      --reg:{_REGRESSION_COLOR}; --warn:{_WARNING_COLOR};
      --bg:{_BG}; --surface:{_SURFACE}; --border:{_BORDER};
      --text:#2D3748; --muted:#718096;
    }}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
         background:var(--bg);color:var(--text);line-height:1.6}}
    a{{color:var(--flame);text-decoration:none}}
    header{{background:var(--navy);color:#fff;padding:1.75rem 2.5rem;
            border-bottom:4px solid var(--flame)}}
    header h1{{font-size:1.6rem;font-weight:800;letter-spacing:-.5px}}
    header p{{color:rgba(255,255,255,.65);font-size:.85rem;margin-top:.2rem}}
    .banner{{padding:.9rem 2.5rem;background:{status_color};color:#fff;
             font-weight:700;font-size:1.05rem;letter-spacing:.3px}}
    .wrap{{max-width:1140px;margin:2rem auto;padding:0 2rem}}
    h2{{font-size:1rem;font-weight:700;color:var(--navy);margin:1.75rem 0 .75rem;
        padding-bottom:.4rem;border-bottom:2px solid var(--flame);display:inline-block}}
    /* Meta grid */
    .meta{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
           gap:.75rem;margin-bottom:1.5rem}}
    .card{{background:var(--surface);border:1px solid var(--border);
           border-radius:8px;padding:.9rem 1.1rem}}
    .card .lbl{{font-size:.7rem;text-transform:uppercase;letter-spacing:1px;
                color:var(--muted);font-weight:600}}
    .card .val{{font-size:.95rem;font-weight:700;color:var(--navy);
                font-family:monospace;margin-top:.15rem;word-break:break-all}}
    /* Summary pills */
    .pills{{display:flex;gap:.75rem;margin-bottom:1.75rem;flex-wrap:wrap}}
    .pill{{flex:1;min-width:110px;text-align:center;padding:1.1rem .5rem;
           border-radius:8px;background:var(--surface);border:1px solid var(--border)}}
    .pill .n{{font-size:2.1rem;font-weight:900}}
    .pill .t{{font-size:.72rem;text-transform:uppercase;letter-spacing:1px;
              color:var(--muted);margin-top:.2rem}}
    .pill.red{{border-color:var(--reg)}}.pill.red .n{{color:var(--reg)}}
    .pill.amber{{border-color:var(--warn)}}.pill.amber .n{{color:var(--warn)}}
    .pill.green .n{{color:var(--pass)}}
    /* Table */
    table{{width:100%;border-collapse:collapse;background:var(--surface);
           border-radius:10px;overflow:hidden;border:1px solid var(--border);
           margin-bottom:2rem}}
    thead th{{background:var(--navy);color:#fff;padding:.8rem 1rem;
              text-align:left;font-size:.8rem;letter-spacing:.4px}}
    tbody tr{{border-bottom:1px solid var(--border)}}
    tbody tr:hover{{background:var(--bg)}}
    tbody td{{padding:.8rem 1rem;font-size:.88rem}}
    .mono{{font-family:monospace;color:var(--navy);font-weight:600}}
    .num{{text-align:right}}
    tr.regression{{background:#FEF0F0}}
    tr.warning{{background:#FFF7ED}}
    /* Badges */
    .badge{{text-align:center;font-size:.75rem;font-weight:700;
            border-radius:4px;padding:.2rem .5rem}}
    .badge.regression{{background:#FEE2E2;color:var(--reg)}}
    .badge.warning{{background:#FFF3CD;color:var(--warn)}}
    .badge.pass{{background:#DCFCE7;color:var(--pass)}}
    /* Chart */
    .chart-wrap{{background:var(--surface);border:1px solid var(--border);
                 border-radius:10px;padding:1.25rem;margin-bottom:2rem;overflow-x:auto}}
    canvas{{max-width:100%}}
    /* Summary box */
    .summary-box{{background:var(--surface);border-left:4px solid {status_color};
                  border-radius:0 8px 8px 0;padding:1rem 1.25rem;
                  margin-bottom:1.75rem;font-size:.95rem}}
    footer{{text-align:center;color:var(--muted);font-size:.78rem;
            padding:2rem;border-top:1px solid var(--border)}}
  </style>
</head>
<body>

<header>
  <h1>FlameIQ Performance Report</h1>
  <p>Generated {ts} &nbsp;·&nbsp; FlameIQ v{_VERSION}
  &nbsp;·&nbsp; Deterministic · CI-Native · Offline-First</p>
</header>

<div class="banner">
  Status: {result.status.value.upper()} &nbsp;·&nbsp;
  {len(result.regressions)} regression(s) &nbsp;·&nbsp;
  {len(result.warnings)} warning(s) &nbsp;·&nbsp;
  {len(result.diffs)} metric(s) compared
</div>

<div class="wrap">

  <h2>Run Metadata</h2>
  <div class="meta">
    <div class="card"><div class="lbl">Baseline Commit</div>
      <div class="val">{baseline.metadata.commit or "—"}</div></div>
    <div class="card"><div class="lbl">Current Commit</div>
      <div class="val">{current.metadata.commit or "—"}</div></div>
    <div class="card"><div class="lbl">Baseline Branch</div>
      <div class="val">{baseline.metadata.branch or "—"}</div></div>
    <div class="card"><div class="lbl">Current Branch</div>
      <div class="val">{current.metadata.branch or "—"}</div></div>
    <div class="card"><div class="lbl">Environment</div>
      <div class="val">{b_env} → {c_env}</div></div>
    <div class="card"><div class="lbl">Statistical Mode</div>
      <div class="val">{"Enabled" if result.statistical_mode else "Disabled"}</div></div>
  </div>

  <h2>Summary</h2>
  <div class="pills">
    <div class="pill red"><div class="n">{len(result.regressions)}</div>
      <div class="t">Regressions</div></div>
    <div class="pill amber"><div class="n">{len(result.warnings)}</div>
      <div class="t">Warnings</div></div>
    <div class="pill green"><div class="n">{len(result.passed)}</div>
      <div class="t">Passed</div></div>
    <div class="pill"><div class="n">{len(result.diffs)}</div>
      <div class="t">Total</div></div>
  </div>

  <div class="summary-box">{result.summary or ""}</div>

  <h2>Metric Change Chart</h2>
  <div class="chart-wrap">
    <canvas id="chart" height="80"></canvas>
  </div>

  <h2>Metric Comparison</h2>
  <table>
    <thead>
      <tr>
        <th>Metric</th><th style="text-align:right">Baseline</th>
        <th style="text-align:right">Current</th><th style="text-align:right">Change %</th>
        <th style="text-align:right">Threshold</th><th style="text-align:center">Status</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>

</div>

<footer>
  FlameIQ v{_VERSION} &nbsp;·&nbsp;
  <a href="https://github.com/flameiq/flameiq-core">github.com/flameiq/flameiq-core</a>
  &nbsp;·&nbsp; Apache 2.0
</footer>

<script>
(function(){{
  var labels = [{",".join(chart_labels)}];
  var values = [{",".join(str(v) for v in chart_values)}];
  var colors = [{",".join(chart_colors)}];
  var canvas = document.getElementById('chart');
  var ctx = canvas.getContext('2d');
  var barW = 40, gap = 20, pad = 60;
  var total = labels.length;
  canvas.width = total * (barW + gap) + pad * 2;
  canvas.height = 200;
  var h = canvas.height, midY = h * 0.6;
  var maxAbs = Math.max.apply(null, values.map(Math.abs).concat([5]));
  ctx.fillStyle = '#F5F6F8';
  ctx.fillRect(0, 0, canvas.width, h);
  // Zero line
  ctx.strokeStyle = '#CBD5E0'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(pad, midY); ctx.lineTo(canvas.width - pad, midY); ctx.stroke();
  labels.forEach(function(lbl, i){{
    var x = pad + i * (barW + gap);
    var pct = values[i] / maxAbs;
    var barH = Math.abs(pct) * (midY - 20);
    var y = pct >= 0 ? midY - barH : midY;
    ctx.fillStyle = colors[i];
    ctx.fillRect(x, y, barW, barH || 2);
    // Label
    ctx.fillStyle = '#718096'; ctx.font = '10px monospace';
    ctx.save(); ctx.translate(x + barW/2, h - 5);
    ctx.rotate(-Math.PI/4); ctx.textAlign = 'right';
    ctx.fillText(lbl.replace(/"/g,''), 0, 0); ctx.restore();
    // Value
    ctx.fillStyle = '#2D3748'; ctx.font = 'bold 10px sans-serif';
    ctx.textAlign = 'center';
    var valY = pct >= 0 ? y - 4 : y + barH + 12;
    ctx.fillText((values[i] >= 0 ? '+' : '') + values[i].toFixed(1) + '%', x + barW/2, valY);
  }});
}})();
</script>
</body>
</html>"""
