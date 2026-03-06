.. _security:

Security Policy
===============

Supported versions
------------------

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Version
     - Security fixes
   * - 1.x
     - ✅ Actively maintained

Reporting a vulnerability
--------------------------

**Do not open a public GitHub issue for security vulnerabilities.**

Send a detailed report to: **security@flameiq.dev**

Please include:

* A description of the vulnerability
* Steps to reproduce
* Potential impact assessment
* Suggested fix (if available)

We will acknowledge your report within **48 hours** and aim to release a
fix within **14 days** for critical issues.

Security model
--------------

FlameIQ OSS makes the following security guarantees:

**No network calls**
   The engine never makes outbound network connections. All operations
   are local filesystem only.

**No telemetry**
   Zero data is transmitted without explicit user action. FlameIQ
   collects no usage metrics, crash reports, or any other telemetry.

**No credentials required**
   FlameIQ OSS requires no API keys, tokens, or user accounts of any kind.

**Air-gap compatible**
   Fully functional with no internet access. Suitable for use in
   classified and restricted environments.

**Local storage only**
   All data is stored in ``.flameiq/`` in your project directory.
   Nothing is written outside this directory.

**Read-only providers**
   The provider layer is read-only. Providers may only read from their
   input source; they may never write files or make network calls.

Supply chain security
---------------------

FlameIQ's runtime dependencies are:

* ``click`` — CLI framework
* ``scipy`` — statistical computations (Mann-Whitney U)
* ``PyYAML`` — YAML configuration parsing

All dependencies are pinned with minimum versions in ``pyproject.toml``.
Lock files (``requirements.txt``) are provided for reproducible installs.
