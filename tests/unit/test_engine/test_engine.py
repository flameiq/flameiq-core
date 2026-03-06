"""Tests for flameiq.engine.statistics and flameiq.engine.baseline."""

from __future__ import annotations

import pytest

from flameiq.core.errors import BaselineError, InsufficientSamplesError
from flameiq.engine.baseline import BaselineStrategy, select_baseline
from flameiq.engine.statistics import (
    StatisticalResult,
    mann_whitney_compare,
    noise_filter_median,
)
from tests.fixtures.test_fixtures import make_snapshot

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# noise_filter_median
# ---------------------------------------------------------------------------
class TestNoiseFilterMedian:
    def test_odd_count(self):
        assert noise_filter_median([1.0, 3.0, 5.0]) == 3.0

    def test_even_count(self):
        assert noise_filter_median([1.0, 2.0, 3.0, 4.0]) == 2.5

    def test_warmup_discard(self):
        assert noise_filter_median([999.0, 1.0, 3.0, 5.0], warmup=1) == 3.0

    def test_single_value(self):
        assert noise_filter_median([42.5]) == 42.5

    def test_unsorted_input(self):
        assert noise_filter_median([5.0, 1.0, 3.0]) == 3.0

    def test_all_discarded_raises(self):
        with pytest.raises(ValueError):
            noise_filter_median([1.0], warmup=1)

    @pytest.mark.determinism
    def test_determinism(self):
        samples = [3.0, 1.0, 5.0, 2.0, 4.0]
        results = [noise_filter_median(samples) for _ in range(100)]
        assert all(r == results[0] for r in results)


# ---------------------------------------------------------------------------
# mann_whitney_compare
# ---------------------------------------------------------------------------
# Fixed distributions — do NOT use random data here
_FAST = [10.0, 10.5, 9.8, 10.2, 10.1, 9.9, 10.3, 10.0]  # ~10ms
_SLOW = [14.0, 14.5, 13.8, 14.2, 14.1, 13.9, 14.3, 14.0]  # ~14ms (+40%)


class TestMannWhitneyCompare:
    def test_detects_clear_regression(self):
        result = mann_whitney_compare(_FAST, _SLOW)
        assert result.is_significant is True

    def test_p_value_strong_for_clear_difference(self):
        result = mann_whitney_compare(_FAST, _SLOW)
        assert result.p_value < 0.05

    def test_no_regression_same_distribution(self):
        result = mann_whitney_compare(_FAST, _FAST)
        assert result.is_significant is False

    def test_no_regression_current_faster(self):
        result = mann_whitney_compare(_SLOW, _FAST)
        assert result.is_significant is False

    def test_returns_statistical_result(self):
        result = mann_whitney_compare(_FAST, _SLOW)
        assert isinstance(result, StatisticalResult)
        assert result.test_name == "Mann-Whitney U"
        assert 0.0 <= result.p_value <= 1.0

    def test_effect_size_large_for_clear_difference(self):
        result = mann_whitney_compare(_FAST, _SLOW)
        assert result.effect_size > 0.8
        assert result.effect_label == "large"

    def test_custom_confidence_level(self):
        result = mann_whitney_compare(_FAST, _SLOW, confidence=0.99)
        assert result.confidence_level == 0.99
        assert abs(result.alpha - 0.01) < 1e-9

    def test_insufficient_samples_raises(self):
        with pytest.raises(InsufficientSamplesError):
            mann_whitney_compare([1.0, 2.0], _SLOW, minimum_samples=3)

    @pytest.mark.determinism
    def test_determinism_50_runs(self):
        results = [mann_whitney_compare(_FAST, _SLOW) for _ in range(50)]
        first = results[0]
        for r in results[1:]:
            assert r.p_value == first.p_value
            assert r.is_significant == first.is_significant
            assert r.effect_size == first.effect_size


# ---------------------------------------------------------------------------
# select_baseline
# ---------------------------------------------------------------------------
class TestSelectBaseline:
    def test_empty_history_raises(self):
        with pytest.raises(BaselineError):
            select_baseline([])

    def test_last_successful_returns_most_recent(self):
        h = [make_snapshot(commit="old"), make_snapshot(commit="new")]
        result = select_baseline(h, strategy=BaselineStrategy.LAST_SUCCESSFUL)
        assert result.metadata.commit == "new"

    def test_rolling_median_produces_snapshot(self):
        history = [make_snapshot(p95=float(i * 10 + 100)) for i in range(5)]
        result = select_baseline(
            history, strategy=BaselineStrategy.ROLLING_MEDIAN, rolling_window=3
        )
        # Rolling median over p95=[120, 130, 140] = 130
        assert result.metrics.latency is not None
        assert result.metrics.latency.p95 == pytest.approx(130.0)

    def test_tagged_finds_matching_snapshot(self):
        h = [
            make_snapshot(commit="old", tags={}),
            make_snapshot(commit="tagged", tags={"release": "v1.0.0"}),
            make_snapshot(commit="newer", tags={}),
        ]
        result = select_baseline(h, strategy=BaselineStrategy.TAGGED, tag="v1.0.0")
        assert result.metadata.commit == "tagged"

    def test_tagged_not_found_raises(self):
        h = [make_snapshot(commit="notag")]
        with pytest.raises(BaselineError, match="v9.9.9"):
            select_baseline(h, strategy=BaselineStrategy.TAGGED, tag="v9.9.9")

    def test_tagged_requires_tag_arg(self):
        with pytest.raises(BaselineError):
            select_baseline([make_snapshot()], strategy=BaselineStrategy.TAGGED, tag=None)
