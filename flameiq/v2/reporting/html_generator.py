"""FlameIQ v2 Report Generator.

Generates a rich, self-contained, offline HTML performance report.

Features:
  - Baseline vs current diff table (color-coded)
  - Multi-run time series charts (Chart.js via CDN)
  - Drift visualization with direction indicators
  - Correlation summary with rule-based narrative
  - Budget gauge indicators
  - Run history table
  - Zero server-side dependencies — 100% static HTML
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flameiq.v2.analysis.engine import CorrelationReport, DriftSummary, TrendReport
    from flameiq.v2.regression import ComparisonResult
    from flameiq.v2.storage.history import HistoryEntry


def generate_report(
    output_path: str | Path,
    comparison: ComparisonResult | None = None,
    trend_reports: list[TrendReport] | None = None,
    drift_summary: DriftSummary | None = None,
    correlation: CorrelationReport | None = None,
    history: list[HistoryEntry] | None = None,
    title: str = "FlameIQ Performance Report",
) -> Path:
    """Generate and save the HTML report. Returns the output path."""
    html = _build_html(
        title=title,
        comparison=comparison,
        trend_reports=trend_reports or [],
        drift_summary=drift_summary,
        correlation=correlation,
        history=history or [],
    )
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


# ── Color helpers ─────────────────────────────────────────────────────────────


def _status_color(status: str) -> str:
    return {
        "pass": "#22c55e",
        "regression": "#ef4444",
        "budget_breach": "#f97316",
        "warning": "#eab308",
    }.get(status, "#6b7280")


def _change_badge(pct: float, inverted: bool = False) -> str:
    worse = (pct > 0) if not inverted else (pct < 0)
    c = "#ef4444" if worse else "#22c55e"
    arrow = "▲" if pct > 0 else "▼"
    return f'<span style="color:{c};font-weight:600">{arrow} {abs(pct):.2f}%</span>'


# ── Build HTML ─────────────────────────────────────────────────────────────────


def _build_html(
    title: str,
    comparison: Any,
    trend_reports: list[TrendReport],
    drift_summary: Any,
    correlation: Any,
    history: list[HistoryEntry],
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ── Common styles
    td_mono_left = (
        "padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#cbd5e1;font-size:0.85rem"
    )
    td_mono_right = "padding:12px 16px;text-align:right;color:#64748b;font-size:0.85rem"
    td_value = "padding:12px 16px;text-align:right;color:#e2e8f0;font-size:0.85rem"
    td_center = "padding:12px 16px;text-align:center"
    th_header = "padding:10px 16px;text-align:left;color:#475569;font-weight:500;font-size:0.8rem"
    th_right = "padding:10px 16px;text-align:right;color:#475569;font-weight:500;font-size:0.8rem"
    status_badge = (
        "padding:2px 10px;border-radius:12px;font-size:0.7rem;"
        "font-weight:700;text-transform:uppercase"
    )
    hist_th = "padding:8px 14px;text-align:left;color:#334155;font-weight:500;font-size:0.75rem"
    hist_th_right = (
        "padding:8px 14px;text-align:right;color:#334155;font-weight:500;font-size:0.75rem"
    )

    # ── Overall status banner
    overall_badge = ""
    if comparison:
        c = _status_color(comparison.status)
        status_msg = comparison.status.replace("_", " ")
        overall_badge = (
            f'<div style="background:{c}18;border-left:4px solid {c};'
            f"padding:16px 24px;border-radius:8px;margin-bottom:28px;"
            f'display:flex;align-items:center;gap:16px">\n'
            f'  <span style="color:{c};font-size:1.1rem;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.1em">{status_msg}</span>\n'
            f'  <span style="color:#64748b;font-size:0.875rem;'
            f"font-family:'JetBrains Mono',monospace\">{comparison.summary}</span>\n"
            f"</div>"
        )

    # ── Comparison table rows
    comp_rows = ""
    if comparison:
        for m in comparison.metrics:
            inv = m.metric == "throughput"
            rc = _status_color(m.status)
            status_lbl = m.status.replace("_", " ")
            comp_rows += (
                f'  <tr style="border-bottom:1px solid #1e293b">\n'
                f'    <td style="{td_mono_left}">{m.metric}</td>\n'
                f'    <td style="{td_mono_right}">{m.baseline_value:,.3f}</td>\n'
                f'    <td style="{td_value}">{m.current_value:,.3f}</td>\n'
                f'    <td style="{td_mono_right}">{_change_badge(m.change_percent, inv)}</td>\n'
                f'    <td style="{td_center}">\n'
                f'      <span style="background:{rc}18;color:{rc};{status_badge}">'
                f"{status_lbl}</span>\n"
                f"    </td>\n"
                f"  </tr>\n"
            )

    comparison_section = ""
    if comp_rows:
        comparison_section = (
            '<div class="card">\n'
            '  <h2 class="section-title">Baseline Comparison</h2>\n'
            '  <table style="width:100%;border-collapse:collapse">\n'
            "    <thead>\n"
            '      <tr style="border-bottom:2px solid #334155">\n'
            f'        <th style="{th_header}">METRIC</th>\n'
            f'        <th style="{th_right}">BASELINE</th>\n'
            f'        <th style="{th_right}">CURRENT</th>\n'
            f'        <th style="{th_right}">CHANGE</th>\n'
            f'        <th style="padding:10px 16px;text-align:center;color:#475569;'
            f'font-weight:500;font-size:0.8rem">STATUS</th>\n'
            "      </tr>\n"
            "    </thead>\n"
            f"    <tbody>{comp_rows}</tbody>\n"
            "  </table>\n"
            "</div>"
        )

    # ── Drift section
    drift_section = ""
    if drift_summary and drift_summary.details:
        drift_rows = ""
        for key, dr in drift_summary.details.items():
            c = (
                "#ef4444"
                if (dr.is_drifting and dr.direction == "worsening")
                else "#22c55e"
                if (dr.is_drifting and dr.direction == "improving")
                else "#475569"
            )
            flag = "⚠" if dr.is_drifting else "✓"
            drift_rows += f"""
          <tr style="border-bottom:1px solid #1e293b">
            <td style="padding:10px 16px;font-family:'JetBrains Mono',monospace;
