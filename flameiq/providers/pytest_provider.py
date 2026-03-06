"""FlameIQ pytest-benchmark provider.

Adapts output from `pytest-benchmark <https://pytest-benchmark.readthedocs.io/>`_
into a FlameIQ v1 :class:`~flameiq.schema.v1.models.PerformanceSnapshot`.

Generate compatible output with::

    pytest --benchmark-json=benchmark_output.json

Then run::

    flameiq run --metrics benchmark_output.json --provider pytest-benchmark

Mapping
-------

.. list-table::
   :header-rows: 1

   * - pytest-benchmark field
     - FlameIQ field
   * - ``stats.mean`` (s)
     - ``latency.mean`` (ms)
   * - ``stats.median`` (s)
     - ``latency.p50`` (ms)
   * - ``stats.ops``
     - ``throughput`` (ops/s)
   * - ``commit_info.id``
     - ``metadata.commit``
   * - ``commit_info.branch``
     - ``metadata.branch``

When multiple benchmarks are present in a single JSON file, each benchmark
is stored as a separate ``custom.<benchmark_name>`` metric (mean latency in ms),
and the first benchmark's latency percentiles are used for the primary signals.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flameiq.core.errors import MetricsFileNotFoundError, ProviderError
from flameiq.providers.base import MetricProvider
from flameiq.schema.v1.models import (
    LatencyMetrics,
    Metrics,
    PerformanceSnapshot,
    SnapshotMetadata,
)


class PytestBenchmarkProvider(MetricProvider):
    """Provider for pytest-benchmark JSON output files."""

    @property
    def name(self) -> str:
        return "pytest-benchmark"

    def collect(self, source: str) -> dict[str, Any]:
        path = Path(source)
        if not path.exists():
            raise MetricsFileNotFoundError(source)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Invalid JSON in '{source}': {exc}") from exc

    def validate(self, raw: dict[str, Any]) -> bool:
        return (
            isinstance(raw, dict)
            and "benchmarks" in raw
            and isinstance(raw["benchmarks"], list)
            and len(raw["benchmarks"]) > 0
        )

    def normalize(self, raw: dict[str, Any]) -> PerformanceSnapshot:
        benchmarks: list[dict[str, Any]] = raw.get("benchmarks", [])
        if not benchmarks:
            raise ProviderError("pytest-benchmark output contains no benchmarks.")

        def _ms(val: float | None) -> float | None:
            """Convert seconds → milliseconds."""
            return val * 1000.0 if val is not None else None

        # Primary benchmark latency (first entry)
        primary_stats: dict[str, Any] = benchmarks[0].get("stats", {})
        latency = LatencyMetrics(
            mean=_ms(primary_stats.get("mean")),
            p50=_ms(primary_stats.get("median")),
        )

        # Sum ops/s across all benchmarks
        total_ops = sum(float(b.get("stats", {}).get("ops", 0.0)) for b in benchmarks)

        # Per-benchmark means as custom metrics (useful for multi-benchmark files)
        custom: dict[str, float] = {}
        for bench in benchmarks:
            bench_name: str = bench.get("name", "unknown")
            mean_s: float | None = bench.get("stats", {}).get("mean")
            if mean_s is not None:
                safe_name = bench_name.replace(".", "_").replace(" ", "_")
                custom[safe_name] = mean_s * 1000.0

        commit_info: dict[str, Any] = raw.get("commit_info") or {}
        metadata = SnapshotMetadata(
            commit=commit_info.get("id"),
            branch=commit_info.get("branch"),
        )

        metrics = Metrics(
            latency=latency if (latency.mean or latency.p50) else None,
            throughput=total_ops if total_ops > 0 else None,
            custom=custom,
        )

        return PerformanceSnapshot(
            schema_version=1,
            metadata=metadata,
            metrics=metrics,
        )
