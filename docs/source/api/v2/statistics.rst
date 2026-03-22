.. _api_v2_statistics:

flameiq.v2.statistics — Statistics Engine
==========================================

The v2 statistics engine is a complete stdlib-only reimplementation
of all statistical algorithms. No scipy dependency in v2.

All algorithms are deterministic: same input → same output, always.

.. automodule:: flameiq.v2.statistics.engine
   :members: percent_change, mann_whitney_u, bootstrap_mean_ci,
             cohens_d, effect_label, variance_ratio, summarize,
             detect_drift, DriftResult
   :noindex:

Design notes
------------

**stdlib-only**
   v2 eliminates the scipy runtime dependency. All algorithms are
   implemented from first principles using Python's ``math`` and
   ``random`` (seeded) modules only.

**Deterministic bootstrap**
   :func:`bootstrap_mean_ci` uses a fixed seed (``seed=42`` by default)
   so the confidence interval is identical on every run given the same
   input data.

**Mann-Whitney U normal approximation**
   The U statistic is computed exactly (O(n×m)) and the p-value is
   derived via the normal approximation using ``math.erf``. Valid for
   n, m ≥ 8; conservative for smaller samples.

**Drift via linear regression**
   :func:`detect_drift` fits a linear model to the time series using
   ordinary least squares (pure Python, no numpy). R² ≥ 0.30 is
   required alongside the cumulative threshold to reduce false positives
   from noisy data.
