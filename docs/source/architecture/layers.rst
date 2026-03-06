.. _architecture_layers:

Module Layer Reference
======================

flameiq/schema/
---------------

**Dependency level:** 0 (no internal imports)

The schema layer defines the canonical, versioned data contract.
Once ``schema/v1/`` is released, it is **immutable**.

Key files:

* ``v1/models.py`` — ``PerformanceSnapshot``, ``Metrics``,
  ``LatencyMetrics``, ``SnapshotMetadata``, ``Environment``

flameiq/core/
-------------

**Dependency level:** 1 (imports ``schema/`` only)

Core contains the comparison engine, domain models, and typed exceptions.
This is the most critical module in the codebase.

Key files:

* ``comparator.py`` — ``compare_snapshots()``, ``compute_change_percent()``
* ``models.py`` — ``ComparisonResult``, ``MetricDiff``, ``RegressionStatus``
* ``thresholds.py`` — ``parse_threshold()``, ``evaluate_threshold()``
* ``errors.py`` — Full typed exception hierarchy

flameiq/engine/
---------------

**Dependency level:** 2 (imports ``core/``, ``schema/``)

Statistical algorithms and baseline selection strategies.

Key files:

* ``statistics.py`` — ``mann_whitney_compare()``, ``noise_filter_median()``
* ``baseline.py`` — ``select_baseline()``, ``BaselineStrategy``

flameiq/storage/
----------------

**Dependency level:** 2 (imports ``core/``, ``schema/``)

Filesystem-based persistence for baselines and run history.

Key files:

* ``baseline_store.py`` — ``BaselineStore``

flameiq/providers/
------------------

**Dependency level:** 1 (imports ``schema/`` only — never ``core/``)

Plugin adapters that convert any benchmark format into a
``PerformanceSnapshot``.

Key files:

* ``base.py`` — ``MetricProvider`` ABC
* ``json_provider.py`` — ``JsonProvider``
* ``pytest_provider.py`` — ``PytestBenchmarkProvider``
* ``registry.py`` — ``PROVIDER_REGISTRY``, ``get_provider()``, ``list_providers()``

flameiq/reporting/
------------------

**Dependency level:** 3 (imports ``engine/``, ``core/``, ``schema/``)

Generates self-contained HTML reports from comparison results.

Key files:

* ``html_generator.py`` — ``generate_report()``

flameiq/cli/
------------

**Dependency level:** Top (imports all layers)

Click-based CLI. Contains zero business logic — all computation is
delegated to the appropriate layer.

Key files:

* ``main.py`` — ``cli`` group, ``main()`` entry point
* ``commands/init.py``, ``run.py``, ``compare.py``, ``baseline.py``,
  ``report.py``, ``validate.py``
