"""FlameIQ statistical comparison engine.

Provides optional statistical significance testing as a complement to the
threshold-based comparator. Use when benchmark noise is high and you need
confidence that a detected regression is real rather than noise.

Supported methods (v1.0)
------------------------

1. **Mann-Whitney U test** — non-parametric, distribution-free.
   Preferred for latency distributions, which are typically right-skewed.

2. **Median-based noise filter** — warmup-aware, stable central tendency.

All methods are **deterministic** given fixed inputs. No random seeds.

Mathematical specification
--------------------------
See :doc:`/specs/statistical-methodology` for the full specification.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import scipy as sp

from flameiq.core.errors import InsufficientSamplesError

logger = logging.getLogger(__name__)

#: Minimum samples required for any statistical test.
MINIMUM_SAMPLES: int = 3


@dataclass(frozen=True)
class StatisticalResult:
    """Result of a statistical significance test."""

    is_significant: bool
    """True if the difference is statistically significant."""
    p_value: float
    """The test p-value. Lower = stronger evidence."""
    effect_size: float
    """Cohen's *d* effect size. Positive = current > baseline."""
    test_name: str
    """The test used (e.g. ``"Mann-Whitney U"``)."""
    confidence_level: float
    """The confidence level (default 0.95)."""

    @property
    def alpha(self) -> float:
        """Significance threshold α = 1 − confidence_level."""
        return round(1.0 - self.confidence_level, 10)

    @property
    def effect_label(self) -> str:
        """Cohen (1988) verbal label for the effect size magnitude."""
        d = abs(self.effect_size)
        if d < 0.2:
            return "negligible"
        if d < 0.5:
            return "small"
        if d < 0.8:
            return "medium"
        return "large"


def mann_whitney_compare(
    baseline_samples: list[float],
    current_samples: list[float],
    confidence: float = 0.95,
    minimum_samples: int = MINIMUM_SAMPLES,
) -> StatisticalResult:
    """Compare two sample sets using the Mann-Whitney U test.

    Tests the one-tailed hypothesis that the current distribution tends to
    produce **larger** values than the baseline distribution.

    This is the preferred test for latency distributions, which are
    typically right-skewed and non-normal.

    Args:
        baseline_samples: Measurements from the baseline run.
        current_samples:  Measurements from the current run.
        confidence:       Required confidence level. Default 0.95 (95%).
        minimum_samples:  Minimum samples required in each group.

    Returns:
        A :class:`StatisticalResult` with significance, p-value, and effect size.

    Raises:
        :class:`~flameiq.core.errors.InsufficientSamplesError`:
            If either sample set has fewer than ``minimum_samples`` entries.

    References:
        Mann, H. B., & Whitney, D. R. (1947). On a test of whether one of
        two random variables is stochastically larger than the other.
        *Annals of Mathematical Statistics*, 18(1), 50–60.
    """
    if len(baseline_samples) < minimum_samples:
        raise InsufficientSamplesError("baseline", len(baseline_samples), minimum_samples)
    if len(current_samples) < minimum_samples:
        raise InsufficientSamplesError("current", len(current_samples), minimum_samples)

    alpha = 1.0 - confidence
    _, p_value_raw = sp.stats.mannwhitneyu(
        current_samples,
        baseline_samples,
        alternative="greater",
    )
    p_value = float(p_value_raw)
    is_significant = bool(p_value < alpha)
    effect = _cohens_d(baseline_samples, current_samples)

    logger.debug(
        "Mann-Whitney U: p=%.6f significant=%s effect_size=%.4f alpha=%.4f",
        p_value,
        is_significant,
        effect,
        alpha,
    )

    return StatisticalResult(
        is_significant=is_significant,
        p_value=round(p_value, 6),
        effect_size=round(effect, 4),
        test_name="Mann-Whitney U",
        confidence_level=confidence,
    )


def noise_filter_median(samples: list[float], warmup: int = 0) -> float:
    """Compute a noise-resistant median, optionally discarding warmup runs.

    Args:
        samples: Raw measurement samples (any order).
        warmup:  Number of leading samples to discard as warmup. Default 0.

    Returns:
        Median of the remaining samples.

    Raises:
        ValueError: If no samples remain after the warmup discard.

    Notes:
        The median is more robust than the mean for noisy benchmark data
        with occasional outlier spikes.

    Examples::

        noise_filter_median([1.0, 3.0, 5.0])             # → 3.0
        noise_filter_median([99.0, 1.0, 3.0], warmup=1)  # → 2.0
    """
    filtered = samples[warmup:]
    if not filtered:
        raise ValueError(
            f"No samples remain after discarding {warmup} warmup run(s) from {len(samples)} total."
        )
    s = sorted(filtered)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 == 1 else (s[mid - 1] + s[mid]) / 2.0


def _cohens_d(group1: list[float], group2: list[float]) -> float:
    """Compute Cohen's *d* effect size.

    Cohen's d = (mean₂ − mean₁) / pooled_std

    Positive values indicate group2 > group1 (current > baseline).
    Returns ``0.0`` if pooled standard deviation is zero.

    References:
        Cohen, J. (1988). *Statistical Power Analysis for the Behavioral
        Sciences* (2nd ed.). Erlbaum.
    """
    n1, n2 = len(group1), len(group2)
    mean1 = sum(group1) / n1
    mean2 = sum(group2) / n2
    var1 = (sum((x - mean1) ** 2 for x in group1) / (n1 - 1)) if n1 > 1 else 0.0
    var2 = (sum((x - mean2) ** 2 for x in group2) / (n2 - 1)) if n2 > 1 else 0.0
    pooled_std = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if pooled_std == 0.0:
        return 0.0
    return (mean2 - mean1) / pooled_std
