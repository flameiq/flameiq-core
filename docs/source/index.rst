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

.. note::

   FlameIQ OSS requires **no internet connection**, **no account**, and **no
   API keys**. It is fully offline and air-gap compatible.

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
