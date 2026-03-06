.. _architecture_schema:

Schema Design
=============

The schema layer (``flameiq/schema/v1/``) is the foundation of the
entire FlameIQ system. It defines the data contract that all other
layers depend on.

Versioning philosophy
---------------------

FlameIQ uses explicit schema versioning. Every snapshot carries a
``schema_version`` field. Version 1 is **stable and immutable**:

* Fields are **never removed** or **renamed** in v1
* New optional fields may be added in minor releases (1.0.x → 1.1.x)
* Breaking changes require a new schema version (v2)

This guarantees that a baseline stored today will always be readable
by a future version of FlameIQ.

Why dataclasses?
----------------

The schema layer uses only Python's standard library ``dataclasses``.
This is a deliberate design choice:

* Zero external runtime dependencies
* Importable in any Python 3.10+ environment
* Human-readable ``to_dict()`` / ``from_dict()`` serialisation
* Frozen instances discourage mutation after construction

The ``flat()`` method
---------------------

``Metrics.flat()`` returns a single ``dict[str, float]`` of all non-null
metric values. This is the canonical representation used by the
comparison engine.

.. code-block:: python

   metrics = Metrics(
       latency=LatencyMetrics(mean=100.0, p95=150.0),
       throughput=1000.0,
       memory_mb=512.0,
   )
   metrics.flat()
   # {
   #   "latency.mean": 100.0,
   #   "latency.p95":  150.0,
   #   "throughput":  1000.0,
   #   "memory_mb":   512.0,
   # }

The dotted key format (``latency.p95``) is the universal identifier
used in threshold configuration, comparison results, and HTML reports.
