"""Shared deterministic test fixtures.

All fixtures produce identical output on every call.
No randomness. No live timestamps used for comparison.
"""

from __future__ import annotations

from flameiq.schema.v1.models import (
    Environment,
    LatencyMetrics,
    Metrics,
    PerformanceSnapshot,
    SnapshotMetadata,
)


def make_snapshot(
    *,
    p95: float = 120.0,
    p99: float = 200.0,
    mean: float = 100.0,
    throughput: float = 1000.0,
    memory_mb: float = 512.0,
    cpu_percent: float | None = None,
    commit: str = "abc123",
    branch: str = "main",
    env: str = "ci",
    tags: dict | None = None,
) -> PerformanceSnapshot:
    return PerformanceSnapshot(
        metadata=SnapshotMetadata(
            commit=commit,
            branch=branch,
            environment=Environment(env),
            tags=tags or {},
        ),
        metrics=Metrics(
            latency=LatencyMetrics(mean=mean, p95=p95, p99=p99),
            throughput=throughput,
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
        ),
    )


# Named canonical fixtures
BASELINE = make_snapshot(commit="baseline-001")
PASSING = make_snapshot(
    p95=122.0, p99=204.0, mean=101.5, throughput=992.0, memory_mb=515.0, commit="pass-001"
)
REGRESSION = make_snapshot(
    p95=145.0, p99=260.0, mean=138.0, throughput=840.0, memory_mb=580.0, commit="regression-001"
)
BORDERLINE = make_snapshot(
    p95=131.0, p99=218.0, mean=109.0, throughput=951.0, memory_mb=549.0, commit="borderline-001"
)
