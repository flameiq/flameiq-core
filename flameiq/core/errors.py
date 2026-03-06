"""FlameIQ exception hierarchy.

All FlameIQ exceptions derive from :class:`FlameIQError`. This lets callers
catch the entire FlameIQ surface with a single ``except FlameIQError``, or
target specific classes for fine-grained handling.

**Rule:** Never raise a bare ``Exception`` anywhere in the FlameIQ codebase.
Always raise from this hierarchy.

Hierarchy::

    FlameIQError
    ├── ValidationError
    │   └── SchemaVersionError
    ├── ConfigurationError
    │   └── ThresholdConfigError
    ├── BaselineError
    │   ├── BaselineNotFoundError
    │   └── BaselineCorruptedError
    ├── ProviderError
    │   ├── ProviderNotFoundError
    │   └── MetricsFileNotFoundError
    ├── ComparisonError
    │   └── InsufficientSamplesError
    └── StorageError
        └── MigrationError
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class FlameIQError(Exception):
    """Base class for all FlameIQ exceptions."""


# ---------------------------------------------------------------------------
# Schema & Validation
# ---------------------------------------------------------------------------


class ValidationError(FlameIQError):
    """Raised when a snapshot fails schema validation."""


class SchemaVersionError(ValidationError):
    """Raised when an unsupported schema version is encountered.

    Args:
        version: The unsupported version number that was encountered.
    """

    def __init__(self, version: int) -> None:
        super().__init__(
            f"Unsupported schema version: {version}. FlameIQ v1.0 supports schema_version 1 only."
        )
        self.version = version


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class ConfigurationError(FlameIQError):
    """Raised when flameiq.yaml is missing, malformed, or invalid."""


class ThresholdConfigError(ConfigurationError):
    """Raised when a threshold value cannot be parsed or is out of range.

    Args:
        key:    The metric key the threshold applies to.
        value:  The raw invalid threshold string.
        reason: Human-readable explanation of the error.
    """

    def __init__(self, key: str, value: str, reason: str) -> None:
        super().__init__(f"Invalid threshold for '{key}: {value}' — {reason}")
        self.key = key
        self.value = value


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------


class BaselineError(FlameIQError):
    """Raised for baseline management failures."""


class BaselineNotFoundError(BaselineError):
    """Raised when no baseline snapshot exists for the current context.

    Args:
        path: The filesystem path where the baseline was expected.
    """

    def __init__(self, path: str) -> None:
        super().__init__(
            f"No baseline found at '{path}'. Run: flameiq baseline set --metrics <file>"
        )
        self.path = path


class BaselineCorruptedError(BaselineError):
    """Raised when a baseline file exists but cannot be deserialised.

    Args:
        path:   Path to the corrupted file.
        reason: Description of the parse failure.
    """

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Baseline at '{path}' is corrupted: {reason}")
        self.path = path


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class ProviderError(FlameIQError):
    """Raised when a metric provider fails to collect or normalise data."""


class ProviderNotFoundError(ProviderError):
    """Raised when a requested provider name is not registered.

    Args:
        name: The requested provider name.
    """

    def __init__(self, name: str) -> None:
        super().__init__(
            f"Provider '{name}' is not registered. Use: flameiq validate --list-providers"
        )
        self.name = name


class MetricsFileNotFoundError(ProviderError):
    """Raised when the metrics source file does not exist.

    Args:
        path: The path that was not found.
    """

    def __init__(self, path: str) -> None:
        super().__init__(f"Metrics file not found: '{path}'")
        self.path = path


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


class ComparisonError(FlameIQError):
    """Raised when a comparison cannot be completed."""


class InsufficientSamplesError(ComparisonError):
    """Raised when statistical mode is enabled but sample count is too low.

    Args:
        metric:   The metric name with insufficient samples.
        got:      Number of samples available.
        required: Minimum samples required.
    """

    def __init__(self, metric: str, got: int, required: int) -> None:
        super().__init__(
            f"Insufficient samples for '{metric}': "
            f"got {got}, need at least {required} for statistical comparison."
        )
        self.metric = metric
        self.got = got
        self.required = required


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


class StorageError(FlameIQError):
    """Raised for storage read/write failures."""


class MigrationError(StorageError):
    """Raised when a storage schema migration fails."""
