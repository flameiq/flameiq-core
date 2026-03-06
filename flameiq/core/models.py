"""FlameIQ core domain models.

These dataclasses represent the *results* of FlameIQ operations.
They are distinct from schema models (:mod:`flameiq.schema.v1.models`),
which represent *input data*.

No external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RegressionStatus(str, Enum):
    """The overall outcome of a baseline-vs-current comparison."""

    PASS = "pass"
    """All metrics are within their configured thresholds."""

    REGRESSION = "regression"
    """One or more metrics exceeded their threshold."""

    WARNING = "warning"
    """No threshold breached, but metrics are approaching limits."""

    INSUFFICIENT_DATA = "insufficient_data"
    """Statistical mode requested but sample count too low."""


@dataclass(frozen=True)
class MetricDiff:
    """The computed difference for a single metric key."""

    metric_key: str
    """Dotted key, e.g. ``"latency.p95"``."""
    baseline_value: float
    """The reference measurement."""
    current_value: float
    """The current measurement."""
    change_percent: float
    """Signed % change. Positive = current is larger."""
    threshold_percent: float
    """Configured allowance for this metric."""
    is_regression: bool
    """Whether the threshold was exceeded."""
    is_warning: bool = False
    """Within threshold but approaching the limit."""
    p_value: float | None = None
    """Statistical p-value (if statistical mode used)."""
    effect_size: float | None = None
    """Cohen's d (if statistical mode used)."""

    @property
    def direction(self) -> str:
        """Human-readable direction: ``'increased'``, ``'decreased'``, or ``'unchanged'``."""
        if self.change_percent > 0:
            return "increased"
        if self.change_percent < 0:
            return "decreased"
        return "unchanged"

    @property
    def abs_change_percent(self) -> float:
        """Absolute magnitude of the change."""
        return abs(self.change_percent)

    @property
    def status_label(self) -> str:
        """Short status string suitable for display."""
        if self.is_regression:
            return "REGRESSION"
        if self.is_warning:
            return "WARNING"
        return "PASS"


@dataclass(frozen=True)
class ComparisonResult:
    """The complete result of a baseline-vs-current comparison."""

    status: RegressionStatus
    """Overall pass/regression/warning outcome."""
    diffs: list[MetricDiff] = field(default_factory=list)
    """Per-metric differences, in metric-key order."""
    baseline_commit: str | None = None
    """Git SHA of the baseline snapshot, if available."""
    current_commit: str | None = None
    """Git SHA of the current snapshot, if available."""
    statistical_mode: bool = False
    """Whether the Mann-Whitney U test was applied."""
    summary: str | None = None
    """Optional human-readable summary string."""

    @property
    def regressions(self) -> list[MetricDiff]:
        """Metrics that breached their threshold."""
        return [d for d in self.diffs if d.is_regression]

    @property
    def warnings(self) -> list[MetricDiff]:
        """Metrics within threshold but approaching the limit."""
        return [d for d in self.diffs if d.is_warning and not d.is_regression]

    @property
    def passed(self) -> list[MetricDiff]:
        """Metrics that passed cleanly, with no warning."""
        return [d for d in self.diffs if not d.is_regression and not d.is_warning]

    @property
    def exit_code(self) -> int:
        """Standard CI exit code.

        Returns:
            ``0`` for PASS / WARNING, ``1`` for REGRESSION.
        """
        return 1 if self.status == RegressionStatus.REGRESSION else 0

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict (e.g. for ``--json`` CLI output)."""
        return {
            "status": self.status.value,
            "exit_code": self.exit_code,
            "baseline_commit": self.baseline_commit,
            "current_commit": self.current_commit,
            "statistical_mode": self.statistical_mode,
            "summary": self.summary,
            "counts": {
                "regressions": len(self.regressions),
                "warnings": len(self.warnings),
                "passed": len(self.passed),
                "total": len(self.diffs),
            },
            "diffs": [
                {
                    "metric_key": d.metric_key,
                    "baseline_value": d.baseline_value,
                    "current_value": d.current_value,
                    "change_percent": d.change_percent,
                    "threshold_percent": d.threshold_percent,
                    "is_regression": d.is_regression,
                    "is_warning": d.is_warning,
                    "status": d.status_label,
                    "p_value": d.p_value,
                    "effect_size": d.effect_size,
                }
                for d in self.diffs
            ],
        }
