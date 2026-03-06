=========
Changelog
=========

All notable changes to FlameIQ are documented here.

The format follows `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_.
FlameIQ adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

----

`1.0.0`_ — 2026-03-01
======================

First stable release of FlameIQ.

Added
-----

- Deterministic baseline vs. current snapshot comparison with configurable
  per-metric thresholds
- Schema v1: immutable, versioned ``PerformanceSnapshot`` data model
  (latency percentiles, throughput, memory, CPU, custom metrics)
- Three baseline strategies: ``last_successful``, ``rolling_median``, ``tagged``
- Optional Mann-Whitney U significance test with Cohen's *d* effect size
- CLI: ``init``, ``run``, ``compare``, ``baseline``, ``report``, ``validate``
- Built-in providers: ``json`` (native schema), ``pytest-benchmark`` adapter
- ``MetricProvider`` ABC for custom providers
- Self-contained offline HTML comparison report
- Local JSON + JSONL filesystem storage — zero external services
- Full Sphinx/RST documentation at https://docs.flameiq.dev
- GitHub Actions CI (Python 3.10 / 3.11 / 3.12)
- Formal specifications: Schema v1, Statistical Methodology, Threshold
  Algorithm, Exit Codes

.. _1.0.0: https://github.com/flameiq/flameiq-core/releases/tag/v1.0.0

----

Unreleased
==========

*Changes to be included in the next release.*
