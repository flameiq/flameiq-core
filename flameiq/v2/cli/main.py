"""FlameIQ v2 CLI main entry point.

All v2 commands are registered here and exposed under the main `flameiq` group.
v2 commands coexist with v1 commands — the CLI is backward compatible.
"""

from __future__ import annotations

import click

from flameiq.v2.cli.baseline_cmd import baseline_grp_v2
from flameiq.v2.cli.compare_cmd import compare_cmd_v2
from flameiq.v2.cli.drift_cmd import drift_cmd
from flameiq.v2.cli.report_cmd import report_cmd_v2
from flameiq.v2.cli.run_cmd import run_cmd_v2
from flameiq.v2.cli.trend_cmd import history_cmd, trend_cmd


@click.group("v2")  # type: ignore[misc]
def v2_grp() -> None:
    r"""FlameIQ v2 — performance evolution intelligence.

    \b
    v2 extends v1 with:
      • Persistent local run history (SQLite)
      • Time-travel commit comparison
      • Gradual drift detection
      • Performance budget enforcement
      • Multi-metric correlation analysis
      • Rich offline HTML reports

    \b
    Quick start:
      flameiq v2 run --metrics benchmark.json
      flameiq v2 baseline set
      flameiq v2 compare
      flameiq v2 trend --metric latency.p95 --last 30
      flameiq v2 drift
      flameiq v2 report
    """


v2_grp.add_command(run_cmd_v2, name="run")
v2_grp.add_command(compare_cmd_v2, name="compare")
v2_grp.add_command(baseline_grp_v2, name="baseline")
v2_grp.add_command(trend_cmd, name="trend")
v2_grp.add_command(history_cmd, name="history")
v2_grp.add_command(drift_cmd, name="drift")
v2_grp.add_command(report_cmd_v2, name="report")


__all__ = [
    "v2_grp",
    "run_cmd_v2",
    "compare_cmd_v2",
    "baseline_grp_v2",
    "trend_cmd",
    "history_cmd",
    "drift_cmd",
    "report_cmd_v2",
]
