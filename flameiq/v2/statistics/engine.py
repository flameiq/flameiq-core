"""FlameIQ v2 Statistics Engine.

Deterministic, stdlib-only statistical methods.

All algorithms documented. No external dependencies.
Same input → same output guaranteed.

Methods:
  percent_change()         — signed % change
  mann_whitney_u()         — non-parametric significance test
  bootstrap_mean_ci()      — bootstrap confidence interval (deterministic)
  cohens_d()               — standardized effect size
  variance_ratio()         — stability comparison
  detect_drift()           — linear regression slope on time series
  summarize()              — descriptive statistics
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# ── Percent change ─────────────────────────────────────────────────────────────


def percent_change(baseline: float, current: float) -> float:
    """Signed percent change from baseline to current.

    Positive = increase (worse for latency).
    Negative = decrease (worse for throughput).
    Returns 0.0 if baseline == 0.
    """
    if baseline == 0.0:
        return 0.0
    return ((current - baseline) / abs(baseline)) * 100.0


# ── Mann-Whitney U ─────────────────────────────────────────────────────────────


def mann_whitney_u(x: Sequence[float], y: Sequence[float]) -> tuple[float, float]:
    """Non-parametric Mann-Whitney U test.

    Does NOT assume normal distribution — appropriate for benchmark data.

    Returns (U_statistic, p_value).
    p < 0.05 → statistically significant difference at 95% confidence.

    Algorithm: exact U statistic + normal approximation for p-value.
    Reference: Mann & Whitney (1947), Asymptotic theory of rank tests.

    Time complexity: O(n*m). Use normal approx for large n, m.
    """
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0

    u1 = sum(1.0 if xi > yj else 0.5 if xi == yj else 0.0 for xi in x for yj in y)
    u2 = n1 * n2 - u1
    u_stat = min(u1, u2)

    # Normal approximation (valid for n1,n2 >= 8; conservative for smaller)
    mean_u = n1 * n2 / 2.0
    std_u = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12.0)
    if std_u == 0:
        return u_stat, 1.0

    z = (u_stat - mean_u) / std_u
    # Two-tailed p-value via complementary error function
    p_value = 2.0 * (1.0 - _normal_cdf(abs(z)))
    return u_stat, max(1e-10, min(1.0, p_value))


def _normal_cdf(z: float) -> float:
    """Standard normal CDF via math.erf (stdlib)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# ── Bootstrap CI ──────────────────────────────────────────────────────────────


