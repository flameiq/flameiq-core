============
Contributing
============

Thank you for contributing to FlameIQ. This document covers everything
you need to set up, work on, test, and submit changes.

.. contents:: Table of Contents
   :depth: 2
   :local:

----

Before you start
================

1. **Check existing issues** — search GitHub Issues before opening a new one
2. **Open an issue first** for non-trivial changes — discuss the approach
   before writing code
3. **Read the RFC process** for major changes (algorithm changes, schema
   changes, CLI changes)

Development setup
=================

Prerequisites: Python 3.10+, Git 2.30+.

.. code-block:: bash

   # Fork and clone
   git clone https://github.com/<your-fork>/flameiq-core.git
   cd flameiq-core

   # Virtual environment
   python -m venv .venv
   source .venv/bin/activate

   # Install all dependencies
   pip install -e ".[dev,test,docs]"

   # Install pre-commit hooks
   pre-commit install
   pre-commit install --hook-type commit-msg

   # Verify setup
   make check

Makefile reference
==================

.. code-block:: text

   make install          Install all dependencies
   make test             Full test suite with coverage
   make test-unit        Unit tests only (fast)
   make test-statistical Statistical + determinism tests
   make lint             ruff check
   make format           ruff format + ruff fix
   make typecheck        mypy --strict
   make check            lint + typecheck + tests
   make docs             Build Sphinx documentation
   make clean            Remove all build artefacts

Code standards
==============

Architecture rules
------------------

1. ``schema/`` has **no** internal imports
2. ``core/`` imports **only** ``schema/``
3. ``engine/`` imports ``core/`` and ``schema/`` only
4. ``storage/`` imports ``core/`` and ``schema/`` only
5. ``providers/`` imports **only** ``schema/`` — never ``core/`` or ``engine/``
6. ``reporting/`` imports ``engine/``, ``core/``, ``schema/`` — never ``cli/``
7. ``cli/`` may import all layers — it is the **only** top-level consumer

Style
-----

- **ruff** for linting and formatting (line length: 100)
- **mypy --strict** — all code must pass strict type checking
- **Google-style docstrings** on all public functions and classes
- No bare ``print()`` in library code — use ``logging``
- No hardcoded paths — use ``pathlib.Path``
- Never raise ``Exception`` — always raise from the error hierarchy

Determinism requirements
------------------------

Any function in ``core/`` or ``engine/`` must be **deterministic**:

- No ``random`` module without a fixed seed
- No ``datetime.now()`` — pass timestamps as arguments
- No network calls
- Explicit floating-point rounding (see the comparator's policy)
- Must pass a 100-repetition determinism test

Commit message format
=====================

FlameIQ uses `Conventional Commits <https://www.conventionalcommits.org/>`_:

.. code-block:: text

   <type>(<scope>): <description>

   [optional body]

Types: ``feat``, ``fix``, ``docs``, ``test``, ``perf``,
``refactor``, ``chore``, ``ci``, ``build``.

Examples::

   feat(engine): add bootstrapped confidence intervals
   fix(comparator): guard against NaN baseline values
   docs(specs): clarify Mann-Whitney one-tailed rationale
   test(storage): add history corruption recovery test

Pull request process
====================

1. Create a branch from ``main``: ``feat/<description>``
2. Write code and tests (see coverage requirements below)
3. Run ``make check`` — all checks must pass
4. Push and open a PR against ``main``
5. Respond to review within 5 days
6. Squash-merge when approved

Coverage requirements
=====================

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Module
     - Minimum
     - Notes
   * - ``core/``
     - 95%
     - Critical — all branches must be tested
   * - ``schema/``
     - 100%
     - Every field, every validation path
   * - ``engine/``
     - 90%
     - Known-input statistical tests required
   * - ``storage/``
     - 85%
     - Include corruption recovery
   * - ``providers/``
     - 80%
     - Valid / invalid / missing file per provider
   * - ``cli/``
     - 75%
     - Integration tests count toward coverage

RFC process
===========

Major changes require a formal RFC before implementation:

- Schema changes (v2, new fields)
- Algorithm changes (comparator, statistics)
- CLI exit code changes
- Breaking public API changes

Open a GitHub Discussion with ``[RFC]`` prefix and use the template
in ``docs/source/contributing/rfc_process.rst``.

Getting help
============

- **GitHub Discussions** — questions, ideas, design discussions
- **GitHub Issues** — bug reports, feature requests
- Look for ``good first issue`` and ``help wanted`` labels

License
=======

By contributing, you agree that your contributions will be licensed
under the **Apache License 2.0**.
