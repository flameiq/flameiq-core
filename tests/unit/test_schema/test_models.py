"""Tests for flameiq.schema.v1.models."""

from __future__ import annotations

import pytest

from flameiq.schema.v1.models import (
    Environment,
    LatencyMetrics,
    Metrics,
    PerformanceSnapshot,
    SnapshotMetadata,
)

pytestmark = pytest.mark.unit


class TestLatencyMetrics:
    def test_requires_at_least_one_value(self):
        with pytest.raises(ValueError, match="at least one"):
            LatencyMetrics()

    def test_valid_mean_only(self):
        m = LatencyMetrics(mean=100.0)
        assert m.mean == 100.0

    def test_negative_value_raises(self):
        with pytest.raises(ValueError):
            LatencyMetrics(mean=-1.0)

    def test_all_fields(self):
        m = LatencyMetrics(mean=100.0, p50=95.0, p95=150.0, p99=200.0)
        assert m.p95 == 150.0


class TestMetrics:
    def test_requires_at_least_one_metric(self):
        with pytest.raises(ValueError, match="at least one"):
            Metrics()

    def test_flat_latency(self):
        m = Metrics(latency=LatencyMetrics(mean=100.0, p95=150.0))
        f = m.flat()
        assert f["latency.mean"] == 100.0
        assert f["latency.p95"] == 150.0
        assert "latency.p50" not in f  # Not set

    def test_flat_all_fields(self):
        m = Metrics(
            latency=LatencyMetrics(p95=150.0),
            throughput=1000.0,
            memory_mb=512.0,
            cpu_percent=45.0,
            custom={"db_ms": 12.5},
        )
        f = m.flat()
        assert f["latency.p95"] == 150.0
        assert f["throughput"] == 1000.0
        assert f["memory_mb"] == 512.0
        assert f["cpu_percent"] == 45.0
        assert f["custom.db_ms"] == 12.5

    def test_custom_only_is_valid(self):
        m = Metrics(custom={"score": 0.98})
        assert m.flat()["custom.score"] == 0.98


class TestPerformanceSnapshot:
    def test_schema_version_1_only(self):
        with pytest.raises(ValueError, match="schema_version"):
            PerformanceSnapshot(
                metrics=Metrics(latency=LatencyMetrics(p95=100.0)),
                schema_version=2,
            )

    def test_roundtrip_to_dict_from_dict(self):
        snap = PerformanceSnapshot(
            metadata=SnapshotMetadata(commit="abc123", branch="main"),
            metrics=Metrics(
                latency=LatencyMetrics(mean=100.0, p95=150.0, p99=200.0),
                throughput=1000.0,
                memory_mb=512.0,
            ),
        )
        d = snap.to_dict()
        restored = PerformanceSnapshot.from_dict(d)

        assert restored.schema_version == 1
        assert restored.metadata.commit == "abc123"
        assert restored.metadata.branch == "main"
        assert restored.metrics.latency.p95 == 150.0
        assert restored.metrics.throughput == 1000.0

    def test_from_dict_minimal(self):
        data = {
            "schema_version": 1,
            "metrics": {"latency": {"p95": 120.0}},
        }
        snap = PerformanceSnapshot.from_dict(data)
        assert snap.metrics.latency.p95 == 120.0

    def test_from_dict_missing_metrics_raises(self):
        with pytest.raises(ValueError, match="metrics"):
            PerformanceSnapshot.from_dict({"schema_version": 1})

    def test_from_dict_invalid_schema_version_raises(self):
        with pytest.raises(ValueError, match="schema_version"):
            PerformanceSnapshot.from_dict(
                {
                    "schema_version": 99,
                    "metrics": {"latency": {"p95": 100.0}},
                }
            )

    def test_environment_enum_roundtrip(self):
        for env in ("ci", "local", "staging", "custom"):
            snap = PerformanceSnapshot(
                metadata=SnapshotMetadata(environment=Environment(env)),
                metrics=Metrics(latency=LatencyMetrics(p95=100.0)),
            )
            d = snap.to_dict()
            assert d["metadata"]["environment"] == env

    def test_unknown_environment_maps_to_custom(self):
        data = {
            "schema_version": 1,
            "metadata": {"environment": "production-special"},
            "metrics": {"throughput": 1000.0},
        }
        snap = PerformanceSnapshot.from_dict(data)
        assert snap.metadata.environment == Environment.CUSTOM

    def test_custom_metrics_roundtrip(self):
        snap = PerformanceSnapshot(
            metrics=Metrics(custom={"score": 0.95, "latency_99th": 200.0}),
        )
        d = snap.to_dict()
        restored = PerformanceSnapshot.from_dict(d)
        assert restored.metrics.custom["score"] == 0.95
