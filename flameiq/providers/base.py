"""FlameIQ metric provider base class.

Providers are the plugin layer that translates raw benchmark output from
any tool or format into a :class:`~flameiq.schema.v1.models.PerformanceSnapshot`.

All providers must be:

- **Stateless** — no mutable state between calls.
- **Deterministic** — same input always produces the same snapshot.
- **Side-effect free** — read-only access to the source file.

Implementing a custom provider
-------------------------------

Subclass :class:`MetricProvider`, implement the three abstract methods,
and register in :mod:`flameiq.providers.registry`::

    from flameiq.providers.base import MetricProvider
    from flameiq.providers.registry import PROVIDER_REGISTRY

    class MyProvider(MetricProvider):

        @property
        def name(self) -> str:
            return "my-tool"

        def collect(self, source: str) -> dict:
            ...

        def validate(self, raw: dict) -> bool:
            ...

        def normalize(self, raw: dict) -> PerformanceSnapshot:
            ...

    PROVIDER_REGISTRY["my-tool"] = MyProvider

Then use it::

    flameiq run --metrics output.json --provider my-tool
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flameiq.schema.v1.models import PerformanceSnapshot


class MetricProvider(ABC):
    """Abstract base class for all FlameIQ metric providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier, e.g. ``'pytest-benchmark'``."""
        ...

    @abstractmethod
    def collect(self, source: str) -> dict[str, Any]:
        """Read raw benchmark data from a source path.

        Args:
            source: File path containing benchmark output.

        Returns:
            Raw data as a Python dict.

        Raises:
            :class:`~flameiq.core.errors.MetricsFileNotFoundError`:
                If the file does not exist.
            :class:`~flameiq.core.errors.ProviderError`:
                On any read or parse failure.
        """
        ...

    @abstractmethod
    def validate(self, raw: dict[str, Any]) -> bool:
        """Check whether *raw* can be processed by this provider.

        Args:
            raw: The dict returned by :meth:`collect`.

        Returns:
            ``True`` if the data is valid for this provider.
        """
        ...

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> PerformanceSnapshot:
        """Transform validated *raw* data into a ``PerformanceSnapshot``.

        Full type: :class:`~flameiq.schema.v1.models.PerformanceSnapshot`.

        Args:
            raw: Validated dict from :meth:`collect`.

        Returns:
            A valid :class:`~flameiq.schema.v1.models.PerformanceSnapshot`.

        Raises:
            :class:`~flameiq.core.errors.ProviderError`:
                On normalisation failure.
        """
        ...

    def load(self, source: str) -> PerformanceSnapshot:
        """Convenience pipeline: :meth:`collect` → :meth:`validate` → :meth:`normalize`.

        Args:
            source: Path to the metrics file.

        Returns:
            A validated, normalised snapshot.

        Raises:
            :class:`~flameiq.core.errors.ProviderError`:
                If validation fails.
        """
        from flameiq.core.errors import ProviderError

        raw = self.collect(source)
        if not self.validate(raw):
            raise ProviderError(
                f"Provider '{self.name}' could not validate '{source}'. "
                "Check that the file format matches this provider."
            )
        return self.normalize(raw)
