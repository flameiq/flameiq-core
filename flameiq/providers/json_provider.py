"""FlameIQ JSON provider.

The default built-in provider. Accepts any JSON file that already
conforms to the FlameIQ v1 schema. This is the simplest integration path.

Usage::

    flameiq run --metrics output.json
    flameiq run --metrics output.json --provider json  # explicit
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flameiq.core.errors import MetricsFileNotFoundError, ProviderError
from flameiq.providers.base import MetricProvider
from flameiq.schema.v1.models import PerformanceSnapshot


class JsonProvider(MetricProvider):
    """Provider for files already in FlameIQ v1 JSON schema format."""

    @property
    def name(self) -> str:
        return "json"

    def collect(self, source: str) -> dict[str, Any]:
        path = Path(source)
        if not path.exists():
            raise MetricsFileNotFoundError(source)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProviderError(f"'{source}' is not valid JSON: {exc}") from exc

    def validate(self, raw: dict[str, Any]) -> bool:
        return (
            isinstance(raw, dict)
            and raw.get("schema_version") == 1
            and "metrics" in raw
            and bool(raw["metrics"])
        )

    def normalize(self, raw: dict[str, Any]) -> PerformanceSnapshot:
        try:
            return PerformanceSnapshot.from_dict(raw)
        except Exception as exc:
            raise ProviderError(f"Failed to parse FlameIQ v1 snapshot: {exc}") from exc
