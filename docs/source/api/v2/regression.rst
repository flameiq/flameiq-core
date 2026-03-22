.. _api_v2_regression:

flameiq.v2.regression — Regression Engine
==========================================

The v2 regression engine extends v1 threshold detection with budget
ceiling enforcement and optional statistical analysis.

RegressionEngine
----------------

.. automodule:: flameiq.v2.regression
   :members: RegressionEngine, ComparisonResult, MetricResult, StatDetail

Exit codes
----------

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Constant
     - Value
     - Meaning
   * - ``EXIT_PASS``
     - ``0``
     - All metrics within thresholds and budgets
   * - ``EXIT_REGRESSION``
     - ``1``
     - One or more metrics exceeded threshold
   * - ``EXIT_CONFIG_ERROR``
     - ``2``
     - Configuration or baseline error
   * - ``EXIT_INVALID_METRICS``
     - ``3``
     - Metrics file invalid or unreadable
   * - ``EXIT_BUDGET_BREACH``
     - ``4``
     - Absolute budget ceiling exceeded
   * - ``EXIT_DRIFT_DETECTED``
     - ``5``
     - Drift detected (only when ``--fail-on-drift`` set)
