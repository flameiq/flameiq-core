"""FlameIQ v2 Analysis Engine.

Drift detection, trend analysis, multi-metric correlation, budget monitoring.

All analysis is:
  - Deterministic (same input → same output)
  - Rule-based (no AI/ML — transparent, auditable)
  - Offline-capable (no network calls)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from flameiq.v2.statistics.engine import DriftResult, detect_drift, percent_change

if TYPE_CHECKING:
    from flameiq.v2.storage.history import HistoryEntry, HistoryStore

# ── Trend Analyzer ────────────────────────────────────────────────────────────


@dataclass
class TrendPoint:
    """A single data point in a trend report."""

    timestamp: str
    commit: str
    value: float
    change_from_first: float


@dataclass
class TrendReport:
    """Report of metric trend over time with drift analysis."""

    metric: str
    points: list[TrendPoint]
    first_value: float
    last_value: float
    overall_change_percent: float
    drift: DriftResult

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict representation."""
        return {
            "metric": self.metric,
            "first_value": self.first_value,
            "last_value": self.last_value,
            "overall_change_percent": round(self.overall_change_percent, 4),
            "drift": {
                "is_drifting": self.drift.is_drifting,
                "direction": self.drift.direction,
                "cumulative_percent": round(self.drift.cumulative_percent, 4),
                "slope_percent_per_run": round(self.drift.slope_percent, 4),
                "r_squared": round(self.drift.confidence, 4),
                "run_count": self.drift.run_count,
            },
            "points": [
                {
                    "timestamp": p.timestamp,
                    "commit": p.commit,
                    "value": p.value,
                    "change_from_first": round(p.change_from_first, 4),
                }
                for p in self.points
            ],
        }


class TrendAnalyzer:
    """Time-travel comparison and multi-run trend analysis.

    Usage:
        analyzer = TrendAnalyzer(store)
        report = analyzer.trend("latency.p95", n=30)
        comparison = analyzer.compare_commits("abc123", "def456")
    """

    def __init__(self, store: HistoryStore) -> None:
        """Initialize with a HistoryStore."""
        self._store = store

    def trend(
        self,
        metric: str,
        n: int = 30,
        branch: str | None = None,
        drift_threshold_percent: float = 5.0,
    ) -> TrendReport | None:
        """Compute trend report for a single metric over the last n runs.

        Returns None if insufficient data.
        """
        entries = self._store.get_last_n(n, branch=branch)
        pts: list[TrendPoint] = []
        vals: list[float] = []

        for e in entries:
            v = e.metric_value(metric)
            if v is not None:
                vals.append(v)
                pts.append(
                    TrendPoint(
                        timestamp=e.timestamp, commit=e.commit, value=v, change_from_first=0.0
                    )
                )

        if len(vals) < 2:
            return None

        first = vals[0]
        for pt in pts:
            pt.change_from_first = percent_change(first, pt.value)

        drift = detect_drift(vals, drift_threshold_percent=drift_threshold_percent)

        return TrendReport(
            metric=metric,
            points=pts,
            first_value=first,
            last_value=vals[-1],
            overall_change_percent=percent_change(first, vals[-1]),
            drift=drift,
        )

    def compare_commits(self, commit_a: str, commit_b: str) -> dict[str, dict[str, Any]] | None:
        """Time-travel: compare metrics between two specific commits."""
        runs_a = self._store.get_by_commit(commit_a)
        runs_b = self._store.get_by_commit(commit_b)
        if not runs_a or not runs_b:
            return None

        fa = runs_a[0].run.metrics.flat()
        fb = runs_b[0].run.metrics.flat()
        result = {}
        for key in sorted(set(fa) | set(fb)):
            va, vb = fa.get(key), fb.get(key)
            if va is not None and vb is not None:
                result[key] = {
                    "commit_a_value": va,
                    "commit_b_value": vb,
                    "change_percent": round(percent_change(va, vb), 4),
                }
        return result


# ── Drift Analyzer ────────────────────────────────────────────────────────────


