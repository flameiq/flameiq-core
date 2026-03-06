"""flameiq init — initialise FlameIQ in the current project."""

from __future__ import annotations

from pathlib import Path

import click

_DEFAULT_CONFIG = """\
# flameiq.yaml — FlameIQ configuration
# Docs: https://docs.flameiq.dev/guides/configuration.html

# ── Regression thresholds ─────────────────────────────────────────────
# Format: "<metric_key>: <percent>"
# Positive = allow up to N% increase (latency, memory)
# Negative = allow up to N% decrease (throughput)
thresholds:
  latency.p95:   10%
  latency.p99:   15%
  throughput:    -5%
  memory_mb:      8%

# ── Baseline strategy ─────────────────────────────────────────────────
baseline:
  strategy: rolling_median     # last_successful | rolling_median | tagged
  rolling_window: 5

# ── Statistical significance (optional) ───────────────────────────────
statistics:
  enabled: false
  confidence: 0.95

# ── Noise tolerance ───────────────────────────────────────────────────
noise:
  warmup_runs: 0

# ── Default metric provider ───────────────────────────────────────────
provider: json                 # json | pytest-benchmark
"""

_GITIGNORE_BLOCK = "\n# FlameIQ — do not commit baselines\n.flameiq/baselines/\n"


@click.command()
@click.option("--force", "-f", is_flag=True, default=False, help="Overwrite existing flameiq.yaml.")
@click.pass_context
def init(ctx: click.Context, force: bool) -> None:
    """Initialise FlameIQ in the current project.

    Creates flameiq.yaml and the .flameiq/ storage directory.
    Updates .gitignore if present.

    \b
    Exit codes:
      0  Initialised successfully.
    """
    config_path = Path(ctx.obj.get("config", "flameiq.yaml"))

    # Create .flameiq/baselines/
    baselines_dir = Path(".flameiq") / "baselines"
    baselines_dir.mkdir(parents=True, exist_ok=True)
    click.echo(click.style("✓", fg="green") + " Created .flameiq/")

    # Write flameiq.yaml
    if config_path.exists() and not force:
        click.echo(
            click.style("!", fg="yellow")
            + f" {config_path} already exists (use --force to overwrite)."
        )
    else:
        config_path.write_text(_DEFAULT_CONFIG, encoding="utf-8")
        click.echo(click.style("✓", fg="green") + f" Created {config_path}")

    # Update .gitignore
    gi = Path(".gitignore")
    if gi.exists():
        content = gi.read_text(encoding="utf-8")
        if ".flameiq" not in content:
            gi.write_text(content + _GITIGNORE_BLOCK, encoding="utf-8")
            click.echo(click.style("✓", fg="green") + " Updated .gitignore")

    click.echo("")
    click.echo(click.style("FlameIQ initialised.", bold=True))
    click.echo("Next steps:")
    click.echo("  1. Run your benchmarks and produce a metrics JSON file.")
    click.echo("  2. flameiq baseline set --metrics benchmark.json")
    click.echo("  3. flameiq compare --metrics current.json --fail-on-regression")
