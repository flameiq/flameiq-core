.. _custom_provider:

Building a Custom Provider
==========================

Providers are the plugin layer that allows FlameIQ to ingest benchmark
output from any tool, language, or data format. If you use a benchmarking
framework not natively supported by FlameIQ, you can add support in
minutes by implementing the :class:`~flameiq.providers.base.MetricProvider`
abstract base class.

Provider contract
-----------------

A provider must:

1. Be **stateless** — no instance variables that change between calls
2. Be **deterministic** — same input file → same output snapshot, every time
3. Be **read-only** — never write to disk or network
4. Implement three methods: :meth:`~flameiq.providers.base.MetricProvider.collect`,
   :meth:`~flameiq.providers.base.MetricProvider.validate`,
   :meth:`~flameiq.providers.base.MetricProvider.normalize`

The :meth:`~flameiq.providers.base.MetricProvider.load` method is provided
by the base class and calls all three in sequence.

Minimal example
---------------

Suppose your load testing tool produces JSON like this:

.. code-block:: json

   {
     "run_summary": {
       "avg_response_ms": 145.2,
       "p95_response_ms": 280.0,
       "p99_response_ms": 410.0,
       "requests_per_second": 850.0
     }
   }

Here is the complete provider implementation:

.. code-block:: python

   # my_project/providers/load_test_provider.py

   from __future__ import annotations

   import json
   from typing import Any

   from flameiq.core.errors import MetricsFileNotFoundError, ProviderError
   from flameiq.providers.base import MetricProvider
   from flameiq.schema.v1.models import (
       LatencyMetrics,
       Metrics,
       PerformanceSnapshot,
       SnapshotMetadata,
   )


   class LoadTestProvider(MetricProvider):
       """Provider for Acme LoadBot JSON output files."""

       @property
       def name(self) -> str:
           return "loadbot"

       def collect(self, source: str) -> dict[str, Any]:
           """Read and parse a LoadBot JSON output file."""
           from pathlib import Path
           path = Path(source)
           if not path.exists():
               raise MetricsFileNotFoundError(source)
           try:
               return json.loads(path.read_text(encoding="utf-8"))
           except json.JSONDecodeError as exc:
               raise ProviderError(f"Invalid JSON in '{source}': {exc}") from exc

       def validate(self, raw: dict[str, Any]) -> bool:
           """Return True if raw data is a valid LoadBot output."""
           return (
               isinstance(raw, dict)
               and "run_summary" in raw
               and "avg_response_ms" in raw.get("run_summary", {})
           )

       def normalize(self, raw: dict[str, Any]) -> PerformanceSnapshot:
           """Convert LoadBot output to a FlameIQ v1 snapshot."""
           s = raw["run_summary"]
           return PerformanceSnapshot(
               metadata=SnapshotMetadata(),
               metrics=Metrics(
                   latency=LatencyMetrics(
                       mean=s.get("avg_response_ms"),
                       p95=s.get("p95_response_ms"),
                       p99=s.get("p99_response_ms"),
                   ),
                   throughput=s.get("requests_per_second"),
               ),
           )

Register the provider
---------------------

Add your provider to the FlameIQ registry so the CLI can find it:

.. code-block:: python

   # At application startup or in a conftest.py / plugin init:
   from flameiq.providers.registry import PROVIDER_REGISTRY
   from my_project.providers.load_test_provider import LoadTestProvider

   PROVIDER_REGISTRY["loadbot"] = LoadTestProvider

Or extend the registry in a ``flameiq_plugins.py`` at your project root —
FlameIQ will auto-discover it if ``flameiq.yaml`` lists it:

.. code-block:: yaml

   provider: loadbot
   plugin: my_project.providers.load_test_provider

Use the provider
----------------

.. code-block:: bash

   flameiq validate loadbot_output.json --provider loadbot
   flameiq baseline set --metrics loadbot_output.json --provider loadbot
   flameiq compare --metrics loadbot_current.json --provider loadbot

Testing your provider
---------------------

Always write tests with at least three fixture files:

1. **Valid** — correct output, should parse successfully
2. **Invalid format** — wrong structure, ``validate()`` should return ``False``
3. **Missing file** — ``MetricsFileNotFoundError`` should be raised

.. code-block:: python

   import json
   import pytest
   from pathlib import Path
   from my_project.providers.load_test_provider import LoadTestProvider

   VALID = {
       "run_summary": {
           "avg_response_ms": 100.0,
           "p95_response_ms": 150.0,
           "requests_per_second": 1000.0,
       }
   }


   @pytest.fixture
   def provider():
       return LoadTestProvider()


   @pytest.fixture
   def valid_file(tmp_path):
       f = tmp_path / "result.json"
       f.write_text(json.dumps(VALID))
       return f


   def test_name(provider):
       assert provider.name == "loadbot"

   def test_load_valid(provider, valid_file):
       snap = provider.load(str(valid_file))
       assert snap.metrics.latency.mean == 100.0
       assert snap.metrics.throughput == 1000.0

   def test_validate_false_for_wrong_format(provider):
       assert provider.validate({"other": "data"}) is False

   def test_deterministic(provider, valid_file):
       results = [provider.load(str(valid_file)) for _ in range(20)]
       p95s = [r.metrics.latency.p95 for r in results]
       assert all(v == p95s[0] for v in p95s)

Provider checklist
------------------

Before submitting a provider to the FlameIQ community:

.. code-block:: text

   ☐  Stateless — no mutable instance variables
   ☐  Deterministic — identical file → identical output (test 20+ times)
   ☐  Raises MetricsFileNotFoundError for missing files
   ☐  Raises ProviderError for invalid content
   ☐  validate() returns False (not raises) for wrong format
   ☐  normalize() sets metadata.commit and metadata.branch if available
   ☐  Unit tests: valid, invalid, missing, determinism
   ☐  Docstring with example output format