@dataclass
class DriftSummary:
    """Summary of drift analysis across all metrics."""

    has_drifting_metrics: bool
    drifting_metrics: list[str]
    stable_metrics: list[str]
    details: dict[str, DriftResult]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict representation."""
        return {
            "has_drifting_metrics": self.has_drifting_metrics,
            "drifting_metrics": self.drifting_metrics,
            "stable_metrics": self.stable_metrics,
            "details": {
                k: {
                    "is_drifting": v.is_drifting,
                    "direction": v.direction,
                    "cumulative_percent": round(v.cumulative_percent, 4),
                    "slope_percent_per_run": round(v.slope_percent, 4),
                    "r_squared": round(v.confidence, 4),
                    "run_count": v.run_count,
                }
                for k, v in self.details.items()
            },
        }


class DriftAnalyzer:
    """Detects cumulative gradual performance degradation.

    Catches slow regressions that never trigger single-run thresholds.
    """

    def __init__(self, store: HistoryStore) -> None:
        """Initialize with a HistoryStore."""
        self._store = store

    def analyze(
        self,
        n: int = 30,
        branch: str | None = None,
        drift_threshold_percent: float = 5.0,
        min_runs: int = 5,
    ) -> DriftSummary:
        """Analyze drift across all metrics in recent history.

        Returns DriftSummary identifying which metrics are drifting and the direction.
        """
        entries = self._store.get_last_n(n, branch=branch)
        if not entries:
            return DriftSummary(False, [], [], {})

        all_keys = self._store.all_metric_keys(n)
        details: dict[str, DriftResult] = {}
        drifting: list[str] = []
        stable: list[str] = []

        for key in sorted(all_keys):
            vals = [v for e in entries if (v := e.metric_value(key)) is not None]
            if len(vals) < min_runs:
                continue
            result = detect_drift(
                vals, drift_threshold_percent=drift_threshold_percent, min_runs=min_runs
            )
            details[key] = result
            (drifting if result.is_drifting else stable).append(key)

        return DriftSummary(
            has_drifting_metrics=bool(drifting),
            drifting_metrics=drifting,
            stable_metrics=stable,
            details=details,
        )


# ── Correlation Analyzer ──────────────────────────────────────────────────────


@dataclass
class CorrelationFinding:
    """A finding that two metrics are correlated based on rule table."""

    primary_metric: str
    correlated_metric: str
    primary_change_percent: float
    correlated_change_percent: float
    correlation_coefficient: float
    narrative: str


@dataclass
class CorrelationReport:
    """Report of correlated metric changes between baseline and current runs."""

    findings: list[CorrelationFinding]
    primary_driver: str | None
    narrative: str

    def to_dict(self) -> dict[str, Any]:
        """If multiple findings, the primary driver is the one with the largest % change."""
        return {
            "primary_driver": self.primary_driver,
            "narrative": self.narrative,
            "findings": [
                {
                    "primary_metric": f.primary_metric,
                    "correlated_metric": f.correlated_metric,
                    "primary_change_percent": round(f.primary_change_percent, 4),
                    "correlated_change_percent": round(f.correlated_change_percent, 4),
                    "correlation_coefficient": round(f.correlation_coefficient, 4),
                    "narrative": f.narrative,
                }
                for f in self.findings
            ],
        }


# Known cause-effect rules (deterministic, auditable)
_CORRELATION_RULES: list[tuple[str, str, str]] = [
    (
        "cpu_percent",
        "latency.p95",
        " High CPU utilization is correlated with p95 latency increase"
        " — likely CPU-bound regression.",
    ),
    (
        "cpu_percent",
        "latency.p99",
        "High CPU utilization is correlated with p99 latency — tail latency may be CPU-contended.",
    ),
    (
        "memory_mb",
        "latency.p95",
        "Memory growth is correlated with p95 latency"
        " — possible GC pressure or allocation overhead.",
    ),
    (
        "memory_mb",
        "latency.p99",
        "Memory growth is correlated with p99 latency — GC pauses may explain tail latency spikes.",
    ),
    (
        "throughput",
        "latency.p95",
        "Throughput drop is correlated with p95 latency increase — possible resource saturation.",
    ),
]


class CorrelationAnalyzer:
    """Rule-based multi-metric correlation engine.

    NOT AI. Fully deterministic. Transparent rule table.

    Detects causal relationships between resource metrics and latency.
    """

    def __init__(self, store: HistoryStore) -> None:
        """Initialize with a HistoryStore."""
        self._store = store

    def analyze_between(
        self,
        baseline_entries: list[HistoryEntry],
        current_entries: list[HistoryEntry],
        change_threshold: float = 5.0,
    ) -> CorrelationReport:
        """Detect correlated metric changes between two groups of runs.

        Uses rule table — fully deterministic and auditable.
        """
        if not baseline_entries or not current_entries:
            return CorrelationReport([], None, "Insufficient data for correlation analysis.")

        def avg(entries: list[HistoryEntry], key: str) -> float | None:
            vals = [v for e in entries if (v := e.metric_value(key)) is not None]
            return sum(vals) / len(vals) if vals else None

        changes: dict[str, float] = {}
        all_entries = baseline_entries + current_entries
        all_keys: set[str] = set()
        for e in all_entries:
            all_keys.update(e.run.metrics.flat().keys())

        for key in all_keys:
            b = avg(baseline_entries, key)
            c = avg(current_entries, key)
            if b is not None and c is not None:
                changes[key] = percent_change(b, c)

        findings: list[CorrelationFinding] = []
        for cause, effect, narrative in _CORRELATION_RULES:
            c_chg = changes.get(cause)
            e_chg = changes.get(effect)
            if c_chg is None or e_chg is None:
                continue
            if abs(c_chg) < change_threshold or abs(e_chg) < change_threshold:
                continue

            corr = self._pearson(all_entries, cause, effect)
            if corr is not None and abs(corr) >= 0.4:
                findings.append(
                    CorrelationFinding(
                        primary_metric=cause,
                        correlated_metric=effect,
                        primary_change_percent=c_chg,
                        correlated_change_percent=e_chg,
                        correlation_coefficient=corr,
                        narrative=narrative,
                    )
                )

        driver = None
        if findings:
            driver = max(findings, key=lambda f: abs(f.primary_change_percent)).primary_metric
            f = findings[0]
            narr = (
                f"Primary regression driver: {driver} ({f.primary_change_percent:+.1f}%). "
                f"{f.narrative}"
            )
        else:
            narr = "No significant metric correlations detected."

        return CorrelationReport(findings=findings, primary_driver=driver, narrative=narr)

    def _pearson(self, entries: list[HistoryEntry], key_a: str, key_b: str) -> float | None:
        pairs = [
            (va, vb)
            for e in entries
            if (va := e.metric_value(key_a)) is not None
            and (vb := e.metric_value(key_b)) is not None
        ]
        if len(pairs) < 4:
            return None
        n = len(pairs)
        mx = sum(p[0] for p in pairs) / n
        my = sum(p[1] for p in pairs) / n
        num = sum((p[0] - mx) * (p[1] - my) for p in pairs)
        dx = sum((p[0] - mx) ** 2 for p in pairs) ** 0.5
        dy = sum((p[1] - my) ** 2 for p in pairs) ** 0.5
        if dx * dy == 0:
            return None
        return float(num / (dx * dy))


# ── Budget Monitor ────────────────────────────────────────────────────────────


@dataclass
class BudgetStatus:
    """Status of a single metric against its SLO budget."""

    metric: str
    budget: float
    current_value: float
    consumed_percent: float
    headroom_percent: float
    status: str  # "safe" | "warning" | "critical" | "breached"


class BudgetMonitor:
    """Tracks SLO budget consumption and margin erosion.

    Warns before a breach, not just after.
    """

    WARNING_AT = 80.0
    CRITICAL_AT = 95.0

    def check(
        self, current_flat: dict[str, float], budgets: dict[str, float]
    ) -> list[BudgetStatus]:
        """Check which metrics breach their SLO budgets."""
        results = []
        for metric, budget in budgets.items():
            val = current_flat.get(metric)
            if val is None or budget <= 0:
                continue
            consumed = (val / budget) * 100.0
            headroom = 100.0 - consumed
            if consumed > 100.0:
                status = "breached"
            elif consumed >= self.CRITICAL_AT:
                status = "critical"
            elif consumed >= self.WARNING_AT:
                status = "warning"
            else:
                status = "safe"
            results.append(
                BudgetStatus(
                    metric=metric,
                    budget=budget,
                    current_value=val,
                    consumed_percent=round(consumed, 2),
                    headroom_percent=round(headroom, 2),
                    status=status,
                )
            )
        return results
