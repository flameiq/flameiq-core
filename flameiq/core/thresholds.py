"""FlameIQ threshold configuration and evaluation.

Thresholds are specified in ``flameiq.yaml`` as percent strings::

    thresholds:
      latency.p95:  10%     # Allow up to 10% latency increase
      throughput:   -5%     # Allow up to 5% throughput decrease
      memory_mb:     8%     # Allow up to 8% memory increase

**Sign convention:**

- Positive threshold (e.g. ``10%``) → allow up to +10% increase.
- Negative threshold (e.g. ``-5%``) → allow up to 5% decrease.
- For known metrics the direction is inferred automatically
  (see :func:`evaluate_threshold`).

**Default threshold:** 10% in either direction for unknown metrics.
"""

from __future__ import annotations

import re

from flameiq.core.errors import ThresholdConfigError

# Regex that matches "10%", "-5%", "2.5%"
_PERCENT_RE = re.compile(r"^(-?\d+(?:\.\d+)?)%$")

#: Default allowance applied when no explicit threshold is configured.
DEFAULT_THRESHOLD_PERCENT: float = 10.0

# Metrics where an *increase* is a regression signal.
_HIGHER_IS_WORSE: frozenset[str] = frozenset(
    {
        "latency.mean",
        "latency.p50",
        "latency.p95",
        "latency.p99",
        "memory_mb",
        "cpu_percent",
    }
)

# Metrics where a *decrease* is a regression signal.
_LOWER_IS_WORSE: frozenset[str] = frozenset(
    {
        "throughput",
    }
)


def parse_threshold(key: str, raw: str | float | int) -> float:
    """Parse a raw threshold value into a signed float.

    Args:
        key: Metric key (used only for error messages).
        raw: A percent string (``"10%"``, ``"-5%"``) or a numeric value.

    Returns:
        Float percentage, e.g. ``10.0`` or ``-5.0``.

    Raises:
        :class:`~flameiq.core.errors.ThresholdConfigError`: If the
            string is not a valid percent.

    Examples::

        parse_threshold("latency.p95", "10%")  # → 10.0
        parse_threshold("throughput",  "-5%")  # → -5.0
        parse_threshold("memory_mb",   10.0)   # → 10.0
    """
    if isinstance(raw, (int, float)):
        return float(raw)
    m = _PERCENT_RE.match(str(raw).strip())
    if not m:
        raise ThresholdConfigError(key, str(raw), "must be a percent string like '10%' or '-5%'")
    return float(m.group(1))


def evaluate_threshold(
    metric_key: str,
    change_percent: float,
    threshold_percent: float,
) -> bool:
    """Determine whether a ``change_percent`` breaches its threshold.

    Direction semantics:

    - **Higher-is-worse** metrics (``latency.*``, ``memory_mb``,
      ``cpu_percent``): a regression is ``change_percent > +threshold``.
    - **Lower-is-worse** metrics (``throughput``): a regression is
      ``change_percent < -abs(threshold)``.
    - **Unknown / custom** metrics: any absolute deviation beyond the
      threshold is flagged as a regression.

    Args:
        metric_key:        Dotted metric name.
        change_percent:    Signed percent change (positive = increased).
        threshold_percent: The configured threshold float.

    Returns:
        ``True`` if the change is a regression.
    """
    if metric_key in _HIGHER_IS_WORSE:
        return change_percent > abs(threshold_percent)
    if metric_key in _LOWER_IS_WORSE:
        return change_percent < -abs(threshold_percent)
    # Unknown / custom: absolute deviation
    return abs(change_percent) > abs(threshold_percent)


def build_threshold_map(raw_config: dict[str, str | float]) -> dict[str, float]:
    """Parse a full threshold config dict into float values.

    Args:
        raw_config: Raw mapping from ``flameiq.yaml``, e.g.
            ``{"latency.p95": "10%", "throughput": "-5%"}``.

    Returns:
        Parsed mapping of metric key → float threshold.

    Raises:
        :class:`~flameiq.core.errors.ThresholdConfigError`: If any value
            is invalid.
    """
    return {key: parse_threshold(key, val) for key, val in raw_config.items()}
