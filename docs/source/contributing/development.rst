.. _contributing_development:

Development Setup
=================

Prerequisites
-------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Tool
     - Version
   * - Python
     - 3.10, 3.11, or 3.12
   * - Git
     - 2.30+
   * - pip
     - 23.0+

Setup steps
-----------

.. code-block:: bash

   # 1. Fork and clone
   git clone https://github.com/<your-fork>/flameiq-core.git
   cd flameiq-core

   # 2. Create a virtual environment
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   # .venv\Scripts\activate    # Windows

   # 3. Install all dependencies
   pip install -e ".[dev,test,docs]"

   # 4. Install pre-commit hooks
   pre-commit install
   pre-commit install --hook-type commit-msg

   # 5. Verify the setup
   make check

Running the tests
-----------------

.. code-block:: bash

   make test              # Full suite with coverage
   make test-unit         # Fast unit tests only
   make test-statistical  # Statistical + determinism tests

Linting and type checking
--------------------------

.. code-block:: bash

   make lint              # ruff check
   make format            # ruff format + ruff check --fix
   make typecheck         # mypy --strict

Commit conventions
------------------

FlameIQ uses `Conventional Commits <https://www.conventionalcommits.org/>`_:

.. code-block:: text

   feat(engine): add bootstrapped confidence intervals
   fix(comparator): guard against NaN baseline values
   docs(specs): clarify Mann-Whitney one-tailed rationale
   test(storage): add corruption recovery test
   perf(engine): vectorise median computation
   refactor(cli): extract shared JSON output helper
   chore(deps): bump scipy to 1.12

Types: ``feat``, ``fix``, ``docs``, ``test``, ``perf``,
``refactor``, ``chore``, ``ci``, ``build``.

Branch naming
-------------

.. code-block:: text

   feat/engine-bootstrap-ci
   fix/nan-baseline-guard
   docs/statistical-methodology
   refactor/cli-json-helper
   rfc/schema-v2-design
