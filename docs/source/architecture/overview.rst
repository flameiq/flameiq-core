.. _architecture_overview:

Architecture Overview
=====================

FlameIQ is built on three principles that drive all architectural decisions:

1. **Strict layering** — dependencies flow in one direction only
2. **Determinism first** — every module in ``core/`` and ``engine/`` is
   mathematically deterministic given fixed inputs
3. **Zero external runtime requirements** — the engine works without a
   network, without a database, and without any cloud service

Module layers
-------------

.. code-block:: text

   ┌──────────────────────────────────────────────────────────┐
   │                        CLI Layer                         │
   │   flameiq/cli/          Top-level consumer only.         │
   │                         No business logic here.          │
   ├──────────────────────────────────────────────────────────┤
   │              Reporting Layer                             │
   │   flameiq/reporting/    HTML report generation.          │
   │                         Reads from engine + schema.      │
   ├──────────────────────────────────────────────────────────┤
   │    Storage Layer           Engine Layer                  │
   │    flameiq/storage/        flameiq/engine/               │
   │    Baseline & history      Statistics, baseline          │
   │    persistence.            selection strategies.         │
   ├──────────────────────────────────────────────────────────┤
   │                       Core Layer                         │
   │   flameiq/core/         Comparison engine, domain        │
   │                         models, threshold evaluation,    │
   │                         typed exception hierarchy.       │
   ├──────────────────────────────────────────────────────────┤
   │    Schema Layer             Providers Layer              │
   │    flameiq/schema/v1/       flameiq/providers/           │
   │    Versioned data           Plugin adapters.             │
   │    contracts.               Depend only on schema/.      │
   │    No dependencies.                                      │
   └──────────────────────────────────────────────────────────┘

Dependency rules
----------------

These rules are enforced in CI and must never be violated:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Module
     - Allowed to import from
   * - ``schema/``
     - Nothing else in FlameIQ (zero internal deps)
   * - ``core/``
     - ``schema/`` only
   * - ``engine/``
     - ``core/``, ``schema/``
   * - ``storage/``
     - ``core/``, ``schema/``
   * - ``providers/``
     - ``schema/`` only — never ``core/`` or ``engine/``
   * - ``reporting/``
     - ``engine/``, ``core/``, ``schema/`` — never ``cli/`` or ``storage/``
   * - ``cli/``
     - All layers — top-level consumer only

.. warning::

   ``providers/`` must never import from ``core/`` or ``engine/``.
   Providers are schema-level plugins — they produce data, they do not
   evaluate it.

Data flow
---------

A standard FlameIQ comparison follows this data flow:

.. code-block:: text

   Benchmark tool output (any format)
           │
           ▼
   MetricProvider.load(source)
   ┌──────────────────────────┐
   │  collect() → raw dict    │  reads file, parses format
   │  validate() → bool       │  checks structure
   │  normalize() → Snapshot  │  maps to PerformanceSnapshot
   └──────────────────────────┘
           │
           ▼
   PerformanceSnapshot  ◄──── BaselineStore.load_baseline()
   (current)                          │
           │                          │ (PerformanceSnapshot from disk)
           ▼                          │
   compare_snapshots(baseline, current)
   ┌──────────────────────────────────────┐
   │  For each metric in baseline:        │
   │    compute_change_percent()          │
   │    evaluate_threshold()              │
   │    → MetricDiff                      │
   │  → ComparisonResult                  │
   └──────────────────────────────────────┘
           │
           ├──► CLI: print table / JSON output / exit code
           └──► HTMLGenerator: generate_report() → report.html

Design decisions
----------------

**Why dataclasses, not Pydantic?**
   The schema layer has zero external runtime dependencies. Using
   stdlib ``dataclasses`` keeps ``flameiq/schema/`` importable in any
   environment, including constrained embedded CI agents.

**Why JSON + JSONL for storage?**
   Human-readable, inspectable with any text editor, no migration
   tooling required, no database process to manage. History is
   append-only which makes corruption recovery trivial.

**Why scipy for statistics?**
   scipy's ``mannwhitneyu`` is a vetted, audited implementation of
   a well-understood algorithm. Rolling our own would introduce
   unverified floating-point behaviour.

**Why not async?**
   FlameIQ is a CLI tool. Async adds complexity with no benefit for
   sequential file I/O and in-memory computation.
