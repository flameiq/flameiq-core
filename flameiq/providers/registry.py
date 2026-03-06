"""FlameIQ provider registry.

Maps provider name strings to provider classes.
Add new providers here to make them available via ``--provider <name>``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flameiq.core.errors import ProviderNotFoundError
from flameiq.providers.json_provider import JsonProvider
from flameiq.providers.pytest_provider import PytestBenchmarkProvider

if TYPE_CHECKING:
    from flameiq.providers.base import MetricProvider

#: Mutable registry — add custom providers here.
PROVIDER_REGISTRY: dict[str, type[MetricProvider]] = {
    "json": JsonProvider,
    "pytest-benchmark": PytestBenchmarkProvider,
}


def get_provider(name: str) -> MetricProvider:
    """Instantiate a registered provider by name.

    Args:
        name: Provider identifier, e.g. ``'json'`` or ``'pytest-benchmark'``.

    Returns:
        An instantiated :class:`~flameiq.providers.base.MetricProvider`.

    Raises:
        :class:`~flameiq.core.errors.ProviderNotFoundError`:
            If *name* is not in :data:`PROVIDER_REGISTRY`.
    """
    cls = PROVIDER_REGISTRY.get(name)
    if cls is None:
        raise ProviderNotFoundError(name)
    return cls()


def list_providers() -> list[str]:
    """Return all registered provider names, sorted alphabetically."""
    return sorted(PROVIDER_REGISTRY.keys())
