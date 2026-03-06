"""FlameIQ Performance Schema — Version 1.

This module defines the canonical, versioned data contract for all FlameIQ
performance snapshots. Schema v1 is **stable and immutable** — fields will
never be removed or renamed. New optional fields may appear in minor patch
releases.

All classes use standard-library ``dataclasses`` only.
Zero external runtime dependencies in this module.

Schema version: 1
Stability:      Production / Stable
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Environment(str, Enum):
    """The execution environment for a benchmark run."""

    CI = "ci"
    LOCAL = "local"
    STAGING = "staging"
    CUSTOM = "custom"

    @classmethod
    def _missing_(cls, value: object) -> Environment:
        return cls.CUSTOM


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


@dataclass
class LatencyMetrics:
    """Latency measurements in **milliseconds**.

    At least one field must be provided. ``p95`` is the primary regression
    signal used by the comparison engine.

    Args:
        mean: Arithmetic mean latency (ms).
        p50:  Median latency (ms).
        p95:  95th-percentile latency (ms). **Primary regression signal.**
        p99:  99th-percentile latency (ms). Tail latency signal.
    """

    mean: float | None = None
    p50: float | None = None
    p95: float | None = None
    p99: float | None = None

    def __post_init__(self) -> None:
        if all(v is None for v in (self.mean, self.p50, self.p95, self.p99)):
            raise ValueError("LatencyMetrics requires at least one value (mean, p50, p95, or p99).")
        for name, val in (
            ("mean", self.mean),
            ("p50", self.p50),
            ("p95", self.p95),
            ("p99", self.p99),
        ):
            if val is not None and (not isinstance(val, (int, float)) or val < 0):
                raise ValueError(
                    f"LatencyMetrics.{name} must be a non-negative number, got {val!r}"
                )


@dataclass
class Metrics:
    """All performance measurements for a single benchmark run.

    At least one metric must be non-null/non-empty.

    Args:
        latency:     Latency breakdown in milliseconds.
        throughput:  Operations or requests per second.
        memory_mb:   Peak memory usage in megabytes.
        cpu_percent: Average CPU utilisation (0–100).
        custom:      User-defined numeric metrics. Keys are dotted names.
    """

    latency: LatencyMetrics | None = None
    throughput: float | None = None
    memory_mb: float | None = None
    cpu_percent: float | None = None
    custom: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        has_std = any(
            [
                self.latency is not None,
                self.throughput is not None,
                self.memory_mb is not None,
                self.cpu_percent is not None,
            ]
        )
        if not has_std and not self.custom:
            raise ValueError(
                "Metrics must contain at least one measurement "
                "(latency, throughput, memory_mb, cpu_percent, or custom)."
            )

    def flat(self) -> dict[str, float]:
        """Return a flat ``{key: value}`` dict of all non-null metrics.

        Keys follow a dotted naming convention:
        ``latency.mean``, ``latency.p95``, ``throughput``, ``memory_mb``,
        ``cpu_percent``, ``custom.<name>``.

        Returns:
            Ordered dict of all non-null metric values.
        """
        result: dict[str, float] = {}
        if self.latency:
            for attr in ("mean", "p50", "p95", "p99"):
                v = getattr(self.latency, attr)
                if v is not None:
                    result[f"latency.{attr}"] = float(v)
        if self.throughput is not None:
            result["throughput"] = float(self.throughput)
        if self.memory_mb is not None:
            result["memory_mb"] = float(self.memory_mb)
        if self.cpu_percent is not None:
            result["cpu_percent"] = float(self.cpu_percent)
        for k, v in self.custom.items():
            result[f"custom.{k}"] = float(v)
        return result


@dataclass
class SnapshotMetadata:
    """Contextual metadata attached to a :class:`PerformanceSnapshot`.

    Args:
        run_id:      UUID4 uniquely identifying this run. Auto-generated.
        commit:      Git commit hash (short or full SHA).
        branch:      Git branch name.
        timestamp:   UTC datetime of the run. Auto-generated if omitted.
        environment: Execution environment label.
        tags:        Arbitrary ``str → str`` metadata for user context.
    """

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    commit: str | None = None
    branch: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    environment: Environment = Environment.CI
    tags: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Top-level snapshot
# ---------------------------------------------------------------------------


@dataclass
class PerformanceSnapshot:
    """A complete, versioned performance snapshot.

    This is the primary data unit in FlameIQ. Every benchmark run produces
    exactly one ``PerformanceSnapshot``. Snapshots are immutable in intent —
    do not mutate after construction.

    Args:
        metrics:        All performance measurements for this run.
        schema_version: Must be ``1`` for v1 snapshots.
        metadata:       Run context (commit, branch, timestamp, etc.).

    Example::

        snapshot = PerformanceSnapshot(
            metadata=SnapshotMetadata(commit="abc123", branch="main"),
            metrics=Metrics(
                latency=LatencyMetrics(mean=120.5, p95=180.0, p99=240.0),
                throughput=950.2,
                memory_mb=512.0,
            ),
        )
    """

    metrics: Metrics
    schema_version: int = 1
    metadata: SnapshotMetadata = field(default_factory=SnapshotMetadata)

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError(
                f"Unsupported schema_version: {self.schema_version!r}. "
                "FlameIQ v1.0 supports schema version 1 only."
            )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain ``dict`` suitable for JSON serialisation.

        Returns:
            A ``dict`` that round-trips through :meth:`from_dict`.
        """
        m = self.metadata
        metrics_d: dict[str, Any] = {}
        if self.metrics.latency:
            lat = self.metrics.latency
            metrics_d["latency"] = {
                k: getattr(lat, k)
                for k in ("mean", "p50", "p95", "p99")
                if getattr(lat, k) is not None
            }
        if self.metrics.throughput is not None:
            metrics_d["throughput"] = self.metrics.throughput
        if self.metrics.memory_mb is not None:
            metrics_d["memory_mb"] = self.metrics.memory_mb
        if self.metrics.cpu_percent is not None:
            metrics_d["cpu_percent"] = self.metrics.cpu_percent
        if self.metrics.custom:
            metrics_d["custom"] = dict(self.metrics.custom)

        return {
            "schema_version": self.schema_version,
            "metadata": {
                "run_id": m.run_id,
                "commit": m.commit,
                "branch": m.branch,
                "timestamp": m.timestamp.isoformat(),
                "environment": m.environment.value,
                "tags": dict(m.tags),
            },
            "metrics": metrics_d,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PerformanceSnapshot:
        """Deserialise a ``PerformanceSnapshot`` from a plain ``dict``.

        Args:
            data: A dict as produced by :meth:`to_dict`, or a compatible
                  JSON structure conforming to the FlameIQ v1 schema.

        Returns:
            A validated :class:`PerformanceSnapshot`.

        Raises:
            ValueError: If required fields are missing or invalid.
            TypeError:  If field types are wrong.
        """
        schema_version = data.get("schema_version", 1)
        if schema_version != 1:
            raise ValueError(f"Unsupported schema_version: {schema_version!r}")

        # --- metadata ---
        raw_meta = data.get("metadata", {})
        ts_raw = raw_meta.get("timestamp")
        if ts_raw:
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                ts = datetime.now(tz=timezone.utc)
        else:
            ts = datetime.now(tz=timezone.utc)

        env_raw = raw_meta.get("environment", "ci")
        try:
            env = Environment(env_raw)
        except ValueError:
            env = Environment.CUSTOM

        metadata = SnapshotMetadata(
            run_id=raw_meta.get("run_id", str(uuid.uuid4())),
            commit=raw_meta.get("commit"),
            branch=raw_meta.get("branch"),
            timestamp=ts,
            environment=env,
            tags=dict(raw_meta.get("tags", {})),
        )

        # --- metrics ---
        raw_metrics = data.get("metrics")
        if not raw_metrics:
            raise ValueError("'metrics' is required and must not be empty.")

        latency: LatencyMetrics | None = None
        lat_raw = raw_metrics.get("latency")
        if lat_raw:
            latency = LatencyMetrics(
                mean=lat_raw.get("mean"),
                p50=lat_raw.get("p50"),
                p95=lat_raw.get("p95"),
                p99=lat_raw.get("p99"),
            )

        metrics = Metrics(
            latency=latency,
            throughput=raw_metrics.get("throughput"),
            memory_mb=raw_metrics.get("memory_mb"),
            cpu_percent=raw_metrics.get("cpu_percent"),
            custom=dict(raw_metrics.get("custom", {})),
        )

        return cls(
            schema_version=schema_version,
            metadata=metadata,
            metrics=metrics,
        )
