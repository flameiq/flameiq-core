.. _index:

FlameIQ |release| Documentation
================================

.. image:: https://img.shields.io/pypi/v/flameiq-core.svg
   :target: https://pypi.org/project/flameiq-core/

.. image:: https://img.shields.io/pypi/pyversions/flameiq-core.svg
   :target: https://pypi.org/project/flameiq-core/

.. image:: https://img.shields.io/badge/license-Apache%202.0-blue.svg
   :target: https://github.com/flameiq/flameiq-core/blob/main/LICENSE

**Deterministic, CI-native performance regression and evolution engine.**

Make performance a first-class, enforceable engineering signal — without
requiring any SaaS platform, cloud account, or vendor dependency.

.. code-block:: bash

   pip install flameiq-core
   flameiq init
   flameiq baseline set --metrics benchmark.json
   flameiq compare --metrics current.json --fail-on-regression

   # v2 — performance evolution intelligence
   flameiq v2 run --metrics benchmark.json
   flameiq v2 baseline set
   flameiq v2 compare
   flameiq v2 trend --metric latency.p95 --last 30
   flameiq v2 drift
   flameiq v2 report

.. note::

   FlameIQ OSS requires **no internet connection**, **no account**, and **no
   API keys**. It is fully offline and air-gap compatible.

What is new in v2
-----------------

FlameIQ v2 extends v1 with a full performance evolution layer:

- **Persistent run history** — every run stored locally in SQLite
- **Drift detection** — catches gradual degradation across many commits
- **Time-travel comparison** — compare any two commits directly
- **Performance budgets** — enforce absolute metric ceilings (SLO enforcement)
- **Correlation analysis** — rule-based multi-metric cause-effect detection
- **Rich HTML reports** — trend charts, drift visualization, run history
- **Named baselines** — multiple named baselines with explicit promotion

v1 commands remain fully supported and backward compatible.

----

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting_started/installation
   getting_started/quickstart
   getting_started/ci_integration

.. toctree::
   :maxdepth: 2
   :caption: User Guides

   guides/configuration
   guides/baseline_strategies
   guides/custom_provider

.. toctree::
   :maxdepth: 2
   :caption: CLI Reference

   cli/reference
   cli/v2_reference

.. toctree::
   :maxdepth: 2
   :caption: Architecture

   architecture/overview
   architecture/layers
   architecture/schema

.. toctree::
   :maxdepth: 2
   :caption: Specifications

   specs/schema-v1
   specs/statistical-methodology
   specs/threshold-algorithm
   specs/exit-codes

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/schema
   api/core
   api/engine
   api/storage
   api/providers
   api/reporting
   api/v2/analysis
   api/v2/regression
   api/v2/storage
   api/v2/statistics

.. toctree::
   :maxdepth: 1
   :caption: Contributing

   contributing/development
   contributing/rfc_process
   contributing/testing_standards

.. toctree::
   :maxdepth: 1
   :caption: Project

   changelog
   security

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
