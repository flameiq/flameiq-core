.. _changelog:

Changelog
=========

All notable changes to FlameIQ are documented here.

The format follows `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_.
FlameIQ adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

----

`1.0.0`_ — 2026-03-01
----------------------

The first stable release of FlameIQ.

Added
~~~~~

**Core engine**

- Deterministic baseline vs. current snapshot comparison
  (:func:`~flameiq.core.comparator.compare_snapshots`)
- Configurable per-metric thresholds with direction-aware evaluation
  (``latency.*`` → higher-is-worse; ``throughput`` → lower-is-worse;
  ``custom.*`` → absolute deviation)
- Warning zone detection: metrics within 5 percentage points of their
  threshold emit a WARNING without failing the build
- Typed exception hierarchy with 12 exception classes
  (:mod:`flameiq.core.errors`)
- Machine-readable ``ComparisonResult.to_dict()`` for CI JSON output

**Schema v1**

- Immutable, versioned performance snapshot data model
  (:class:`~flameiq.schema.v1.models.PerformanceSnapshot`)
- Latency percentiles (mean, p50, p95, p99) in milliseconds
- Throughput (operations/requests per second)
- Memory (peak MB), CPU (percent utilisation)
- Custom user-defined numeric metrics (``metrics.custom``)
- Round-trip JSON serialisation via ``to_dict()`` / ``from_dict()``

**Baseline management**

- Three strategies: ``last_successful``, ``rolling_median``, ``tagged``
- Local filesystem storage: JSON baseline + append-only JSONL history
  (:class:`~flameiq.storage.baseline_store.BaselineStore`)
- Zero external services — fully offline

**Statistical engine**

- Optional Mann-Whitney U test (non-parametric, distribution-free)
  (:func:`~flameiq.engine.statistics.mann_whitney_compare`)
- Cohen's *d* effect size with verbal labels (negligible / small /
  medium / large)
- Noise-resistant median filter with warmup discard
  (:func:`~flameiq.engine.statistics.noise_filter_median`)
- Configurable confidence level (default: 95%)

**CLI**

- ``flameiq init`` — initialise project
- ``flameiq run`` — load and validate a snapshot
- ``flameiq compare`` — compare against baseline (``--fail-on-regression``,
  ``--json``)
- ``flameiq baseline set / show / promote / clear``
- ``flameiq report`` — self-contained offline HTML report
- ``flameiq validate`` — validate a metrics file

**Providers**

- ``json`` — native FlameIQ v1 JSON schema
- ``pytest-benchmark`` — adapter for ``pytest --benchmark-json`` output
- :class:`~flameiq.providers.base.MetricProvider` ABC for custom providers

**HTML report**

- Self-contained, offline-capable static HTML
- No CDN, no JavaScript frameworks
- Metric diff table with colour coding
- Summary pills (regressions / warnings / passed)
- Metadata cards (baseline commit, current commit, environment)

**Tooling**

- ``pyproject.toml`` with ruff, mypy (strict), pytest, coverage
- ``Makefile`` with ``make check``, ``make test``, ``make docs``
- GitHub Actions CI (Python 3.10 / 3.11 / 3.12 matrix)
- GitHub Actions release workflow (PyPI publish on tag)
- Pre-commit hooks (ruff, mypy, commitizen, trailing whitespace)
- Sphinx + sphinx-rtd-theme documentation (RST)

**Documentation** (https://docs.flameiq.dev)

- Getting Started: installation, quick start, CI integration
- User Guides: configuration, baseline strategies, custom providers
- CLI Reference (all commands)
- Architecture: overview, layers, schema design
- Specifications: Schema v1, Statistical Methodology, Threshold Algorithm,
  Exit Codes
- API Reference: all public modules
- Contributing: development setup, RFC process, testing standards

----

.. _1.0.0: https://github.com/flameiq/flameiq-core/releases/tag/v1.0.0

Unreleased
----------

v2 is currently in active development on the ``v2-dev`` branch.
All v1 commands remain fully supported and backward compatible.

Added
~~~~~

**Persistent run history**

- SQLite-backed local run history via :class:`~flameiq.v2.storage.history.HistoryStore`
- JSONL audit sidecar (``runs.jsonl``) alongside SQLite for human inspection
- ``flameiq v2 run`` — records every run into persistent local history
- ``flameiq v2 history`` — browse recent runs with branch and commit metadata

**Named baseline management**

- :class:`~flameiq.v2.storage.history.BaselineStoreV2` — named baseline
  files stored as individual JSON files in ``.flameiq/baselines/``
- ``flameiq v2 baseline set`` — set a named baseline (default: ``main``)
- ``flameiq v2 baseline promote`` — explicitly promote one named baseline
  to another (e.g. ``staging`` → ``main``)
- ``flameiq v2 baseline list`` — list all saved named baselines
- ``flameiq v2 baseline show`` — inspect metrics in a named baseline
- ``flameiq v2 baseline delete`` — delete a named baseline
- No auto-promotion — all baseline changes are explicit (trust through
  explicitness)

**Drift detection**

- :class:`~flameiq.v2.analysis.engine.DriftAnalyzer` — linear regression
  on time series to detect gradual performance degradation
- Catches slow regressions that never trigger single-run thresholds
  (e.g. +1% latency per commit for 20 commits = +20% cumulative)
- Drift flagged when: cumulative change ≥ threshold AND R² ≥ 0.30
- ``flameiq v2 drift`` — drift analysis with ``--fail-on-drift`` (exit code 5)
- Direction-aware: ``worsening`` vs ``improving``

**Trend analysis and time-travel**

- :class:`~flameiq.v2.analysis.engine.TrendAnalyzer` — multi-run trend
  computation per metric
- ``flameiq v2 trend --metric latency.p95 --last 30`` — single metric trend
- ``flameiq v2 trend --from abc123 --to def456`` — time-travel: compare
  any two commits directly from stored history
- Overall change, slope per run, R², and per-point change-from-first

**Performance budget enforcement**

- Budget ceilings in ``flameiq.yaml`` under ``budgets:`` block
- ``latency.p95: 200`` → fail if p95 exceeds 200ms (SLO enforcement)
- New exit code ``4`` for budget breach (separate from threshold regression)
- Budget breach takes precedence over threshold regression in exit code

**Correlation analysis**

- :class:`~flameiq.v2.analysis.engine.CorrelationAnalyzer` — rule-based
  multi-metric cause-effect detection
- Deterministic rule table (not AI/ML) — transparent and auditable
- Pearson correlation computed from run history
- Identifies primary regression driver with human-readable narrative
- Built-in rules: CPU→latency, memory→latency, throughput→latency

**Statistics engine (stdlib-only)**

- :func:`~flameiq.v2.statistics.engine.mann_whitney_u` — reimplemented
  from first principles using stdlib only (no scipy dependency in v2)
- :func:`~flameiq.v2.statistics.engine.bootstrap_mean_ci` — deterministic
  bootstrap confidence interval (fixed seed = reproducible)
- :func:`~flameiq.v2.statistics.engine.cohens_d` — standardized effect
  size with verbal labels
- :func:`~flameiq.v2.statistics.engine.detect_drift` — linear regression
  slope detection for drift analysis
- ``--statistical`` flag on ``flameiq v2 compare`` enables full analysis

**Rich HTML reports**

- :func:`~flameiq.v2.reporting.html_generator.generate_report` — new
  rich HTML report generator
- Baseline vs current diff table with color-coded status badges
- Metric trend charts (Chart.js via CDN, falls back offline)
- Drift analysis table with direction indicators
- Correlation findings with Pearson r and narrative
- Run history table (last 20 runs)
- Dark theme design with FlameIQ branding

**v2 CLI subgroup**

- All v2 commands accessible under ``flameiq v2 ...``
- v1 commands unchanged and fully backward compatible
- ``--json-output`` flag on all v2 commands for machine-readable output
- ``--no-fail`` flag on ``flameiq v2 compare`` for reporting-only mode

**v2 Configuration (flameiq.yaml)**

New v2 configuration blocks:

.. code-block:: yaml

   history:
     backend: sqlite
     max_runs: 500rbitrary
  key-value metadata
- :func:`~flameiq.v2.schema.ingest_metrics_file` — universal ingestion
  function accepting both v1 native format and flat benchmark output
- Full backward compatibility with v1 JSON snapshots

----

`1.0.2`_ — 2026-03-10

   drift:
     enabled: true
     threshold_percent: 5.0
     min_runs: 5
     window: 30

   budgets:
     latency.p95: 200
     memory_mb: 1024

   statistics:
     enabled: false
     confidence: 0.95
     noise_tolerance: 0.5

   correlation:
     enabled: true
     change_threshold: 5.0

   baseline:
     strategy: rolling_median
     window: 10
     name: main

**Schema v2**

- :class:`~flameiq.v2.schema.RunV2` — v2 run schema with extended metadata
- :class:`~flameiq.v2.schema.MetadataV2` — adds ``tags`` dict for a
----------------------

Changes to be included in the next release.

.. note::

   Add items here during development. They will be moved to a versioned
   section at release time.
