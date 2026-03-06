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

Changes to be included in the next release.

.. note::

   Add items here during development. They will be moved to a versioned
   section at release time.
