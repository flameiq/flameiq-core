"""FlameIQ v2 Schema.

Extends the v1 FlameIQSnapshot with v2-specific helpers.
Uses stdlib only — no pydantic, no scipy.
"""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = 2


# ── Lightweight v2 snapshot (stdlib, no pydantic) ─────────────────────────────


@dataclass
class LatencyV2:
    """Latency metrics with percentiles."""

    mean: float | None = None
    p50: float | None = None
    p95: float | None = None
    p99: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LatencyV2:
        """Construct from dict."""
        return cls(mean=d.get("mean"), p50=d.get("p50"), p95=d.get("p95"), p99=d.get("p99"))


@dataclass
class MetricsV2:
    """Performance metrics including latency, throughput, and resource usage."""

    latency: LatencyV2 | None = None
    throughput: float | None = None
    memory_mb: float | None = None
    cpu_percent: float | None = None
    custom: dict[str, float] = field(default_factory=dict)

    def flat(self) -> dict[str, float]:
        """Return a dot-notation flat dict of all metric values."""
        out: dict[str, float] = {}
        if self.latency:
            for k, v in self.latency.to_dict().items():
                out[f"latency.{k}"] = v
        if self.throughput is not None:
            out["throughput"] = self.throughput
        if self.memory_mb is not None:
            out["memory_mb"] = self.memory_mb
        if self.cpu_percent is not None:
            out["cpu_percent"] = self.cpu_percent
        for k, v in self.custom.items():
            out[f"custom.{k}"] = v
        return out

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict, excluding None values."""
        out: dict[str, Any] = {}
        if self.latency:
            out["latency"] = self.latency.to_dict()
        if self.throughput is not None:
            out["throughput"] = self.throughput
        if self.memory_mb is not None:
            out["memory_mb"] = self.memory_mb
        if self.cpu_percent is not None:
            out["cpu_percent"] = self.cpu_percent
        if self.custom:
            out["custom"] = self.custom
        return out

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MetricsV2:
        """Construct from dict, supporting both native and v1 formats."""
        lat = LatencyV2.from_dict(d["latency"]) if "latency" in d else None
        custom_raw = d.get("custom", {})
        # Support both {key: float} and {key: {value: float}} (v1 format)
        custom: dict[str, float] = {}
        for k, v in custom_raw.items():
            if isinstance(v, dict):
                custom[k] = float(v.get("value", 0))
            else:
                custom[k] = float(v)
        return cls(
            latency=lat,
            throughput=d.get("throughput"),
            memory_mb=d.get("memory_mb"),
            cpu_percent=d.get("cpu_percent"),
            custom=custom,
        )


@dataclass
class MetadataV2:
    """Metadata for a performance run (commit, branch, environment, tags)."""

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    commit: str = ""
    branch: str = ""
    environment: str = "ci"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        return {
            "run_id": self.run_id,
            "commit": self.commit,
            "branch": self.branch,
            "environment": self.environment,
            "timestamp": self.timestamp,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MetadataV2:
        """Construct from dict, supporting both v1 and v2 formats."""
        tags_raw = d.get("tags", {})
        # v1 tags are dict[str,str], handle both
        tags = tags_raw if isinstance(tags_raw, dict) else {}
        return cls(
            run_id=d.get("run_id", str(uuid.uuid4())),
            commit=d.get("commit") or "",
            branch=d.get("branch") or "",
            environment=d.get("environment", "ci"),
            timestamp=d.get("timestamp", datetime.now(timezone.utc).isoformat()),
            tags=tags,
        )


@dataclass
class RunV2:
    """A v2 performance run.

    Self-contained, stdlib-only. Can be constructed from v1 FlameIQSnapshot JSON
    for backward compatibility.
    """

    schema_version: int = SCHEMA_VERSION
    metadata: MetadataV2 = field(default_factory=MetadataV2)
    metrics: MetricsV2 = field(default_factory=MetricsV2)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        return {
            "schema_version": self.schema_version,
            "metadata": self.metadata.to_dict(),
            "metrics": self.metrics.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RunV2:
        """Construct from dict, supporting both v1 and v2 formats."""
        meta_raw = d.get("metadata", {})
        # v1 schema has metadata.run_id nested differently
        if "run_id" not in meta_raw and "run_id" in d:
            meta_raw["run_id"] = d["run_id"]
        return cls(
            schema_version=d.get("schema_version", 1),
            metadata=MetadataV2.from_dict(meta_raw),
            metrics=MetricsV2.from_dict(d.get("metrics", {})),
        )

    @classmethod
    def from_json_file(cls, path: str) -> RunV2:
        """Load a RunV2 from a JSON file."""
        import pathlib

        data = json.loads(pathlib.Path(path).read_text())
        return cls.from_dict(data)

    @property
    def run_id(self) -> str:
        """Get the run ID from metadata."""
        return self.metadata.run_id


# ── JSON ingestion helper ────────────────────────────────────────────────────


def ingest_metrics_file(path: str, commit: str = "", branch: str = "", env: str = "ci") -> RunV2:
    """Load any JSON metrics file and normalize it into a RunV2.

    Accepts FlameIQ native format or flat benchmark output.
    """
    import pathlib

    raw = json.loads(pathlib.Path(path).read_text())
    return ingest_metrics_dict(raw, commit=commit, branch=branch, env=env)


def ingest_metrics_dict(
    raw: dict[str, Any], commit: str = "", branch: str = "", env: str = "ci"
) -> RunV2:
    """Normalize a raw dict into RunV2.

    Handles both native FlameIQ format and flat benchmark output.
    """
    # Native FlameIQ format
    if "metrics" in raw and isinstance(raw.get("metrics"), dict):
        run = RunV2.from_dict(raw)
        if commit:
            run.metadata.commit = commit
        if branch:
            run.metadata.branch = branch
        run.metadata.environment = env
        return run

    # Flat key format: {"p95_latency": 180, "throughput": 950}
    lat = LatencyV2(
        mean=_first(raw, "latency_mean", "mean_latency", "mean"),
        p50=_first(raw, "latency_p50", "p50", "median"),
        p95=_first(raw, "latency_p95", "p95_latency", "p95"),
        p99=_first(raw, "latency_p99", "p99_latency", "p99"),
    )
    if "latency" in raw and isinstance(raw["latency"], dict):
        ld = raw["latency"]
        lat = LatencyV2(
            mean=ld.get("mean", lat.mean),
            p50=ld.get("p50", lat.p50),
            p95=ld.get("p95", lat.p95),
            p99=ld.get("p99", lat.p99),
        )

    has_lat = any(v is not None for v in [lat.mean, lat.p50, lat.p95, lat.p99])
    return RunV2(
        metadata=MetadataV2(commit=commit, branch=branch, environment=env),
        metrics=MetricsV2(
            latency=lat if has_lat else None,
            throughput=_first(raw, "throughput", "rps", "requests_per_second", "ops_per_sec"),
            memory_mb=_first(raw, "memory_mb", "memory", "mem_mb", "rss_mb"),
            cpu_percent=_first(raw, "cpu_percent", "cpu", "cpu_usage"),
        ),
    )


def _first(d: dict[str, Any], *keys: str) -> float | None:
    for k in keys:
        v = d.get(k)
        if v is not None:
            try:
                f = float(v)
                return f if math.isfinite(f) else None
            except (TypeError, ValueError):
                continue
    return None
