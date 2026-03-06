.. _baseline_strategies:

Baseline Strategies
===================

A *baseline strategy* determines which historical snapshot is used as the
reference point when comparing a new run. FlameIQ v1.0 provides three
strategies, each suited to different workflows.

Overview
--------

.. list-table::
   :header-rows: 1
   :widths: 25 40 35

   * - Strategy
     - How it selects the baseline
     - Best for
   * - ``last_successful``
     - Most recently stored snapshot
     - Simple projects, low-noise CI
   * - ``rolling_median``
     - Median of the last *N* snapshots
     - Shared CI runners, noisy benchmarks
   * - ``tagged``
     - Snapshot with a specific release tag
     - Release-to-release comparisons

last_successful
---------------

Uses the single most recent snapshot saved via ``flameiq baseline set``.

This is the default and simplest strategy. On every merge to ``main``,
the baseline advances to the latest measurements.

.. code-block:: yaml

   baseline:
     strategy: last_successful

**Workflow:**

.. code-block:: text

   main branch:
     commit A → flameiq baseline set  →  baseline = A
     commit B → flameiq baseline set  →  baseline = B
     ...

   PR branch:
     current commit → flameiq compare → compared against B (latest)

**Characteristics:**

* Deterministic: same baseline file → same result
* Sensitive to one-off performance spikes on ``main``
* Requires ``flameiq baseline set`` to be run on every main commit

rolling_median
--------------

Computes a **synthetic baseline** from the median values across the last
*N* snapshots. This filters out one-off measurement noise that can
cause false regressions or false passes.

.. code-block:: yaml

   baseline:
     strategy: rolling_median
     rolling_window: 5

**How the synthetic baseline is computed:**

For each metric key (e.g. ``latency.p95``), FlameIQ collects the values
from the last *N* stored snapshots and computes the median:

.. math::

   \text{baseline}_{key} = \text{median}(v_1, v_2, \ldots, v_N)

The synthetic snapshot uses the most recent snapshot's metadata
(commit, branch, tags) and is marked with
``tags["flameiq_synthetic"] = "rolling_median"``.

**Choosing a window size:**

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Window
     - Guidance
   * - 3
     - Minimal smoothing. Responsive to real changes.
   * - 5 *(default)*
     - Balanced. Recommended for most projects.
   * - 10
     - Heavy smoothing. Good for very noisy CI.

**Characteristics:**

* Immune to single outlier runs
* Requires at least *N* prior runs before becoming fully effective
* The first run after ``flameiq init`` uses only 1 snapshot regardless

tagged
------

Uses a snapshot explicitly tagged with a label such as ``"v1.0.0"``.
All subsequent comparisons are made against that fixed point, regardless
of how many other baselines have been set in between.

**Tag a release:**

.. code-block:: bash

   # After your v1.0.0 release:
   flameiq baseline set \
     --metrics release_v1.0.0.json \
     --tag v1.0.0

**Compare PRs against v1.0.0:**

.. code-block:: yaml

   baseline:
     strategy: tagged
     # FlameIQ will search history for any snapshot tagged "v1.0.0"

**Characteristics:**

* Pinned reference — comparisons are always against the same baseline
* Ideal for ``main`` development comparing against a release tag
* Requires ``--tag`` to have been used when setting the baseline

Switching strategies
--------------------

You can switch strategies at any time by editing ``flameiq.yaml``. The
strategy only affects how ``flameiq compare`` selects the baseline — all
stored history is retained.

.. code-block:: bash

   # Change strategy by editing flameiq.yaml, then re-run comparison:
   flameiq compare --metrics current.json --fail-on-regression

The new strategy takes effect immediately.
