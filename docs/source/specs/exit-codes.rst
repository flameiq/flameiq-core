.. _spec_exit_codes:

Exit Code Specification
========================

:Status: Stable / Immutable

FlameIQ uses a fixed set of exit codes. These are part of the public API
and will never change. CI systems should rely on them unconditionally.

.. list-table::
   :header-rows: 1
   :widths: 10 30 60

   * - Code
     - Name
     - When returned
   * - ``0``
     - **PASS**
     - No regression detected. All metrics within thresholds.
       Also returned by non-comparison commands on success.
   * - ``1``
     - **REGRESSION**
     - One or more metrics exceeded their configured threshold.
       Only returned by ``compare`` when ``--fail-on-regression`` is set.
   * - ``2``
     - **CONFIG_ERROR**
     - ``flameiq.yaml`` is missing or malformed.
       No baseline exists where one is required.
       Storage filesystem error.
   * - ``3``
     - **METRICS_ERROR**
     - The metrics file does not exist.
       The metrics file is not valid JSON.
       The provider cannot parse the file format.
       The snapshot fails schema validation.

Using exit codes in CI
-----------------------

.. code-block:: bash

   flameiq compare --metrics current.json --fail-on-regression
   EXIT=$?

   if [ $EXIT -eq 0 ]; then
     echo "✓ No regressions"
   elif [ $EXIT -eq 1 ]; then
     echo "✗ Regression detected — failing build"
     exit 1
   elif [ $EXIT -eq 2 ]; then
     echo "⚠ FlameIQ configuration error"
     exit 2
   elif [ $EXIT -eq 3 ]; then
     echo "⚠ Metrics file error"
     exit 3
   fi

Using JSON output with exit codes
-----------------------------------

The ``--json`` flag does not affect the exit code. Both can be used
together:

.. code-block:: bash

   RESULT=$(flameiq compare --metrics current.json --json)
   EXIT=$?

   echo "$RESULT" | python3 -c "
   import json, sys
   r = json.load(sys.stdin)
   for d in r['diffs']:
       if d['is_regression']:
           print(f\"  REGRESSION: {d['metric_key']} {d['change_percent']:+.2f}%\")
   "

   [ $EXIT -eq 0 ] || exit $EXIT