color:#cbd5e1;font-size:0.85rem">{key}</td>
            <td style="padding:10px 16px;text-align:right;color:#64748b;
font-size:0.85rem">{dr.slope_percent:+.3f}%/run</td>
            <td style="padding:10px 16px;text-align:right;color:{c};
font-size:0.85rem;font-weight:600">{dr.cumulative_percent:+.2f}%</td>
            <td style="padding:10px 16px;text-align:right;color:#64748b;
font-size:0.85rem">{dr.confidence:.2f}</td>
            <td style="padding:10px 16px;text-align:center;font-size:0.85rem">
              <span style="color:{c};font-weight:700">{flag} {dr.direction.upper()}</span>
            </td>
          </tr>"""

        sample_count = (
            list(drift_summary.details.values())[0].run_count if drift_summary.details else 0
        )
        drift_section = f"""
    <div class="card">
      <h2 class="section-title">Drift Analysis</h2>
      <p style="color:#475569;font-size:0.8rem;margin-bottom:16px">
        Linear regression across {sample_count} runs · Flagged when cumulative Δ ≥ 5% and R² ≥ 0.30
      </p>
      <table style="width:100%;border-collapse:collapse">
        <thead>
          <tr style="border-bottom:2px solid #334155">
            <th style="padding:10px 16px;text-align:left;color:#475569;
font-weight:500;font-size:0.8rem">METRIC</th>
            <th style="padding:10px 16px;text-align:right;color:#475569;
font-weight:500;font-size:0.8rem">SLOPE/RUN</th>
            <th style="padding:10px 16px;text-align:right;color:#475569;
font-weight:500;font-size:0.8rem">CUMULATIVE</th>
            <th style="padding:10px 16px;text-align:right;color:#475569;
font-weight:500;font-size:0.8rem">R²</th>
            <th style="padding:10px 16px;text-align:center;color:#475569;
