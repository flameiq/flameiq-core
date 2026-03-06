"""flameiq validate — validate a metrics file against the FlameIQ schema."""

from __future__ import annotations

import json
import sys

import click

from flameiq.providers.registry import get_provider, list_providers


@click.command()
@click.argument("metrics_file", type=click.Path(exists=True))
@click.option(
    "--provider", "-p", default="json", show_default=True, help="Provider to use for validation."
)
@click.option(
    "--list-providers",
    "show_providers",
    is_flag=True,
    default=False,
    help="List all available providers and exit.",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def validate(
    metrics_file: str,
    provider: str,
    show_providers: bool,
    as_json: bool,
) -> None:
    r"""Validate a metrics file against the FlameIQ v1 schema.

    \b
    Exit codes:
      0  File is valid.
      3  File is invalid.
    """
    if show_providers:
        providers = list_providers()
        if as_json:
            click.echo(json.dumps({"providers": providers}))
        else:
            click.echo(click.style("Available providers:", bold=True))
            for p in providers:
                click.echo(f"  • {p}")
        return

    try:
        snapshot = get_provider(provider).load(metrics_file)
        flat = snapshot.metrics.flat()
        if as_json:
            click.echo(
                json.dumps(
                    {
                        "valid": True,
                        "schema_version": snapshot.schema_version,
                        "metrics_count": len(flat),
                    }
                )
            )
        else:
            click.echo(
                click.style("✓ Valid", fg="green", bold=True)
                + f" — {len(flat)} metric(s) found in '{metrics_file}'"
            )
    except Exception as exc:
        if as_json:
            click.echo(json.dumps({"valid": False, "error": str(exc)}))
        else:
            click.echo(
                click.style("✗ Invalid: ", fg="red", bold=True) + str(exc),
                err=True,
            )
        sys.exit(3)
