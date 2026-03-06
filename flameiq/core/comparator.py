"""FlameIQ deterministic comparison engine.

This is the most critical module in the codebase. It compares a current
:class:`~flameiq.schema.v1.models.PerformanceSnapshot` against a baseline
and produces a :class:`~flameiq.core.models.ComparisonResult`.

Determinism guarantee
---------------------
Given identical inputs this module **always** produces identical outputs.

- No randomness of any kind.
- No ``datetime.now()`` calls.
- No network I/O.
- Floating-point arithmetic is explicit and documented.
- All rounding uses Python's built-in ``round()`` with fixed precision.

Floating-point policy
---------------------
``change_percent`` is computed as::

    ((current - baseline) / baseline) * 100

rounded to **4 decimal places** for stable threshold comparisons.
Division by zero is guarded — if ``baseline == 0`` the metric is skipped
with a warning and a :class:`~flameiq.core.errors.ComparisonError`
is raised internally (caught and logged).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flameiq.core.errors import ComparisonError
from flameiq.core.models import ComparisonResult, MetricDiff, RegressionStatus
from flameiq.core.thresholds import (
    DEFAULT_THRESHOLD_PERCENT,
    build_threshold_map,
    evaluate_threshold,
)

if TYPE_CHECKING:
    from flameiq.schema.v1.models import PerformanceSnapshot

logger = logging.getLogger(__name__)

# Decimal places for change_percent — do not change without an RFC.
_CHANGE_PERCENT_PRECISION: int = 4

# A metric must be within this many percentage points of its threshold
# to trigger a WARNING (rather than PASS).
_WARNING_MARGIN_PERCENT: float = 5.0


def compute_change_percent(baseline: float, current: float) -> float:
    """Compute the signed percentage change from *baseline* to *current*.

    Formula::

        ((current - baseline) / baseline) * 100

    Rounded to :data:`_CHANGE_PERCENT_PRECISION` decimal places.

    Args:
        baseline: Reference value. Must be non-zero.
        current:  Measured value.

    Returns:
        Signed percentage change, rounded to 4 d.p.
        Positive means current is larger than baseline.

    Raises:
        :class:`~flameiq.core.errors.ComparisonError`: If ``baseline``
            is exactly zero.

    Examples::

        compute_change_percent(100.0, 110.0)  # →  10.0
        compute_change_percent(100.0,  90.0)  # → -10.0
        compute_change_percent(100.0, 100.0)  # →   0.0
    """
    if baseline == 0.0:
        raise ComparisonError(
            f"Cannot compute percent change: baseline value is zero "
            f"(current={current}). Metric will be skipped."
        )
    raw = ((current - baseline) / baseline) * 100.0
    return round(raw, _CHANGE_PERCENT_PRECISION)


def compare_snapshots(
    baseline: PerformanceSnapshot,
    current: PerformanceSnapshot,
    threshold_config: dict[str, str | float] | None = None,
    warning_margin_percent: float = _WARNING_MARGIN_PERCENT,
) -> ComparisonResult:
    """Compare *current* against *baseline* and return a full diff.

    For every metric present in the baseline, the engine:

    1. Computes ``change_percent`` via :func:`compute_change_percent`.
    2. Looks up the configured threshold (or applies the default).
    3. Calls :func:`~flameiq.core.thresholds.evaluate_threshold` to
       determine pass / warning / regression.

    Metrics present in *current* but absent from *baseline* are ignored —
    they have no reference value and cannot regress.

    Args:
        baseline:               The reference snapshot.
        current:                The snapshot under evaluation.
        threshold_config:       Raw threshold dict from ``flameiq.yaml``,
                                e.g. ``{"latency.p95": "10%"}``.
                                Falls back to defaults if ``None``.
        warning_margin_percent: Distance from threshold that triggers a
                                WARNING instead of PASS.

    Returns:
        A :class:`~flameiq.core.models.ComparisonResult` with complete
        per-metric diffs and an overall :class:`~flameiq.core.models.RegressionStatus`.
    """
    thresholds = build_threshold_map(threshold_config or {})
    baseline_flat = baseline.metrics.flat()
    current_flat = current.metrics.flat()

    diffs: list[MetricDiff] = []
    any_regression = False

    for metric_key in sorted(baseline_flat.keys()):
        baseline_value = baseline_flat[metric_key]
        current_value = current_flat.get(metric_key)

        if current_value is None:
            logger.warning(
                "Metric '%s' in baseline but missing from current — skipped.",
                metric_key,
            )
            continue

        try:
            change_pct = compute_change_percent(baseline_value, current_value)
        except ComparisonError as exc:
            logger.warning("Skipping metric '%s': %s", metric_key, exc)
            continue

        threshold = thresholds.get(metric_key, DEFAULT_THRESHOLD_PERCENT)
        is_regression = evaluate_threshold(metric_key, change_pct, threshold)

        # Warn if approaching threshold (but not yet breaching it)
        is_warning = (
            not is_regression
            and abs(change_pct) >= abs(threshold) - warning_margin_percent
            and abs(change_pct) > 0
        )

        diff = MetricDiff(
            metric_key=metric_key,
            baseline_value=baseline_value,
            current_value=current_value,
            change_percent=change_pct,
            threshold_percent=threshold,
            is_regression=is_regression,
            is_warning=is_warning,
        )
        diffs.append(diff)

        if is_regression:
            any_regression = True
            logger.info(
                "REGRESSION: %s changed %+.2f%% (threshold: %.1f%%)",
                metric_key,
                change_pct,
                threshold,
            )

    status = RegressionStatus.REGRESSION if any_regression else RegressionStatus.PASS

    regression_keys = [d.metric_key for d in diffs if d.is_regression]
    summary = (
        f"{len(regression_keys)} regression(s) in: {', '.join(regression_keys)}"
        if regression_keys
        else f"All {len(diffs)} metric(s) within threshold."
    )

    return ComparisonResult(
        status=status,
        diffs=diffs,
        baseline_commit=baseline.metadata.commit,
        current_commit=current.metadata.commit,
        statistical_mode=False,
        summary=summary,
    )
