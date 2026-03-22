"""FlameIQ v2 Regression Engine.

Deterministic threshold-based and statistical regression detection.

Pipeline:
  1. Flatten both runs to dot-notation metric dicts
  2. Compute percent change per metric
  3. Apply threshold gates
  4. Check budget ceilings
  5. (Optional) Mann-Whitney U statistical significance test
  6. Return structured ComparisonResult with exit code
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flameiq.v2.schema import RunV2

from flameiq.v2.statistics.engine import (
    bootstrap_mean_ci,
    cohens_d,
    effect_label,
    mann_whitney_u,
    percent_change,
)

# Exit codes — never change these, CI depends on them
EXIT_PASS = 0
EXIT_REGRESSION = 1
EXIT_CONFIG_ERROR = 2
EXIT_INVALID_METRICS = 3
EXIT_BUDGET_BREACH = 4
EXIT_DRIFT_DETECTED = 5


@dataclass
class MetricResult:
    """Result of comparing one metric between baseline and current run."""

    metric: str
    baseline_value: float
    current_value: float
    change_percent: float
    threshold_percent: float | None
    budget_value: float | None
    threshold_breached: bool
    budget_breached: bool
    status: str  # "pass" | "regression" | "budget_breach"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict representation."""
        return {
            "metric": self.metric,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "change_percent": round(self.change_percent, 4),
            "threshold_percent": self.threshold_percent,
            "budget_value": self.budget_value,
            "threshold_breached": self.threshold_breached,
            "budget_breached": self.budget_breached,
            "status": self.status,
        }


@dataclass
class StatDetail:
    """Statistical significance details for a metric from Mann-Whitney U test."""

    metric: str
    p_value: float
    significant: bool
    effect_size: float
    effect_label: str
    ci_lower: float
    ci_upper: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict representation."""
        return {
            "metric": self.metric,
            "p_value": round(self.p_value, 6),
            "significant": self.significant,
            "effect_size": round(self.effect_size, 4),
            "effect_label": self.effect_label,
            "ci_lower": round(self.ci_lower, 4),
            "ci_upper": round(self.ci_upper, 4),
        }


@dataclass
class ComparisonResult:
    """Complete result of comparing baseline and current runs."""

    status: str
    exit_code: int
    summary: str
    baseline_commit: str = ""
    current_commit: str = ""
    metrics: list[MetricResult] = field(default_factory=list)
    statistical: list[StatDetail] = field(default_factory=list)
    regressions: list[str] = field(default_factory=list)
    budget_breaches: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict representation."""
        return {
            "status": self.status,
            "exit_code": self.exit_code,
            "summary": self.summary,
            "baseline_commit": self.baseline_commit,
            "current_commit": self.current_commit,
            "regressions": self.regressions,
            "budget_breaches": self.budget_breaches,
            "metrics": [m.to_dict() for m in self.metrics],
            "statistical": [s.to_dict() for s in self.statistical],
        }


class RegressionEngine:
    """Core regression comparator. Fully deterministic.

    Args:
        thresholds:       metric → max allowed % change (positive = increase limit).
        budgets:          metric → absolute ceiling value.
        statistical_mode: Run Mann-Whitney U + bootstrap CI if sample lists provided.
        confidence:       CI/significance confidence level (default 0.95).
        noise_tolerance:  % band added to thresholds to absorb benchmark noise.
    """

    def __init__(
        self,
        thresholds: dict[str, float] | None = None,
        budgets: dict[str, float] | None = None,
        statistical_mode: bool = False,
        confidence: float = 0.95,
        noise_tolerance: float = 0.0,
    ) -> None:
        """Initialize the regression engine with configuration."""
        self.thresholds = thresholds or {}
        self.budgets = budgets or {}
        self.statistical_mode = statistical_mode
        self.confidence = confidence
        self.noise_tolerance = noise_tolerance

    def compare(
        self,
        baseline: RunV2,
        current: RunV2,
        baseline_samples: dict[str, list[float]] | None = None,
        current_samples: dict[str, list[float]] | None = None,
    ) -> ComparisonResult:
        """Compare current against baseline.

        baseline_samples / current_samples: optional per-metric raw sample lists
        for statistical analysis (Mann-Whitney U, bootstrap CI).
        """
        b_flat = baseline.metrics.flat()
        c_flat = current.metrics.flat()

        metrics: list[MetricResult] = []
        stat_details: list[StatDetail] = []
        regressions: list[str] = []
        budget_breaches: list[str] = []

        for key in sorted(set(b_flat) | set(c_flat)):
            b_val = b_flat.get(key)
            c_val = c_flat.get(key)
            if b_val is None or c_val is None:
                continue

            pct = percent_change(b_val, c_val)
            threshold = self.thresholds.get(key)
            budget = self.budgets.get(key)

            effective_thr = threshold
            if threshold is not None and self.noise_tolerance > 0:
                effective_thr = threshold + self.noise_tolerance

            thr_breached = effective_thr is not None and pct > effective_thr
            bud_breached = budget is not None and c_val > budget

            # Budget breach takes precedence over threshold regression
            if bud_breached:
                status = "budget_breach"
                budget_breaches.append(key)
            elif thr_breached:
                status = "regression"
                regressions.append(key)
            else:
                status = "pass"

            metrics.append(
                MetricResult(
                    metric=key,
                    baseline_value=b_val,
                    current_value=c_val,
                    change_percent=round(pct, 4),
                    threshold_percent=threshold,
                    budget_value=budget,
                    threshold_breached=thr_breached,
                    budget_breached=bud_breached,
                    status=status,
                )
            )

            if self.statistical_mode and baseline_samples and current_samples:
                bs = baseline_samples.get(key, [b_val])
                cs = current_samples.get(key, [c_val])
                _, p = mann_whitney_u(bs, cs)
                d = cohens_d(bs, cs)
                lo, hi = bootstrap_mean_ci(cs, confidence=self.confidence)
                stat_details.append(
                    StatDetail(
                        metric=key,
                        p_value=round(p, 6),
                        significant=p < (1.0 - self.confidence),
                        effect_size=round(d, 4),
                        effect_label=effect_label(d),
                        ci_lower=round(lo, 4),
                        ci_upper=round(hi, 4),
                    )
                )

        if budget_breaches:
            overall, code = "budget_breach", EXIT_BUDGET_BREACH
        elif regressions:
            overall, code = "regression", EXIT_REGRESSION
        else:
            overall, code = "pass", EXIT_PASS

        reg_s = ", ".join(regressions) or "none"
        bud_s = ", ".join(budget_breaches) or "none"
        summary = f"Status: {overall.upper()} | Regressions: {reg_s} | Budget breaches: {bud_s}"

        return ComparisonResult(
            status=overall,
            exit_code=code,
            summary=summary,
            baseline_commit=baseline.metadata.commit,
            current_commit=current.metadata.commit,
            metrics=metrics,
            statistical=stat_details,
            regressions=regressions,
            budget_breaches=budget_breaches,
        )
