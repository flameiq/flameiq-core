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
from flameiq.v2.cli.main import v2_grp

_v1_available = False

try:
    from flameiq.cli.commands.baseline import baseline
    from flameiq.cli.commands.compare import compare
    from flameiq.cli.commands.init import init
    from flameiq.cli.commands.report import report
    from flameiq.cli.commands.run import run
    from flameiq.cli.commands.validate import validate

    _v1_available = True
except (ImportError, Exception):
    pass


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


@click.group()  # type: ignore[misc]
@click.version_option(version=__version__, prog_name="flameiq")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose/debug logging.",
)
@click.option(  # type: ignore[misc]
    "--config",
    type=click.Path(),
    default="flameiq.yaml",
    show_default=True,
    envvar="FLAMEIQ_CONFIG",
    help="Path to flameiq.yaml configuration file.",
)
@click.pass_context  # type: ignore[misc]
def cli(ctx: click.Context, verbose: bool, config: str) -> None:
    r"""FlameIQ — deterministic, CI-native performance regression engine.

    \b
    Make performance a first-class, enforceable engineering signal.

    \b
    v1 quick start:
      flameiq init
      flameiq baseline set --metrics benchmark.json
      flameiq compare --metrics current.json --fail-on-regression

    \b
    v2 quick start:
      flameiq v2 run --metrics benchmark.json
      flameiq v2 baseline set
      flameiq v2 compare
      flameiq v2 trend --metric latency.p95 --last 30
      flameiq v2 drift
      flameiq v2 report
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config"] = config
    _setup_logging(verbose)


cli.add_command(v2_grp)

if _v1_available:
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
