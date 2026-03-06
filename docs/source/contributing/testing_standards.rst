.. _contributing_testing:

Testing Standards
=================

FlameIQ has high testing standards. The core comparison engine is
mathematically critical, and bugs here cause missed regressions in
production systems at scale.

Test organisation
-----------------

.. code-block:: text

   tests/
   ├── unit/
   │   ├── test_core/          # comparator, thresholds, models
   │   ├── test_engine/        # statistics, baseline strategies
   │   ├── test_schema/        # schema models, serialisation
   │   ├── test_storage/       # baseline store
   │   └── test_providers/     # json, pytest-benchmark providers
   ├── statistical/            # Algorithm correctness on known distributions
   ├── integration/            # Full end-to-end pipeline tests
   ├── e2e/                    # CLI invocation tests
   └── fixtures/               # Shared test data and snapshot builders

Coverage requirements
---------------------

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Module
     - Minimum coverage
     - Notes
   * - ``core/``
     - 95%
     - Critical path. All branches must be tested.
   * - ``schema/``
     - 100%
     - Immutable contract. Every field validated.
   * - ``engine/``
     - 90%
     - All statistical paths tested with known inputs.
   * - ``storage/``
     - 85%
     - Including corruption recovery and empty history.
   * - ``providers/``
     - 80%
     - Valid, invalid, missing file for each provider.
   * - ``cli/``
     - 75%
     - Integration tests count toward CLI coverage.

Determinism tests
-----------------

Any function in ``core/`` or ``engine/`` that is advertised as
deterministic **must** have a determinism test:

.. code-block:: python

   @pytest.mark.determinism
   def test_compare_snapshots_is_deterministic():
       results = [
           compare_snapshots(BASELINE, CURRENT)
           for _ in range(100)
       ]
       first = results[0]
       for r in results[1:]:
           assert r.status == first.status
           assert r.exit_code == first.exit_code
           for d1, d2 in zip(r.diffs, first.diffs):
               assert d1.change_percent == d2.change_percent

Statistical tests
-----------------

Statistical tests use **analytically known** distributions — never
random data:

.. code-block:: python

   @pytest.mark.statistical
   @pytest.mark.parametrize("p95_current,threshold,expected", [
       (105.0, "10%", RegressionStatus.PASS),       # +5.0% < threshold
       (110.0, "10%", RegressionStatus.PASS),       # +10.0% = threshold (pass)
       (110.1, "10%", RegressionStatus.REGRESSION), # +10.1% > threshold
       (115.0, "10%", RegressionStatus.REGRESSION), # +15.0% > threshold
   ])
   def test_latency_threshold(p95_current, threshold, expected):
       baseline = make_snapshot(p95=100.0)
       current  = make_snapshot(p95=p95_current)
       result   = compare_snapshots(
           baseline, current,
           threshold_config={"latency.p95": threshold},
       )
       assert result.status == expected

Fixture conventions
-------------------

* Use ``tmp_path`` (pytest built-in) for all filesystem tests — never
  write to the actual project directory
* Use ``make_snapshot()`` from ``tests/fixtures/`` for all snapshot
  construction — never construct snapshots inline in tests
* Mark all tests with the appropriate marker: ``unit``,
  ``integration``, ``statistical``, ``determinism``
