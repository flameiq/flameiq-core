.. _configuration:

Configuration Reference
=======================

FlameIQ is configured via ``flameiq.yaml`` in your project root. Run
``flameiq init`` to generate the file with annotated defaults.

Complete example
----------------

.. code-block:: yaml

   # flameiq.yaml
   # Full reference: https://docs.flameiq.dev/guides/configuration.html

   # ── Regression Thresholds ────────────────────────────────────────────────
   thresholds:
     latency.mean:  10%    # Allow up to 10% mean latency increase
     latency.p50:   10%
     latency.p95:   10%    # Primary regression signal — recommended
     latency.p99:   15%    # Tail latency — wider tolerance
     throughput:    -5%    # Allow up to 5% throughput decrease
     memory_mb:      8%    # Allow up to 8% memory increase
     cpu_percent:   10%
     custom.score:   5%    # User-defined metric

   # ── Performance Budgets (v2 only) ────────────────────────────────────────
   # Absolute ceilings — exit code 4 if exceeded (SLO enforcement)
   budgets:
     latency.p95:  200      # never exceed 200ms p95
     memory_mb:   1024      # never exceed 1GB

   # ── Baseline Management ──────────────────────────────────────────────────
   baseline:
     strategy: rolling_median    # last_successful | rolling_median | tagged
     rolling_window: 5           # Used only with rolling_median
     name: main                  # named baseline to use (v2 only)

   # ── Statistical Significance Testing ────────────────────────────────────
   statistics:
     enabled: false              # Enable Mann-Whitney U test
     confidence: 0.95            # 95% confidence level
     noise_tolerance: 0.5        # % band to absorb benchmark noise (v2 only)

  # ── Drift Detection (v2 only) ────────────────────────────────────────────
   drift:
     enabled: true
     threshold_percent: 5.0      # cumulative % change to flag drift
     min_runs: 5                 # minimum runs before flagging
     window: 30                  # look-back window in runs

   # ── Correlation Analysis (v2 only) ───────────────────────────────────────
   correlation:
     enabled: true
     change_threshold: 5.0       # minimum % change to consider correlated

   # ── Run History (v2 only) ────────────────────────────────────────────────
   history:
     backend: sqlite             # sqlite | jsonl
     max_runs: 500

   # ── Noise Handling ───────────────────────────────────────────────────────
   noise:
     warmup_runs: 0              # Discard N leading samples before computing

   # ── Metric Provider ──────────────────────────────────────────────────────
   provider: json                # json | pytest-benchmark

Thresholds
----------

Thresholds define how much change is allowed before a metric is declared
a regression. They are percent strings with an optional sign:

.. code-block:: yaml

   thresholds:
     latency.p95: 10%     # ← positive: allow up to 10% increase
     throughput:  -5%     # ← negative: allow up to 5% decrease

See :ref:`spec_threshold_algorithm` for the full specification.

Direction semantics
~~~~~~~~~~~~~~~~~~~

FlameIQ applies direction-aware logic for known metrics:

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Metric
     - Regression when…
     - Example threshold
   * - ``latency.*``
     - ``change_percent`` > +threshold
     - ``10%``
   * - ``memory_mb``
     - ``change_percent`` > +threshold
     - ``8%``
   * - ``cpu_percent``
     - ``change_percent`` > +threshold
     - ``10%``
   * - ``throughput``
     - ``change_percent`` < -(threshold)
     - ``-5%`` or ``5%``
   * - ``custom.*``
     - abs(``change_percent``) > abs(threshold)
     - ``5%``

The default threshold is **10%** for any metric not explicitly configured.

Per-metric threshold examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   thresholds:
     # Strict: production API latency gate
     latency.p95:  5%
     latency.p99: 10%

     # Relaxed: noisy ML inference benchmark
     latency.mean: 20%

     # Throughput: allow 10% drop
     throughput: 10%

     # Custom metrics from your benchmark
     custom.tokens_per_second: -8%
     custom.db_query_ms:        5%

Baseline strategies
-------------------

The baseline strategy controls *which* snapshot is used as the reference
point for each comparison.

``last_successful`` (default)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the most recently stored snapshot. Simple, predictable, and correct for
most use cases.

.. code-block:: yaml

   baseline:
     strategy: last_successful

``rolling_median``
~~~~~~~~~~~~~~~~~~

Compute a synthetic baseline from the **median** of the last *N* snapshots.
More resistant to noise from a single outlier run. Recommended for
benchmarks running on shared CI infrastructure.

.. code-block:: yaml

   baseline:
     strategy: rolling_median
     rolling_window: 5    # Use last 5 runs (default)

The synthetic baseline uses median values for each metric key individually.

``tagged``
~~~~~~~~~~

Use a snapshot explicitly tagged with a release label. Useful for
comparing all PRs against a known-good release.

.. code-block:: yaml

   baseline:
     strategy: tagged

Tag a snapshot at release time:

.. code-block:: bash

   flameiq baseline set --metrics release.json --tag v1.0.0

Future PRs will compare against the ``v1.0.0`` baseline.

Statistical mode
----------------

When enabled, FlameIQ applies the **Mann-Whitney U test** alongside
threshold comparison. A regression is only declared if *both* the threshold
is exceeded *and* the difference is statistically significant.

.. code-block:: yaml

   statistics:
     enabled: true
     confidence: 0.95    # 95% confidence (α = 0.05)

Requires at least 3 samples per metric (configurable).

.. note::

   Statistical mode requires your benchmark to produce *sample arrays*
   rather than single summary values. See the
   :ref:`statistical-methodology` specification for details.

Noise handling
--------------

If your benchmark framework produces multiple raw timing samples,
FlameIQ can discard leading warmup samples before computing medians:

.. code-block:: yaml

   noise:
     warmup_runs: 2    # Discard the first 2 samples

Config file location
--------------------

By default FlameIQ looks for ``flameiq.yaml`` in the current working
directory. Override with the global ``--config`` option:

.. code-block:: bash

   flameiq --config path/to/custom.yaml compare --metrics metrics.json

Budgets (v2 only)
-----------------

Budgets enforce **absolute ceilings** rather than relative changes.
A budget breach exits with code ``4`` regardless of the threshold result.

.. code-block:: yaml

   budgets:
     latency.p95:  200    # fail if p95 exceeds 200ms
     memory_mb:   1024    # fail if memory exceeds 1024MB

Use budgets for SLO enforcement — a hard limit that must never be
crossed regardless of how good the baseline is.

Drift configuration (v2 only)
------------------------------

.. code-block:: yaml

   drift:
     enabled: true
     threshold_percent: 5.0   # flag if cumulative change ≥ 5%
     min_runs: 5               # require at least 5 runs
     window: 30                # analyze last 30 runs

Drift is flagged when **both** conditions are true:

1. Cumulative change ≥ ``threshold_percent``
2. Linear fit R² ≥ 0.30 (trend is real, not noise)

Correlation configuration (v2 only)
-------------------------------------

.. code-block:: yaml

   correlation:
     enabled: true
     change_threshold: 5.0   # only consider metrics that changed ≥ 5%

When regressions are detected, FlameIQ applies a rule-based correlation
table to identify the primary driver (e.g. CPU increase causing latency
increase). This is deterministic and auditable — not AI.
