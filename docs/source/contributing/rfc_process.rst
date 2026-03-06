.. _contributing_rfc:

RFC Process
===========

Major changes to FlameIQ require a formal RFC (Request for Comments)
before implementation begins.

When is an RFC required?
-------------------------

An RFC is required for:

* Any change to ``flameiq/schema/v1/`` (schema is immutable; v2 needs RFC)
* New statistical algorithms or changes to existing ones
* New baseline strategies
* Changes to CLI exit codes
* Changes to the threshold evaluation logic
* New top-level CLI commands
* Breaking changes to the public Python API

An RFC is **not** required for:

* Bug fixes
* Documentation improvements
* New providers (use a PR with the provider checklist)
* Dependency updates
* Performance improvements that do not change observable behaviour

RFC lifecycle
-------------

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Stage
     - Description
   * - **Draft**
     - Author opens a GitHub Discussion with ``[RFC]`` prefix
   * - **Discussion**
     - Community feedback, 7-day minimum comment period
   * - **Revised**
     - Author incorporates feedback and marks as ready for vote
   * - **Vote**
     - Maintainers vote. Requires two-thirds majority to pass.
   * - **Accepted**
     - RFC merged to ``docs/rfcs/``. Implementation may begin.
   * - **Rejected**
     - RFC closed with rationale documented.
   * - **Final**
     - Implementation complete and shipped.

RFC template
------------

.. code-block:: rst

   RFC-NNNN: <Title>
   ==================

   :Author:   <name>
   :Status:   Draft
   :Created:  YYYY-MM-DD

   Motivation
   ----------
   Why is this change needed? What problem does it solve?

   Proposed Change
   ---------------
   Precise description of what will change.

   Mathematical Specification
   ---------------------------
   (Required for algorithm changes.) Full formal specification.

   Backward Compatibility
   -----------------------
   What breaks? What migration is required?

   Alternatives Considered
   -----------------------
   What other approaches were evaluated and why were they rejected?

   Test Plan
   ---------
   How will the change be verified?
