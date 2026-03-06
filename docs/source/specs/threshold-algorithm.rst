.. _spec_threshold_algorithm:

Threshold Algorithm Specification
====================================

:Status:   **Stable**
:Version:  1.0
:Module:   ``flameiq.core.thresholds``, ``flameiq.core.comparator``

This document specifies the threshold-based regression detection algorithm
used by FlameIQ's comparison engine. This is the **default and primary**
regression detection method.

Overview
--------

The threshold algorithm detects regressions by comparing the *signed
percentage change* between a baseline and current metric value against
a configured tolerance threshold.

It is:

* **Deterministic** — same input → same result, always
* **Efficient** — O(n) in the number of metrics
* **Configurable** — per-metric thresholds in ``flameiq.yaml``
* **Direction-aware** — different regression directions for different metric types

Step 1 — Compute change percent
---------------------------------

For each metric present in both the baseline and current snapshot:

.. math::

   \text{change\_percent} = \text{round}\!\left(
     \frac{(\text{current} - \text{baseline})}{\text{baseline}} \times 100,
     \; 4
   \right)

**Floating-point policy:** Rounded to **4 decimal places** using Python's
built-in ``round()`` for stable threshold comparisons.

**Zero baseline guard:** If ``baseline == 0``, the metric is skipped with
a warning. Division by zero is undefined behaviour and would produce
meaningless percentages.

Examples:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 40

   * - Baseline
     - Current
     - change_percent
     - Interpretation
   * - 100.0
     - 110.0
     - +10.0000
     - 10% increase
   * - 100.0
     - 90.0
     - −10.0000
     - 10% decrease
   * - 100.0
     - 100.0
     - 0.0000
     - No change
   * - 3.0
     - 4.0
     - +33.3333
     - 33.33% increase

Step 2 — Evaluate against threshold
--------------------------------------

The threshold evaluation depends on the *metric type*:

Higher-is-worse metrics
~~~~~~~~~~~~~~~~~~~~~~~

For metrics where an **increase** is a regression (latency, memory, CPU):

.. math::

   \text{is\_regression} = \text{change\_percent} > |\text{threshold}|

Example: ``latency.p95 = 10%`` threshold:

* ``change_percent = +12%`` → **REGRESSION** (12 > 10)
* ``change_percent = +10%`` → **PASS** (10 not > 10, exactly at threshold is pass)
* ``change_percent = −5%``  → **PASS** (improvement)

Metrics in this group: ``latency.mean``, ``latency.p50``, ``latency.p95``,
``latency.p99``, ``memory_mb``, ``cpu_percent``.

Lower-is-worse metrics
~~~~~~~~~~~~~~~~~~~~~~

For metrics where a **decrease** is a regression (throughput):

.. math::

   \text{is\_regression} = \text{change\_percent} < -|\text{threshold}|

Example: ``throughput = 5%`` threshold:

* ``change_percent = −8%``  → **REGRESSION** (−8 < −5)
* ``change_percent = −5%``  → **PASS** (−5 not < −5)
* ``change_percent = +20%`` → **PASS** (improvement)

Metrics in this group: ``throughput``.

Unknown / custom metrics
~~~~~~~~~~~~~~~~~~~~~~~~

For metrics not in either known group, **absolute deviation** is used:

.. math::

   \text{is\_regression} = |\text{change\_percent}| > |\text{threshold}|

This catches regressions in both directions for custom metrics.

Metrics in this group: All ``custom.*`` keys, and any metric not
explicitly listed in the above groups.

Step 3 — Warning detection
----------------------------

A metric in the WARNING state has not crossed its threshold but is
approaching it. The warning margin is configurable (default: 5
percentage points):

.. math::

   \text{is\_warning} = \neg\,\text{is\_regression}
     \;\wedge\; |\text{change\_percent}| \geq |\text{threshold}| - \text{margin}
     \;\wedge\; |\text{change\_percent}| > 0

Example with threshold = 10%, margin = 5%:

* ``change_percent = +9%`` → WARNING (9 ≥ 10−5=5, not yet regression)
* ``change_percent = +4%`` → PASS (4 < 5)

Threshold format
----------------

Thresholds in ``flameiq.yaml`` are **percent strings**:

.. code-block:: text

   "10%"    →   float 10.0
   "-5%"    →   float -5.0
   "2.5%"   →   float 2.5

The regex used for parsing:

.. code-block:: text

   ^(-?\d+(?:\.\d+)?)%$

Numeric values (``int`` or ``float``) are also accepted directly
(useful when building threshold configs programmatically).

Default threshold
-----------------

If no threshold is configured for a metric, the default is applied:

.. code-block:: python

   DEFAULT_THRESHOLD_PERCENT = 10.0

This means any metric with no explicit configuration allows up to 10%
absolute deviation before triggering a regression.

Overall status
--------------

The comparison result status is determined as:

.. math::

   \text{status} =
   \begin{cases}
     \text{REGRESSION} & \text{if any metric is\_regression} \\
     \text{PASS}       & \text{otherwise}
   \end{cases}

.. note::

   The current implementation does not set status to WARNING at the
   result level — individual ``MetricDiff.is_warning`` flags are set,
   but the result ``status`` is either PASS or REGRESSION. This matches
   the CI exit code semantics (warnings do not fail the build).
