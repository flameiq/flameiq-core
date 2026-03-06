"""FlameIQ core engine — comparison, models, errors, thresholds."""

from flameiq.core.comparator import compare_snapshots, compute_change_percent
from flameiq.core.errors import (
    BaselineCorruptedError,
    BaselineError,
    BaselineNotFoundError,
    ComparisonError,
    ConfigurationError,
    FlameIQError,
    InsufficientSamplesError,
    MetricsFileNotFoundError,
    ProviderError,
    ProviderNotFoundError,
    SchemaVersionError,
    StorageError,
    ThresholdConfigError,
    ValidationError,
)
from flameiq.core.models import ComparisonResult, MetricDiff, RegressionStatus

__all__ = [
    # Comparison
    "compare_snapshots",
    "compute_change_percent",
    # Result types
    "ComparisonResult",
    "MetricDiff",
    "RegressionStatus",
    # Errors
    "FlameIQError",
    "ValidationError",
    "SchemaVersionError",
    "ConfigurationError",
    "ThresholdConfigError",
    "BaselineError",
    "BaselineNotFoundError",
    "BaselineCorruptedError",
    "ProviderError",
    "ProviderNotFoundError",
    "MetricsFileNotFoundError",
    "ComparisonError",
    "InsufficientSamplesError",
    "StorageError",
]
