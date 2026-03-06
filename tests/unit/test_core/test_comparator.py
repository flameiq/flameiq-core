"""Tests for flameiq.core.comparator and flameiq.core.thresholds."""

from __future__ import annotations

import pytest

from flameiq.core.comparator import compare_snapshots, compute_change_percent
from flameiq.core.errors import ComparisonError, ThresholdConfigError
from flameiq.core.models import RegressionStatus
from flameiq.core.thresholds import (
    build_threshold_map,
    evaluate_threshold,
    parse_threshold,
)
from tests.fixtures.test_fixtures import BASELINE, PASSING, REGRESSION, make_snapshot

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# compute_change_percent
# ---------------------------------------------------------------------------
class TestComputeChangePercent:
    def test_increase(self):
        assert compute_change_percent(100.0, 110.0) == 10.0

    def test_decrease(self):
        assert compute_change_percent(100.0, 90.0) == -10.0

    def test_no_change(self):
        assert compute_change_percent(100.0, 100.0) == 0.0

    def test_zero_baseline_raises(self):
        with pytest.raises(ComparisonError):
            compute_change_percent(0.0, 50.0)

    def test_precision_4dp(self):
        result = compute_change_percent(3.0, 4.0)
        assert result == round(((4.0 - 3.0) / 3.0) * 100, 4)

    @pytest.mark.determinism
    def test_determinism_100_runs(self):
        results = [compute_change_percent(120.5, 138.6) for _ in range(100)]
        assert all(r == results[0] for r in results)


# ---------------------------------------------------------------------------
# parse_threshold / evaluate_threshold / build_threshold_map
# ---------------------------------------------------------------------------
class TestThresholds:
    def test_parse_positive_percent(self):
        assert parse_threshold("k", "10%") == 10.0

    def test_parse_negative_percent(self):
        assert parse_threshold("k", "-5%") == -5.0

    def test_parse_decimal_percent(self):
        assert parse_threshold("k", "2.5%") == 2.5

    def test_parse_numeric_passthrough(self):
        assert parse_threshold("k", 10.0) == 10.0

    def test_parse_invalid_raises(self):
        with pytest.raises(ThresholdConfigError):
            parse_threshold("k", "ten percent")

    def test_parse_no_percent_sign_raises(self):
        with pytest.raises(ThresholdConfigError):
            parse_threshold("k", "10")

    def test_evaluate_latency_regression(self):
        assert evaluate_threshold("latency.p95", 15.0, 10.0) is True

    def test_evaluate_latency_pass(self):
        assert evaluate_threshold("latency.p95", 5.0, 10.0) is False

    def test_evaluate_latency_exactly_at_threshold_is_pass(self):
        assert evaluate_threshold("latency.p95", 10.0, 10.0) is False

    def test_evaluate_throughput_decrease_regression(self):
        assert evaluate_threshold("throughput", -8.0, 5.0) is True

    def test_evaluate_throughput_decrease_pass(self):
        assert evaluate_threshold("throughput", -3.0, 5.0) is False

    def test_evaluate_throughput_increase_not_regression(self):
        # Throughput going up is good — should not regress
        assert evaluate_threshold("throughput", 20.0, 5.0) is False

    def test_evaluate_custom_metric_both_directions(self):
        assert evaluate_threshold("custom.score", 15.0, 10.0) is True
        assert evaluate_threshold("custom.score", -15.0, 10.0) is True
        assert evaluate_threshold("custom.score", 5.0, 10.0) is False

    def test_build_threshold_map(self):
        result = build_threshold_map({"latency.p95": "10%", "throughput": "-5%"})
        assert result == {"latency.p95": 10.0, "throughput": -5.0}


# ---------------------------------------------------------------------------
# compare_snapshots
# ---------------------------------------------------------------------------
class TestCompareSnapshots:
    def test_passing_result(self):
        result = compare_snapshots(BASELINE, PASSING)
        assert result.status == RegressionStatus.PASS
        assert result.exit_code == 0
        assert len(result.regressions) == 0

    def test_regression_detected(self):
        result = compare_snapshots(BASELINE, REGRESSION)
        assert result.status == RegressionStatus.REGRESSION
        assert result.exit_code == 1
        assert len(result.regressions) > 0

    def test_regression_on_latency_p95(self):
        result = compare_snapshots(BASELINE, REGRESSION)
        regression_keys = {d.metric_key for d in result.regressions}
        assert "latency.p95" in regression_keys

    def test_tighter_threshold_catches_small_regression(self):
        result = compare_snapshots(
            BASELINE,
            PASSING,
            threshold_config={"latency.p95": "1%"},
        )
        assert result.status == RegressionStatus.REGRESSION

    def test_looser_threshold_ignores_large_regression(self):
        result = compare_snapshots(
            BASELINE,
            REGRESSION,
            threshold_config={
                "latency.p95": "50%",
                "latency.p99": "50%",
                "latency.mean": "50%",
                "throughput": "50%",
                "memory_mb": "50%",
            },
        )
        assert result.status == RegressionStatus.PASS

    def test_commit_info_preserved(self):
        result = compare_snapshots(BASELINE, PASSING)
        assert result.baseline_commit == "baseline-001"
        assert result.current_commit == "pass-001"

    def test_result_has_summary(self):
        result = compare_snapshots(BASELINE, PASSING)
        assert result.summary is not None
        assert len(result.summary) > 0

    def test_result_to_dict_structure(self):
        result = compare_snapshots(BASELINE, REGRESSION)
        d = result.to_dict()
        assert "status" in d
        assert "exit_code" in d
        assert "diffs" in d
        assert d["exit_code"] == 1

    def test_missing_metric_in_current_skipped(self):
        from flameiq.schema.v1.models import LatencyMetrics, Metrics

        # current has no throughput
        current = make_snapshot(commit="x")
        current.metrics.__class__  # it has throughput by default
        # Now make one without throughput
        from flameiq.schema.v1.models import PerformanceSnapshot, SnapshotMetadata

        partial = PerformanceSnapshot(
            metadata=SnapshotMetadata(commit="partial"),
            metrics=Metrics(latency=LatencyMetrics(mean=101.0, p95=121.0, p99=201.0)),
        )
        result = compare_snapshots(BASELINE, partial)
        # Should not crash — missing metrics skipped
        compared_keys = {d.metric_key for d in result.diffs}
        assert "latency.p95" in compared_keys

    @pytest.mark.determinism
    def test_determinism_100_runs(self):
        results = [compare_snapshots(BASELINE, REGRESSION) for _ in range(100)]
        first = results[0]
        for r in results[1:]:
            assert r.status == first.status
            assert r.exit_code == first.exit_code
            assert len(r.diffs) == len(first.diffs)
            for d1, d2 in zip(first.diffs, r.diffs):
                assert d1.change_percent == d2.change_percent
                assert d1.is_regression == d2.is_regression