font-weight:500;font-size:0.8rem">STATUS</th>
          </tr>
        </thead>
        <tbody>{drift_rows}</tbody>
      </table>
    </div>"""

    # ── Correlation section
    corr_section = ""
    if correlation and correlation.findings:
        cards = ""
        for f in correlation.findings:
            cards += (
                '<div style="background:#0a0f1e;border:1px solid #1e293b;'
                'border-radius:8px;padding:16px;margin-bottom:10px">\n'
                '  <div style="display:flex;gap:12px;align-items:center;'
                "margin-bottom:8px;font-family:'JetBrains Mono',monospace;"
                'font-size:0.8rem">\n'
                f'    <span style="color:#f97316">{f.primary_metric}</span>\n'
                '    <span style="color:#334155">→ correlates with →</span>\n'
                f'    <span style="color:#6366f1">{f.correlated_metric}</span>\n'
                "  </div>\n"
                f'  <p style="color:#64748b;font-size:0.85rem;margin:0 0 8px">'
                f"{f.narrative}</p>\n"
                '  <div style="display:flex;gap:20px;font-size:0.8rem;'
                'color:#475569">\n'
                f'    <span>Pearson r: <strong style="color:#e2e8f0">'
                f"{f.correlation_coefficient:.2f}</strong></span>\n"
                f'    <span>Primary Δ: <strong style="color:#e2e8f0">'
                f"{f.primary_change_percent:+.1f}%</strong></span>\n"
                "  </div>\n"
                "</div>\n"
            )

        corr_section = (
            '<div class="card">\n'
            '  <h2 class="section-title">Correlation Analysis</h2>\n'
            '  <div style="background:#0a0f1e;border:1px solid #f9741620;'
            'border-radius:8px;padding:14px 16px;margin-bottom:16px">\n'
            '    <span style="color:#f97316;font-weight:600;font-size:0.85rem">'
            "Primary Driver: </span>\n"
            f'    <span style="color:#cbd5e1;font-size:0.85rem">'
            f"{correlation.narrative}</span>\n"
            "  </div>\n"
            f"  {cards}"
            "</div>"
        )

    # ── Trend charts
    chart_html = ""
    chart_js = ""
    for i, tr in enumerate(trend_reports):
        cid = f"tc{i}"
        labels = json.dumps([p.timestamp[:10] for p in tr.points])
        vals = json.dumps([round(p.value, 4) for p in tr.points])
        commits = json.dumps([(p.commit[:7] if p.commit else "") for p in tr.points])
        dc = (
            "#ef4444"
            if (tr.drift.is_drifting and tr.drift.direction == "worsening")
            else "#22c55e"
            if (tr.drift.is_drifting and tr.drift.direction == "improving")
            else "#6366f1"
        )

        badge = ""
        if tr.drift.is_drifting:
            drift_pct = tr.drift.cumulative_percent
            badge = (
                f'<span style="background:{dc}18;color:{dc};'
                f"padding:2px 10px;border-radius:12px;font-size:0.7rem;"
                f'font-weight:700;margin-left:10px">DRIFT {drift_pct:+.1f}%</span>'
            )

        metric_style = (
            "font-family:'JetBrains Mono',monospace;color:#e2e8f0;font-size:0.9rem;font-weight:600"
        )
        overall_pct = tr.overall_change_percent
        chart_html += (
            f'  <div class="card">\n'
            f'    <div style="display:flex;align-items:center;margin-bottom:16px">\n'
            f'      <span style="{metric_style}">{tr.metric}</span>\n'
            f"      {badge}\n"
            f'      <span style="margin-left:auto;color:#475569;font-size:0.75rem">'
            f"{len(tr.points)} runs · Δ overall {overall_pct:+.1f}%</span>\n"
            f"    </div>\n"
            f'    <canvas id="{cid}" height="90"></canvas>\n'
            f"  </div>\n"
        )

        chart_js += (
            f"    new Chart(document.getElementById('{cid}'), {{\n"
            f"      type: 'line',\n"
            f"      data: {{\n"
            f"        labels: {labels},\n"
            f"        datasets: [{{\n"
            f"          data: {vals},\n"
            f"          borderColor: '{dc}',\n"
            f"          backgroundColor: '{dc}0f',\n"
            f"          tension: 0.35,\n"
            f"          fill: true,\n"
            f"          pointBackgroundColor: '{dc}',\n"
            f"          pointRadius: 3,\n"
            f"          pointHoverRadius: 6,\n"
            f"        }}]\n"
            f"      }},\n"
            f"      options: {{\n"
            f"        responsive: true,\n"
            f"        plugins: {{\n"
            f"          legend: {{ display: false }},\n"
            f"          tooltip: {{\n"
            f"            backgroundColor: '#0f172a',\n"
            f"            borderColor: '#334155',\n"
            f"            borderWidth: 1,\n"
            f"            callbacks: {{\n"
            f"              title: (ctx) => {{\n"
            f"                const c={commits};\n"
            f"                return ctx[0].label + (c[ctx[0].dataIndex] ? ' · ' + "
            f"c[ctx[0].dataIndex] : '');\n"
            f"              }},\n"
            f"              label: (ctx) => ' ' + ctx.parsed.y.toFixed(3),\n"
            f"            }}\n"
            f"          }}\n"
            f"        }},\n"
            f"        scales: {{\n"
            f"          x: {{ grid: {{ color: '#1e293b' }}, ticks: "
            f"{{ color: '#475569', font: {{ size: 11 }} }} }},\n"
            f"          y: {{ grid: {{ color: '#1e293b' }}, ticks: "
            f"{{ color: '#475569', font: {{ size: 11 }} }} }},\n"
            f"        }}\n"
            f"      }}\n"
            f"    }});\n"
        )

    trends_section = ""
    if chart_html:
        trends_section = (
            f'<h2 class="section-title" style="margin-bottom:16px">Metric Trends</h2>{chart_html}'
        )

    # ── History table
    hist_rows = ""
    for e in (history or [])[-20:]:
        flat = e.run.metrics.flat()
        lat = flat.get("latency.p95")
        tput = flat.get("throughput")
        commit_short = e.commit[:7] if e.commit else "—"
        hist_rows += (
            f'  <tr style="border-bottom:1px solid #0f172a">\n'
            f"    <td style=\"padding:8px 14px;font-family:'JetBrains Mono',"
            f'monospace;color:#475569;font-size:0.78rem">{commit_short}</td>\n'
            f'    <td style="padding:8px 14px;color:#475569;'
            f'font-size:0.78rem">{e.branch or "—"}</td>\n'
            f'    <td style="padding:8px 14px;color:#334155;'
            f'font-size:0.78rem">{e.timestamp[:16]}</td>\n'
            f'    <td style="padding:8px 14px;text-align:right;color:#cbd5e1;'
            f'font-size:0.78rem">{f"{lat:.1f}ms" if lat else "—"}</td>\n'
            f'    <td style="padding:8px 14px;text-align:right;color:#cbd5e1;'
            f'font-size:0.78rem">{f"{tput:.0f}" if tput else "—"}</td>\n'
            f"  </tr>\n"
        )

    history_section = ""
    if hist_rows:
        history_section = (
            '<div class="card">\n'
            '  <h2 class="section-title">Run History (last 20)</h2>\n'
            '  <table style="width:100%;border-collapse:collapse">\n'
            "    <thead>\n"
            '      <tr style="border-bottom:2px solid #1e293b">\n'
            f'        <th style="{hist_th}">COMMIT</th>\n'
            f'        <th style="{hist_th}">BRANCH</th>\n'
            f'        <th style="{hist_th}">TIME</th>\n'
            f'        <th style="{hist_th_right}">p95 LAT</th>\n'
            f'        <th style="{hist_th_right}">THROUGHPUT</th>\n'
            "      </tr>\n"
            "    </thead>\n"
            f"    <tbody>{hist_rows}</tbody>\n"
            "  </table>\n"
            "</div>"
        )

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        f'  <meta charset="UTF-8">\n'
        f'  <meta name="viewport" content="width=device-width,'
        f'initial-scale=1">\n'
        f"  <title>{title}</title>\n"
        '  <script src="https://cdn.jsdelivr.net/npm/chart.js@'
        '4.4.0/dist/chart.umd.min.js"></script>\n'
        '  <link rel="stylesheet"\n'
        '        href="https://fonts.googleapis.com/css2?'
        "family=JetBrains+Mono:wght@400;600&amp;"
        'family=Syne:wght@400;600;700;800&amp;display=swap">\n'
        "  <style>\n"
        "    *{box-sizing:border-box;margin:0;padding:0}\n"
        "    body{background:#020817;color:#e2e8f0;"
        "font-family:'Syne',sans-serif;line-height:1.6;"
        "min-height:100vh}\n"
        "    .header{background:linear-gradient(135deg,#060d1f 0%,"
        "#0f0a2e 100%);border-bottom:1px solid #0f172a;"
        "padding:24px 48px;display:flex;align-items:center;"
        "justify-content:space-between}\n"
        "    .logo{display:flex;align-items:center;gap:14px}\n"
        "    .logo-icon{width:38px;height:38px;"
        "background:linear-gradient(135deg,#ff4500,#ff8c00);"
        "border-radius:10px;display:flex;align-items:center;"
        "justify-content:center;font-size:20px;"
        "box-shadow:0 0 20px #ff450040}\n"
        "    .logo-text{font-size:1.5rem;font-weight:800;"
        "background:linear-gradient(90deg,#ff6b35 0%,#a78bfa 100%);"
        "-webkit-background-clip:text;-webkit-text-fill-color:"
        "transparent;background-clip:text;letter-spacing:-0.02em}\n"
        "    .header-meta{color:#334155;font-size:0.78rem;"
        "text-align:right;font-family:'JetBrains Mono',monospace}\n"
        "    .main{max-width:1160px;margin:0 auto;padding:40px 48px;"
        "display:flex;flex-direction:column;gap:20px}\n"
        "    .page-title{font-size:2rem;font-weight:800;"
        "color:#f1f5f9;letter-spacing:-0.03em;margin-bottom:4px}\n"
        "    .page-sub{color:#334155;font-size:0.85rem;"
        "font-family:'JetBrains Mono',monospace;margin-bottom:8px}\n"
        "    .card{background:#080f1e;border:1px solid #0f172a;"
        "border-radius:14px;padding:24px}\n"
        "    .section-title{font-size:0.72rem;font-weight:700;"
        "color:#334155;letter-spacing:0.12em;text-transform:uppercase;"
        "margin-bottom:18px;display:flex;align-items:center;gap:8px}\n"
        "    .section-title::before{content:'';width:3px;height:12px;"
        "background:linear-gradient(180deg,#f97316,#6366f1);"
        "border-radius:2px}\n"
        "    footer{border-top:1px solid #080f1e;padding:20px 48px;"
        "text-align:center;color:#1e293b;font-size:0.75rem;"
        "font-family:'JetBrains Mono',monospace}\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        '  <header class="header">\n'
        '    <div class="logo">\n'
        '      <div class="logo-icon">🔥</div>\n'
        '      <span class="logo-text">FlameIQ</span>\n'
        "    </div>\n"
        '    <div class="header-meta">\n'
        "      <div>Performance Report v2.0</div>\n"
        f'      <div style="color:#1e293b;margin-top:2px">{ts}</div>\n'
        "    </div>\n"
        "  </header>\n\n"
        '  <main class="main">\n'
        "    <div>\n"
        f'      <h1 class="page-title">{title}</h1>\n'
        '      <p class="page-sub">flameiq v2.0 · deterministic · '
        "ci-native · offline-safe · no telemetry</p>\n"
        "    </div>\n"
        f"    {overall_badge}\n"
        f"    {comparison_section}\n"
        f"    {corr_section}\n"
        f"    {drift_section}\n"
        f"    {trends_section}\n"
        f"    {history_section}\n"
        "  </main>\n\n"
        "  <footer>FlameIQ OSS v2.0 · Apache 2.0 · "
        "github.com/flameiq/flameiq</footer>\n\n"
        "  <script>\n"
        "    Chart.defaults.color = '#334155';\n"
        "    Chart.defaults.borderColor = '#0f172a';\n"
        f"    {chart_js}"
        "  </script>\n"
        "</body>\n"
        "</html>"
    )
