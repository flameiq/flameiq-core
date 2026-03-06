.. _statistical_methodology:

Statistical Methodology Specification
=======================================

:Status:    **Stable**
:Version:   1.0
:Module:    ``flameiq.engine.statistics``
:Spec file: ``specs/statistical-methodology.rst``

This document is the authoritative mathematical specification for all
statistical algorithms used in FlameIQ. Any change to an algorithm
described here requires a formal RFC. See ``RFC_PROCESS.md``.

.. note::

   All algorithms described here are **deterministic**: given identical
   inputs, they always produce identical outputs. No random seeds. No
   sampling. No time-dependent logic.

Overview
--------

FlameIQ provides two regression detection modes:

1. **Threshold-based** (default) — direct percentage comparison against
   configured thresholds. See :ref:`spec_threshold_algorithm`.

2. **Statistical mode** (optional) — adds the Mann-Whitney U test for
   significance testing. Use when benchmark noise is high enough that
   threshold crossings alone are unreliable.

Statistical mode is enabled via ``flameiq.yaml``:

.. code-block:: yaml

   statistics:
     enabled: true
     confidence: 0.95

Mann-Whitney U Test
-------------------

Background
~~~~~~~~~~

The Mann-Whitney U test is a non-parametric significance test that
makes **no assumptions about the underlying distribution**. It is
particularly well-suited for latency data, which is typically:

* Right-skewed (long tail of slow requests)
* Non-normal (bimodal distributions are common)
* Sensitive to outliers

Reference:
  Mann, H. B., & Whitney, D. R. (1947). On a test of whether one of
  two random variables is stochastically larger than the other.
  *Annals of Mathematical Statistics*, 18(1), 50–60.

Hypothesis
~~~~~~~~~~

:Null hypothesis H₀: The baseline and current distributions are identical.

:Alternative hypothesis H₁: The current distribution tends to produce
  **larger** values than the baseline distribution (one-tailed).

Using a one-tailed test reflects the engineering question: *"Is this
metric getting worse?"* A two-tailed test would also flag improvements
as significant, which is not useful for regression detection.

Significance decision
~~~~~~~~~~~~~~~~~~~~~

A regression is declared **statistically significant** if:

.. math::

   p\text{-value} < \alpha

where:

.. math::

   \alpha = 1 - \text{confidence\_level}

With the default ``confidence_level = 0.95``, this gives
:math:`\alpha = 0.05`.

Implementation
~~~~~~~~~~~~~~

FlameIQ uses ``scipy.stats.mannwhitneyu`` with ``alternative="greater"``:

.. code-block:: python

   _, p_value = scipy.stats.mannwhitneyu(
       current_samples,     # first argument = "greater" group
       baseline_samples,
       alternative="greater",
   )

The p-value is cast to Python ``float`` (from numpy scalar) and rounded
to 6 decimal places for stable serialisation.

Minimum samples
~~~~~~~~~~~~~~~

The test requires at least **3 samples** per group (``MINIMUM_SAMPLES = 3``).
If either group has fewer samples, :class:`~flameiq.core.errors.InsufficientSamplesError`
is raised.

Effect Size — Cohen's *d*
--------------------------

Cohen's *d* quantifies the **magnitude** of the difference, independent
of sample size. It complements the p-value, which only measures significance.

Formula
~~~~~~~

.. math::

   d = \frac{\bar{x}_2 - \bar{x}_1}{s_p}

where :math:`\bar{x}_1` and :math:`\bar{x}_2` are the sample means of
the baseline and current groups respectively, and :math:`s_p` is the
pooled standard deviation:

.. math::

   s_p = \sqrt{
     \frac{(n_1 - 1)\,s_1^2 \;+\; (n_2 - 1)\,s_2^2}
          {n_1 + n_2 - 2}
   }

**Sign convention:** Positive *d* means current > baseline (a potential
regression for higher-is-worse metrics).

If :math:`s_p = 0` (all measurements identical), Cohen's *d* is defined
as ``0.0``.

Verbal labels (Cohen 1988 conventions)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - :math:`|d|`
     - Label
   * - :math:`< 0.2`
     - **Negligible** — practically meaningless
   * - :math:`0.2 \leq d < 0.5`
     - **Small** — noticeable in controlled experiments
   * - :math:`0.5 \leq d < 0.8`
     - **Medium** — practically significant
   * - :math:`\geq 0.8`
     - **Large** — practically very significant

Reference:
  Cohen, J. (1988). *Statistical Power Analysis for the Behavioral
  Sciences* (2nd ed.). Lawrence Erlbaum Associates.

Noise-resistant Median
-----------------------

Formula
~~~~~~~

Given *n* samples :math:`x_1, x_2, \ldots, x_n`:

1. Optionally discard the first *k* samples (warmup runs):
   :math:`x_{k+1}, x_{k+2}, \ldots, x_n`

2. Sort the remaining samples:
   :math:`x_{(1)} \leq x_{(2)} \leq \ldots \leq x_{(n-k)}`

3. Compute the median:

.. math::

   \text{median} =
   \begin{cases}
     x_{(m+1)}                          & \text{if } (n-k) \text{ is odd} \\[6pt]
     \dfrac{x_{(m)} + x_{(m+1)}}{2}    & \text{if } (n-k) \text{ is even}
   \end{cases}

where :math:`m = \lfloor (n-k) / 2 \rfloor`.

Use cases
~~~~~~~~~

The median is used by the ``rolling_median`` baseline strategy:

.. code-block:: python

   baseline_p95 = noise_filter_median(
       [snap.metrics.latency.p95 for snap in last_N_snapshots]
   )

The median is preferred over the mean for benchmark data because it is:

* Robust to outliers (a single spike does not distort it)
* Stable under bimodal distributions
* More representative of typical performance than the mean

Determinism guarantees
-----------------------

All algorithms in this specification satisfy:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Property
     - Guarantee
   * - No random state
     - No ``random`` module. No seeds.
   * - No time-dependent logic
     - Timestamps are arguments, never ``datetime.now()``
   * - Explicit floating-point policy
     - ``change_percent`` rounded to 4 d.p.; p-value to 6 d.p.
   * - scipy determinism
     - ``mannwhitneyu`` is a closed-form computation, not stochastic
   * - Sorted median
     - ``sorted()`` in Python is a stable, deterministic sort

The FlameIQ test suite verifies determinism with 100-repetition runs:

.. code-block:: python

   results = [mann_whitney_compare(baseline, current) for _ in range(100)]
   assert all(r.p_value == results[0].p_value for r in results)
