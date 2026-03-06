"""FlameIQ CLI entry point.

The CLI is the top-level consumer of all FlameIQ layers.
No business logic lives here — it parses arguments and delegates.

Entry point: ``flameiq`` (configured in pyproject.toml)
"""

from __future__ import annotations

import logging
import sys

import click

from flameiq import __version__
from flameiq.cli.commands.baseline import baseline
from flameiq.cli.commands.compare import compare
from flameiq.cli.commands.init import init
from flameiq.cli.commands.report import report
from flameiq.cli.commands.run import run
from flameiq.cli.commands.validate import validate


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


@click.group()
@click.version_option(version=__version__, prog_name="flameiq")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose/debug logging.",
)
@click.option(
    "--config",
    type=click.Path(),
    default="flameiq.yaml",
    show_default=True,
    envvar="FLAMEIQ_CONFIG",
    help="Path to flameiq.yaml configuration file.",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: str) -> None:
    """FlameIQ — deterministic, CI-native performance regression engine.

    \b
    Make performance a first-class, enforceable engineering signal.
    No SaaS. No accounts. No network. Fully offline. Fully deterministic.

    \b
    Quick start:
      flameiq init
      flameiq baseline set --metrics benchmark.json
      flameiq compare --metrics current.json --fail-on-regression
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config"] = config
    _setup_logging(verbose)


cli.add_command(init)
cli.add_command(run)
cli.add_command(compare)
cli.add_command(baseline)
cli.add_command(report)
cli.add_command(validate)


def main() -> None:
    """Package entry point."""
    cli(auto_envvar_prefix="FLAMEIQ")


if __name__ == "__main__":
    main()
