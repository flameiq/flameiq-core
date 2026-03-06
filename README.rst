FlameIQ
=======

.. image:: https://img.shields.io/pypi/v/flameiq-core.svg
   :target: https://pypi.org/project/flameiq-core/
   :alt: PyPI

.. image:: https://img.shields.io/pypi/pyversions/flameiq-core.svg
   :target: https://pypi.org/project/flameiq-core/
   :alt: Python Versions

.. image:: https://img.shields.io/badge/license-Apache%202.0-blue.svg
   :target: https://github.com/flameiq/flameiq-core/blob/main/LICENSE
   :alt: License

.. image:: https://img.shields.io/badge/CI-passing-brightgreen.svg
   :target: https://github.com/flameiq/flameiq-core/actions
   :alt: CI

**Deterministic, CI-native performance regression and evolution engine.**

Make performance a first-class, enforceable engineering signal —
without requiring any SaaS platform, cloud account, or vendor dependency.

.. code-block:: bash

   pip install flameiq-core
   flameiq init
   flameiq baseline set --metrics benchmark.json
   flameiq compare --metrics current.json --fail-on-regression

.. note::

   FlameIQ OSS requires **no internet connection**, **no account**,
   and **no API keys**. Fully offline. Fully air-gap compatible.


Why FlameIQ?
------------

Performance regressions are rarely caught in code review. They accumulate
silently across hundreds of commits — a 3 ms latency increase here,
a 2% throughput drop there — until they become expensive production incidents.

FlameIQ brings the same engineering discipline to performance that type
checkers bring to correctness: **automated, deterministic, CI-enforced**.

Design Principles
-----------------

+--------------------+------------------------------------------------------+
| Principle          | What it means                                        |
+====================+======================================================+
| Deterministic      | Same input → same output, always. No flakiness.     |
+--------------------+------------------------------------------------------+
| CI-native          | Exit codes, JSON output, works in any pipeline.     |
+--------------------+------------------------------------------------------+
| Offline-first      | No network calls. No telemetry. Air-gap ready.      |
+--------------------+------------------------------------------------------+
| Language-agnostic  | Provider plugin system. Any tool, any language.     |
+--------------------+------------------------------------------------------+
| Statistically      | Optional Mann-Whitney U test with effect size.      |
| grounded           |                                                      |
+--------------------+------------------------------------------------------+
| Auditable          | Math documented in ``/specs``. No black boxes.      |
+--------------------+------------------------------------------------------+
| Vendor-neutral     | No cloud lock-in. Your data stays local.            |
+--------------------+------------------------------------------------------+
| Extensible         | Stable plugin SDK. Easy to add new providers.       |
+--------------------+------------------------------------------------------+


Installation
------------

.. code-block:: bash

   pip install flameiq-core

Requires Python 3.10+. No system dependencies.


Quick Start
-----------

**Step 1: Initialise**

.. code-block:: bash

   cd my-project
   flameiq init

**Step 2: Write a FlameIQ v1 metrics file**

.. code-block:: json

   {
     "schema_version": 1,
     "metadata": {
       "commit": "abc123",
       "branch": "main",
       "environment": "ci"
     },
     "metrics": {
       "latency": {
         "mean": 120.5,
         "p95": 180.0,
         "p99": 240.0
       },
       "throughput": 950.2,
       "memory_mb": 512.0
     }
   }

**Step 3: Set a baseline**

.. code-block:: bash

   flameiq baseline set --metrics benchmark.json

**Step 4: Compare on every PR**

.. code-block:: bash

   flameiq compare --metrics current.json --fail-on-regression

**Step 5: Generate an HTML report**

.. code-block:: bash

   flameiq report --metrics current.json --output report.html


GitHub Actions Integration
--------------------------

.. code-block:: yaml

   - name: Install FlameIQ
     run: pip install flameiq-core

   - name: Restore baseline cache
     uses: actions/cache@v4
     with:
       path: .flameiq/
       key: flameiq-${{ github.base_ref }}

   - name: Run benchmarks
     run: python run_benchmarks.py > metrics.json

   - name: Check for regressions
     run: flameiq compare --metrics metrics.json --fail-on-regression


Exit Codes
----------

+------+--------------------------------------------------+
| Code | Meaning                                          |
+======+==================================================+
| 0    | Pass — no regression detected                    |
+------+--------------------------------------------------+
| 1    | Regression — metric(s) exceeded threshold        |
+------+--------------------------------------------------+
| 2    | Configuration / baseline error                   |
+------+--------------------------------------------------+
| 3    | Metrics file invalid or unreadable               |
+------+--------------------------------------------------+


Python API
----------

.. code-block:: python

   from flameiq.schema.v1.models import PerformanceSnapshot
   from flameiq.core.comparator import compare_snapshots
   from flameiq.core.models import RegressionStatus
   from flameiq.storage.baseline_store import BaselineStore

   store = BaselineStore()
   baseline = store.load_baseline()

   current = PerformanceSnapshot.from_dict({
       "schema_version": 1,
       "metadata": {"commit": "def456"},
       "metrics": {"latency": {"p95": 185.0}, "throughput": 940.0},
   })

   result = compare_snapshots(baseline, current)

   if result.status == RegressionStatus.REGRESSION:
       for reg in result.regressions:
           print(f"  REGRESSION: {reg.metric_key} {reg.change_percent:+.2f}%")
   else:
       print("All metrics within threshold.")

   # Machine-readable JSON
   import json
   print(json.dumps(result.to_dict(), indent=2))


Configuration
-------------

``flameiq.yaml`` (created by ``flameiq init``):

.. code-block:: yaml

   thresholds:
     latency.p95:   10%
     latency.p99:   15%
     throughput:    -5%
     memory_mb:      8%

   baseline:
     strategy: rolling_median
     rolling_window: 5

   statistics:
     enabled: false
     confidence: 0.95

   provider: json


Documentation
-------------

Full documentation: https://docs.flameiq.dev

- `Installation Guide <https://docs.flameiq.dev/getting_started/installation.html>`_
- `Quick Start <https://docs.flameiq.dev/getting_started/quickstart.html>`_
- `CLI Reference <https://docs.flameiq.dev/cli/reference.html>`_
- `Configuration Reference <https://docs.flameiq.dev/guides/configuration.html>`_
- `Statistical Methodology Specification <https://docs.flameiq.dev/specs/statistical-methodology.html>`_
- `Schema v1 Specification <https://docs.flameiq.dev/specs/schema-v1.html>`_
- `Custom Provider Guide <https://docs.flameiq.dev/guides/custom-provider.html>`_


Contributing
------------

Contributions are welcome. Please read
`CONTRIBUTING.rst <https://github.com/flameiq/flameiq-core/blob/main/CONTRIBUTING.rst>`_
and open an issue before starting significant work.


License
-------

Apache License 2.0. See `LICENSE <https://github.com/flameiq/flameiq-core/blob/main/LICENSE>`_.

"FlameIQ" is a trademark of the FlameIQ project.
Use of the name or logo to endorse derived products requires written permission.
Contact: Angufibo Lincoln <angufibolinc@gmail.com>