def bootstrap_mean_ci(
    samples: Sequence[float],
    confidence: float = 0.95,
    iterations: int = 1000,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap confidence interval for the mean.

    DETERMINISTIC: fixed seed guarantees reproducibility across runs.

    Args:
        samples:    Input data points.
        confidence: Confidence level (default 0.95).
        iterations: Bootstrap resamples (default 1000).
        seed:       RNG seed for reproducibility.

    Returns:
        (lower_bound, upper_bound) of the confidence interval.
    """
    n = len(samples)
    if n == 0:
        return 0.0, 0.0
    if n == 1:
        return float(samples[0]), float(samples[0])

    rng = random.Random(seed)
    sample_list = list(samples)
    boot_means: list[float] = []

    for _ in range(iterations):
        resample = [rng.choice(sample_list) for _ in range(n)]
        boot_means.append(sum(resample) / n)

    boot_means.sort()
    alpha = 1.0 - confidence
    lo_idx = max(0, int(alpha / 2 * iterations))
    hi_idx = min(iterations - 1, int((1 - alpha / 2) * iterations) - 1)
    return boot_means[lo_idx], boot_means[hi_idx]


# ── Cohen's d ─────────────────────────────────────────────────────────────────


def cohens_d(baseline: Sequence[float], current: Sequence[float]) -> float:
    r"""Cohen's d: standardized effect size.

    Interpretation:
        ``|d|`` < 0.2  negligible
        0.2 - 0.5      small
        0.5 - 0.8      medium
        > 0.8          large

    Uses pooled standard deviation.
    """
    n1, n2 = len(baseline), len(current)
    if n1 < 2 or n2 < 2:
        return 0.0

    m1 = sum(baseline) / n1
    m2 = sum(current) / n2
    v1 = sum((x - m1) ** 2 for x in baseline) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in current) / (n2 - 1)
    pooled_var = ((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)
    pooled = math.sqrt(max(0.0, pooled_var))

    if pooled == 0:
        # Zero variance: if means differ it is an infinite effect; return sign × large value
        diff = m2 - m1
        if diff == 0:
            return 0.0
        return math.copysign(999.0, diff)
    return (m2 - m1) / pooled


def effect_label(d: float) -> str:
    """Interpret Cohen's d as a qualitative effect size label."""
    ad = abs(d)
    if ad < 0.2:
        return "negligible"
    if ad < 0.5:
        return "small"
    if ad < 0.8:
        return "medium"
    return "large"


# ── Variance ratio ────────────────────────────────────────────────────────────


def variance_ratio(baseline: Sequence[float], current: Sequence[float]) -> float:
    """Ratio of current variance to baseline variance. > 1 = noisier."""

    def _var(s: Sequence[float]) -> float:
        n = len(s)
        if n < 2:
            return 0.0
        m = sum(s) / n
        return sum((x - m) ** 2 for x in s) / (n - 1)

    bv = _var(baseline)
    cv = _var(current)
    return (cv / bv) if bv > 0 else 1.0


# ── Drift detection ───────────────────────────────────────────────────────────


@dataclass
class DriftResult:
    """Result of drift detection analysis over a time series.

    Attributes:
        slope: Change per run in absolute units.
        slope_percent: Slope as percentage of first value.
        cumulative_change: Total absolute change over all runs.
        cumulative_percent: Total change as percentage of first value.
        is_drifting: True if drift detected (based on threshold and R²).
        confidence: R² coefficient of determination (0-1, higher = better fit).
        run_count: Number of data points analyzed.
        direction: "worsening", "improving", or "stable".
    """

    slope: float  # change per run
    slope_percent: float  # slope as % of first value
    cumulative_change: float
    cumulative_percent: float
    is_drifting: bool
    confidence: float  # R² of linear fit
    run_count: int
    direction: str  # "worsening" | "improving" | "stable"


def detect_drift(
    values: Sequence[float],
    drift_threshold_percent: float = 5.0,
    min_runs: int = 5,
) -> DriftResult:
    """Linear regression on a time series to detect gradual performance drift.

    Flags drift when:
        1. Cumulative change ≥ drift_threshold_percent
        2. R² ≥ 0.30 (linear fit explains 30%+ of variance)
        3. At least min_runs data points

    This catches slow regressions that never trigger single-run thresholds.

    Args:
        values:                  Time-ordered metric values.
        drift_threshold_percent: Minimum cumulative % change to flag.
        min_runs:                Minimum data points required.

    Returns:
        DriftResult with slope, cumulative change, R², direction.
    """
    n = len(values)
    if n < min_runs:
        return DriftResult(0.0, 0.0, 0.0, 0.0, False, 0.0, n, "stable")

    xs = list(range(n))
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n

    ss_xy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values, strict=False))
    ss_xx = sum((x - x_mean) ** 2 for x in xs)
    ss_yy = sum((y - y_mean) ** 2 for y in values)

    slope = ss_xy / ss_xx if ss_xx != 0 else 0.0
    intercept = y_mean - slope * x_mean

    # R² coefficient of determination
    if ss_yy == 0:
        r_sq = 1.0
    else:
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, values, strict=False))
        r_sq = max(0.0, 1.0 - ss_res / ss_yy)

    cumulative = slope * (n - 1)
    first = values[0] if values[0] != 0 else 1.0
    slope_pct = (slope / abs(first)) * 100.0
    cumul_pct = (cumulative / abs(first)) * 100.0

    is_drifting = abs(cumul_pct) >= drift_threshold_percent and r_sq >= 0.30

    if not is_drifting:
        direction = "stable"
    elif cumul_pct > 0:
        direction = "worsening"
    else:
        direction = "improving"

    return DriftResult(
        slope=slope,
        slope_percent=slope_pct,
        cumulative_change=cumulative,
        cumulative_percent=cumul_pct,
        is_drifting=is_drifting,
        confidence=r_sq,
        run_count=n,
        direction=direction,
    )


# ── Descriptive statistics ────────────────────────────────────────────────────


def summarize(values: Sequence[float]) -> dict[str, float]:
    """Compute descriptive stats for a sample list."""
    if not values:
        return {}
    n = len(values)
    sv = sorted(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n if n > 1 else 0.0
    return {
        "count": float(n),
        "mean": round(mean, 6),
        "median": round(_pct(sv, 50), 6),
        "p95": round(_pct(sv, 95), 6),
        "p99": round(_pct(sv, 99), 6),
        "min": sv[0],
        "max": sv[-1],
        "std": round(math.sqrt(variance), 6),
    }


def _pct(sv: list[float], p: float) -> float:
    if not sv:
        return 0.0
    idx = (p / 100) * (len(sv) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sv) - 1)
    return sv[lo] * (1 - (idx - lo)) + sv[hi] * (idx - lo)
