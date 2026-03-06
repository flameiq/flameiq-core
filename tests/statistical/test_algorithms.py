"""
Statistical algorithm validation tests.

These tests verify that FlameIQ's regression detection algorithms produce
correct, statistically meaningful results on known fixed distributions.

All inputs and expected outcomes are analytically determined.
No random data. No flakiness.
"""

from __future__ import annotations

import pytest

from flameiq.core.comparator import compare_snapshots
from flameiq.core.models import RegressionStatus
from flameiq.engine.statistics import mann_whitney_compare
from tests.fixtures.test_fixtures import make_snapshot

pytestmark = pytest.mark.statistical


class TestKnownRegressionScenarios:
    """
    Regression scenarios at analytically known magnitudes.
    Each case documents the exact percent change and expected outcome.
    """

    @pytest.mark.parametrize(
        "p95_current,threshold,expected",
        [
            (105.0, "10%", RegressionStatus.PASS),  # +5.0% < 10% threshold
            (110.0, "10%", RegressionStatus.PASS),  # +10.0% = threshold (pass)
            (110.1, "10%", RegressionStatus.REGRESSION),  # +10.1% > threshold
            (115.0, "10%", RegressionStatus.REGRESSION),  # +15% > threshold
            (100.0, "10%", RegressionStatus.PASS),  # +0.0% no change
            (95.0, "10%", RegressionStatus.PASS),  # -5% improvement
        ],
    )
    def test_latency_threshold_boundary(
        self, p95_current: float, threshold: str, expected: RegressionStatus
    ):
        baseline = make_snapshot(p95=100.0)
        current = make_snapshot(p95=p95_current)
        result = compare_snapshots(
            baseline,
            current,
            threshold_config={"latency.p95": threshold},
        )
        assert result.status == expected, (
            f"p95={p95_current} threshold={threshold}: "
            f"expected {expected.value}, got {result.status.value}"
        )

    @pytest.mark.parametrize(
        "throughput_current,threshold,expected",
        [
            (950.0, "10%", RegressionStatus.PASS),  # -5% within 10%
            (900.0, "10%", RegressionStatus.PASS),  # -10% at boundary
            (899.0, "10%", RegressionStatus.REGRESSION),  # -10.1% over threshold
            (1100.0, "10%", RegressionStatus.PASS),  # +10% improvement
        ],
    )
    def test_throughput_threshold_boundary(
        self, throughput_current: float, threshold: str, expected: RegressionStatus
    ):
        baseline = make_snapshot(throughput=1000.0)
        current = make_snapshot(throughput=throughput_current)
        result = compare_snapshots(
            baseline,
            current,
            threshold_config={"throughput": threshold},
        )
        assert result.status == expected

    def test_multiple_metrics_all_must_pass(self):
        """All metrics must be within threshold — one regression fails the run."""
        baseline = make_snapshot(p95=100.0, throughput=1000.0, memory_mb=512.0)
        current = make_snapshot(p95=105.0, throughput=990.0, memory_mb=600.0)
        result = compare_snapshots(
            baseline,
            current,
            threshold_config={
                "latency.p95": "10%",
                "throughput": "10%",
                "memory_mb": "10%",  # 600/512 = +17.2% → REGRESSION
            },
        )
        assert result.status == RegressionStatus.REGRESSION
        reg_keys = {d.metric_key for d in result.regressions}
        assert "memory_mb" in reg_keys

    def test_performance_improvement_never_regresses(self):
        """A 40% improvement in latency must never be flagged."""
        baseline = make_snapshot(p95=150.0)
        current = make_snapshot(p95=90.0)  # Much better
        result = compare_snapshots(baseline, current)
        assert result.status == RegressionStatus.PASS

    @pytest.mark.determinism
    def test_100_run_determinism(self):
        baseline = make_snapshot(p95=100.0)
        current = make_snapshot(p95=115.0)
        statuses = [
            compare_snapshots(
                baseline,
                current,
                threshold_config={"latency.p95": "10%"},
            ).status
            for _ in range(100)
        ]
        unique = set(statuses)
        assert len(unique) == 1, f"Non-deterministic! Got statuses: {unique}"
        assert unique.pop() == RegressionStatus.REGRESSION


class TestMannWhitneyKnownDistributions:
    """
    Mann-Whitney U tests on hand-crafted distributions with known outcomes.
    """

    # 40% slower: clear regression
    BASELINE_FAST = [10.0, 10.5, 9.8, 10.2, 10.1, 9.9, 10.3, 10.0, 9.7, 10.4]
    CURRENT_SLOW = [14.0, 14.5, 13.8, 14.2, 14.1, 13.9, 14.3, 14.0, 13.7, 14.4]

    def test_detects_40_percent_regression(self):
        r = mann_whitney_compare(self.BASELINE_FAST, self.CURRENT_SLOW)
        assert r.is_significant is True
        assert r.p_value < 0.001

    def test_does_not_flag_improvement(self):
        # current FASTER than baseline → not a regression (one-tailed test)
        r = mann_whitney_compare(self.CURRENT_SLOW, self.BASELINE_FAST)
        assert r.is_significant is False

    def test_identical_distributions_not_significant(self):
        r = mann_whitney_compare(self.BASELINE_FAST, self.BASELINE_FAST)
        assert r.is_significant is False

    def test_effect_size_large_for_40pct_difference(self):
        r = mann_whitney_compare(self.BASELINE_FAST, self.CURRENT_SLOW)
        assert r.effect_size > 0.8  # Cohen: large effect

    @pytest.mark.parametrize(
        "confidence,expect_sig",
        [
            (0.90, True),
            (0.95, True),
            (0.99, True),
        ],
    )
    def test_confidence_levels(self, confidence: float, expect_sig: bool):
        r = mann_whitney_compare(self.BASELINE_FAST, self.CURRENT_SLOW, confidence=confidence)
        assert r.is_significant is expect_sig

    @pytest.mark.determinism
    def test_determinism_50_runs(self):
        results = [mann_whitney_compare(self.BASELINE_FAST, self.CURRENT_SLOW) for _ in range(50)]
        p_values = [r.p_value for r in results]
        assert len(set(p_values)) == 1, "Mann-Whitney is non-deterministic!"
