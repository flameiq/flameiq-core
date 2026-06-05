.. _v2_cli_reference:

v2 CLI Reference
================

All v2 commands are accessed under the ``flameiq v2`` subgroup.
v1 commands remain available at the top level and are unchanged.

.. code-block:: bash

   flameiq v2 --help

----

flameiq v2 run
--------------

Record a performance snapshot into persistent local history.

.. code-block:: bash

   flameiq v2 run --metrics benchmark.json
   flameiq v2 run --metrics benchmark.json --commit abc123 --branch main
   flameiq v2 run --metrics benchmark.json --env staging --json-output

Unlike v1 ``flameiq run``, this command **stores the run in SQLite**
for later use by ``trend``, ``drift``, ``history``, and ``compare``.

**Options:**

.. code-block:: text

   --metrics PATH        Path to metrics JSON file. Required.
   --commit TEXT         Git commit SHA (auto-detected if omitted).
   --branch TEXT         Git branch name (auto-detected if omitted).
   --env TEXT            Environment label: ci, local, staging. Default: ci.
   --config PATH         Path to flameiq.yaml. Default: flameiq.yaml.
   --json-output         Emit JSON instead of human output.

**JSON output:**

.. code-block:: json

   {
     "status": "ok",
     "run_id": "550e8400-e29b-41d4-a716-446655440000",
     "commit": "abc123",
     "branch": "main",
     "environment": "ci",
     "metrics_recorded": 8,
     "flameiq_dir": ".flameiq"
   }

**Exit codes:** ``0`` success, ``2`` storage error, ``3`` metrics error.

----

flameiq v2 baseline
--------------------

Manage named baselines explicitly.

.. note::

   v2 uses **named baselines**. The default name is ``main``.
   You can maintain multiple named baselines simultaneously (e.g.
   ``main``, ``release-1.2``, ``staging``).

flameiq v2 baseline set
~~~~~~~~~~~~~~~~~~~~~~~~

Promote recent run history to a named baseline.

.. code-block:: bash

   flameiq v2 baseline set
   flameiq v2 baseline set --name release-1.2
   flameiq v2 baseline set --strategy rolling_median --window 20
   flameiq v2 baseline set --json-output

**Options:**

.. code-block:: text

   --name TEXT           Name for this baseline. Default: main.
   --strategy TEXT       last_successful | rolling_median. Default from config.
   --window INT          Window size for rolling_median. Default from config.
   --config PATH         Path to flameiq.yaml.
   --json-output         Emit JSON output.

flameiq v2 baseline promote
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Promote one named baseline to another name.

.. code-block:: bash

   flameiq v2 baseline promote staging main


**Exit codes:**

.. list-table::
   :header-rows: 1
   :widths: 10 90

   * - Code
     - Meaning
   * - ``0``
     - Pass — all metrics within thresholds
   * - ``1``
     - Regression — threshold exceeded
   * - ``2``
     - Configuration or baseline error
   * - ``3``
     - Invalid or missing metrics file

----

flameiq v2 baseline list
~~~~~~~~~~~~~~~~~~~~~~~~~

List all saved named baselines.

.. code-block:: bash

   flameiq v2 baseline list

flameiq v2 baseline show
~~~~~~~~~~~~~~~~~~~~~~~~~

Show metrics stored in a named baseline.

.. code-block:: bash

   flameiq v2 baseline show
   flameiq v2 baseline show --name release-1.2

flameiq v2 baseline delete
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Delete a named baseline.

.. code-block:: bash

   flameiq v2 baseline delete release-1.2

----

flameiq v2 compare
-------------------

Compare current run against a named baseline with full v2 analysis.

.. code-block:: bash

   flameiq v2 compare
   flameiq v2 compare --baseline main
   flameiq v2 compare --metrics benchmark.json --statistical
   flameiq v2 compare --json-output
   flameiq v2 compare --no-fail

**Options:**

