.. _quickstart:

Quick Start
===========

This guide takes you from zero to a working regression check in under
five minutes.

Step 1 — Initialise FlameIQ
-----------------------------

Run this in your project root:

.. code-block:: bash

   cd my-project
   flameiq init

This creates two things:

* ``flameiq.yaml`` — your project configuration file (edit thresholds here)
* ``.flameiq/`` — local storage directory (add to ``.gitignore``)

The generated ``flameiq.yaml`` looks like this:

.. code-block:: yaml

   thresholds:
     latency.p95:  10%
     latency.p99:  15%
     throughput:   -5%
     memory_mb:     8%

   baseline:
     strategy: rolling_median
     rolling_window: 5

   statistics:
     enabled: false
     confidence: 0.95

   provider: json

Step 2 — Prepare benchmark output
-----------------------------------

Write your benchmark results as a FlameIQ v1 JSON file:

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
         "p95":  180.0,
         "p99":  240.0
       },
       "throughput": 950.2,
       "memory_mb":  512.0
     }
   }

Save this as ``benchmark.json``. For pytest-benchmark, see
:doc:`../guides/custom_provider`

Validate the file before using it:

.. code-block:: bash

   flameiq validate benchmark.json
   # ✓ Valid — 5 metrics found in benchmark.json

Step 3 — Set a baseline
------------------------

On your stable branch (e.g. ``main``), run your benchmarks and set the
baseline:

.. code-block:: bash

   flameiq baseline set --metrics benchmark.json

   # ✓ Baseline set
   #   Strategy: last_successful
   #   Commit:   abc123
   #   Metrics:  5 values stored

Step 4 — Compare on every pull request
----------------------------------------

On your feature branch, re-run your benchmarks and compare:

.. code-block:: bash

   flameiq compare --metrics current.json --fail-on-regression

**If all metrics pass:**

.. code-block:: text

   ┏━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┓
   ┃ Metric        ┃ Baseline ┃ Current  ┃ Change ┃ Threshold ┃ Status    ┃
   ┡━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━┩
   │ latency.mean  │ 120.50   │ 121.20   │ +0.58% │ ±10.0%    │ PASS      │
   │ latency.p95   │ 180.00   │ 182.00   │ +1.11% │ ±10.0%    │ PASS      │
   │ latency.p99   │ 240.00   │ 242.00   │ +0.83% │ ±15.0%    │ PASS      │
   │ memory_mb     │ 512.00   │ 515.00   │ +0.59% │ ±8.0%     │ PASS      │
   │ throughput    │ 950.20   │ 948.00   │ -0.23% │ ±5.0%     │ PASS      │
   └───────────────┴──────────┴──────────┴────────┴───────────┴───────────┘

   Status: PASS — All metrics within thresholds.

FlameIQ exits with code ``0``. Your CI pipeline continues.

**If a regression is detected:**

.. code-block:: text

   Status: REGRESSION — 1 metric(s) exceeded threshold.
   Exit code: 1

FlameIQ exits with code ``1``. Your CI pipeline fails.

Step 5 — Generate an HTML report
----------------------------------

.. code-block:: bash

   flameiq report \
     --metrics current.json \
     --output .flameiq/report.html

Open ``report.html`` in any browser. No internet connection required.

Step 6 — Advance the baseline
-------------------------------

After merging a passing PR, update the baseline on ``main``:

.. code-block:: bash

   flameiq baseline set --metrics benchmark.json

This appends the run to the history file (``history.jsonl``) and updates
``current.json`` as the new active baseline.

That's it
---------

Your performance gate is now live. Any PR that degrades a tracked metric
beyond its threshold will fail CI automatically.

Next steps:

* :ref:`ci_integration` — GitHub Actions, GitLab CI, Jenkins examples
* :ref:`configuration` — Tune thresholds and baseline strategies
* :ref:`cli_reference` — Full CLI reference
