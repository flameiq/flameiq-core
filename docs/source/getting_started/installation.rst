.. _installation:

Installation
============

Requirements
------------

* **Python** 3.10, 3.11, or 3.12
* No external services, accounts, or API keys required
* No system-level dependencies

Install from PyPI
-----------------

.. code-block:: bash

   pip install flameiq-core

Verify the installation:

.. code-block:: bash

   flameiq --version
   # flameiq, version 1.0.0

   flameiq --help
   flameiq v2 --help

Install in a virtual environment (recommended)
-----------------------------------------------

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate.bat       # Windows

   pip install flameiq-core
   flameiq --version

Install with optional dependencies
-----------------------------------

.. code-block:: bash

   # Include pytest-benchmark adapter
   pip install flameiq-core

   # Development (ruff, mypy, pre-commit, build, twine)
   pip install "flameiq-core[dev]"

   # Testing (pytest, pytest-cov, hypothesis)
   pip install "flameiq-core[test]"

   # Documentation (sphinx, sphinx-rtd-theme)
   pip install "flameiq-core[docs]"

   # All extras
   pip install "flameiq-core[dev,test,docs]"

Install from source
-------------------

.. code-block:: bash

   git clone https://github.com/flameiq/flameiq-core.git
   cd flameiq-core
   pip install -e ".[dev,test,docs]"

Offline / air-gap installation
-------------------------------

FlameIQ has **zero runtime network requirements**. To install in an
air-gapped environment:

.. code-block:: bash

   # On a connected machine — download wheel and all dependencies:
   pip download flameiq-core --dest ./flameiq-packages

   # Transfer ./flameiq-packages/ to the air-gapped system, then:
   pip install flameiq-core \
       --no-index \
       --find-links ./flameiq-packages

Upgrading
---------

.. code-block:: bash

   pip install --upgrade flameiq-core

.. note::

   FlameIQ follows `Semantic Versioning <https://semver.org/>`_.
   Patch releases (1.0.x) are backwards-compatible bug fixes only.
   Minor releases (1.x.0) add features in a backwards-compatible manner.
   Major releases (x.0.0) may introduce breaking changes.

Uninstalling
------------

.. code-block:: bash

   pip uninstall flameiq-core

   # Also remove local FlameIQ data (baselines, history):
   rm -rf .flameiq/

v1 vs v2
--------

Both v1 and v2 commands are available after installation. v1 commands
are stable and unchanged. v2 commands are accessible under the ``v2``
subgroup:

.. code-block:: bash

   # v1 commands — unchanged
   flameiq init
   flameiq baseline set --metrics benchmark.json
   flameiq compare --metrics current.json --fail-on-regression

   # v2 commands — new
   flameiq v2 run --metrics benchmark.json
   flameiq v2 baseline set
   flameiq v2 compare
   flameiq v2 trend --metric latency.p95
   flameiq v2 drift
   flameiq v2 history
   flameiq v2 report
