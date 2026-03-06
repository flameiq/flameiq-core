"""FlameIQ engine — statistical algorithms and baseline strategies."""

from flameiq.engine.baseline import BaselineStrategy, select_baseline
from flameiq.engine.statistics import (
    MINIMUM_SAMPLES,
    StatisticalResult,
    mann_whitney_compare,
    noise_filter_median,
)

__all__ = [
    "BaselineStrategy",
    "select_baseline",
    "StatisticalResult",
    "mann_whitney_compare",
    "noise_filter_median",
    "MINIMUM_SAMPLES",
]