.. code-block:: text

   --metrics PATH        Metrics file. Uses last recorded run if omitted.
   --baseline TEXT       Named baseline to compare against. Default from config.
   --statistical         Enable Mann-Whitney U + bootstrap CI analysis.
   --config PATH         Path to flameiq.yaml.
   --json-output         Emit JSON output.
   --no-fail             Always exit 0 (report regressions, don't fail CI).

**What v2 compare adds over v1:**

- Budget ceiling enforcement (exit code 4 on breach)
- Optional statistical significance testing with bootstrap CI
- Correlation analysis narrative when regressions detected
- Named baseline selection

**Exit codes:**

.. list-table::
   :header-rows: 1
   :widths: 10 90

   * - Code
     - Meaning
   * - ``0``
     - Pass — all metrics within thresholds
   * - ``1``
     - Regression — threshold exceeded
   * - ``2``
     - Configuration or baseline error
   * - ``3``
     - Invalid or missing metrics file
   * - ``4``
     - Budget breach — absolute ceiling exceeded

----

flameiq v2 trend
-----------------

Analyze performance trends and detect drift over time.

.. code-block:: bash

   # Single metric trend
   flameiq v2 trend --metric latency.p95 --last 30

   # All metrics
   flameiq v2 trend --last 20

   # Time-travel: compare two specific commits
   flameiq v2 trend --from abc123 --to def456

   # Filter by branch
   flameiq v2 trend --metric latency.p95 --branch main

**Options:**

.. code-block:: text

   --metric TEXT         Metric to analyze. Omit to show all.
   --last INT            Number of recent runs to include. Default: 30.
   --branch TEXT         Filter to a specific branch.
   --from TEXT           Compare FROM this commit (requires --to).
   --to TEXT             Compare TO this commit (requires --from).
   --drift-threshold FLOAT  Minimum cumulative % change to flag drift. Default: 5.0.
   --config PATH         Path to flameiq.yaml.
   --json-output         Emit JSON output.

**Single metric output example:**

.. code-block:: text

   Trend: latency.p95
     runs:           30
     first value:    2.4500
     last value:     2.8900
     overall change: +17.96%
     slope/run:      +0.0147%
     R²:             0.812
     ⚠ DRIFT: WORSENING  cumulative +17.96%

**Time-travel output example:**

.. code-block:: text

   Time-travel comparison: abc1234 → def5678

   METRIC                         FROM          TO      CHANGE
   ──────────────────────────────────────────────────────────
   latency.p95                   2.450       4.510     +84.08%
   throughput                   412.30      231.50     -43.84%

----

flameiq v2 drift
-----------------

Detect gradual performance degradation across multiple runs.

Drift catches slow regressions that never trigger single-run thresholds —
for example, +1% latency per commit for 20 commits = +20% total.

.. code-block:: bash

   flameiq v2 drift
   flameiq v2 drift --window 50 --threshold 3.0
   flameiq v2 drift --branch main --json-output
   flameiq v2 drift --fail-on-drift

**Drift is flagged when:**

- Cumulative change ≥ ``threshold_percent`` (default 5%)
- Linear fit R² ≥ 0.30 (trend is real, not noise)
- At least ``min_runs`` data points available

**Options:**

.. code-block:: text

   --window INT          Number of recent runs to analyze. Default from config.
   --threshold FLOAT     Minimum cumulative % to flag drift. Default from config.
   --min-runs INT        Minimum runs required before flagging.
   --branch TEXT         Filter to a specific branch.
   --config PATH         Path to flameiq.yaml.
   --json-output         Emit JSON output.
   --fail-on-drift       Exit with code 5 if drift is detected.

**Output example:**

.. code-block:: text

   Drift Analysis — last 30 runs  (threshold: 5.0%  R² ≥ 0.30)

   METRIC                    SLOPE/RUN   CUMULATIVE   R²              STATUS
   ────────────────────────────────────────────────────────────────────────
   latency.p95               +0.0147%      +17.96%  0.81   ▲ WORSENING
   throughput                -0.0082%       -9.84%  0.62   ▼ WORSENING
   memory_mb                 +0.0001%       +0.12%  0.04       ✓ stable

   ⚠  Drifting metrics (2): latency.p95, throughput

**Exit codes:** ``0`` no drift, ``5`` drift detected (only with ``--fail-on-drift``).

----

flameiq v2 history
-------------------

Show recent run history stored in the local SQLite database.

.. code-block:: bash

   flameiq v2 history
   flameiq v2 history --last 50
   flameiq v2 history --branch main
   flameiq v2 history --json-output

**Options:**

.. code-block:: text

   --last INT            Number of runs to show. Default: 20.
   --branch TEXT         Filter by branch.
   --config PATH         Path to flameiq.yaml.
   --json-output         Emit JSON output.

**Output example:**

.. code-block:: text

   Run History — showing 20 of 47 runs

   COMMIT     BRANCH           ENV        TIMESTAMP             p95 LAT   THROUGHPUT
   ──────────────────────────────────────────────────────────────────────────────────
   abc1234    main             ci         2026-03-09 14:22       2.4ms         412
   def5678    feat/refactor    ci         2026-03-09 15:31       4.5ms         231

----

flameiq v2 report
------------------

Generate a rich offline HTML performance report.

.. code-block:: bash

   flameiq v2 report
   flameiq v2 report --output perf-report.html --last 50
   flameiq v2 report --metric latency.p95 --metric throughput

**The report includes:**

- Baseline vs current comparison table (color-coded)
- Drift analysis across recent runs
- Metric correlation findings with narrative
- Time-series trend charts per metric (Chart.js)
- Run history table
- Zero external assets — 100% offline static HTML

**Options:**

.. code-block:: text

   --output PATH         Output path for HTML report. Default: .flameiq/report.html.
   --last INT            Number of recent runs in trend charts. Default: 30.
   --metric TEXT         Specific metrics to chart. Repeatable. Default: all.
   --baseline TEXT       Named baseline for comparison section.
   --title TEXT          Report title. Default: FlameIQ Performance Report.
   --branch TEXT         Filter history to a branch.
   --config PATH         Path to flameiq.yaml.

**Exit codes:** ``0`` success, ``3`` no run history.
