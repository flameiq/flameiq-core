"""FlameIQ baseline selection strategies.

A *baseline strategy* determines which historical snapshot is used as
the reference point for a comparison run.

v1.0 supports three strategies:

``last_successful``
    Use the most recently stored snapshot. Simple and predictable.

``rolling_median``
    Compute median values over the last *N* snapshots. More resistant
    to noise from a single outlier run.

``tagged``
    Use a snapshot explicitly tagged with a release label (e.g. ``"v1.0.0"``).
    Useful for comparing against a known-good release.

Configuration in ``flameiq.yaml``::

    baseline:
      strategy: rolling_median
      rolling_window: 5
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

from flameiq.core.errors import BaselineError
from flameiq.engine.statistics import noise_filter_median

if TYPE_CHECKING:
    from flameiq.schema.v1.models import PerformanceSnapshot

logger = logging.getLogger(__name__)


class BaselineStrategy(str, Enum):
    """Supported baseline selection strategies."""

    LAST_SUCCESSFUL = "last_successful"
    ROLLING_MEDIAN = "rolling_median"
    TAGGED = "tagged"


def select_baseline(
    history: list[PerformanceSnapshot],
    strategy: BaselineStrategy = BaselineStrategy.LAST_SUCCESSFUL,
    rolling_window: int = 5,
    tag: str | None = None,
) -> PerformanceSnapshot:
    """Select a baseline from the history using the configured strategy.

    Args:
        history:        List of stored snapshots, **oldest first**.
        strategy:       Which selection strategy to apply.
        rolling_window: Window size for ``ROLLING_MEDIAN`` strategy.
        tag:            Required when strategy is ``TAGGED``.

    Returns:
        The selected (or synthesised) baseline snapshot.

    Raises:
        :class:`~flameiq.core.errors.BaselineError`: If history is empty
            or a tagged snapshot cannot be found.
    """
    if not history:
        raise BaselineError(
            "No baseline history available. Run: flameiq baseline set --metrics <file>"
        )

    if strategy == BaselineStrategy.LAST_SUCCESSFUL:
        return _last_successful(history)
    if strategy == BaselineStrategy.ROLLING_MEDIAN:
        return _rolling_median(history, rolling_window)
    if strategy == BaselineStrategy.TAGGED:
        if not tag:
            raise BaselineError("Strategy 'tagged' requires --tag <label>.")
        return _tagged(history, tag)

    raise BaselineError(f"Unknown baseline strategy: '{strategy}'")  # pragma: no cover


# ---------------------------------------------------------------------------
# Strategy implementations
# ---------------------------------------------------------------------------


def _last_successful(
    history: list[PerformanceSnapshot],
) -> PerformanceSnapshot:
    return history[-1]


def _rolling_median(
    history: list[PerformanceSnapshot],
    window: int,
) -> PerformanceSnapshot:
    """Synthesise a baseline from the median of the last *window* snapshots."""
    from flameiq.schema.v1.models import (
        LatencyMetrics,
        Metrics,
        PerformanceSnapshot,
        SnapshotMetadata,
    )

    window_snaps = history[-window:]
    logger.debug("Rolling median: %d/%d snapshots in window", len(window_snaps), window)

    # Collect all values per flat key
    samples: dict[str, list[float]] = {}
    for snap in window_snaps:
        for key, val in snap.metrics.flat().items():
            samples.setdefault(key, []).append(val)

    medians: dict[str, float] = {key: noise_filter_median(vals) for key, vals in samples.items()}

    # Reconstruct Metrics from medians
    lat_keys = {k.split(".")[1]: v for k, v in medians.items() if k.startswith("latency.")}
    latency = LatencyMetrics(**lat_keys) if lat_keys else None

    metrics = Metrics(
        latency=latency,
        throughput=medians.get("throughput"),
        memory_mb=medians.get("memory_mb"),
        cpu_percent=medians.get("cpu_percent"),
        custom={
            k.removeprefix("custom."): v for k, v in medians.items() if k.startswith("custom.")
        },
    )

    ref = window_snaps[-1]
    metadata = SnapshotMetadata(
        commit=ref.metadata.commit,
        branch=ref.metadata.branch,
        environment=ref.metadata.environment,
        tags={**ref.metadata.tags, "flameiq_synthetic": "rolling_median"},
    )

    return PerformanceSnapshot(
        schema_version=1,
        metadata=metadata,
        metrics=metrics,
    )


def _tagged(
    history: list[PerformanceSnapshot],
    tag: str,
) -> PerformanceSnapshot:
    """Find the most recent snapshot whose tags dict contains *tag* as a value."""
    for snap in reversed(history):
        if tag in snap.metadata.tags.values():
            logger.debug("Found tagged baseline: tag=%r commit=%s", tag, snap.metadata.commit)
            return snap
    raise BaselineError(
        f"No baseline snapshot found with tag '{tag}'. "
        f"Set one with: flameiq baseline set --tag {tag} --metrics <file>"
    )
