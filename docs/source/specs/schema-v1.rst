.. _spec_schema_v1:

FlameIQ Performance Schema — Version 1
=========================================

:Status:    **Stable / Production**
:Version:   1
:Stability: Immutable — no breaking changes will ever be made to v1
:Released:  2026-03-01

This document is the authoritative specification for the FlameIQ v1
performance snapshot schema. It defines the data format, field semantics,
validation rules, and serialisation contract.

Overview
--------

A *performance snapshot* is a structured, versioned record of benchmark
measurements captured during a single run. Snapshots are:

* **Immutable by convention** — do not mutate after construction
* **Self-describing** — carry their own schema version
* **Serialisable** — round-trip through JSON without loss of information
* **Minimal** — contain only what is needed for comparison

JSON structure
--------------

.. code-block:: json

   {
     "schema_version": 1,
     "metadata": {
       "run_id":      "550e8400-e29b-41d4-a716-446655440000",
       "commit":      "abc123def456",
       "branch":      "feature/my-change",
       "timestamp":   "2026-01-01T10:00:00+00:00",
       "environment": "ci",
       "tags":        { "pr": "42", "runner": "ubuntu-22" }
     },
     "metrics": {
       "latency": {
         "mean": 120.5,
         "p50":  110.0,
         "p95":  180.0,
         "p99":  240.0
       },
       "throughput":  950.2,
       "memory_mb":   512.0,
       "cpu_percent":  73.4,
       "custom": {
         "tokens_per_second": 1250.0,
         "db_query_ms":          8.5
       }
     }
   }

Field reference
---------------

``schema_version``
~~~~~~~~~~~~~~~~~~

:Type:     integer
:Required: yes
:Value:    Always ``1`` for v1 snapshots.

Must be validated on deserialisation. If the value is not ``1``, raise
:class:`~flameiq.core.errors.SchemaVersionError`.

``metadata``
~~~~~~~~~~~~

:Type:     object
:Required: no (defaults applied if absent)

Contextual information about the run. All sub-fields are optional.

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - ``run_id``
     - string
     - UUID4 identifying this specific run. Auto-generated if absent.
   * - ``commit``
     - string | null
     - Git commit hash (short or full SHA). ``null`` if not in a git repo.
   * - ``branch``
     - string | null
     - Git branch name. ``null`` if not available.
   * - ``timestamp``
     - string
     - ISO 8601 UTC datetime. Auto-generated if absent.
       Example: ``"2026-01-01T10:00:00+00:00"``
   * - ``environment``
     - string enum
     - One of: ``"ci"``, ``"local"``, ``"staging"``, ``"custom"``.
       Unknown values map to ``"custom"``. Default: ``"ci"``.
   * - ``tags``
     - object
     - Arbitrary ``string → string`` key-value pairs for user metadata.
       Maximum 50 entries. Keys and values must be strings.

``metrics``
~~~~~~~~~~~

:Type:     object
:Required: yes
:Constraint: Must contain at least one non-empty sub-object or non-null value.

``metrics.latency``
^^^^^^^^^^^^^^^^^^^

:Type:     object
:Required: no

All values are in **milliseconds** and must be non-negative.
At least one sub-field must be provided if the ``latency`` key is present.

.. list-table::
   :header-rows: 1
   :widths: 15 15 70

   * - Field
     - Type
     - Description
   * - ``mean``
     - float
     - Arithmetic mean latency in milliseconds.
   * - ``p50``
     - float
     - 50th percentile (median) latency in milliseconds.
   * - ``p95``
     - float
     - 95th percentile latency. **Primary regression signal.**
       Recommended for all threshold configurations.
   * - ``p99``
     - float
     - 99th percentile (tail) latency. Use to catch worst-case regressions.

``metrics.throughput``
^^^^^^^^^^^^^^^^^^^^^^

:Type:     float
:Required: no
:Unit:     Requests or operations per second.
:Constraint: Must be non-negative.

``metrics.memory_mb``
^^^^^^^^^^^^^^^^^^^^^

:Type:     float
:Required: no
:Unit:     Megabytes (peak resident memory).
:Constraint: Must be non-negative.

``metrics.cpu_percent``
^^^^^^^^^^^^^^^^^^^^^^^

:Type:     float
:Required: no
:Unit:     CPU utilisation percentage, range 0–100.
:Constraint: Must be in [0, 100].

``metrics.custom``
^^^^^^^^^^^^^^^^^^

:Type:     object (``string → float``)
:Required: no

User-defined numeric metrics. Keys must be non-empty strings and must not
contain the ``.`` separator character (reserved for flat key paths).
Values must be non-negative floats.

Example:

.. code-block:: json

   "custom": {
     "tokens_per_second": 1250.0,
     "db_query_ms": 8.5,
     "cache_hit_rate": 0.94
   }

These are addressable in thresholds as ``custom.tokens_per_second``, etc.

Flat key format
---------------

The comparison engine uses a *flat key format* to address individual
metric values. The flat key space is derived from the nested JSON:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Flat key
     - Source field
   * - ``latency.mean``
     - ``metrics.latency.mean``
   * - ``latency.p50``
     - ``metrics.latency.p50``
   * - ``latency.p95``
     - ``metrics.latency.p95``
   * - ``latency.p99``
     - ``metrics.latency.p99``
   * - ``throughput``
     - ``metrics.throughput``
   * - ``memory_mb``
     - ``metrics.memory_mb``
   * - ``cpu_percent``
     - ``metrics.cpu_percent``
   * - ``custom.<name>``
     - ``metrics.custom.<name>``

These flat keys are used in ``flameiq.yaml`` threshold configuration,
comparison result diffs, and HTML reports.

Validation rules
----------------

A snapshot is valid if and only if all of the following hold:

1. ``schema_version == 1``
2. ``metrics`` is present and non-empty
3. At least one metric value is non-null
4. All numeric values are non-negative finite floats
5. ``metadata.environment`` is one of the allowed enum values (unknown
   values are coerced to ``"custom"`` rather than raising an error)
6. ``metadata.timestamp`` parses as a valid ISO 8601 datetime

Serialisation contract
-----------------------

The ``to_dict()`` / ``from_dict()`` pair must satisfy the round-trip
property:

.. code-block:: python

   snapshot == PerformanceSnapshot.from_dict(snapshot.to_dict())

The following normalisation is applied during ``from_dict()``:

* Missing ``metadata`` → all defaults applied
* Missing ``run_id`` → new UUID4 generated
* Missing ``timestamp`` → current UTC time
* Unknown ``environment`` → coerced to ``"custom"``
* ``"Z"`` timezone suffix → replaced with ``"+00:00"`` before parsing

Changelog
---------

Version 1.0 (2026-03-01)
~~~~~~~~~~~~~~~~~~~~~~~~~

* Initial stable release.
* Fields: ``schema_version``, ``metadata``, ``metrics``
  (``latency``, ``throughput``, ``memory_mb``, ``cpu_percent``, ``custom``).
