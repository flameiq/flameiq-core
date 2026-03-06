.. _cli_reference:

CLI Reference
=============

The ``flameiq`` command-line interface is the primary interface for FlameIQ.
Every command supports ``--help`` for inline documentation.

.. code-block:: bash

   flameiq --help
   flameiq compare --help

Global options
--------------

These options apply to all commands:

.. code-block:: text

   --version           Show the version and exit.
   --verbose, -v       Enable debug-level logging.
   --config PATH       Path to flameiq.yaml. Default: ./flameiq.yaml
   --help              Show this message and exit.

----

flameiq init
------------

Initialise FlameIQ in the current project directory.

.. code-block:: bash

   flameiq init
   flameiq init --force    # Overwrite existing flameiq.yaml

**What it does:**

* Creates ``flameiq.yaml`` with annotated defaults
* Creates ``.flameiq/baselines/`` directory structure
* Appends ``.flameiq/baselines/`` to ``.gitignore`` if it exists

**Options:**

.. code-block:: text

   --force, -f    Overwrite flameiq.yaml if it already exists.

**Exit codes:** ``0`` success, ``2`` filesystem error.

----

flameiq run
-----------

Load and validate a metrics snapshot from a file.

.. code-block:: bash

   flameiq run --metrics benchmark.json
   flameiq run --metrics benchmark.json --provider pytest-benchmark
   flameiq run --metrics benchmark.json --output snapshot.json
   flameiq run --metrics benchmark.json --json

Use this command to verify that your metrics file is valid before
setting a baseline or running a comparison.

**Options:**

.. code-block:: text

   --metrics, -m PATH    Path to the metrics file. Required.
   --provider, -p TEXT   Metric provider to use. Default: json.
   --output, -o PATH     Write the normalised snapshot to this path (optional).
   --json                Output result as machine-readable JSON.

**Exit codes:**

.. list-table::
   :widths: 10 90

   * - ``0``
     - Snapshot loaded and validated successfully
   * - ``3``
     - Metrics file invalid, missing, or cannot be parsed

----

flameiq compare
---------------

Compare the current run against the stored baseline.

.. code-block:: bash

   flameiq compare --metrics current.json
   flameiq compare --metrics current.json --fail-on-regression
   flameiq compare --metrics current.json --provider pytest-benchmark --json

**Options:**

.. code-block:: text

   --metrics, -m PATH       Current metrics file. Required.
   --provider, -p TEXT      Metric provider. Default: json.
   --fail-on-regression     Exit with code 1 if any regression is detected.
                            Default: true.
   --json                   Output the full comparison result as JSON.

**JSON output format:**

.. code-block:: json

   {
     "status": "regression",
     "exit_code": 1,
     "baseline_commit": "abc123",
     "current_commit": "def456",
     "statistical_mode": false,
     "summary": "1 regression(s) in: latency.p95",
     "counts": {
       "regressions": 1, "warnings": 0, "passed": 4, "total": 5
     },
     "diffs": [
       {
         "metric_key": "latency.p95",
         "baseline_value": 180.0,
         "current_value": 210.5,
         "change_percent": 16.9444,
         "threshold_percent": 10.0,
         "is_regression": true,
         "is_warning": false,
         "status": "REGRESSION"
       }
     ]
   }

**Exit codes:**

.. list-table::
   :widths: 10 90

   * - ``0``
     - No regression detected
   * - ``1``
     - Regression detected (with ``--fail-on-regression``)
   * - ``2``
     - Configuration error or no baseline available
   * - ``3``
     - Metrics file error

----

flameiq baseline
----------------

The ``baseline`` group manages stored baseline snapshots.

flameiq baseline set
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   flameiq baseline set --metrics benchmark.json
   flameiq baseline set --metrics release.json --tag v1.0.0
   flameiq baseline set --metrics benchmark.json --strategy rolling_median

**Options:**

.. code-block:: text

   --metrics, -m PATH    Metrics file to store as baseline. Required.
   --provider, -p TEXT   Metric provider. Default: json.
   --strategy TEXT       Baseline selection strategy.
                         Choices: last_successful, rolling_median, tagged.
                         Default: last_successful.
   --tag TEXT            Tag this baseline (e.g. "v1.0.0").

**Exit codes:** ``0`` success, ``3`` metrics error.

flameiq baseline show
~~~~~~~~~~~~~~~~~~~~~

Display the current baseline snapshot.

.. code-block:: bash

   flameiq baseline show

**Exit codes:** ``0`` success, ``2`` no baseline found.

flameiq baseline promote
~~~~~~~~~~~~~~~~~~~~~~~~

Mark the latest run as the new baseline. A convenience alias for
``baseline set`` using the most recently loaded metrics.

.. code-block:: bash

   flameiq baseline promote

flameiq baseline clear
~~~~~~~~~~~~~~~~~~~~~~

Delete all stored baselines and run history. **Destructive.**

.. code-block:: bash

   flameiq baseline clear    # Prompts for confirmation

**Exit codes:** ``0`` success, ``2`` filesystem error.

----

flameiq report
--------------

Generate a self-contained, offline-capable HTML comparison report.

.. code-block:: bash

   flameiq report --metrics current.json
   flameiq report --metrics current.json --output ./reports/pr-42.html

The report includes:

* Pass/regression/warning banner
* Metadata table (baseline commit, current commit, environment)
* Summary pill counts (regressions, warnings, passed)
* Full per-metric diff table with colour coding
* Percentage change bars

**Options:**

.. code-block:: text

   --metrics, -m PATH    Current metrics file. Required.
   --provider, -p TEXT   Metric provider. Default: json.
   --output, -o PATH     Output path for the HTML file.
                         Default: .flameiq/report.html.

**Exit codes:** ``0`` success, ``2`` no baseline, ``3`` metrics error.

----

flameiq validate
----------------

Validate a metrics file against the FlameIQ v1 schema.

.. code-block:: bash

   flameiq validate benchmark.json
   flameiq validate benchmark.json --provider pytest-benchmark
   flameiq validate --list-providers
   flameiq validate benchmark.json --json

**Options:**

.. code-block:: text

   METRICS_FILE             Path to the metrics file to validate.
   --provider, -p TEXT      Provider to use. Default: json.
   --list-providers         List all registered providers and exit.
   --json                   Output result as JSON.

**JSON output (valid):**

.. code-block:: json

   { "valid": true, "schema_version": 1, "metrics_count": 5 }

**JSON output (invalid):**

.. code-block:: json

   { "valid": false, "error": "Provider 'json' could not validate..." }

**Exit codes:** ``0`` valid, ``3`` invalid.
