"""flameiq run — load and validate a metrics snapshot."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from flameiq.providers.registry import get_provider, list_providers


@click.command()
@click.option(
    "--metrics", "-m", required=True, type=click.Path(exists=True), help="Path to the metrics file."
)
@click.option(
    "--provider",
    "-p",
    default="json",
    show_default=True,
    help=f"Metric provider. Available: {', '.join(list_providers())}",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Write normalised snapshot to this path.",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
@click.pass_context
def run(
    ctx: click.Context,
    metrics: str,
    provider: str,
    output: str | None,
    as_json: bool,
) -> None:
    """Load and validate a metrics snapshot.

    \b
    Exit codes:
      0  Snapshot loaded and validated successfully.
      3  Metrics file is invalid or cannot be parsed.
    """
    try:
        snapshot = get_provider(provider).load(metrics)
    except Exception as exc:
        if as_json:
            click.echo(json.dumps({"status": "error", "message": str(exc)}))
        else:
            click.echo(click.style(f"Error: {exc}", fg="red"), err=True)
        sys.exit(3)

    if output:
        Path(output).write_text(
            json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    flat = snapshot.metrics.flat()
    if as_json:
        click.echo(
            json.dumps(
                {
                    "status": "ok",
                    "schema_version": snapshot.schema_version,
                    "commit": snapshot.metadata.commit,
                    "metrics_count": len(flat),
                    "metrics": flat,
                },
                indent=2,
            )
        )
    else:
        click.echo(
            click.style("✓ Snapshot loaded", fg="green", bold=True) + f" via provider '{provider}'"
        )
        click.echo(f"  Commit:  {snapshot.metadata.commit or '(none)'}")
        click.echo(f"  Metrics: {len(flat)} value(s)")
        for k, v in flat.items():
            click.echo(f"    {k:<24} {v:.4f}")
